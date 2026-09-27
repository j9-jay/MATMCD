"""User-approved, root-included 30-pod development run; not paper reproduction.

Full parent inputs and upstream functions remain immutable. The fixed selection
is materialized before any RCA output. No truncation, retry or model fallback.
"""
import argparse
import contextlib
import copy
import gc
import hashlib
import json
import time
import traceback
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT
from rca_log_evidence import build_plans, read_json, sha256, within, finalize_node_information
from run_local_rca import verified_prompt, local_server, write, LOG_THEMES, AGENT_THEMES
from setup_graphviz import assert_original_source, source_hashes, python_packages, system_packages

PROFILE_PATH = PROJECT / "configs/rca_development_30.json"


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def profile():
    value = read_json(PROFILE_PATH)
    if value["authorization"] != "USER_APPROVED_ROOT_INCLUDED_30_PODS_AND_ACTUAL_EXECUTION":
        raise RuntimeError("Missing scoped execution authorization")
    if (value["case"], value["pod_count"], value["stages"]) != ("Product_Review/20211203", 30, ["PC", "MATMCD"]):
        raise RuntimeError("Unsupported development scope")
    if value["selection_rule"] != "include_provisional_root_then_top29_other_pods_by_max_channel_positive_scores_divided_by_aligned_rows":
        raise RuntimeError("Selection rule differs")
    return value


def select_plan(config):
    parent = build_plans()[config["case"]]
    manifest = read_json(within(ASSETS, parent["csv"]).parent / "manifest.json")
    truth = next(c for c in read_json(PROJECT / "configs/rca_protocol.json")["d04"]["cases"]
                 if f"{c['system']}/{c['day']}" == config["case"])
    root = truth["evaluation_pod"]
    if root not in parent["columns"][:-1]:
        raise RuntimeError("Provisional root is not a unique parent pod")
    scores = {pod: 0.0 for pod in parent["columns"][:-1]}
    for channel in manifest["channels"]:
        if channel.get("status") == "DETECTED":
            fraction = channel["positive_scores"] / channel["aligned_rows"]
            if not 0 <= fraction <= 1:
                raise RuntimeError("Invalid anomaly fraction")
            scores[channel["pod"]] = max(scores[channel["pod"]], fraction)
    ordered = sorted(scores, key=lambda name: (-scores[name], name))
    selected = {root, *[name for name in ordered if name != root][:29]}
    columns = [name for name in parent["columns"] if name in selected] + [config["kpi"]]
    if len(selected) != 30 or len(columns) != 31 or columns[-1] != parent["columns"][-1]:
        raise RuntimeError("Shortlist/KPI invariant failed")
    plan = copy.deepcopy(parent)
    plan["columns"] = columns
    plan["nodes"] = [n for n in parent["nodes"] if n["name"] in columns]
    available = sum(n["evidence_available"] is True for n in plan["nodes"])
    plan["counts"] = {"pods": 30, "available": available, "missing": 30 - available, "kpi": 1}
    plan["system_coverage_notice"] = (
        f"Exact pod log pairs are available for {available} of 30 candidate pods. "
        f"{30 - available} candidate pods have no matching log evidence in this case. "
        "All candidates remain included. Missing evidence does not establish normality, "
        "abnormality, absence of causal influence, or a restart/death event. The input KPI column is not a pod.")
    selection = {"profile": config, "profile_sha256": sha256(PROFILE_PATH),
                 "parent_plan_sha256": digest(parent), "parent_csv_sha256": parent["csv_sha256"],
                 "truth": truth, "selected_columns": columns, "parent_pods": len(scores),
                 "root_anomaly_rank_before_forcing": ordered.index(root) + 1,
                 "root_would_be_in_natural_top30": root in ordered[:30],
                 "all_pod_scores": [{"pod": name, "max_positive_fraction": scores[name],
                                     "selected": name in selected} for name in ordered],
                 "selection_uses_ground_truth": True, "paper_equivalence": False}
    return parent, plan, selection


def narrowed_message(parent, node, columns):
    """Rebuild only the official pod_list argument; retain captured log bytes.

    Match the whole upstream template around its generate_log_text insertion,
    then call that same upstream template with the narrowed variable list.
    This avoids rereading gigabyte CSVs and verifies every retained prompt byte.
    """
    import pandas as pd
    from local_rca_components import extract
    message = verified_prompt(parent, node)
    sentinel = "__MATMCD_VERIFIED_LOG_TEXT_INSERTION__"
    namespace = extract("Log_tools.py", {"generate_log_prompt"},
                        {"pd": pd, "generate_log_text": lambda *a: sentinel})
    function = namespace["generate_log_prompt"]
    arguments = (LOG_THEMES[parent["system"]], node["name"])
    skeleton = function(*arguments, parent["columns"], None, None)
    head, tail = skeleton.split(sentinel)
    if not message["prompt"].startswith(head) or not message["prompt"].endswith(tail):
        raise RuntimeError("Captured prompt does not match the complete original template")
    log_text = message["prompt"][len(head):-len(tail)]
    namespace["generate_log_text"] = lambda *a: log_text
    if function(*arguments, parent["columns"], None, None) != message["prompt"]:
        raise RuntimeError("Full prompt reconstruction differs")
    narrowed = dict(message, prompt=function(*arguments, columns, None, None))
    if narrowed["prompt"] == message["prompt"]:
        raise RuntimeError("Shortlist was not applied to the prompt's entity list")
    return narrowed


def prepare():
    import numpy as np
    import pandas as pd
    assert_original_source()
    config = profile()
    parent, plan, selection = select_plan(config)
    directory = within(ASSETS, config["prepared_storage"])
    directory.mkdir(parents=True, exist_ok=False)
    write(directory / "selection.json", selection)
    write(directory / "plan.json", plan)
    # Read with the same default parser as the full original local runner, then
    # index existing values. No rewritten CSV parsing or changed precision.
    frame = pd.read_csv(within(ASSETS, parent["csv"]))
    values = frame[plan["columns"]].to_numpy(copy=True)
    indices = [frame.columns.get_loc(c) for c in plan["columns"]]
    if not np.array_equal(values, frame.values[:, indices]) or values.shape != (51529, 31):
        raise RuntimeError("Selected numeric values/rows differ")
    if not np.isfinite(values).all():
        raise RuntimeError("Nonfinite data")
    np.save(directory / "metrics.npy", values)
    captures = []
    for node in plan["nodes"]:
        if node["evidence_available"] is True:
            message = narrowed_message(parent, node, plan["columns"])
            path = directory / "prompts" / (node["name"] + ".json")
            write(path, message)
            captures.append({"pod": node["name"], "file": path.relative_to(directory).as_posix(),
                             "sha256": sha256(path), "characters": len(message["prompt"])})
    result = {"status": "PREPARED", "prepared_utc": now(), "profile_sha256": sha256(PROFILE_PATH),
              "selection_sha256": sha256(directory / "selection.json"), "plan_sha256": sha256(directory / "plan.json"),
              "metrics_sha256": sha256(directory / "metrics.npy"), "shape": list(values.shape),
              "values_identical_to_parent_column_selection": True, "prompts": captures,
              "generation_calls": 0, "selection_before_rca": True}
    write(directory / "prepared.json", result)
    print(json.dumps({"status": result["status"], "directory": str(directory), "counts": plan["counts"],
                      "root_anomaly_rank": selection["root_anomaly_rank_before_forcing"]}), flush=True)


def evaluate(ranking, selection):
    from rca_metrics import evaluate_ranks
    root = selection["truth"]["evaluation_pod"]
    full = ranking["ranking"]
    full_rank = next(r["rank"] for r in full if r["node"] == root)
    pods = [r for r in full if r["node"] != "Latency"]
    pod_rank = next(i + 1 for i, r in enumerate(pods) if r["node"] == root)
    tied = next(r["visits"] for r in full if r["node"] == root)
    return {"evaluation_scope": "oracle30_provisional_single_case_development", "paper_equivalence": False,
            "candidate_recall_not_measured": True, "truth": selection["truth"],
            "root_rank_including_kpi": full_rank, "root_rank_pods_only": pod_rank,
            "pod_only_metrics": {"Hit@1": int(pod_rank <= 1), "Hit@3": int(pod_rank <= 3),
                                 "Hit@5": int(pod_rank <= 5), "reciprocal_rank": 1 / pod_rank},
            "pod_count_tied_with_root": sum(r["visits"] == tied for r in pods),
            "tie_rule": "original_stable_input_column_order", "original_public_metrics_including_kpi": evaluate_ranks([full_rank])}


def snapshot():
    return {"python": python_packages(), "system": system_packages(), "official_sources": source_hashes(),
            "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")},
            "scripts": {p.name: sha256(p) for p in (PROJECT / "scripts").glob("*.py")}}


def execute(directory, plan, selection, prepared):
    import numpy as np
    from local_llm_runtime import CONFIG
    from local_rca_components import official_pc, official_visualize, official_agent_class, original_dataset_summary
    from rca_local_client import RecordedLocalClient, llamaindex_local_llm, approved_log_summary_sampling
    from rca_ranking import rank_stage_with_original_rwr

    def progress(stage, **details):
        value = {"stage": stage, "utc": now(), **details}
        (directory / "progress.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        with (directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        print(json.dumps(value, ensure_ascii=False), flush=True)

    labels = plan["columns"]
    data = np.load(prepared / "metrics.npy", allow_pickle=False)
    graphs = directory / "graphs"
    graphs.mkdir()
    discover, visualize = official_pc(), official_visualize()
    progress("PC_RUNNING", shape=list(data.shape))
    started = time.monotonic()
    initial = discover(data, labels, method="pc")
    np.save(graphs / "PC.npy", initial)
    visualize(initial, labels, str(graphs / "PC.png"))
    ranking = rank_stage_with_original_rwr("PC", initial, None, labels)
    write(directory / "rankings/PC.json", ranking)
    write(directory / "evaluation/PC.json", evaluate(ranking, selection))
    progress("PC_COMPLETE", seconds=time.monotonic() - started)
    chosen = CONFIG["smoke_test"]
    sampling = {k: chosen[k] for k in ("top_p", "top_k", "min_p", "presence_penalty")}
    with local_server(directory / "server"):
        client = RecordedLocalClient(directory / "calls", max_tokens=chosen["max_tokens"], seed=chosen["seed"], sampling=sampling)
        try:
            client.phase = "pod_log_summary"
            case_name = f"{plan['system']}_{plan['day']}"
            corpus = directory / "summaries" / case_name
            corpus.mkdir(parents=True)
            progress("LOG_SUMMARIES_RUNNING", required=plan["counts"]["available"])
            completed = 0
            with approved_log_summary_sampling(client):
                for node in plan["nodes"]:
                    if node["evidence_available"] is True:
                        message = read_json(prepared / "prompts" / (node["name"] + ".json"))
                        text = client.inquire_LLMs(message["prompt"], message["system_prompt"], message["temperature"])
                        completed += 1
                    else:
                        text = node["fixed_information"]
                    (corpus / (node["name"] + "_summary.txt")).write_text(text, encoding="utf-8")
                    progress("LOG_SUMMARIES_RUNNING", completed=completed, required=plan["counts"]["available"], pod=node["name"])
            progress("RAG_RUNNING")
            from local_embedding import DenseBGE, llamaindex_embedding, CONFIG as EMBEDDING_CONFIG
            client.phase = "dataset_RAG_summary"
            write(directory / "rag_index/embedding_profile.json", EMBEDDING_CONFIG)
            def embedding_audit(event):
                with (directory / "rag_index/encoding.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            engine = DenseBGE(audit_callback=embedding_audit)
            functions = original_dataset_summary(llamaindex_embedding(engine),
                llamaindex_local_llm(client, context_window=CONFIG["server"]["context_tokens"]))
            output = directory / "dataset_summary"
            output.mkdir()
            summary = functions["generate_dataset_summary"](case_name, labels, database_path=str(corpus.parent),
                output_dir=str(output), embeddings_path=str(directory / "rag_index"), save_embeddings=True)
            data_info, parsed = functions["split_summary_into_sub_questions"](summary)
            available = {n["name"] for n in plan["nodes"] if n["evidence_available"] is True}
            if not available <= set(parsed) or set(parsed) - set(labels):
                raise RuntimeError(f"Original RAG parser coverage failure: missing={sorted(available - set(parsed))}; unknown={sorted(set(parsed) - set(labels))}")
            node_info = finalize_node_information(plan, {name: parsed[name] for name in labels if name in available})
            data_info += "\n\n" + plan["system_coverage_notice"]
            write(directory / "node_information.json", {"dataset_information": data_info, "node_information": node_info})
            del functions, engine
            gc.collect()
            progress("MATMCD_RUNNING", directed_pairs=930, expected_agent_calls=1860, prior_calls=client.counter)
            client.phase = "MATMCD"
            Agent = official_agent_class(client, re_audit=lambda event: None)
            agent = Agent(labels, AGENT_THEMES[plan["system"]], graph_matrix=initial, causal_discovery_algorithm="pc",
                          use_reasoning=False, dataset_information=data_info, node_information=node_info)
            agent.domain_knowledge_LLM.generate_prompt(0, 1, node_info)
            constraints = agent.run(use_cache=False, cache_path=str(directory / "domain_cache/MATMCD"))
            if constraints.shape != initial.shape or not np.isin(constraints, [-1, 0, 1]).all():
                raise RuntimeError("Invalid original constraints; no replacement")
            np.save(graphs / "MATMCD_constraints.npy", constraints)
            progress("MATMCD_REFINED_PC_RUNNING", generation_calls=client.counter)
            refined = discover(data, labels, method="pc", constraint_matrix=constraints)
            np.save(graphs / "MATMCD.npy", refined)
            visualize(refined, labels, str(graphs / "MATMCD.png"))
            ranking = rank_stage_with_original_rwr("MATMCD", initial, refined, labels)
            write(directory / "rankings/MATMCD.json", ranking)
            write(directory / "evaluation/MATMCD.json", evaluate(ranking, selection))
            progress("COMPLETED", generation_calls=client.counter)
        finally:
            client.close()


def run():
    assert_original_source()
    config = profile()
    parent, plan, selection = select_plan(config)
    prepared = within(ASSETS, config["prepared_storage"])
    receipt = read_json(prepared / "prepared.json")
    if read_json(prepared / "selection.json") != selection or read_json(prepared / "plan.json") != plan:
        raise RuntimeError("Prepared selection differs from fixed rule/parent")
    for file, key in (("selection.json", "selection_sha256"), ("plan.json", "plan_sha256"), ("metrics.npy", "metrics_sha256")):
        if sha256(prepared / file) != receipt[key]:
            raise RuntimeError(f"Prepared artifact changed: {file}")
    for capture in receipt["prompts"]:
        if sha256(prepared / capture["file"]) != capture["sha256"]:
            raise RuntimeError("Prepared prompt changed")
    if receipt["profile_sha256"] != sha256(PROFILE_PATH):
        raise RuntimeError("Profile changed after selection")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = within(ASSETS, config["run_storage"]) / stamp
    directory.mkdir(parents=True, exist_ok=False)
    before = snapshot()
    write(directory / "environment_before.json", before)
    write(directory / "selection.json", selection)
    write(directory / "input_plan.json", plan)
    write(directory / "configs.json", {p.name: read_json(p) for p in (PROJECT / "configs").glob("*.json")})
    print(json.dumps({"status": "STARTED", "directory": str(directory)}), flush=True)
    started = time.monotonic()
    report = {"status": "RUNNING", "started_utc": now(), "profile": config["profile_id"], "paper_equivalence": False}
    try:
        with (directory / "execution.log").open("w", encoding="utf-8") as output, contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            execute(directory, plan, selection, prepared)
        report["status"] = "COMPLETED_ORACLE30_LOCAL_DEVELOPMENT_RUN"
    except Exception:
        report.update(status="FAILED", error=traceback.format_exc())
    finally:
        after = snapshot()
        write(directory / "environment_after.json", after)
        report.update(finished_utc=now(), seconds=time.monotonic() - started, environment_unchanged=before == after)
        if before != after:
            report["status"] = "REQUIRES_ENVIRONMENT_REVIEW"
        write(directory / "result.json", report)
        write(PROJECT / f"docs/evidence/rca_oracle30_{stamp}.json", {**report, "run_directory": directory.relative_to(ASSETS).as_posix()})
    print(json.dumps({**report, "directory": str(directory)}), flush=True)
    return 0 if report["status"] == "COMPLETED_ORACLE30_LOCAL_DEVELOPMENT_RUN" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        raise SystemExit(run())
