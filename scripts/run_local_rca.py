"""Sequential local RCA orchestration with unchanged official scientific code.

--prepare-prompts reads all active exact pairs but performs no generation or RCA.
--run stays gated until the real prompt capacity validation is explicitly ready.
Raw outputs/errors are retained; no automatic scientific changes or retries.
"""
import argparse
import contextlib
import gc
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, asset_path
from rca_case_scope import active_cases, case_key
from rca_log_evidence import build_plans, verify_prepared_plans, read_json, sha256, within, finalize_node_information
from rca_log_worker import prepare_one
from setup_graphviz import assert_original_source, python_packages, source_hashes, system_packages


EXECUTION_PATH = PROJECT / "configs/local_rca_execution.json"
LOG_THEMES = {"Product_Review": "Microservice System for Product Review", "Cloud_Computing": "Cloud Computing System"}
AGENT_THEMES = {"Product_Review": "MicroService system about Product Review", "Cloud_Computing": "MicroService system about Cloud Computing"}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def prompt_directory(key, node, *, recovered=False):
    config = read_json(EXECUTION_PATH)
    node_key = hashlib.sha256(node["name"].encode()).hexdigest()
    return within(ASSETS, config["recovered_prompt_storage" if recovered else "prompt_storage"]) / key / node_key


def verified_prompt(plan, node):
    key = f"{plan['system']}/{plan['day']}"
    directory = prompt_directory(key, node)
    strict_result = read_json(directory / "result.json")
    if strict_result["status"] == "FAILED" and "UnicodeDecodeError" in strict_result.get("error", ""):
        from rca_log_encoding import POLICY
        config = read_json(EXECUTION_PATH)
        if config["log_encoding_policy"]["id"] != POLICY or config["log_encoding_policy"]["status"] != "USER_APPROVED":
            raise RuntimeError("D06 recovery is not approved")
        strict_directory = directory
        directory = prompt_directory(key, node, recovered=True)
        reader = read_json(directory / "reader.json")
        if reader != {"policy": POLICY, "strict_failure_directory": strict_directory.relative_to(ASSETS).as_posix(),
                       "strict_failure_sha256": sha256(strict_directory / "result.json")}:
            raise RuntimeError("D06 reader provenance differs")
    request = read_json(directory / "request.json")
    expected = {"case": key, "pod": node["name"], "sources": node["sources"],
                "theme": LOG_THEMES[plan["system"]], "columns": plan["columns"]}
    if request != expected:
        raise RuntimeError(f"Saved prompt input manifest differs: {key}/{node['name']}")
    result = read_json(directory / "result.json")
    path = directory / "message.json"
    if result["status"] != "CAPTURED" or sha256(path) != result["message_sha256"]:
        raise RuntimeError(f"Incomplete/changed capture: {directory}; preserve failure and review")
    message = read_json(path)
    from rca_log_encoding import require_valid_prompt
    require_valid_prompt(message)
    return message


def prepare_prompts():
    assert_original_source()
    plans = build_plans()
    verify_prepared_plans(plans)
    completed, failed = [], []
    for key, plan in plans.items():
        for node in plan["nodes"]:
            if node["evidence_available"] is not True:
                continue
            directory = prompt_directory(key, node)
            try:
                if not directory.exists():
                    prepare_one(plan, node, LOG_THEMES[plan["system"]], directory)
                message = verified_prompt(plan, node)
            except Exception:
                # Inventory independent preparation failures, not a subset run.
                # Existing failure directories are never overwritten or retried.
                failed.append({"case": key, "pod": node["name"], "directory": directory.relative_to(ASSETS).as_posix(),
                               "error": traceback.format_exc()})
                print(json.dumps({"preparation_failure": key, "pod": node["name"]}), flush=True)
                continue
            strict_result = read_json(directory / "result.json")
            if strict_result["status"] != "CAPTURED":
                directory = prompt_directory(key, node, recovered=True)
            completed.append({"case": key, "pod": node["name"], "directory": directory.relative_to(ASSETS).as_posix(),
                              "characters": len(message["prompt"]), "message_sha256": sha256(directory / "message.json")})
            print(json.dumps({"prepared": len(completed), "case": key, "pod": node["name"]}), flush=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    write(PROJECT / f"docs/evidence/rca_prompt_preparation_{stamp}.json",
          {"status": "PREPARED" if not failed else "BLOCKED_PREPARATION_ERRORS", "prompts": completed,
           "failures": failed, "generation_calls": 0, "actual_experiment_results": False,
           "excluded_from_experiment": [], "all_required_pairs": len(completed) + len(failed)})
    if failed:
        raise RuntimeError(f"{len(failed)} required prompts remain blocked; no reduced experiment is allowed")


def recover_failed_prompts():
    """Apply the approved D06 reader once, keeping the original strict failure."""
    from rca_log_encoding import POLICY
    policy = read_json(EXECUTION_PATH)["log_encoding_policy"]
    if policy["id"] != POLICY or policy["status"] != "USER_APPROVED":
        raise RuntimeError("D06 approval is required")
    assert_original_source()
    plans = build_plans()
    verify_prepared_plans(plans)
    # Complete the independent strict inventory before starting recovery; never
    # overlap another large-CSV preparation worker or reinterpret missing files.
    for key, plan in plans.items():
        for node in plan["nodes"]:
            if node["evidence_available"] is True and not (prompt_directory(key, node) / "result.json").is_file():
                raise RuntimeError("Finish the complete strict-reader inventory first")
    recovered, unchanged, failed = [], [], []
    for key, plan in plans.items():
        for node in plan["nodes"]:
            if node["evidence_available"] is not True:
                continue
            strict_directory = prompt_directory(key, node)
            strict_result = read_json(strict_directory / "result.json")
            directory = strict_directory
            try:
                is_recovery = strict_result["status"] == "FAILED" and "UnicodeDecodeError" in strict_result.get("error", "")
                if is_recovery:
                    directory = prompt_directory(key, node, recovered=True)
                    if not directory.exists():
                        prepare_one(plan, node, LOG_THEMES[plan["system"]], directory,
                                    strict_failure_directory=strict_directory)
                message = verified_prompt(plan, node)
                item = {"case": key, "pod": node["name"], "directory": directory.relative_to(ASSETS).as_posix(),
                        "characters": len(message["prompt"]), "message_sha256": sha256(directory / "message.json")}
                (recovered if is_recovery else unchanged).append(item)
                if is_recovery:
                    print(json.dumps({"recovered": len(recovered), "case": key, "pod": node["name"]}), flush=True)
            except Exception:
                failed.append({"case": key, "pod": node["name"], "directory": directory.relative_to(ASSETS).as_posix(),
                               "error": traceback.format_exc()})
                print(json.dumps({"recovery_failure": key, "pod": node["name"]}), flush=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    write(PROJECT / f"docs/evidence/rca_log_recovery_{stamp}.json",
          {"status": "PREPARED" if not failed else "BLOCKED_PREPARATION_ERRORS", "policy": policy,
           "recovered": recovered, "strict_unchanged": unchanged, "failures": failed,
           "generation_calls": 0, "actual_experiment_results": False, "excluded_from_experiment": [],
           "all_required_pairs": len(recovered) + len(unchanged) + len(failed)})
    if failed:
        raise RuntimeError(f"{len(failed)} required prompts remain blocked; no byte replacement, file omission or automatic retry")


@contextlib.contextmanager
def local_server(directory):
    import httpx
    from local_llm_runtime import CONFIG, runtime_command, base_url
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", CONFIG["server"]["port"])) == 0:
            raise RuntimeError("Port occupied; do not reuse or terminate an unrelated server")
    command, env = runtime_command()
    directory.mkdir(parents=True, exist_ok=False)
    write(directory / "launch.json", {"command": command, "model": CONFIG["model"], "server": CONFIG["server"]})
    with (directory / "server.log").open("w") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 240
            with httpx.Client(base_url=base_url(), trust_env=False, timeout=10) as health:
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Local server exited; see server.log")
                    try:
                        if health.get("/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError("Local server readiness timeout")
                    time.sleep(.5)
            yield
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=20)


def run_case(plan, directory):
    import numpy as np
    import pandas as pd
    from local_embedding import DenseBGE, llamaindex_embedding, CONFIG as EMBEDDING_CONFIG
    from local_llm_runtime import CONFIG
    from local_rca_components import official_pc, official_visualize, official_agent_class, original_dataset_summary
    from rca_local_client import RecordedLocalClient, llamaindex_local_llm, approved_log_summary_sampling
    from rca_ranking import rank_stage_with_original_rwr
    from rca_evaluation import evaluate_case

    key = f"{plan['system']}/{plan['day']}"
    labels = plan["columns"]
    csv_path = within(ASSETS, plan["csv"])
    if sha256(csv_path) != plan["csv_sha256"]:
        raise RuntimeError("Metric CSV changed")
    data = pd.read_csv(csv_path)
    if data.columns.tolist() != labels:
        raise RuntimeError("Complete column order differs")
    data = data.values
    discover = official_pc()
    initial = discover(data, labels, method="pc")
    graph_dir = directory / "graphs"
    graph_dir.mkdir()
    np.save(graph_dir / "PC.npy", initial)
    visualize = official_visualize()
    visualize(initial, labels, str(graph_dir / "PC.png"))
    rankings = {"PC": rank_stage_with_original_rwr("PC", initial, None, labels)}
    write(directory / "rankings/PC.json", rankings["PC"])
    write(directory / "evaluation/PC.json", evaluate_case(key, rankings["PC"]))
    chosen = CONFIG["smoke_test"]
    sampling = {k: chosen[k] for k in ("top_p", "top_k", "min_p", "presence_penalty")}
    with local_server(directory / "server"):
        client = RecordedLocalClient(directory / "calls", max_tokens=chosen["max_tokens"], seed=chosen["seed"], sampling=sampling)
        re_events = directory / "re_format.jsonl"
        def record_re(event):
            with re_events.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"phase": client.phase, "call": client.counter, **event}, ensure_ascii=False) + "\n")
        try:
            Agent = official_agent_class(client, re_audit=record_re)
            for stage in ("CC_without_external_information", "MATMCD", "MATMCD_RE"):
                if stage == "MATMCD":
                    client.phase = "pod_log_summary"
                    case_name = key.replace("/", "_")
                    corpus = directory / "summaries" / case_name
                    corpus.mkdir(parents=True)
                    with approved_log_summary_sampling(client):
                        for node in plan["nodes"]:
                            if node["evidence_available"] is True:
                                message = verified_prompt(plan, node)
                                text = client.inquire_LLMs(message["prompt"], message["system_prompt"], message["temperature"])
                            else:
                                text = node["fixed_information"]
                            (corpus / f"{node['name']}_summary.txt").write_text(text, encoding="utf-8")
                    # Fixed absence/KPI entries stay distinguishable in the
                    # corpus and are restored after the original summary parser.
                    client.phase = "dataset_RAG_summary"
                    write(directory / "rag_index" / "embedding_profile.json", EMBEDDING_CONFIG)
                    def record_embedding(event):
                        with (directory / "rag_index" / "encoding.jsonl").open("a", encoding="utf-8") as stream:
                            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
                    engine = DenseBGE(audit_callback=record_embedding)
                    functions = original_dataset_summary(llamaindex_embedding(engine),
                        llamaindex_local_llm(client, context_window=CONFIG["server"]["context_tokens"]))
                    output = directory / "dataset_summary"
                    output.mkdir()
                    summary = functions["generate_dataset_summary"](case_name, labels,
                        database_path=str(corpus.parent), output_dir=str(output),
                        embeddings_path=str(directory / "rag_index"), save_embeddings=True)
                    data_info, parsed = functions["split_summary_into_sub_questions"](summary)
                    available = {n["name"] for n in plan["nodes"] if n["evidence_available"] is True}
                    if not available <= set(parsed) or set(parsed) - set(labels):
                        raise RuntimeError("Original summary parser did not return every available pod exactly; no invented summary")
                    node_info = finalize_node_information(plan, {name: parsed[name] for name in labels if name in available})
                    data_info += "\n\n" + plan["system_coverage_notice"]
                    write(directory / "node_information.json", {"dataset_information": data_info, "node_information": node_info})
                    del functions, engine
                    gc.collect()
                client.phase = stage
                kwargs = {} if stage == "CC_without_external_information" else {
                    "dataset_information": data_info, "node_information": node_info}
                agent = Agent(labels, AGENT_THEMES[plan["system"]], graph_matrix=initial,
                              causal_discovery_algorithm="pc", use_reasoning=stage == "MATMCD_RE", **kwargs)
                if kwargs:
                    agent.domain_knowledge_LLM.generate_prompt(0, 1, node_info)
                constraints = agent.run(use_cache=False, cache_path=str(directory / "domain_cache" / stage))
                if constraints.shape != initial.shape or not np.isin(constraints, [-1, 0, 1]).all():
                    raise RuntimeError("Original constraint parser returned invalid entries; no replacement")
                np.save(graph_dir / f"{stage}_constraints.npy", constraints)
                refined = discover(data, labels, method="pc", constraint_matrix=constraints)
                np.save(graph_dir / f"{stage}.npy", refined)
                visualize(refined, labels, str(graph_dir / f"{stage}.png"))
                rankings[stage] = rank_stage_with_original_rwr(stage, initial, refined, labels)
                write(directory / "rankings" / f"{stage}.json", rankings[stage])
                write(directory / "evaluation" / f"{stage}.json", evaluate_case(key, rankings[stage]))
                del agent, constraints, refined
                gc.collect()
        finally:
            client.close()
    return rankings


def run():
    profile = read_json(EXECUTION_PATH)
    if profile["status"] != "READY_FOR_LOCAL_RUN":
        raise RuntimeError("Actual RCA is gated: finish capacity approval and integration validation first")
    assert_original_source()
    plans = build_plans()
    verify_prepared_plans(plans)
    for plan in plans.values():
        for node in plan["nodes"]:
            if node["evidence_available"] is True:
                verified_prompt(plan, node)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = within(ASSETS, profile["run_storage"]) / stamp
    directory.mkdir(parents=True, exist_ok=False)
    before = {"system_packages": system_packages(), "python_packages": python_packages(),
              "official_sources": source_hashes(), "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}
    write(directory / "environment_before.json", before)
    write(directory / "profile.json", profile)
    write(directory / "input_plans.json", plans)
    write(directory / "config_snapshot.json", {p.name: read_json(p) for p in (PROJECT / "configs").glob("*.json")})
    report = {"status": "RUNNING", "cases": {}, "author_equivalence": "UNCONFIRMED"}
    all_rankings = {}
    try:
        for key, plan in plans.items():
            case_dir = directory / key.replace("/", "_")
            case_dir.mkdir()
            print(json.dumps({"case": key, "status": "STARTED", "directory": str(case_dir)}), flush=True)
            with (case_dir / "execution.log").open("w") as output, contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                all_rankings[key] = run_case(plan, case_dir)
            report["cases"][key] = "COMPLETED"
        from rca_evaluation import evaluate_active_cases
        for stage in profile["stages"]:
            write(directory / "evaluation" / f"{stage}.json", evaluate_active_cases({k: value[stage] for k, value in all_rankings.items()}))
        report["status"] = "COMPLETED_LOCAL_PROVISIONAL_RUN"
    except Exception:
        report.update(status="FAILED", error=traceback.format_exc())
    finally:
        after = {"system_packages": system_packages(), "python_packages": python_packages(),
                 "official_sources": source_hashes(), "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}
        write(directory / "environment_after.json", after)
        report["environment_unchanged"] = before == after
        if before != after:
            report["status"] = "REQUIRES_ENVIRONMENT_REVIEW"
        write(directory / "result.json", report)
    print(json.dumps({"status": report["status"], "directory": str(directory)}), flush=True)
    return 0 if report["status"] == "COMPLETED_LOCAL_PROVISIONAL_RUN" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-prompts", action="store_true")
    group.add_argument("--recover-failed-prompts", action="store_true")
    group.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.prepare_prompts:
        prepare_prompts()
    elif args.recover_failed_prompts:
        recover_failed_prompts()
    else:
        raise SystemExit(run())
