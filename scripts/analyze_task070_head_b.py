"""Aggregate a head B run (TASK_070) and compare methods case by case.

Applies the frozen failure rule: a failed case-method run is scored as all
candidates tied (AC@k = k/n, RR = H_n/n). Ranking metrics are averaged over all
cases; evidence metrics (silver precision/recall, attribution precision) over the
completed runs that have a value. Paired comparisons use the same cases for both
methods: bootstrap 95% CI of the mean difference (10,000 resamples) and a
two-sided sign-flip permutation test (100,000 draws), both with seed 0.

Usage: python -B analyze_task070_head_b.py <head_b run dir>
Writes <run dir>/analysis.json and prints a Markdown summary.
"""
import json
import sys
from pathlib import Path

import numpy as np

RANK_KEYS = ["AC@1", "AC@3", "AC@5", "Avg@5", "RR"]
EVIDENCE_KEYS = ["silver_precision", "silver_recall", "attribution_precision"]
PROPOSED = "state_dynamic"
SEED = 0


def tied_metrics(n):
    ac = {k: min(int(k[3:]), n) / n for k in ["AC@1", "AC@2", "AC@3", "AC@4", "AC@5"]}
    return {"AC@1": ac["AC@1"], "AC@3": ac["AC@3"], "AC@5": ac["AC@5"],
            "Avg@5": sum(ac.values()) / 5, "RR": sum(1.0 / p for p in range(1, n + 1)) / n}


def n_candidates(run, method_names, case):
    for m in method_names:
        path = run / m / f"{case}.json"
        if path.exists():
            return len(json.loads(path.read_text(encoding="utf-8"))["mean_positions"])
    raise RuntimeError(f"No completed run gives the candidate count for {case}")


def paired(a, b, rng):
    d = np.asarray(a) - np.asarray(b)
    boot = d[rng.integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    flips = rng.choice([-1.0, 1.0], size=(100000, len(d)))
    perm = np.abs((flips * d).mean(axis=1))
    p = (1 + np.sum(perm >= abs(d.mean()) - 1e-12)) / (1 + len(perm))
    return {"mean_diff": float(d.mean()), "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "p_permutation": float(p), "wins": int(np.sum(d > 0)), "losses": int(np.sum(d < 0)), "ties": int(np.sum(d == 0))}


def main():
    run = Path(sys.argv[1])
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    cases, methods = summary["cases"], list(summary["methods"])
    scores, table = {}, {}
    for m in methods:
        rows = {r["case"]: r for r in summary["methods"][m]}
        if set(rows) != set(cases):
            raise RuntimeError(f"{m}: cases differ from the run's case list")
        per_case = []
        for c in cases:
            r = rows[c]
            per_case.append({k: r[k] for k in RANK_KEYS} if r["status"] == "COMPLETE"
                            else tied_metrics(n_candidates(run, methods, c)))
        scores[m] = per_case
        done = [rows[c] for c in cases if rows[c]["status"] == "COMPLETE"]
        entry = {k: float(np.mean([p[k] for p in per_case])) for k in RANK_KEYS}
        entry["failed"] = len(cases) - len(done)
        entry["failed_cases"] = [c for c in cases if rows[c]["status"] != "COMPLETE"]
        for k in EVIDENCE_KEYS:
            vals = [r[k] for r in done if r[k] is not None]
            entry[k] = float(np.mean(vals)) if vals else None
            entry[f"{k}_n"] = len(vals)
        entry["missing_names"] = int(sum(r["missing_names"] for r in done))
        entry["seconds_mean"] = float(np.mean([r["seconds"] for r in done])) if done else None
        table[m] = entry
    rng = np.random.default_rng(SEED)
    comparisons = {}
    for other in [m for m in methods if m != PROPOSED]:
        comparisons[f"{PROPOSED}_vs_{other}"] = {
            k: paired([s[k] for s in scores[PROPOSED]], [s[k] for s in scores[other]], rng)
            for k in ["Avg@5", "AC@1", "RR"]}
    out = {"run": run.name, "cases": len(cases), "failure_rule": "failed run = all candidates tied",
           "paired_test": {"bootstrap": 10000, "permutation_sign_flip": 100000, "seed": SEED},
           "methods": table, "comparisons": comparisons,
           "per_case": {m: dict(zip(cases, scores[m])) for m in methods}}
    (run / "analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("| method | Avg@5 | AC@1 | AC@3 | RR | failed | silver P | silver R | attribution P |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    fmt = lambda v: "-" if v is None else f"{v:.3f}"
    for m, e in table.items():
        print(f"| {m} | {e['Avg@5']:.3f} | {e['AC@1']:.3f} | {e['AC@3']:.3f} | {e['RR']:.3f} | {e['failed']} | "
              f"{fmt(e['silver_precision'])} | {fmt(e['silver_recall'])} | {fmt(e['attribution_precision'])} |")
    print()
    print("| comparison | metric | diff | 95% CI | p | W/L/T |")
    print("|---|---|---:|---|---:|---|")
    for name, comp in comparisons.items():
        for k, r in comp.items():
            print(f"| {name} | {k} | {r['mean_diff']:+.3f} | [{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}] | "
                  f"{r['p_permutation']:.4f} | {r['wins']}/{r['losses']}/{r['ties']} |")


if __name__ == "__main__":
    main()
