"""Synthetic D03 A routing and D04 withholding checks; no RCA experiment."""
import copy
import hashlib
import json
import traceback
from datetime import datetime, timezone

import numpy as np

from project_paths import PROJECT
from rca_case_scope import active_cases, case_key
from rca_evaluation import evaluate_case, evaluate_active_cases, evaluation_context
from rca_log_evidence import sha256
from rca_ranking import encode_rng_state, rank_stage_with_original_rwr
from setup_graphviz import assert_original_source, python_packages, source_hashes


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = PROJECT / f"docs/evidence/rca_approved_protocol_{stamp}.json"
    report = {"status": "IN_PROGRESS", "checked_utc": stamp, "checks": [],
              "actual_experiment_results": False, "inference_calls": 0,
              "synthetic_counts_only": True, "full_RCA_integration": False}
    source_before, packages_before = source_hashes(), python_packages()
    configs_before = {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}
    rng_before = np.random.get_state()

    def expect(name, condition):
        report["checks"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    def rejects(name, callback):
        try:
            callback()
        except ValueError:
            expect(name, True)
        else:
            expect(name, False)

    try:
        assert_original_source()
        expect("official_37_files_match_archive", len(source_before) == 37)
        initial = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        refined = np.array([[0, 1, 0], [0, 0, 0], [1, 0, 0]])
        roles = {"PC": "initial", "CC_without_external_information": "initial",
                 "MATMCD": "refined", "MATMCD_RE": "refined"}
        for stage, role in roles.items():
            record = rank_stage_with_original_rwr(stage, initial, refined, ["A", "B", "Latency"])
            matrix = initial if role == "initial" else refined
            expect(f"D03_A_graph:{stage}", record["graph_role"] == role and
                   record["graph"]["sha256_c_order_bytes"] == hashlib.sha256(matrix.tobytes()).hexdigest())
            expect(f"no_seed_override:{stage}", record["seed_assigned"] is False)
        rejects("unknown_stage_rejected", lambda: rank_stage_with_original_rwr("unknown", initial, refined, ["A", "B", "Latency"]))
        rejects("no_missing_refined_graph_fallback", lambda: rank_stage_with_original_rwr("MATMCD", initial, None, ["A", "B", "Latency"]))

        # Full column inventories are metadata. Counts below are artificial,
        # not computed from the actual metrics or logs.
        fixtures = {}
        for c in active_cases():
            key = case_key(c)
            protocol, _, columns, protocol_hash, _ = evaluation_context(key)
            fixture = copy.deepcopy(record)
            counts = [float(len(columns) - i) for i in range(len(columns))]
            fixture.update(stage="MATMCD", graph_role="refined", protocol_id=protocol["profile_id"],
                           protocol_sha256=protocol_hash, labels_in_original_order=columns,
                           counts_in_original_order=counts,
                           start_node={"index": len(columns) - 1, "name": columns[-1]},
                           ranking=[{"rank": i + 1, "node": name, "visits": counts[i]}
                                    for i, name in enumerate(columns)])
            fixtures[key] = fixture
        result = evaluate_active_cases(fixtures)
        pr = [r for r in result["cases"] if r["case"].startswith("Product_Review/")]
        expect("active_PR_provisional_scores", bool(pr) and all(r["evaluation_status"] == "PROVISIONAL_SCORE" and
               r["ground_truth_status"] == "PROVISIONAL_RELEASED_HELPER_LABEL" for r in pr))
        cc = next(r for r in result["cases"] if r["case"] == "Cloud_Computing/20231207")
        expect("CC_both_ranks_no_single_score", len(cc["candidate_ranks"]) == 2 and cc["evaluation"] is None)
        expect("no_active_case_or_partial_aggregate", result["aggregate"] is None and result["partial_aggregate"] is None and
               result["case_count"] == len(active_cases()) and result["scored_case_count"] == len(pr))
        key = case_key(active_cases()[0])
        all_ties = copy.deepcopy(fixtures[key])
        all_ties["counts_in_original_order"] = [1.] * len(all_ties["ranking"])
        for item in all_ties["ranking"]:
            item["visits"] = 1.
        evaluate_case(key, all_ties)
        expect("KPI_kept_and_stable_ties_accepted", all_ties["ranking"][-1]["node"] == "Latency")
        swapped = copy.deepcopy(all_ties)
        swapped["ranking"][0], swapped["ranking"][1] = swapped["ranking"][1], swapped["ranking"][0]
        for i, item in enumerate(swapped["ranking"]):
            item["rank"] = i + 1
        rejects("tie_reordering_rejected", lambda: evaluate_case(key, swapped))
        missing = copy.deepcopy(fixtures[key])
        missing["ranking"].pop()
        rejects("KPI_removal_rejected", lambda: evaluate_case(key, missing))
        changed = copy.deepcopy(fixtures[key])
        changed["protocol_sha256"] = "different_profile"
        rejects("protocol_mixing_rejected", lambda: evaluate_case(key, changed))
        changed = copy.deepcopy(fixtures[key])
        changed["counts_in_original_order"][0] = float("nan")
        rejects("nonfinite_count_rejected", lambda: evaluate_case(key, changed))
        rejects("excluded_case_rejected", lambda: evaluate_case("Product_Review/20210517", fixtures[key]))
        rejects("newly_excluded_PR20220606_rejected", lambda: evaluate_case("Product_Review/20220606", fixtures[key]))
        extra = {**fixtures, "Product_Review/20220606": fixtures[key]}
        rejects("excluded_case_cannot_enter_aggregate", lambda: evaluate_active_cases(extra))
        partial = dict(fixtures)
        partial.pop("Cloud_Computing/20231207")
        rejects("partial_aggregate_request_rejected", lambda: evaluate_active_cases(partial))
        mixed = copy.deepcopy(fixtures)
        mixed[key].update(stage="PC", graph_role="initial")
        rejects("different_stage_aggregate_rejected", lambda: evaluate_active_cases(mixed))
        cc_key = "Cloud_Computing/20231207"
        alternate = copy.deepcopy(fixtures[cc_key])
        names = alternate["labels_in_original_order"]
        alternate["counts_in_original_order"] = [0.] * len(names)
        alternate["counts_in_original_order"][names.index(cc["candidate_ranks"][1]["pod"])] = 1000.
        alternate["ranking"] = [{"rank": i + 1, "node": n, "visits": v} for i, (n, v) in
                                enumerate(sorted(zip(names, alternate["counts_in_original_order"]), key=lambda p: p[1], reverse=True))]
        other = evaluate_case(cc_key, alternate)
        expect("CC_rank1_candidate_still_not_selected", other["candidate_ranks"][1]["rank"] == 1 and other["evaluation"] is None)
        report["status"] = "PASS"
    except Exception:
        report.update(status="FAILED", error=traceback.format_exc())
    finally:
        np.random.set_state(rng_before)
        report["preservation"] = {"official_source": source_hashes() == source_before,
                                  "python_packages": python_packages() == packages_before,
                                  "configs": configs_before == {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")},
                                  "global_numpy_rng": encode_rng_state(np.random.get_state()) == encode_rng_state(rng_before)}
        if not all(report["preservation"].values()):
            report["status"] = "FAILED"
        report["script_sha256"] = {name: sha256(PROJECT / "scripts" / name) for name in
                                   ("rca_ranking.py", "rca_evaluation.py", "check_rca_approved_protocol.py")}
        report["protocol_sha256"] = sha256(PROJECT / "configs/rca_protocol.json")
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "report": str(path)}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
