"""Aggregate the head A evaluation (TASK_070), which ran in several folders.

Rows from all given run folders are merged per method and case; a case that
appears twice for one method is an error. A case with no row (the runner stopped
on it) or with status FAILED is scored by the frozen failure rule: all candidates
tied. The candidate count per case comes from a head B run on the same cases.
Paired comparisons as in analyze_task070_head_b.

Usage: python -B analyze_task070_head_a.py <out json> <head B run dir> <head A run dir>...
"""
import json
import sys
from pathlib import Path

import numpy as np

from analyze_task070_head_b import PROPOSED, RANK_KEYS, SEED, n_candidates, paired, tied_metrics

ORDER = ["pc_only", "none", "flat", "role_only", "state_fixed", "state_dynamic", "matmcd"]


def main():
    out_path, head_b, runs = Path(sys.argv[1]), Path(sys.argv[2]), [Path(p) for p in sys.argv[3:]]
    b_methods = list(json.loads((head_b / "summary.json").read_text(encoding="utf-8"))["methods"])
    summaries = {run: json.loads((run / "summary.json").read_text(encoding="utf-8")) for run in runs}
    cases = max((s["cases"] for s in summaries.values()), key=len)
    rows = {}
    for run, summary in summaries.items():
        if summary["cases"] != cases[cases.index(summary["cases"][0]):][:len(summary["cases"])]:
            raise RuntimeError(f"{run.name}: cases are not a contiguous part of the full case list")
        for method, items in summary["methods"].items():
            for r in items:
                key = (method, r["case"])
                if key in rows:
                    raise RuntimeError(f"Duplicate row {key}")
                rows[key] = {**r, "run": run.name}
    methods = [m for m in ORDER if any(k[0] == m for k in rows)]
    scores, table = {}, {}
    for m in methods:
        per_case, failed, missing = [], [], []
        for c in cases:
            r = rows.get((m, c))
            if r is None or r.get("status", "COMPLETE") != "COMPLETE":
                (missing if r is None else failed).append(c if r is None else f"{c}: {r.get('error')}")
                per_case.append(tied_metrics(n_candidates(head_b, b_methods, c)))
            else:
                per_case.append({k: r[k] for k in RANK_KEYS})
        scores[m] = per_case
        done = [rows[(m, c)] for c in cases if (m, c) in rows and rows[(m, c)].get("status", "COMPLETE") == "COMPLETE"]
        entry = {k: float(np.mean([p[k] for p in per_case])) for k in RANK_KEYS}
        entry.update({"failed": failed, "missing_scored_tied": missing,
                      "runs": sorted({rows[(m, c)]["run"] for c in cases if (m, c) in rows})})
        yes = [r["constraint_counts"]["yes"] for r in done if "yes" in r.get("constraint_counts", {})]
        edges = [r["graph_edges"] for r in done if "graph_edges" in r]
        if yes:
            entry["yes_mean"] = float(np.mean(yes))
        if edges:
            entry["graph_edges_mean"] = float(np.mean(edges))
        table[m] = entry
    rng = np.random.default_rng(SEED)
    comparisons = {f"{PROPOSED}_vs_{o}": {k: paired([s[k] for s in scores[PROPOSED]], [s[k] for s in scores[o]], rng)
                                          for k in ["Avg@5", "AC@1", "RR"]}
                   for o in methods if o != PROPOSED}
    out = {"runs": [r.name for r in runs], "head_b_for_candidate_counts": head_b.name, "cases": len(cases),
           "failure_rule": "failed or missing run = all candidates tied",
           "methods": table, "comparisons": comparisons, "per_case": {m: dict(zip(cases, scores[m])) for m in methods}}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("| method | Avg@5 | AC@1 | AC@3 | RR | failed+missing | mean Yes | mean edges |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for m, e in table.items():
        print(f"| {m} | {e['Avg@5']:.3f} | {e['AC@1']:.3f} | {e['AC@3']:.3f} | {e['RR']:.3f} | "
              f"{len(e['failed']) + len(e['missing_scored_tied'])} | {e.get('yes_mean', float('nan')):.1f} | "
              f"{e.get('graph_edges_mean', float('nan')):.1f} |")
    print()
    print("| comparison | metric | diff | 95% CI | p | W/L/T |")
    print("|---|---|---:|---|---:|---|")
    for name, comp in comparisons.items():
        for k, r in comp.items():
            print(f"| {name} | {k} | {r['mean_diff']:+.3f} | [{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}] | "
                  f"{r['p_permutation']:.4f} | {r['wins']}/{r['losses']}/{r['ties']} |")
    for m, e in table.items():
        for item in e["failed"] + e["missing_scored_tied"]:
            print(m, item)


if __name__ == "__main__":
    main()
