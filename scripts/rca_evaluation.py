"""Approved D04 policy on recorded predictions; no fitting or model calls.

Ground-truth metadata is used only after prediction, never for LLM/RAG inputs.
CC candidate ranks are preserved without selecting a winner or scoring it.
"""
import math

from project_paths import ASSETS, PROJECT
from rca_case_scope import active_cases, case_key, validate_input_scope
from rca_log_evidence import read_json, sha256, within
from rca_metrics import evaluate_ranks


def evaluation_context(key):
    path = PROJECT / "configs/rca_protocol.json"
    protocol = read_json(path)
    if protocol["status"] != "APPROVED" or protocol["d03"]["choice"] != "A":
        raise ValueError("Expected approved released-code A protocol")
    cases = protocol["d04"]["cases"]
    if [case_key(c) for c in cases] != [case_key(c) for c in active_cases()]:
        raise ValueError("Evaluation cases differ from active scope")
    matching = [c for c in cases if case_key(c) == key]
    if len(matching) != 1:
        raise ValueError(f"Not an active evaluation case: {key}")
    inputs = read_json(PROJECT / "configs/inputs.json")
    validate_input_scope(inputs)
    plan_path = within(ASSETS, inputs["rca_log_evidence_manifests"][key])
    plan = read_json(plan_path)
    case = matching[0]
    columns = plan["columns"]
    prefix = case["official_helper_label"]
    candidates = [n for n in columns if n == prefix or n.startswith(prefix + "-")]
    if candidates != case["candidate_pods"]:
        raise ValueError("Candidate inventory changed; do not remap ground truth automatically")
    if case["evaluation_pod"] is not None and candidates != [case["evaluation_pod"]]:
        raise ValueError("Only the approved unique provisional mapping may be scored")
    return protocol, case, columns, sha256(path), sha256(plan_path)


def evaluate_case(key, ranking_record):
    """Return per-case scores for provisional PR, candidate ranks only for CC.

    Input must be a complete single stage record from rank_stage_with_original_rwr.
    No missing pods, KPI removal, ties reordering or cross-profile mixing allowed.
    """
    protocol, case, columns, protocol_hash, plan_hash = evaluation_context(key)
    d04 = protocol["d04"]
    stage = ranking_record["stage"]
    role = protocol["d03"]["rwr_graph_by_stage"].get(stage)
    if (role is None or ranking_record.get("protocol_id") != protocol["profile_id"] or
            ranking_record.get("protocol_sha256") != protocol_hash or
            ranking_record.get("graph_role") != role or ranking_record.get("d03_choice") != "A"):
        raise ValueError("Prediction protocol/stage differs from approved configuration")
    if (ranking_record["parameters"] != d04["rwr_parameters"] or
            ranking_record["seed_assigned"] is not False or
            ranking_record["labels_in_original_order"] != columns or
            ranking_record["start_node"] != {"index": len(columns) - 1, "name": columns[-1]}):
        raise ValueError("RWR conditions or complete candidate order differ")
    counts = ranking_record["counts_in_original_order"]
    if len(counts) != len(columns) or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in counts):
        raise ValueError("Invalid complete RWR count vector")
    expected = [{"rank": i + 1, "node": name, "visits": float(count)} for i, (name, count) in
                enumerate(sorted(zip(columns, counts), key=lambda pair: pair[1], reverse=True))]
    if ranking_record["ranking"] != expected:
        raise ValueError("Ranking differs from complete stable descending visit order")
    ranks = {r["node"]: r["rank"] for r in expected}
    pod = case["evaluation_pod"]
    score = evaluate_ranks([ranks[pod]]) if pod is not None else None
    return {"case": key, "stage": stage, "protocol_id": protocol["profile_id"],
            "protocol_sha256": protocol_hash, "evidence_plan_sha256": plan_hash,
            "author_run_equivalence": "UNCONFIRMED", "ground_truth_status": case["status"],
            "candidate_ranks": [{"pod": p, "rank": ranks[p]} for p in case["candidate_pods"]],
            "evaluation_pod": pod, "evaluation": score, "limitation": case["limitation"],
            "evaluation_status": "PROVISIONAL_SCORE" if pod else "WITHHELD_UNRESOLVED_GROUND_TRUTH"}


def evaluate_active_cases(predictions):
    """Exactly one complete record per active case, for the same stage.

    No partial aggregate is emitted. With current CC metadata, the whole-set
    aggregate is always withheld. Updating ground truth requires a new reviewed
    protocol, not passing a preferred pod or externally computed score here.
    """
    keys = [case_key(c) for c in active_cases()]
    if set(predictions) != set(keys):
        raise ValueError("Require exactly the active cases, one record per case")
    results = [evaluate_case(key, predictions[key]) for key in keys]
    if len({r["stage"] for r in results}) != 1 or len({r["protocol_sha256"] for r in results}) != 1:
        raise ValueError("Do not combine different stages or protocol versions")
    unresolved = [r["case"] for r in results if r["evaluation"] is None]
    aggregate = None if unresolved else evaluate_ranks([r["evaluation"]["ranks"][0] for r in results])
    return {"cases": results, "aggregate": aggregate, "partial_aggregate": None,
            "aggregate_status": "WITHHELD_UNRESOLVED_GROUND_TRUTH" if unresolved else "LOCAL_EQUAL_CASE_WEIGHT",
            "unresolved_cases": unresolved, "case_count": len(keys),
            "scored_case_count": len(results) - len(unresolved), "paper_table4_aggregate_equivalence": "UNCONFIRMED"}
