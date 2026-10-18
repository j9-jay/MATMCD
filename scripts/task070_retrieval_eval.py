"""TASK_070 retrieval-quality metrics on development runs (silver labels, R5).

Silver relevant unit for a case: an observation unit of the root-cause service
whose minutes are non-empty (it shows deviations or activity) - defined from the
label only at evaluation time. For pairs that involve the root-cause service:
- silver_precision: share of the K evidence units that are silver relevant
- silver_hit: 1 if at least one silver relevant unit is in the evidence
- attribution: share of cited units that are silver relevant
Usage: python -B task070_retrieval_eval.py <pilot_dir> [<pilot_dir> ...]
"""
import json
import sys
from pathlib import Path

import numpy as np

import task070_rcaeval as rc
from task070_common import WORK, write_json


def silver_units(case_id, root):
    units = [json.loads(l) for l in (WORK / "corpus/re2ob" / f"{case_id}.jsonl").read_text(encoding="utf-8").splitlines()]
    return {u["id"] for u in units if u["role"] == "observation" and root in u["services"]
            and u["minutes"] and (u["kind"] != "metric" or len(u["minutes"]) > 0)}


def main(dirs):
    paths = {c["id"]: c["path"] for c in rc.cases("dev")}
    report = {}
    for d in map(Path, dirs):
        for method_dir in sorted(p for p in d.iterdir() if p.is_dir()):
            for f in sorted(method_dir.glob("*.jsonl")):
                case_id = f.stem
                root = rc.evaluation_label(paths[case_id])["root_cause_service"]
                silver = silver_units(case_id, root)
                rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()]
                rel = [r for r in rows if root in (r["cause"], r["effect"])]
                if not rel or not rows[0]["evidence_ids"] and method_dir.name == "none":
                    continue
                prec = [np.mean([e in silver for e in r["evidence_ids"]]) if r["evidence_ids"] else 0.0 for r in rel]
                hit = [any(e in silver for e in r["evidence_ids"]) for r in rel]
                cited = [c for r in rel for c in r["parsed"]["cited_unit_ids"]]
                report.setdefault(method_dir.name, {})[case_id] = {
                    "pairs_with_root": len(rel), "silver_units": len(silver),
                    "silver_precision": float(np.mean(prec)), "silver_hit": float(np.mean(hit)),
                    "attribution_precision": float(np.mean([c in silver for c in cited])) if cited else None}
    for method, cases in report.items():
        cases["_mean"] = {k: float(np.mean([v[k] for v in cases.values() if v.get(k) is not None]))
                          for k in ("silver_precision", "silver_hit", "attribution_precision")}
    write_json(WORK / "p2_pilot" / "retrieval_eval.json", report)
    for method, cases in report.items():
        print(method, {k: round(v, 3) for k, v in cases["_mean"].items()})


if __name__ == "__main__":
    main(sys.argv[1:])
