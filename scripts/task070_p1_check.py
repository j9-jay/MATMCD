"""TASK_070 P1 check: build dev corpora and run the label-free PC-only baseline.

No LLM calls. Development split only (D-6); test cases are not loaded.
Writes MATMCD_DATA/task070/p1_check/<UTC>/report.json.
"""
import os
from datetime import datetime, timezone

import numpy as np

import task070_corpus as tc
import task070_judge as tj
import task070_metrics as tm
import task070_output_head as oh
import task070_rcaeval as rc
from task070_common import CAUSAL_DATA_DIR, WORK, import_official, write_json

PAPER_PC_TABLE = {  # MATMCD Table 1/2, PC row (Prc, F1, FPR, SHD, NHD)
    "Auto_MPG": [0.11, 0.14, 0.40, 8, 0.32], "DWD_climate": [0.14, 0.15, 0.20, 9, 0.25],
    "Sachs": [0.38, 0.44, 0.15, 24, 0.19], "asia": [0.50, 0.50, 0.07, 6, 0.09],
    "child": [0.30, 0.34, 0.06, 24, 0.06],
}


def judge_selftest():
    messages, mapping = tj.build_messages("ctx", ["A", "B"], "A", "B", [{"id": "u1", "text": "t"}])
    ok = tj.parse("Because [E1]. <Yes>", mapping)
    assert ok == {"yes": True, "cited": ["E1"], "cited_unit_ids": ["u1"], "invalid_citations": []}
    assert tj.parse("no [E9]\n<No>", mapping)["invalid_citations"] == ["E9"]
    try:
        tj.parse("maybe", mapping)
        raise AssertionError("missing answer must fail")
    except ValueError:
        pass
    return {"prompt_version": tj.PROMPT_VERSION, "example_user_prompt": messages[1]["content"]}


def main():
    out = WORK / "p1_check" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {"judge": judge_selftest(), "causal_discovery_pc": {}, "rcaeval_dev_pc_only": {}}

    data_mod = import_official("matmcd_data", "Utils/data.py")
    cwd = os.getcwd()
    os.chdir(CAUSAL_DATA_DIR)
    try:
        for name, paper in PAPER_PC_TABLE.items():
            values, truth, labels = data_mod.load_data_from_csv(name)
            metrics = tm.graph_metrics(oh.fit_graph(values, labels), truth)
            ours = [metrics["Precision"], metrics["F1 Score"], metrics["FPR"], metrics["SHD"], metrics["NHD"]]
            report["causal_discovery_pc"][name] = {"rows": int(values.shape[0]), "ours": ours, "paper_pc_row": paper}
    finally:
        os.chdir(cwd)

    case_results, corpus_sizes = [], {}
    for case in rc.cases("dev"):
        _, units = tc.write_case_corpus(case)
        corpus_sizes[case["id"]] = len(units)
        values, labels, info = rc.node_table(case["path"])
        ranking = oh.rwr_rankings(oh.fit_graph(values, labels), labels)
        answer = rc.evaluation_label(case["path"])["root_cause_service"]
        per_rep = [tm.rca_case_metrics(r["ranking"], answer, labels[-1]) for r in ranking["runs"]]
        mean = {k: float(np.mean([p[k] for p in per_rep])) for k in ("AC@1", "AC@3", "AC@5", "Avg@5", "RR")}
        case_results.append({"case": case["id"], "nodes": len(labels), **mean,
                             "by_mean_counts": tm.rca_case_metrics(ranking["ranking_by_mean"], answer, labels[-1])})
    report["rcaeval_dev_pc_only"] = {
        "cases": case_results,
        "mean_over_cases_and_rwr_reps": {k: float(np.mean([c[k] for c in case_results]))
                                          for k in ("AC@1", "AC@3", "AC@5", "Avg@5", "RR")},
        "chance_Avg@5": float(np.mean([c["by_mean_counts"]["chance_Avg@5"] for c in case_results])),
        "corpus_units_per_case": corpus_sizes,
    }
    write_json(out / "report.json", report)
    print(out)
    print(report["rcaeval_dev_pc_only"]["mean_over_cases_and_rwr_reps"])


if __name__ == "__main__":
    main()
