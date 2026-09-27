"""Continue the exact saved 30-pod PC/log/RAG artifacts after a format failure.

Only recognizable response boundaries are canonicalized once. Official parsing,
all descriptions, original retrieval results and scientific functions persist.
No generation retry, invented node information or model substitution.
"""
import argparse
import contextlib
import json
import re
import time
import traceback
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT
from rca_log_evidence import read_json, within, sha256, finalize_node_information
from run_local_rca import write, local_server, AGENT_THEMES
from run_rca_oracle30 import profile, select_plan, evaluate, snapshot, now
from setup_graphviz import assert_original_source


def normalize_rag_response(raw, labels):
    """Keep text bodies exactly, accepting only the observed heading variants."""
    sections = re.split(r"(?m)^\s*---\s*$", raw.strip())
    first = re.fullmatch(r"\s*Dataset Summary:\s*(.+?)\s*", sections[0], flags=re.S)
    if first is None:
        raise ValueError("Unrecognized dataset heading; no inference")
    dataset = first.group(1)
    nodes, relationships = {}, None
    for position, section in enumerate(sections[1:], 1):
        section = section.strip()
        match = re.fullmatch(r"Summary of (?:the )?([^:\n]+):\s*(.+?)\s*", section, flags=re.S)
        if match:
            name, body = match.groups()
            if name not in labels or name in nodes:
                raise ValueError(f"Unknown/duplicate node heading: {name}")
            nodes[name] = body
        elif section.startswith("Relationships between Nodes:\n") and position == len(sections) - 1:
            relationships = section
        else:
            raise ValueError("Unrecognized extra section; no deletion or guessing")
    # The released parser has no separate cross-node-relationship field. Keep
    # the entire explicitly global section in the dataset-wide information.
    combined = dataset + ("\n\n" + relationships if relationships is not None else "")
    canonical = "Dataset Summary: " + combined
    for name, body in nodes.items():
        canonical += f"\n---\nSummary of the {name}: {body}"
    return canonical, combined, nodes, {
        "policy": "rag_heading_boundaries_v1", "changed": canonical != raw,
        "descriptions_modified": False, "nodes_added": [], "nodes_removed": [],
        "global_relationship_section": "preserved_verbatim_in_dataset_information" if relationships else "absent",
        "node_count": len(nodes), "canonicalization_passes": 1,
    }


def domain_profile(*, require_review=True):
    path = PROJECT / "configs/rca_domain_sampling.json"
    value = read_json(path)
    if (value["authorization"] != "USER_APPROVED_DIAGNOSTICS_THEN_UNIFORM_DOMAIN_RESTART"
            or value["phase"] != "MATMCD_domain" or value["overrides"] != {"presence_penalty": 1.5}
            or value["base_presence_penalty"] != 0 or value["constraints_presence_penalty"] != 0
            or value["restart_all_domain_pairs"] != 930 or value["reuse_old_domain_responses"]
            or value["reuse_diagnostic_responses"] or value["automatic_retries"] != 0
            or value["diagnostic_call_numbers"] != [41, 1, 15]
            or value["base_profile"] != profile()["profile_id"]):
        raise RuntimeError("Unsupported domain sampling authorization/scope")
    if require_review:
        review = read_json(within(PROJECT, value["review_receipt"]))
        if (review["status"] != "PASS_SCOPED_DIAGNOSTICS" or review["profile_sha256"] != sha256(path)
                or review["approved_to_start_uniform_domain_run"] is not True):
            raise RuntimeError("Diagnostic review missing or profile changed")
        evidence_path = within(PROJECT, review["diagnostic_evidence"])
        if sha256(evidence_path) != review["diagnostic_evidence_sha256"]:
            raise RuntimeError("Diagnostic evidence changed")
        evidence = read_json(evidence_path)
        if (evidence["status"] != "GENERATED_PENDING_SEMANTIC_REVIEW"
                or not evidence["environment_unchanged"] or not evidence["originals_unchanged"]
                or [t["original_call"] for t in evidence["trials"]] != [41, 1, 15]
                or any(t["finish_reason"] != "stop" or not t["actual_request_diff_only_presence_penalty"]
                       for t in evidence["trials"])):
            raise RuntimeError("Diagnostic trial conditions did not pass")
    return value


def review_environment(parent, domain=None):
    before, after = read_json(parent / "environment_before.json"), read_json(parent / "environment_after.json")
    differences = {section: {key: [before[section].get(key), after[section].get(key)]
                           for key in set(before[section]) | set(after[section])
                           if before[section].get(key) != after[section].get(key)} for section in before}
    allowed = {p["name"]: [None, p["version"]]
               for p in read_json(PROJECT / "configs/local_embedding.json")["runtime"]["packages"]}
    if differences["python"] != allowed or any(v for k, v in differences.items() if k != "python"):
        raise RuntimeError(f"Unexplained parent environment change: {differences}")
    if before["official_sources"] != snapshot()["official_sources"]:
        raise RuntimeError("Official sources changed since parent")
    current_configs = snapshot()["configs"]
    if domain is not None:
        if "rca_domain_sampling.json" in before["configs"]:
            raise RuntimeError("Expected parent before TASK_052 profile addition")
        current_configs.pop("rca_domain_sampling.json")
    if before["configs"] != current_configs:
        raise RuntimeError("Configurations changed since parent")
    return {"status": "EXPECTED_APPROVED_IN_PROCESS_LOADER_OVERLAY", "differences": differences,
            "approved_added_configuration": "rca_domain_sampling.json" if domain else None,
            "actual_package_installation_change_detected": False,
            "explanation": "DenseBGE.activate_loader adds the already-installed approved overlay to sys.path; metadata sees two additional packages."}


def run(parent_relative, *, approved_domain_restart=False):
    import numpy as np
    from local_llm_runtime import CONFIG
    from local_rca_components import extract, official_agent_class, official_pc, official_visualize
    from rca_local_client import RecordedLocalClient
    from rca_ranking import rank_stage_with_original_rwr, decode_rng_state

    assert_original_source()
    config = profile()
    domain = domain_profile() if approved_domain_restart else None
    if domain and parent_relative != domain["completed_stages_parent"]:
        raise RuntimeError("TASK_052 completed-stage parent differs")
    _, plan, selection = select_plan(config)
    parent = within(ASSETS, parent_relative)
    if parent.parent != within(ASSETS, config["run_storage"]):
        raise RuntimeError("Parent outside this development profile")
    prior = read_json(parent / "result.json")
    if "split_summary_into_sub_questions" not in prior.get("error", "") or "IndexError" not in prior["error"]:
        raise RuntimeError("This continuation is only for the observed RAG format failure")
    if read_json(parent / "selection.json") != selection or read_json(parent / "input_plan.json") != plan:
        raise RuntimeError("Parent input/selection differs")
    environment_review = review_environment(parent, domain)
    raw_path = parent / "dataset_summary/Product_Review_20211203_info.txt"
    raw = raw_path.read_text(encoding="utf-8")
    rag_calls = [read_json(p) for p in sorted((parent / "calls").glob("call_*.json"))]
    if len(rag_calls) != 21 or any(c["status"] != "COMPLETE" for c in rag_calls):
        raise RuntimeError("Expected exactly 20 complete log calls plus one RAG call")
    rag_call = rag_calls[-1]
    if rag_call["phase"] != "dataset_RAG_summary" or rag_call["response"]["choices"][0]["message"]["content"] != raw:
        raise RuntimeError("Saved RAG text differs from recorded model response")
    labels = plan["columns"]
    canonical, dataset_body, node_bodies, audit = normalize_rag_response(raw, labels)
    parse = extract("Web_tools.py", {"split_summary_into_sub_questions"})["split_summary_into_sub_questions"]
    data_info, parsed = parse(canonical)
    if data_info.strip() != dataset_body or {k: v.strip() for k, v in parsed.items()} != node_bodies:
        raise RuntimeError("Official parser lost description text after format normalization")
    available = {n["name"] for n in plan["nodes"] if n["evidence_available"] is True}
    if not available <= set(parsed):
        raise RuntimeError("Available node descriptions missing; no fabrication")
    node_info = finalize_node_information(plan, {name: parsed[name] for name in labels if name in available})
    data_info += "\n\n" + plan["system_coverage_notice"]
    failed = within(ASSETS, domain["failed_run"]) if domain else None
    if failed is not None:
        prior_failure = read_json(failed / "result.json")
        if (prior_failure["status"] != "FAILED" or "finish_reason=length" not in prior_failure["error"]
                or not prior_failure["environment_unchanged"]
                or read_json(failed / "lineage.json")["parent_run"] != parent_relative
                or read_json(failed / "selection.json") != selection
                or read_json(failed / "input_plan.json") != plan
                or read_json(failed / "node_information.json") != {"dataset_information": data_info, "node_information": node_info}):
            raise RuntimeError("TASK_052 prior failure or validated input lineage differs")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = within(ASSETS, config["run_storage"]) / stamp
    directory.mkdir(parents=True, exist_ok=False)
    before = snapshot()
    write(directory / "environment_before.json", before)
    write(directory / "parent_environment_review.json", environment_review)
    write(directory / "selection.json", selection)
    write(directory / "input_plan.json", plan)
    write(directory / "configs.json", {p.name: read_json(p) for p in (PROJECT / "configs").glob("*.json")})
    if domain:
        write(directory / "domain_sampling_profile.json", domain)
        write(directory / "domain_diagnostic_review.json", read_json(within(PROJECT, domain["review_receipt"])))
    (directory / "rag_original.txt").write_text(raw, encoding="utf-8")
    (directory / "rag_canonical.txt").write_text(canonical, encoding="utf-8")
    write(directory / "rag_format_audit.json", {**audit, "original_sha256": sha256(directory / "rag_original.txt"),
                                               "canonical_sha256": sha256(directory / "rag_canonical.txt"),
                                               "official_parser_lossless_body_check": True})
    write(directory / "node_information.json", {"dataset_information": data_info, "node_information": node_info})
    required = ["graphs/PC.npy", "graphs/PC.png", "rankings/PC.json", "evaluation/PC.json"]
    for file in required:
        target = directory / file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((parent / file).read_bytes())
        if failed is not None and sha256(parent / file) != sha256(failed / file):
            raise RuntimeError("Saved PC artifacts changed across parent lineage")
    write(directory / "lineage.json", {
        "parent_run": parent_relative, "parent_result_sha256": sha256(parent / "result.json"),
        "reused": {file: sha256(parent / file) for file in required},
        "raw_rag_sha256": sha256(raw_path),
        "parent_calls": {p.name: sha256(p) for p in sorted((parent / "calls").glob("call_*.json"))},
        "no_generation_repeated": True,
        "numpy_rng": "restored_from_saved_PC_RWR_rng_after; no_new_seed; interrupted_process_later_state_unavailable",
        "wrapper_change": "one_pass_lossless_response_boundary_normalization_and_stage_continuation",
        "domain_restart": None if not domain else {
            "profile": domain["profile_id"], "from_pair": 1, "total_pairs": 930,
            "failed_run": domain["failed_run"], "failed_result_sha256": sha256(failed / "result.json"),
            "previous_calls": {p.name: sha256(p) for p in sorted((failed / "calls").glob("call_*.json"))},
            "reused_previous_domain_calls": 0, "reused_diagnostic_calls": 0,
            "approved_sampling_override": domain["overrides"], "constraint_sampling_override": None},
    })
    prepared = within(ASSETS, config["prepared_storage"])
    receipt = read_json(prepared / "prepared.json")
    if sha256(prepared / "metrics.npy") != receipt["metrics_sha256"]:
        raise RuntimeError("Prepared metrics changed")
    data = np.load(prepared / "metrics.npy", allow_pickle=False)
    initial = np.load(directory / "graphs/PC.npy", allow_pickle=False)
    saved_rank = read_json(directory / "rankings/PC.json")
    if initial.shape != (31, 31) or saved_rank["labels_in_original_order"] != labels:
        raise RuntimeError("Parent graph/labels differ")
    np.random.set_state(decode_rng_state(saved_rank["rng_after"]))
    report = {"status": "RUNNING", "started_utc": now(), "profile": domain["profile_id"] if domain else config["profile_id"],
              "parent_run": parent_relative, "paper_equivalence": False}
    def progress(stage, **details):
        value = {"stage": stage, "utc": now(), **details}
        (directory / "progress.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        with (directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        print(json.dumps(value), flush=True)
    print(json.dumps({"status": "STARTED_CONTINUATION", "directory": str(directory), "parent": str(parent)}), flush=True)
    started = time.monotonic()
    try:
        with (directory / "execution.log").open("w", encoding="utf-8") as output, contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            progress("RAG_FORMAT_VALIDATED", node_descriptions=len(parsed), parent_calls_reused=21)
            chosen = CONFIG["smoke_test"]
            sampling = {k: chosen[k] for k in ("top_p", "top_k", "min_p", "presence_penalty")}
            if domain and sampling["presence_penalty"] != domain["base_presence_penalty"]:
                raise RuntimeError("Base sampling changed since approved TASK_052 proposal")
            with local_server(directory / "server"):
                client = RecordedLocalClient(directory / "calls", max_tokens=chosen["max_tokens"], seed=chosen["seed"], sampling=sampling)
                try:
                    Agent = official_agent_class(client, re_audit=lambda event: None)
                    agent = Agent(labels, AGENT_THEMES[plan["system"]], graph_matrix=initial, causal_discovery_algorithm="pc",
                                  use_reasoning=False, dataset_information=data_info, node_information=node_info)
                    agent.domain_knowledge_LLM.generate_prompt(0, 1, node_info)
                    # These are exactly the two calls made by the released run().
                    client.phase = "MATMCD_domain"
                    client.sampling = dict(sampling, **(domain["overrides"] if domain else {}))
                    progress("MATMCD_DOMAIN_RUNNING", directed_pairs=930, sampling=client.sampling, from_pair=1)
                    try:
                        agent.generate_domain_knowledge(use_cache=False, cache_path=str(directory / "domain_cache/MATMCD"))
                    finally:
                        client.sampling = sampling
                    client.phase = "MATMCD_constraints"
                    progress("MATMCD_CONSTRAINTS_RUNNING", domain_calls=client.counter, directed_pairs=930, sampling=client.sampling)
                    constraints = agent.generate_constrain_matrix()
                    if constraints.shape != initial.shape or not np.isin(constraints, [-1, 0, 1]).all():
                        raise RuntimeError("Original constraint parser returned invalid entries")
                    np.save(directory / "graphs/MATMCD_constraints.npy", constraints)
                    progress("MATMCD_REFINED_PC_RUNNING", generation_calls=client.counter)
                    refined = official_pc()(data, labels, method="pc", constraint_matrix=constraints)
                    np.save(directory / "graphs/MATMCD.npy", refined)
                    official_visualize()(refined, labels, str(directory / "graphs/MATMCD.png"))
                    ranking = rank_stage_with_original_rwr("MATMCD", initial, refined, labels)
                    write(directory / "rankings/MATMCD.json", ranking)
                    write(directory / "evaluation/MATMCD.json", evaluate(ranking, selection))
                    progress("COMPLETED", generation_calls=client.counter, parent_generation_calls=21)
                finally:
                    client.close()
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
        write(PROJECT / f"docs/evidence/rca_oracle30_continuation_{stamp}.json", {**report, "run_directory": directory.relative_to(ASSETS).as_posix()})
    print(json.dumps({**report, "directory": str(directory)}), flush=True)
    return 0 if report["status"] == "COMPLETED_ORACLE30_LOCAL_DEVELOPMENT_RUN" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-run", required=True, help="Existing run path relative to MATMCD_DATA")
    parser.add_argument("--approved-domain-restart", action="store_true", help="TASK_052: approved, reviewed 1.5 domain-only profile; restart all 930")
    args = parser.parse_args()
    raise SystemExit(run(args.from_run, approved_domain_restart=args.approved_domain_restart))
