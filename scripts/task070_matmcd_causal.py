"""TASK_070 MATMCD reference baseline on the category-2 causal benchmarks.

Follows the released GTdatasets_experiment.py for each dataset: official PC ->
ConstrainNormalAgent without information (CC-agent only) -> released DA-agent web
collection (collect_web_content, Serper, loop_num=5) -> released dataset summary ->
MATMCD (use_reasoning=False) -> MATMCD-R (use_reasoning=True), each followed by
official PC with the constraints and the official metrics.

Official functions and classes are executed unchanged (byte-checked) with local
dependencies injected, as in the category-1 adapter: the approved local Qwen model
replaces gpt-4 / gpt-4o-mini, BGE-M3 replaces text-embedding-ada-002, and the
Serper key is read from MATMCD_DATA/secrets (never logged).

User decision 2026-10-22 (A):
  1. The released query prompt asks for "Search Query: <question>" but the released
     parser looks for "Search Question". The query-generation response is bridged
     by renaming only that line prefix; raw and bridged texts are both recorded.
  2. The released script loads MATMCD/MATMCD-R explanations from a cache that a
     fresh run does not have; explanations are generated fresh (use_cache=False).
User decision 2026-10-22 (vector store): the released retriever looks up each
retrieved chunk's URL in the current search's link list, so it assumes a fresh
Chroma store per search. With the installed chromadb 1.0.11 (not pinned in the
released requirements) Chroma.from_documents reuses one in-process collection, and
the second search retrieved first-search pages (run 20261022T093804Z failed on
this). Each search now gets its own new collection; nothing else changes.
Everything else follows the release: no Tavily key exists, so a search error that
would fall back to Tavily is recorded as a failure. Approved sampling profile as
in category 1: explanations presence_penalty 1.5, other calls the base profile.

Usage: python -B task070_matmcd_causal.py [--datasets ...]
"""
import argparse
import json
import os
import re
import time
from datetime import datetime, timezone

import numpy as np

import local_rca_components as lrc
import task070_causal as tcd
import task070_metrics as tm
import task070_output_head as oh
from continue_rca_oracle30 import normalize_rag_response
from project_paths import ASSETS, SOURCE
from task070_common import WORK, assert_official_files, write_json
from task070_matmcd import _accept_relationship_heading

DATASETS = ["Auto_MPG", "DWD_climate", "Sachs", "asia", "child"]
OFFICIAL = ["GTdatasets_experiment.py", "Web_tools.py", "web_utils/serper_service.py", "web_utils/web_crawler.py",
            "web_utils/fetch_web_content.py", "web_utils/retrieval.py", "web_utils/llm_answer.py",
            "web_utils/config/config.yaml", "ConstrainAgent/LLMs.py", "ConstrainAgent/ConstrainAgent.py",
            "config.py", "Utils/CausalDiscovery.py", "Utils/data.py", "Utils/metrics.py"]
KEY_PATH = ASSETS / "secrets/serper_api_key.txt"
_QUERY_LINE = re.compile(r"(?m)^(\s*)Search Query:")


class NoTavily:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("Released code fell back to Tavily; no Tavily key is configured (recorded, no fallback)")


class SerperUsage:
    """requests stand-in for SerperClient only: counts searches and keeps responses."""
    def __init__(self, directory):
        import requests
        self._requests = requests
        self.directory = directory
        self.count = 0

    def request(self, method, url, headers=None, data=None):
        self.count += 1
        response = self._requests.request(method, url, headers=headers, data=data, timeout=60)
        (self.directory / f"serper_{self.count:03d}.json").write_text(
            json.dumps({"request": json.loads(data), "status": response.status_code, "response": response.json()},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        return response


class KeyedYaml:
    """yaml stand-in: the released config.yaml with the Serper key filled in."""
    def __init__(self):
        import yaml
        self._yaml = yaml
        self.key = KEY_PATH.read_text(encoding="utf-8").strip()

    def safe_load(self, handle):
        config = self._yaml.safe_load(handle)
        config["serper_api_key"] = self.key
        return config


class FreshChroma:
    """Chroma stand-in for the released retriever: a new collection per search
    (the counter is shared across datasets so names never repeat in a process)."""
    count = 0

    def __init__(self):
        from langchain_community.vectorstores import Chroma
        self._chroma = Chroma

    def from_documents(self, documents, embedding):
        FreshChroma.count += 1
        return self._chroma.from_documents(documents, embedding, collection_name=f"matmcd_search_{FreshChroma.count:03d}")


class QueryBridge:
    """Decision A-1: only the 'Search Query:' line prefix becomes 'Search Question:'."""
    def __init__(self, client, log):
        self.client = client
        self.log = log

    def inquire_LLMs(self, prompt, system_prompt, temperature=0.5):
        raw = self.client.inquire_LLMs(prompt, system_prompt, temperature=temperature)
        bridged = _QUERY_LINE.sub(r"\1Search Question:", raw)
        self.log.append({"raw": raw, "bridged": bridged, "changed": raw != bridged})
        return bridged


def web_functions(client, encoder, query_log, usage):
    """Released Web_tools.search_web / collect_web_content and web_utils classes."""
    import threading
    import requests
    from bs4 import BeautifulSoup
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.prompts import PromptTemplate
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from local_embedding import langchain_embedding

    keyed = KeyedYaml()
    ns = lambda rel, extra: {"os": os, "__file__": str(SOURCE / rel), **extra}

    class LocalChat:
        """ChatOpenAI stand-in: the released call llm([HumanMessage]) with its temperature."""
        def __init__(self, model_name=None, openai_api_key=None, temperature=0.7, streaming=False, callbacks=None):
            self.temperature = temperature

        def __call__(self, messages):
            converted = [{"role": "user", "content": m.content} for m in messages]
            return AIMessage(content=client.inquire_messages(converted, temperature=self.temperature))

    serper = lrc.extract("web_utils/serper_service.py", {"SerperClient"},
                         ns("web_utils/serper_service.py", {"json": json, "re": re, "requests": usage, "yaml": keyed}))
    crawler = lrc.extract("web_utils/web_crawler.py", {"WebScraper"},
                          {"re": re, "requests": requests, "BeautifulSoup": BeautifulSoup})
    fetcher = lrc.extract("web_utils/fetch_web_content.py", {"WebContentFetcher"},
                          {"threading": threading, "time": time, **serper, **crawler})
    retrieval = lrc.extract("web_utils/retrieval.py", {"EmbeddingRetriever"},
                            ns("web_utils/retrieval.py", {"yaml": keyed, "Chroma": FreshChroma(),
                                                          "RecursiveCharacterTextSplitter": RecursiveCharacterTextSplitter,
                                                          "OpenAIEmbeddings": lambda **kw: langchain_embedding(encoder)}))
    answer = lrc.extract("web_utils/llm_answer.py", {"GPTAnswer"},
                         ns("web_utils/llm_answer.py", {"time": time, "yaml": keyed, "ChatOpenAI": LocalChat,
                                                        "StreamingStdOutCallbackHandler": lambda: None,
                                                        "PromptTemplate": PromptTemplate, "HumanMessage": HumanMessage}))
    return lrc.extract("Web_tools.py", {"search_web", "collect_web_content"},
                       {"os": os, "WebContentFetcher": fetcher["WebContentFetcher"],
                        "EmbeddingRetriever": retrieval["EmbeddingRetriever"], "GPTAnswer": answer["GPTAnswer"],
                        "OpenAIClient": lambda *a, **kw: QueryBridge(client, query_log),
                        "OPENAI_API_KEY": "unused-local-dispatch", "TAVILY_API_KEY": "", "TavilyClient": NoTavily})


def run_dataset(name, directory, encoder):
    from local_embedding import llamaindex_embedding
    from local_llm_runtime import CONFIG
    from rca_local_client import RecordedLocalClient, llamaindex_local_llm

    theme = tcd.THEMES[name]
    values, truth, labels = tcd.load(name)
    labels = list(labels)
    base = {k: CONFIG["smoke_test"][k] for k in ("top_p", "top_k", "min_p", "presence_penalty")}
    client = RecordedLocalClient(directory / "calls", max_tokens=8192, seed=42, sampling=base)
    record = {"dataset": name, "labels": labels, "results": {}, "stages": {}}
    started = time.monotonic()
    cwd = os.getcwd()
    usage = SerperUsage(directory)
    query_log = []
    try:
        initial = oh.fit_graph(values, labels)
        np.save(directory / "PC.npy", initial)
        record["results"]["pc_only"] = tm.graph_metrics(initial, truth)
        Agent = lrc.official_agent_class(client, re_audit=lambda event: None)

        def agent_run(phase, **info):
            agent = Agent(labels, theme, graph_matrix=initial, causal_discovery_algorithm="pc", **info)
            if "node_information" in info:
                agent.domain_knowledge_LLM.generate_prompt(0, 1, info["node_information"])
            client.phase = f"{phase}_domain"
            client.sampling = dict(base, presence_penalty=1.5)
            try:
                agent.generate_domain_knowledge(use_cache=False, cache_path=str(directory / "domain_cache" / phase))
            finally:
                client.sampling = base
            client.phase = f"{phase}_constraints"
            constraints = agent.generate_constrain_matrix()
            np.save(directory / f"{phase}_constraints.npy", constraints)
            graph = oh.fit_graph(values, labels, constraints)
            np.save(directory / f"{phase}.npy", graph)
            record["results"][phase] = tm.graph_metrics(graph, truth)
            write_json(directory / "result.json", record)

        # Released order: CC-agent without information first.
        agent_run("CC_agent", use_reasoning=False)

        # DA-agent web collection and summary, run inside the dataset folder so the
        # released relative cache paths stay there.
        os.chdir(directory)
        (directory / "cache/Summarized_info").mkdir(parents=True)
        web = web_functions(client, encoder, query_log, usage)
        client.phase = "DA_agent_web"
        try:
            web["collect_web_content"](name, labels, loop_num=5, use_tavily=False)
        finally:
            record["stages"]["web"] = {"serper_searches": usage.count, "query_responses": query_log}
        client.phase = "DA_agent_summary"
        summary = lrc.original_dataset_summary(llamaindex_embedding(encoder),
                                               llamaindex_local_llm(client, context_window=CONFIG["server"]["context_tokens"]))
        raw = summary["generate_dataset_summary"](name, labels, output_dir="./cache/Summarized_info",
                                                  embeddings_path="./cache/RAG_Database/Embeddings", save_embeddings=True)
        heading_fixed = _accept_relationship_heading(raw)
        canonical, _, _, audit = normalize_rag_response(heading_fixed, labels)
        audit["relationship_heading_variant_accepted"] = heading_fixed != raw
        data_info, node_info = summary["split_summary_into_sub_questions"](canonical)
        record["stages"]["summary"] = {"format_audit": audit, "nodes_parsed": sorted(node_info)}
        write_json(directory / "node_information.json", {"dataset_information": data_info, "node_information": node_info})
        os.chdir(cwd)

        agent_run("MATMCD", dataset_information=data_info, node_information=node_info, use_reasoning=False)
        agent_run("MATMCD_R", dataset_information=data_info, node_information=node_info, use_reasoning=True)
        record["status"] = "COMPLETE"
    except Exception as error:
        record.update(status="FAILED", error=f"{type(error).__name__}: {error}")
    finally:
        os.chdir(cwd)
        client.close()
        record.update(seconds=time.monotonic() - started, generation_calls=client.counter, serper_searches=usage.count)
        write_json(directory / "result.json", record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", default=DATASETS)
    args = parser.parse_args()
    hashes = assert_official_files(OFFICIAL)
    lrc.assert_original_source = lambda: assert_official_files(OFFICIAL)
    out = WORK / "matmcd_causal" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True)
    from local_embedding import DenseBGE
    from task070_pilot import start_server, stop_server
    encoder = DenseBGE()
    summary = {"official_sha256": hashes, "decision": "user 2026-10-22 option A", "datasets": {}}
    proc, log = start_server(out / "server.log")
    try:
        for name in args.datasets:
            directory = out / name
            directory.mkdir()
            record = run_dataset(name, directory, encoder)
            summary["datasets"][name] = {k: record.get(k) for k in
                                         ("status", "error", "results", "seconds", "generation_calls", "serper_searches")}
            write_json(out / "summary.json", summary)
            print(name, json.dumps(summary["datasets"][name], default=str), flush=True)
    finally:
        stop_server(proc, log)
    print(out)


if __name__ == "__main__":
    main()
