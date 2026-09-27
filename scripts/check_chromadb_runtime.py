"""설치된 Chroma/LangChain의 로컬 동작만 점검한다. 논문 실험이 아니다."""
import json
import math
import os
import socket
import sys
import traceback
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT


def main():
    if sys.platform != "linux":
        raise SystemExit("WSL의 실험 환경 Python으로 실행하세요.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = ASSETS / "logs/chromadb_runtime" / stamp
    log_dir.mkdir(parents=True, exist_ok=False)
    os.chdir(log_dir)
    # 아래 설정은 이 점검 프로세스에만 적용한다. 실제 실험 설정을 바꾸지 않는다.
    os.environ.update(ANONYMIZED_TELEMETRY="False", PYTHONDONTWRITEBYTECODE="1",
                      XDG_CACHE_HOME=str(ASSETS / "caches/library_cache"))
    attempts = []

    def denied(*args, **kwargs):
        attempts.append("socket connection denied")
        raise RuntimeError("Chroma local check: network disabled")

    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.create_connection = denied
    report = {"checked_utc": stamp, "experiments_executed": False, "model_api_calls": False,
              "test_vectors_only": True, "network_connections_denied": attempts,
              "log_directory": str(log_dir.relative_to(ASSETS)), "checks": {}}
    try:
        import importlib.metadata
        import chromadb
        from chromadb.config import Settings
        from langchain.embeddings.base import Embeddings
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.vectorstores import Chroma

        report["versions"] = {name: importlib.metadata.version(name) for name in
                              ("chromadb", "langchain", "langchain-community", "protobuf", "posthog", "opentelemetry-proto")}
        report["checks"]["imports"] = True
        texts = ["local-probe-a", "local-probe-b", "local-probe-c"]
        vectors = [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0], [-1.0, 0.0, 0.0]]
        ids = ["probe-a", "probe-b", "probe-c"]
        metadata = [{"url": "https://example.invalid/" + name} for name in ids]
        client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
        collection = client.create_collection("matmcd-dep01-native-check", embedding_function=None)
        collection.upsert(ids=ids, embeddings=vectors, documents=texts, metadatas=metadata)
        assert collection.count() == 3
        result = collection.query(query_embeddings=[vectors[0]], n_results=2,
                                  include=["documents", "metadatas", "distances"])
        assert result["ids"] == [["probe-a", "probe-b"]], result
        assert math.isclose(result["distances"][0][0], 0.0, abs_tol=1e-6)
        assert math.isclose(result["distances"][0][1], 0.02, abs_tol=1e-6)
        report["checks"]["native_store_query"] = True
        report["native_result"] = result
        report["native_collection_configuration"] = collection.configuration
        client.delete_collection("matmcd-dep01-native-check")

        class ProbeVectors(Embeddings):
            """인공 벡터를 반환하는 점검 전용 adapter. 논문의 임베딩 대체물이 아니다."""

            def embed_documents(self, documents):
                return [vectors[texts.index(text)] for text in documents]

            def embed_query(self, query):
                if query != "local-probe-query":
                    raise ValueError("unknown probe query")
                return vectors[0]

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        documents = splitter.create_documents(texts, metadatas=metadata)
        # 공식 코드와 같은 from_documents -> as_retriever -> get_relevant_documents 경로.
        store = Chroma.from_documents(documents, ProbeVectors(), collection_name="matmcd-dep01-langchain-check")
        retriever = store.as_retriever(search_kwargs={"k": 2})
        found = retriever.get_relevant_documents("local-probe-query")
        assert [doc.page_content for doc in found] == texts[:2]
        assert [doc.metadata for doc in found] == metadata[:2]
        report["checks"]["langchain_store_retrieve"] = True
        report["langchain_result"] = [{"text": doc.page_content, "metadata": doc.metadata} for doc in found]
        report["langchain_collection_configuration"] = store._collection.configuration
        store.delete_collection()
        assert not attempts, attempts
        report["checks"]["no_python_socket_connections"] = True
        report["success"] = True
    except Exception:
        report["success"] = False
        report["error"] = traceback.format_exc()
    report["limitations"] = ["Tiny component fixture, not the paper experiment",
                             "No live OpenAI embeddings, web retrieval, full pipeline or author-version comparison",
                             "Socket guard covers Python sockets; test uses local in-memory APIs and telemetry is disabled"]
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (log_dir / "report.json").write_text(text, encoding="utf-8")
    (PROJECT / "docs/evidence/chromadb_runtime.json").write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
