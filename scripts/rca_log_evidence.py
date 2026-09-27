"""Prepare approved exact-pod evidence plans without summaries, models or RCA.

TASK_024 must call dispatch_summary for each column and finalize_node_information
after generation. Missing nodes have deterministic text; callbacks never receive
them. This module does not implement D02's CSV reader or a full RCA entrypoint.
"""
import argparse
import csv
import hashlib
import json
from pathlib import PurePosixPath

from project_paths import ASSETS, PROJECT, asset_path
from rca_case_scope import select_active_cases, validate_input_scope


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def within(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path outside designated root: {relative}")
    return path


def policy_config():
    inputs = read_json(PROJECT / "configs/inputs.json")
    path = within(PROJECT, inputs["rca_log_policy"])
    policy = read_json(path)
    required = {
        "profile_id": "exact_pod_logs_allow_absence_v1", "status": "APPROVED",
        "candidate_policy": "retain_all_in_original_order", "matching": "exact_pod_name_only",
        "missing_policy": "fixed_absence_notice", "partial_or_changed_pair": "fail",
        "missing_reason": "exact_log_pair_unavailable", "underlying_cause": "UNKNOWN",
        "service_or_replica_mapping": False, "infer_normality_or_causality_from_absence": False,
        "kpi_column": "Latency",
    }
    if any(policy.get(key) != value for key, value in required.items()):
        raise ValueError("Unsupported or unapproved log evidence policy")
    for field in ("missing_notice", "kpi_notice"):
        if not isinstance(policy.get(field), str) or not policy[field].strip():
            raise ValueError(f"Empty policy text: {field}")
    return inputs, policy, sha256(path)


def check_node_files(node):
    """Reject runtime drift; a previously present pair cannot become absence."""
    if node["node_kind"] == "kpi":
        return
    for kind, relative in node["expected_paths"].items():
        path = within(ASSETS, relative)
        if node["evidence_available"]:
            source = node["sources"][kind]
            if not path.is_file() or path.stat().st_size != source["bytes"]:
                raise RuntimeError(f"Known exact log missing/changed: {relative}")
        elif path.exists() or path.is_symlink():
            raise RuntimeError(f"Previously absent log appeared; review evidence: {relative}")


def build_plans():
    inputs, policy, policy_hash = policy_config()
    validate_input_scope(inputs)
    connection = read_json(within(PROJECT, inputs["connection_evidence"]))
    validation = read_json(PROJECT / "docs/evidence/rca_preprocessing_validation.json")
    validated = {(c["system"], c["day"]): c for c in select_active_cases(validation["cases"])}
    selected = select_active_cases(connection["cases"])
    plans = {}
    for case in selected:
        system, day = case["system"], case["day"]
        key = f"{system}/{day}"
        vcase = validated[(system, day)]
        runtime_csv = f"LEMMA_RCA/{system}/Metrics/{system}_{day}.csv"
        runtime_logs = f"LEMMA_RCA/{system}/Log/{day}"
        if inputs["rca_files"][runtime_csv] != case["csv"] or inputs["rca_log_directories"][runtime_logs] != case["log_directory"]:
            raise RuntimeError(f"Input paths differ from connection evidence: {key}")
        csv_path = within(ASSETS, case["csv"])
        manifest_path = csv_path.parent / "manifest.json"
        manifest_hash = sha256(manifest_path)
        if manifest_hash != vcase["manifest_sha256"] or manifest_hash != case["manifest_sha256"]:
            raise RuntimeError(f"Approved input manifest changed: {key}")
        manifest = read_json(manifest_path)
        csv_hash = sha256(csv_path)
        if csv_hash != vcase["outputs"][csv_path.name]["sha256"]:
            raise RuntimeError(f"Approved CSV changed: {key}")
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            columns = next(csv.reader(stream))
        pods = manifest["logs"]["pods"]
        kpi = policy["kpi_column"]
        if columns != manifest["columns"] or len(columns) != len(set(columns)):
            raise RuntimeError(f"CSV columns/order changed or duplicated: {key}")
        if columns[-1] != kpi or set(columns) != set(pods) | {kpi} or kpi in pods:
            raise RuntimeError(f"Unclassified columns: {key}")
        records = {(r["pod"], r["kind"]): r for r in case["files"]}
        if len(records) != len(case["files"]):
            raise RuntimeError(f"Duplicate connection records: {key}")
        nodes = []
        for column in columns:
            if column == kpi:
                nodes.append({"name": column, "node_kind": "kpi", "evidence_available": None,
                              "reason": "kpi_not_pod", "sources": {},
                              "fixed_information": policy["kpi_notice"]})
                continue
            spec = pods[column]
            members = spec["members"]
            sources, expected_paths = {}, {}
            for kind in ("templates", "structured"):
                relative = f"{case['log_directory']}/{column}_messages_{kind}.csv"
                expected_paths[kind] = relative
                if spec["exact_unique_pair"]:
                    record = records[(column, kind)]
                    if len(members[kind]) != 1 or record["member"] != members[kind][0] or record["path"] != relative:
                        raise RuntimeError(f"Nonexact log source: {key}/{column}/{kind}")
                    if PurePosixPath(record["member"]).name != f"{column}_messages_{kind}.csv":
                        raise RuntimeError(f"Nonexact log name: {column}")
                    sources[kind] = {field: record[field] for field in ("path", "member", "bytes", "sha256")}
                elif members[kind] or (column, kind) in records:
                    raise RuntimeError(f"Partial/ambiguous pair is not approved absence: {key}/{column}")
            available = spec["exact_unique_pair"]
            node = {"name": column, "node_kind": "pod", "evidence_available": available,
                    "reason": "exact_pair_present" if available else policy["missing_reason"],
                    "underlying_cause": None if available else policy["underlying_cause"],
                    "expected_paths": expected_paths, "sources": sources,
                    "fixed_information": None if available else policy["missing_notice"]}
            check_node_files(node)
            nodes.append(node)
        missing = [n["name"] for n in nodes if n["evidence_available"] is False]
        available = [n["name"] for n in nodes if n["evidence_available"] is True]
        if set(missing) != set(case["missing_pods"]) or len(available) * 2 != len(records):
            raise RuntimeError(f"Coverage differs from verified connection: {key}")
        plans[key] = {
            "schema_version": 1, "policy_id": policy["profile_id"], "policy_sha256": policy_hash,
            "system": system, "day": day, "input_profile": inputs["input_profile"],
            "author_equivalence": "UNCONFIRMED", "csv": case["csv"], "csv_sha256": csv_hash,
            "input_manifest_sha256": manifest_hash, "columns": columns,
            "counts": {"pods": len(pods), "available": len(available), "missing": len(missing), "kpi": 1},
            "system_coverage_notice": (
                f"Exact pod log pairs are available for {len(available)} of {len(pods)} candidate pods. "
                f"{len(missing)} candidate pods have no matching log evidence in this case. "
                "All candidates remain included. Missing evidence does not establish normality, "
                "abnormality, absence of causal influence, or a restart/death event. "
                "The input KPI column is not a pod."),
            "nodes": nodes,
            "log_verification": "Current paths and sizes checked against TASK_032 hashes; full log bytes not rehashed in this preparation.",
            "summaries_generated": False, "full_rca_ready": False,
        }
    if len(plans) != len(selected) or set(plans) != {f"{s}/{d}" for s, d in validated}:
        raise RuntimeError("Case set changed or duplicated")
    return plans


def dispatch_summary(plan, node_name, summarize_exact_pair):
    """Callback handles an available exact pair; absent/KPI nodes bypass it.

Callback receives the unchanged node name and its two provenance records. It
must preserve the official prompt/selection and use the approved local client.
No callback is supplied by this preparation CLI; real generation is TASK_024.
"""
    nodes = {n["name"]: n for n in plan["nodes"]}
    node = nodes[node_name]
    check_node_files(node)
    if node["evidence_available"] is not True:
        return node["fixed_information"]
    result = summarize_exact_pair(node_name, node["sources"])
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"Empty/nontext summary: {node_name}")
    return result


def finalize_node_information(plan, generated_summaries):
    """Fill immutable absence/KPI entries after generation, without dropping nodes."""
    expected = {n["name"] for n in plan["nodes"] if n["evidence_available"] is True}
    if set(generated_summaries) != expected:
        raise ValueError("Provide exactly the available-pod summaries; missing/KPI entries cannot be generated or overwritten")
    return {name: dispatch_summary(plan, name, lambda pod, _: generated_summaries[pod])
            for name in plan["columns"]}


def prepare_plans(plans):
    inputs, policy, _ = policy_config()
    paths = {key: f"{policy['output_directory']}/{key}.json" for key in plans}
    payloads = {key: json.dumps(plan, ensure_ascii=False, indent=2) + "\n" for key, plan in plans.items()}
    # Validate all destinations before writing; never replace a different plan.
    for key, relative in paths.items():
        target = within(ASSETS, relative)
        if target.exists() and target.read_text(encoding="utf-8") != payloads[key]:
            raise RuntimeError(f"Existing evidence plan differs, not overwritten: {target}")
    for key, relative in paths.items():
        target = within(ASSETS, relative)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(payloads[key])
    inputs["rca_log_evidence_manifests"] = paths
    (PROJECT / "configs/inputs.json").write_text(json.dumps(inputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths


def verify_prepared_plans(plans=None):
    plans = build_plans() if plans is None else plans
    inputs, _, _ = policy_config()
    paths = inputs.get("rca_log_evidence_manifests", {})
    if set(paths) != set(plans):
        raise RuntimeError("Prepared evidence plan case set differs")
    for key, relative in paths.items():
        if read_json(within(ASSETS, relative)) != plans[key]:
            raise RuntimeError(f"Prepared evidence plan stale/changed: {key}")
    workspace = asset_path("runtime_workspace")
    for name, relative in {**inputs["rca_files"], **inputs["rca_log_directories"]}.items():
        runtime_path = workspace / "data" / name
        source_path = within(ASSETS, relative)
        if not runtime_path.exists() or runtime_path.resolve() != source_path:
            raise RuntimeError(f"Runtime input link missing/different: {name}")
    return {"status": "PASS", "cases": len(plans),
            "available_pods": sum(p["counts"]["available"] for p in plans.values()),
            "missing_pods": sum(p["counts"]["missing"] for p in plans.values()),
            "full_rca_ready": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Write plans only; no LLM calls or CSV log reads")
    args = parser.parse_args()
    plans = build_plans()
    if args.prepare:
        prepare_plans(plans)
    print(json.dumps(verify_prepared_plans(plans)))
