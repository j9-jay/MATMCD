"""API 요청 없이 실제 기본 embedding resolver와 SDK 객체 생성만 점검한다."""
import asyncio
import importlib.metadata
import inspect
import json
import os
import socket
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from project_paths import ASSETS, PROJECT, SOURCE, asset_path
from setup_chromadb import sha


def main():
    if sys.platform != "linux" or sys.prefix != str(asset_path("environment")):
        raise SystemExit("기존 WSL 실험 환경의 Python으로 실행하세요.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = ASSETS / "logs/openai_embeddings_runtime" / stamp
    log_dir.mkdir(parents=True, exist_ok=False)
    original = {str(p.relative_to(SOURCE)): sha(p) for p in SOURCE.rglob("*") if p.is_file()}
    attempts = []

    def denied(*args, **kwargs):
        attempts.append("network request denied")
        raise RuntimeError("embedding local check: network disabled")

    async def async_denied(*args, **kwargs):
        return denied()

    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.create_connection = denied
    # Only this standalone probe process is changed. Do not inspect or store credentials.
    for name in ("IS_TESTING", "OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_BASE_URL",
                 "OPENAI_API_VERSION", "OPENAI_ORG_ID", "OPENAI_PROJECT_ID"):
        os.environ.pop(name, None)
    report = {"checked_utc": stamp, "experiments_executed": False, "model_api_calls": False,
              "embeddings_generated": False, "network_connections_denied": attempts,
              "log_directory": str(log_dir.relative_to(ASSETS)), "checks": {}}
    client = aclient = None
    try:
        import httpx
        httpx.Client.send = denied
        httpx.AsyncClient.send = async_denied
        import openai
        openai.api_key = None
        openai.base_url = None
        openai.api_version = None
        from llama_index.core import Settings
        from llama_index.core.base.embeddings.base import BaseEmbedding
        from llama_index.core.embeddings.utils import resolve_embed_model
        from llama_index.embeddings.openai import OpenAIEmbedding
        import llama_index.embeddings.openai.base as adapter_base
        import llama_index.embeddings.openai.utils as adapter_utils

        report["versions"] = {name: importlib.metadata.version(name) for name in
                              ("llama-index-embeddings-openai", "llama-index-core", "openai", "httpx", "pydantic")}
        assert report["versions"]["llama-index-embeddings-openai"] == "0.3.1"
        report["checks"]["import"] = True
        report["adapter_source_sha256"] = {
            "base.py": sha(Path(adapter_base.__file__)), "utils.py": sha(Path(adapter_utils.__file__))}
        try:
            resolve_embed_model("default")
        except ValueError as exc:
            assert "No API key found for OpenAI" in str(exc)
            report["missing_key_error"] = str(exc)
            report["checks"]["missing_key_is_separate_access_blocker"] = True
        else:
            raise AssertionError("Default resolver unexpectedly accepted absent credentials")

        # Dummy text permits object construction; it is never sent or persisted as config.
        os.environ["OPENAI_API_KEY"] = "sk-local-object-construction-only-not-a-real-key"
        embedding = resolve_embed_model("default")
        assert isinstance(embedding, OpenAIEmbedding) and isinstance(embedding, BaseEmbedding)
        assert isinstance(Settings.embed_model, OpenAIEmbedding)
        report["checks"]["core_default_resolver_and_settings"] = True
        report["probe_credentials"] = "dummy string in this process only; no authentication request"
        defaults = {name: getattr(embedding, name) for name in
                    ("model_name", "embed_batch_size", "dimensions", "max_retries", "timeout",
                     "reuse_client", "num_workers", "additional_kwargs", "api_base", "api_version")}
        defaults["constructor_mode"] = inspect.signature(OpenAIEmbedding).parameters["mode"].default
        defaults["query_engine"] = embedding._query_engine
        defaults["text_engine"] = embedding._text_engine
        report["observed_local_defaults"] = defaults
        report["checks"]["model_not_overridden"] = (
            defaults["model_name"] == defaults["query_engine"] == defaults["text_engine"] == "text-embedding-ada-002")
        assert report["checks"]["model_not_overridden"]
        client, aclient = embedding._get_client(), embedding._get_aclient()
        assert isinstance(client, openai.OpenAI) and isinstance(aclient, openai.AsyncOpenAI)
        assert embedding._get_client() is client and embedding._get_aclient() is aclient
        assert client.max_retries == aclient.max_retries == defaults["max_retries"]
        assert client.timeout == aclient.timeout == defaults["timeout"]
        assert str(client.base_url).rstrip("/") == str(aclient.base_url).rstrip("/") == defaults["api_base"]
        report["checks"]["sync_async_sdk_construction_and_reuse"] = True
        report["sdk_classes"] = [f"{type(obj).__module__}.{type(obj).__name__}" for obj in (client, aclient)]
        assert not attempts, attempts
        report["success"] = True
    except Exception:
        report["success"] = False
        report["error"] = traceback.format_exc()
    finally:
        if client is not None:
            client.close()
        if aclient is not None:
            asyncio.run(aclient.close())
        os.environ.pop("OPENAI_API_KEY", None)
    current_source = {str(p.relative_to(SOURCE)): sha(p) for p in SOURCE.rglob("*") if p.is_file()}
    report["official_source_unchanged"] = current_source == original
    report["official_file_count"] = len(original)
    report["success"] = report["success"] and report["official_source_unchanged"] and not attempts
    report["limitations"] = [
        "Object construction only; no embedding, HTTP request, authentication or real API response tested",
        "Author adapter version, server model snapshot, tokenizer and numerical output remain unverified",
        "Missing API credentials/access remain ACCESS-01; default model was observed, not selected or overridden",
    ]
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (log_dir / "report.json").write_text(text, encoding="utf-8")
    (PROJECT / "docs/evidence/openai_embeddings_runtime.json").write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
