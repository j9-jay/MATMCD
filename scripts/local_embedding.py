"""Explicit, offline BGE-M3 dense adapters. Never changes global LlamaIndex settings."""
import hashlib
import importlib.metadata
import json
import os
import re
import sys
import threading
import time
from pathlib import Path

from project_paths import ASSETS, PROJECT
from setup_local_llm import asset, sha256

CONFIG_PATH = PROJECT / "configs/local_embedding.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


class EmbeddingLengthError(ValueError):
    """Input exceeds the pinned model capacity; no truncation was performed."""


def activate_loader():
    """Add only the two verified loader packages to this process's import path."""
    overlay = asset(CONFIG["runtime"]["overlay_directory"])
    manifest = json.loads((overlay / "matmcd_overlay_manifest.json").read_text())
    expected = {p["name"]: p["version"] for p in CONFIG["runtime"]["packages"]}
    if manifest["packages"] != expected:
        raise RuntimeError("Embedding loader package manifest differs")
    for name in expected:
        if name in sys.modules and not Path(sys.modules[name].__file__).resolve().is_relative_to(overlay):
            raise RuntimeError(f"Another {name} was already imported")
    if str(overlay) not in sys.path:
        sys.path.insert(0, str(overlay))
    for name, version in expected.items():
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"Unexpected loader version: {name}")
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                      TOKENIZERS_PARALLELISM="false", HF_HOME=str(asset(CONFIG["runtime"]["cache_directory"])),
                      TIKTOKEN_CACHE_DIR=str(asset(CONFIG["runtime"]["splitter_cache_directory"])))


class DenseBGE:
    """Official CLS + L2 dense encoding, CPU float32, one unmodified text at a time."""

    def __init__(self, *, audit_callback=None):
        activate_loader()
        import torch
        from transformers import AutoModel, AutoTokenizer

        model = CONFIG["model"]
        policy = CONFIG["encoding"]
        if (policy["device"], policy["dtype"], policy["batch_size"], policy["pooling"], policy["normalize_l2"]) != ("cpu", "float32", 1, "cls", True):
            raise RuntimeError("This adapter implements only the approved CPU FP32 dense profile")
        if policy["sparse"] or policy["colbert"] or policy["truncation"] or policy["query_instruction"] or policy["document_instruction"]:
            raise RuntimeError("Unapproved encoding mode")
        directory = asset(model["directory"])
        install = json.loads((PROJECT / "docs/evidence/local_embedding_install.json").read_text())
        if install["status"] != "INSTALLED_NOT_YET_RUNTIME_VERIFIED" or install["config_sha256"] != sha256(CONFIG_PATH):
            raise RuntimeError("Run the pinned installer before loading")
        for entry in install["files"]:
            path = asset(entry["path"])
            if path.is_relative_to(directory) and sha256(path) != entry["sha256"]:
                raise RuntimeError(f"Model artifact changed: {path.name}")
        pooling = json.loads((directory / "1_Pooling/config.json").read_text())
        if not pooling["pooling_mode_cls_token"] or any(v for k, v in pooling.items() if k.startswith("pooling_mode_") and k != "pooling_mode_cls_token"):
            raise RuntimeError("Official pooling config differs")
        modules = json.loads((directory / "modules.json").read_text())
        if modules[-1]["type"] != "sentence_transformers.models.Normalize":
            raise RuntimeError("Official normalization module differs")
        self.torch = torch
        self.audit_callback = audit_callback
        self.forward_calls = 0
        self.lock = threading.RLock()
        torch.set_num_threads(policy["torch_threads"])
        self.tokenizer = AutoTokenizer.from_pretrained(str(directory), use_fast=True, local_files_only=True, trust_remote_code=False)
        if not self.tokenizer.is_fast or self.tokenizer.model_max_length != policy["max_tokens_including_special"]:
            raise RuntimeError("Pinned tokenizer capacity differs")
        started = time.monotonic()
        self.model, loading = AutoModel.from_pretrained(
            str(directory), local_files_only=True, trust_remote_code=False, use_safetensors=False,
            weights_only=True, torch_dtype=torch.float32, attn_implementation=policy["attention_implementation"],
            output_loading_info=True)
        if any(loading.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
            raise RuntimeError(f"Checkpoint loading differs: {loading}")
        self.model.to("cpu").eval()
        if {p.dtype for p in self.model.parameters()} != {torch.float32} or {p.device.type for p in self.model.parameters()} != {"cpu"}:
            raise RuntimeError("Model device/dtype differs")
        self.loading = {"seconds": time.monotonic() - started, "loading_info": loading,
                        "parameters": sum(p.numel() for p in self.model.parameters()),
                        "device": "cpu", "dtype": "float32", "batch_size": 1,
                        "torch_threads": torch.get_num_threads(),
                        "attention_implementation": self.model.config._attn_implementation,
                        "cuda_initialized": torch.cuda.is_initialized()}

    def token_length(self, text):
        if not isinstance(text, str):
            raise TypeError("Embedding input must be text")
        return len(self.tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"])

    def encode(self, texts, *, kind="document"):
        if isinstance(texts, str) or kind not in ("query", "document"):
            raise TypeError("Provide a sequence of texts and query/document kind")
        results = []
        for text in texts:
            with self.lock:
                if not isinstance(text, str):
                    raise TypeError("Embedding input must be text")
                tokens = self.tokenizer(text, add_special_tokens=True, truncation=False, return_tensors="pt")
                length = tokens["input_ids"].shape[1]
                event = {"kind": kind, "input_sha256": hashlib.sha256(text.encode()).hexdigest(),
                         "characters": len(text), "tokens_including_special": length,
                         "batch_size": 1, "truncated": False, "status": "IN_PROGRESS"}
                if length > CONFIG["encoding"]["max_tokens_including_special"]:
                    event["status"] = "REJECTED_LENGTH"
                    if self.audit_callback:
                        self.audit_callback(event)
                    raise EmbeddingLengthError(f"BGE-M3 input has {length} tokens including special tokens; maximum 8192; input unchanged")
                started = time.monotonic()
                with self.torch.inference_mode():
                    hidden = self.model(**tokens).last_hidden_state
                    vector = self.torch.nn.functional.normalize(hidden[:, 0], p=2, dim=1)[0]
                self.forward_calls += 1
                if vector.shape != (CONFIG["encoding"]["dimensions"],) or not bool(self.torch.isfinite(vector).all()):
                    raise RuntimeError("Invalid dense vector")
                results.append(vector.tolist())
                event.update(status="ENCODED", seconds=time.monotonic() - started,
                             l2_norm=float(vector.norm()), dimensions=len(results[-1]))
                if self.audit_callback:
                    self.audit_callback(event)
        return results


def langchain_embedding(engine):
    from langchain_core.embeddings import Embeddings

    class LocalBGEEmbeddings(Embeddings):
        def embed_documents(self, texts):
            return engine.encode(texts, kind="document")

        def embed_query(self, text):
            return engine.encode([text], kind="query")[0]

    return LocalBGEEmbeddings()


def llamaindex_embedding(engine):
    from llama_index.core.base.embeddings.base import BaseEmbedding
    from pydantic import PrivateAttr

    class LocalBGEEmbedding(BaseEmbedding):
        _engine: object = PrivateAttr()

        def __init__(self):
            super().__init__(model_name=f'{CONFIG["model"]["repository"]}@{CONFIG["model"]["revision"]}:dense:cpu:fp32', embed_batch_size=1)
            self._engine = engine

        def _get_query_embedding(self, query):
            return self._engine.encode([query], kind="query")[0]

        def _get_text_embedding(self, text):
            return self._engine.encode([text], kind="document")[0]

        async def _aget_query_embedding(self, query):
            return self._get_query_embedding(query)

        async def _aget_text_embedding(self, text):
            return self._get_text_embedding(text)

    return LocalBGEEmbedding()


def index_directory(name):
    """Claim an explicitly named index for this exact embedding configuration."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Index name must contain only letters, digits, underscore or hyphen")
    directory = asset(CONFIG["storage"]["index_directory"]) / name
    marker = directory / "embedding_profile.json"
    identity = {"profile": CONFIG["profile"], "model": CONFIG["model"]["repository"],
                "revision": CONFIG["model"]["revision"], "config_sha256": sha256(CONFIG_PATH),
                "weights_sha256": CONFIG["model"]["weights_sha256"], "encoding": CONFIG["encoding"]}
    if directory.exists():
        if not marker.exists() or json.loads(marker.read_text()) != identity:
            raise RuntimeError("Existing index has absent or incompatible embedding identity")
    else:
        directory.mkdir(parents=True, exist_ok=False)
        marker.write_text(json.dumps(identity, indent=2) + "\n")
    return directory
