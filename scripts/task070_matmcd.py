"""TASK_070 MATMCD reference baseline on RCAEval RE2-OB (category 1).

Same local pipeline as the completed LEMMA 30-pod run, applied to a RE2-OB case:
official PC -> official log-summary prompt per service (D-7 adapter: masked
templates in the released template/structured layout) -> official LlamaIndex
dataset summary over the summaries (BGE-M3, local LLM) -> TASK_051 heading
normalization + official parser -> official ConstrainNormalAgent explanations
and constraints -> official PC with constraints -> shared RWR/metrics.

Kept from the approved LEMMA profile: Qwen local model, log-summary and
explanation presence_penalty 1.5 (D07, TASK_052), released temperatures,
released graph-prompt behaviour (D03 A). Services without logs get the approved
D01 absence notice. No retries, truncation or fallbacks; failures are recorded.
"""
import json
import time

import numpy as np

import local_rca_components as lrc
import task070_corpus as tc
import task070_rcaeval as rc
from continue_rca_oracle30 import normalize_rag_response
from project_paths import PROJECT
from task070_common import assert_official_files

THEME = "MicroService system about Online Boutique"
OFFICIAL = ["ConstrainAgent/LLMs.py", "ConstrainAgent/ConstrainAgent.py", "config.py", "Log_tools.py",
            "Web_tools.py", "Utils/CausalDiscovery.py", "Utils/RCA.py"]
POLICY = json.loads((PROJECT / "configs/rca_log_policy.json").read_text(encoding="utf-8"))
KPI_NOTICE = ("This is an input KPI column (p90 request latency of the frontend), not a service. "
              "No service event log is assigned to this column.")


def _check_sources():
    hashes = assert_official_files(OFFICIAL)
    # local_rca_components still guards with the 37-file LEMMA check; replace it
    # with an equivalent byte check of exactly the files this pipeline uses.
    lrc.assert_original_source = lambda: assert_official_files(OFFICIAL)
    return hashes


def service_log_tables(path, services):
    """D-7 adapter: masked templates in the released template/structured layout."""
    import pandas as pd
    logs = rc.read_csv(path, "logs.csv")
    t0 = int(rc.load_metrics(path)["time"].iloc[0])
    logs["sec"] = logs["timestamp"].astype("int64") // 1_000_000_000 - t0
    logs["EventTemplate"] = logs["message"].map(tc.log_template)
    tables = {}
    for service in services:
        own = logs[logs["container_name"] == service].sort_values("timestamp")
        if own.empty:
            continue
        counts = own["EventTemplate"].value_counts()
        ids = {template: f"E{i + 1}" for i, template in enumerate(counts.index)}
        template = pd.DataFrame({"EventId": [ids[t] for t in counts.index], "EventTemplate": list(counts.index),
                                 "Occurrence": list(counts.values)})
        structured = pd.DataFrame({"EventId": own["EventTemplate"].map(ids).to_numpy(),
                                   "Time": [f"{int(s) // 60:02d}:{int(s) % 60:02d}" for s in own["sec"]],
                                   "Content": own["message"].astype(str).to_numpy()})
        tables[service] = (template, structured)
    return tables


def run_case(case, directory, encoder, rwr):
    """rwr: callable(graph, labels) -> ranking dict (shared output head)."""
    import pandas as pd
    from local_embedding import llamaindex_embedding
    from local_llm_runtime import CONFIG
    from rca_local_client import RecordedLocalClient, approved_log_summary_sampling, llamaindex_local_llm
    import task070_output_head as oh

    sources = _check_sources()
    values, labels, info = rc.node_table(case["path"])
    services = labels[:-1]
    base = {k: CONFIG["smoke_test"][k] for k in ("top_p", "top_k", "min_p", "presence_penalty")}
    client = RecordedLocalClient(directory / "calls", max_tokens=8192, seed=42, sampling=base)
    record = {"case": case["id"], "labels": labels, "official_sha256": sources, "stages": {}}
    started = time.monotonic()
    try:
        initial = oh.fit_graph(values, labels)
        np.save(directory / "PC.npy", initial)

        # 1. Log summaries (released prompt and temperature 0.5; D07 presence 1.5).
        log_fns = lrc.official_log_summary_call(client, pd)
        tables = service_log_tables(case["path"], services)
        summaries_dir = directory / "summaries" / case["id"]
        summaries_dir.mkdir(parents=True)
        client.phase = "log_summary"
        with approved_log_summary_sampling(client):
            for service, (template, structured) in tables.items():
                prompt = log_fns["generate_log_prompt"](THEME, service, labels, template, structured)
                response = client.inquire_LLMs(
                    prompt, f"You are expert in the field of {THEME}, and you are able to analyze the log file and provide the summary of the entity.",
                    temperature=0.5)
                (summaries_dir / f"{service}_summary.txt").write_text(response, encoding="utf-8")
        record["stages"]["log_summaries"] = {"services_with_logs": sorted(tables),
                                             "absent": [s for s in services if s not in tables]}

        # 2. Released dataset summary (LlamaIndex defaults, local BGE + local LLM).
        client.phase = "dataset_RAG_summary"
        embedding = llamaindex_embedding(encoder)
        llm = llamaindex_local_llm(client, context_window=CONFIG["server"]["context_tokens"])
        web = lrc.original_dataset_summary(embedding, llm)
        raw = web["generate_dataset_summary"](case["id"], labels, database_path=str(directory / "summaries"),
                                              output_dir=None)
        (directory / "rag_original.txt").write_text(raw, encoding="utf-8")
        canonical, _, _, audit = normalize_rag_response(raw, labels)
        data_info, parsed = web["split_summary_into_sub_questions"](canonical)
        missing = [s for s in tables if s not in parsed]
        if missing:
            raise RuntimeError(f"RAG summary lacks services with logs: {missing}; no fabrication")
        node_info = {}
        for name in labels:
            if name == labels[-1]:
                node_info[name] = KPI_NOTICE
            elif name in tables:
                node_info[name] = parsed[name]
            else:
                node_info[name] = POLICY["missing_notice"].replace("pod", "service")
        record["stages"]["rag"] = {"format_audit": audit}
        (directory / "node_information.json").write_text(
            json.dumps({"dataset_information": data_info, "node_information": node_info}, ensure_ascii=False, indent=2),
            encoding="utf-8")

        # 3. Released agent: explanations (TASK_052 presence 1.5) and constraints.
        Agent = lrc.official_agent_class(client, re_audit=lambda event: None)
        agent = Agent(labels, THEME, graph_matrix=initial, causal_discovery_algorithm="pc",
                      use_reasoning=False, dataset_information=data_info, node_information=node_info)
        agent.domain_knowledge_LLM.generate_prompt(0, 1, node_info)
        client.phase = "MATMCD_domain"
        client.sampling = dict(base, presence_penalty=1.5)
        try:
            agent.generate_domain_knowledge(use_cache=False, cache_path=str(directory / "domain_cache"))
        finally:
            client.sampling = base
        client.phase = "MATMCD_constraints"
        constraints = agent.generate_constrain_matrix()
        if constraints.shape != initial.shape or not np.isin(constraints, [-1, 0, 1]).all():
            raise RuntimeError("Released constraint parser returned invalid entries")
        np.save(directory / "constraints.npy", constraints)
        refined = oh.fit_graph(values, labels, constraints)
        np.save(directory / "MATMCD.npy", refined)
        record["ranking"] = rwr(refined, labels)
        record["status"] = "COMPLETE"
    except Exception as error:
        record.update(status="FAILED", error=f"{type(error).__name__}: {error}")
    finally:
        client.close()
        record.update(seconds=time.monotonic() - started, generation_calls=client.counter)
        (directory / "result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record
