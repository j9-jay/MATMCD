"""Validate approved CPU BGE-M3 and original retrieval paths using synthetic text only."""
import ast
import json
import os
import resource
import socket
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from local_embedding import CONFIG, CONFIG_PATH, DenseBGE, EmbeddingLengthError, index_directory, langchain_embedding, llamaindex_embedding
from project_paths import ASSETS, PROJECT, SOURCE
from setup_chromadb import pins
from setup_graphviz import assert_original_source, python_packages, source_hashes, system_packages, write_json
from setup_local_llm import asset, sha256


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    logs = asset(CONFIG["storage"]["log_directory"]) / (stamp + "_validation")
    logs.mkdir(parents=True, exist_ok=False)
    os.chdir(logs)
    os.environ.update(ANONYMIZED_TELEMETRY="False", PYTHONDONTWRITEBYTECODE="1",
                      TIKTOKEN_CACHE_DIR=str(asset(CONFIG["runtime"]["splitter_cache_directory"])),
                      XDG_CACHE_HOME=str(ASSETS / "caches/library_cache"))
    before_python, before_source, before_system = python_packages(), source_hashes(), system_packages()
    before_llm = sha256(PROJECT / "configs/local_llm.json")
    before_path = list(sys.path)
    report = {"timestamp_utc": stamp, "status": "IN_PROGRESS", "profile": CONFIG["profile"],
              "log_directory": logs.relative_to(ASSETS).as_posix(), "checks": {}, "events": [],
              "paid_api_calls": 0, "web_search_calls": 0, "generation_calls": 0,
              "experiments_executed": False, "paper_equivalence": False,
              "config_sha256": sha256(CONFIG_PATH),
              "script_hashes": {p.name: sha256(p) for p in [Path(__file__), PROJECT / "scripts/local_embedding.py"]}}
    for snapshot in (CONFIG_PATH, Path(__file__), PROJECT / "scripts/local_embedding.py"):
        (logs / snapshot.name).write_bytes(snapshot.read_bytes())
    denied_connections = []
    def denied(*args, **kwargs):
        denied_connections.append("Python socket connection blocked")
        raise RuntimeError("Offline embedding validation: network disabled")
    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.create_connection = denied

    def checkpoint():
        write_json(logs / "report.json", report)

    def check(name, detail):
        report["checks"][name] = detail
        print("PASS: " + name, flush=True)
        checkpoint()

    started = time.monotonic()
    try:
        assert_original_source()
        expected = pins((PROJECT / "docs/evidence/installed_freeze_with_openai_embeddings.txt").read_text())
        assert before_python == expected and len(before_python) == 201
        engine = DenseBGE(audit_callback=report["events"].append)
        check("model_cpu_fp32_batch1", engine.loading)
        import numpy as np
        texts = [
            "A database connection timeout prevents checkout requests from completing.",
            "A garden contains roses and apple trees.",
            "데이터베이스 연결 시간 초과로 결제 요청이 실패했습니다.",
        ]
        vectors = np.asarray(engine.encode(texts))
        assert vectors.shape == (3, 1024) and np.isfinite(vectors).all()
        assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5)
        repeated = np.asarray(engine.encode([texts[0]], kind="query"))[0]
        assert np.array_equal(vectors[0], repeated)
        check("dense_dimensions_norm_and_query_document_identity", {"shape": list(vectors.shape), "norms": np.linalg.norm(vectors, axis=1).tolist(), "repeat_exact": True})
        np.save(logs / "synthetic_vectors.npy", vectors)
        too_long = "database " * 8200
        forward_before = engine.forward_calls
        try:
            engine.encode([too_long])
        except EmbeddingLengthError as exc:
            assert engine.forward_calls == forward_before
            check("overlength_rejected_before_inference", {"error": str(exc), "extra_forward_calls": 0})
        else:
            raise AssertionError("Overlength input was not rejected")

        # Execute the unchanged original web retriever method; substitute only its embedding constructor.
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.vectorstores import Chroma
        from chromadb.config import Settings as ChromaSettings
        tree = ast.parse((SOURCE / "web_utils/retrieval.py").read_text())
        original_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EmbeddingRetriever")
        ns = {"os": os, "yaml": __import__("yaml"), "__file__": str(SOURCE / "web_utils/retrieval.py"),
              "RecursiveCharacterTextSplitter": RecursiveCharacterTextSplitter, "Chroma": Chroma,
              "OpenAIEmbeddings": lambda **kwargs: langchain_embedding(engine)}
        exec(compile(ast.Module(body=[original_class], type_ignores=[]), str(SOURCE / "web_utils/retrieval.py"), "exec"), ns)
        retriever = ns["EmbeddingRetriever"]()
        corpus = [texts[0], "The sky is blue and clouds carry rain.", "Bread is baked with flour and water.",
                  "A violin is a musical instrument.", "The moon orbits Earth.", "A bicycle has two wheels.",
                  "Paintings are displayed in a museum.", "A train travels between cities.", "A river flows into the sea.",
                  "A sunflower grows from a seed.", "Fish swim in a lake.", "A carpet covers the floor."]
        urls = [f"https://example.invalid/synthetic/{i}" for i in range(len(corpus))]
        docs = retriever.text_splitter.create_documents(corpus, metadatas=[{"url": u} for u in urls])
        assert retriever.TOP_K == 10 and retriever.text_splitter._chunk_size == 1000 and retriever.text_splitter._chunk_overlap == 0
        assert [d.page_content for d in docs] == corpus
        found = retriever.retrieve_embeddings(corpus, urls, corpus[0])
        assert len(found) == 10 and found[0].page_content == corpus[0] and found[0].metadata["url"] == urls[0]
        check("original_web_retriever_top10", {"chunk_size_characters": 1000, "chunk_overlap": 0,
                                              "returned": len(found), "top_url": found[0].metadata["url"]})
        # Persist/reload a separate collection with an explicit model identity.
        chroma_dir = index_directory("synthetic_chroma_" + stamp)
        chroma = Chroma.from_documents(docs[:2], langchain_embedding(engine), collection_name="synthetic-bge-m3",
                                      persist_directory=str(chroma_dir), client_settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True))
        reloaded = Chroma(collection_name="synthetic-bge-m3", embedding_function=langchain_embedding(engine),
                          persist_directory=str(chroma_dir), client_settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True))
        assert reloaded.similarity_search(corpus[0], k=1)[0].page_content == corpus[0]
        check("chroma_profile_isolation_and_reload", {"directory": chroma_dir.relative_to(ASSETS).as_posix(), "count": reloaded._collection.count(), "configuration": reloaded._collection.configuration})

        from llama_index.core import Document, VectorStoreIndex, StorageContext, load_index_from_storage
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.core import Settings as LlamaSettings
        splitter = LlamaSettings.node_parser
        assert isinstance(splitter, SentenceSplitter) and splitter.chunk_size == 1024 and splitter.chunk_overlap == 200
        # A long synthetic passage verifies the existing default splitter instead of shrinking to 512.
        long_text = " ".join(f"Service component {i} reports a database connection timeout." for i in range(180))
        summary_docs = [Document(text=long_text, id_="synthetic-long"), Document(text=corpus[1], id_="synthetic-sky")]
        nodes = splitter.get_nodes_from_documents(summary_docs)
        lengths = [engine.token_length(n.get_content(metadata_mode="embed")) for n in nodes]
        assert len(nodes) > 2 and max(lengths) > 512 and max(lengths) <= 8192
        adapter = llamaindex_embedding(engine)
        index = VectorStoreIndex.from_documents(summary_docs, embed_model=adapter)
        retrieved = index.as_retriever().retrieve(corpus[1])
        assert index.as_retriever().similarity_top_k == 2 and len(retrieved) == 2
        assert retrieved[0].node.ref_doc_id == "synthetic-sky"
        summary_dir = index_directory("synthetic_llamaindex_" + stamp)
        index.storage_context.persist(persist_dir=str(summary_dir))
        loaded = load_index_from_storage(StorageContext.from_defaults(persist_dir=str(summary_dir)), embed_model=adapter)
        again = loaded.as_retriever().retrieve(corpus[1])
        assert [r.node.node_id for r in again] == [r.node.node_id for r in retrieved]
        assert np.allclose([r.score for r in again], [r.score for r in retrieved])
        check("llamaindex_default_split_top2_and_reload", {"chunk_size_original_tokenizer": splitter.chunk_size,
               "chunk_overlap_original_tokenizer": splitter.chunk_overlap, "node_count": len(nodes),
               "bge_token_lengths": lengths, "top_k": 2, "directory": summary_dir.relative_to(ASSETS).as_posix(),
               "scores": [r.score for r in retrieved], "summary_generation": False})
        # Demonstrate that wrong index identity is rejected without changing a real index.
        wrong = asset(CONFIG["storage"]["index_directory"]) / ("synthetic_incompatible_" + stamp)
        wrong.mkdir()
        write_json(wrong / "embedding_profile.json", {"profile": "different-model-test-fixture"})
        try:
            index_directory(wrong.name)
        except RuntimeError:
            check("incompatible_index_rejected", True)
        else:
            raise AssertionError("Incompatible index accepted")
        assert not denied_connections and not engine.torch.cuda.is_initialized()
        report["forward_calls"] = engine.forward_calls
        report["status"] = "PASS"
    except Exception:
        report["status"] = "FAILED"
        report["error"] = traceback.format_exc()
        print(report["error"], flush=True)
    sys.path[:] = before_path
    report["seconds"] = time.monotonic() - started
    report["peak_process_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    report["network_connections_denied"] = denied_connections
    report["preservation"] = {"base_python_201_unchanged": before_python == python_packages(),
                              "official_37_unchanged": before_source == source_hashes(),
                              "system_packages_unchanged": before_system == system_packages(),
                              "qwen_config_unchanged": before_llm == sha256(PROJECT / "configs/local_llm.json")}
    if not all(report["preservation"].values()):
        report["status"] = "FAILED"
    report["limitations"] = ["Synthetic component validation only, not real RCA or retrieval quality evaluation",
                             "CPU batch 1 tested only at recorded lengths, not all 8192-token inputs or concurrent Qwen",
                             "Python socket guard plus local_files_only/offline settings; not a system-wide network firewall",
                             "No actual web search, generated summary, RCA rankings, logs/RWR changes or scientific equivalence claim"]
    checkpoint()
    evidence = PROJECT / "docs/evidence/local_embedding_runtime.json"
    if evidence.exists():
        (logs / "previous_report.json").write_bytes(evidence.read_bytes())
    write_json(evidence, report)
    print(json.dumps({k: report[k] for k in ("status", "seconds", "peak_process_rss_mib", "preservation", "log_directory")}), flush=True)
    return int(report["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
