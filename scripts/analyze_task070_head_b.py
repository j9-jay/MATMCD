"""Aggregate a head B run (TASK_070) into one table for all methods.

Applies the frozen failure rule: a failed case-method run is scored as all
candidates tied (AC@k = k/n, RR = H_n/n). Ranking metrics are averaged over all
cases; evidence metrics (silver precision/recall, attribution precision) over the
completed runs that have a value. Since 2026-10-27 every method gets a case-bootstrap
95% CI of its mean Avg@5 (10,000 resamples, seed 0), plus per-service means and a
complete-case table; there are no pairwise tests (`paired` is kept for older analyses).

Usage: python -B analyze_task070_head_b.py <head_b run dir>
Writes <run dir>/analysis.json and prints a Markdown summary.
"""
import json
import sys
from pathlib import Path

import numpy as np

RANK_KEYS = ["AC@1", "AC@3", "AC@5", "Avg@5", "RR"]
EVIDENCE_KEYS = ["silver_precision", "silver_recall", "attribution_precision",
                 "strict_precision", "strict_recall", "strict_attribution_precision"]
PROPOSED = "state_fixed"  # 2026-10-27: state_fixed is the proposed method; state_dynamic is a reference
ROLES = {"state_fixed": "proposed", "state_dynamic": "reference"}
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
    # Every method failed on this case: take the candidate count from the case data itself
    # (services in the node table; label-free). Added 2026-10-25.
    import task070_rcaeval as rc
    path = {c["id"]: c["path"] for c in rc.cases()}[case]
    return len(rc.node_table(path)[1]) - 1


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
            vals = [r[k] for r in done if r.get(k) is not None]
            entry[k] = float(np.mean(vals)) if vals else None
            entry[f"{k}_n"] = len(vals)
        entry["missing_names"] = int(sum(r["missing_names"] for r in done))
        entry["seconds_mean"] = float(np.mean([r["seconds"] for r in done])) if done else None
        table[m] = entry
    # 2026-10-27 plan: one table for all methods (state_fixed = proposed, state_dynamic =
    # reference), each mean with a case-bootstrap 95% CI; no pairwise tests.
    rng = np.random.default_rng(SEED)
    for m in methods:
        vals = np.array([s["Avg@5"] for s in scores[m]])
        boot = vals[rng.integers(0, len(vals), size=(10000, len(vals)))].mean(axis=1)
        table[m]["Avg@5_ci95"] = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
        unit_kinds = [k for r in summary["methods"][m] if r["status"] == "COMPLETE" for k in r.get("evidence_roles", [])]
        if unit_kinds:
            table[m]["document_share"] = float(np.mean([k == "document" for k in unit_kinds]))
    import task070_rcaeval as rc
    service = {c["id"]: c["path"].split("/")[1].rsplit("_", 1)[0] for c in rc.cases()}
    services = sorted({service[c] for c in cases})
    per_service = {m: {s: float(np.mean([scores[m][i]["Avg@5"] for i, c in enumerate(cases) if service[c] == s]))
                       for s in services} for m in methods}
    failed_any = {c for m in methods for c in table[m]["failed_cases"]}
    complete = [i for i, c in enumerate(cases) if c not in failed_any]
    complete_only = {m: float(np.mean([scores[m][i]["Avg@5"] for i in complete])) if complete else None for m in methods}
    out = {"run": run.name, "cases": len(cases), "failure_rule": "failed run = all candidates tied",
           "roles": {m: ROLES.get(m, "comparison") for m in methods},
           "bootstrap": {"resamples": 10000, "seed": SEED, "note": "per-method CI only; no pairwise tests"},
           "methods": table, "per_service_Avg@5": per_service,
           "complete_cases": {"n": len(complete), "Avg@5": complete_only},
           "per_case": {m: dict(zip(cases, scores[m])) for m in methods}}
    (run / "analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    fmt = lambda v: "-" if v is None else f"{v:.3f}"
    print("| method | role | Avg@5 (95% CI) | AC@1 | AC@3 | RR | failed | strict P | strict R | citation P | doc share |")
    print("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for m, e in table.items():
        lo, hi = e["Avg@5_ci95"]
        print(f"| {m} | {ROLES.get(m, 'comparison')} | {e['Avg@5']:.3f} [{lo:.3f}, {hi:.3f}] | {e['AC@1']:.3f} | "
              f"{e['AC@3']:.3f} | {e['RR']:.3f} | {e['failed']} | {fmt(e.get('strict_precision'))} | "
              f"{fmt(e.get('strict_recall'))} | {fmt(e.get('attribution_precision'))} | {fmt(e.get('document_share'))} |")
    print()
    print("| method | " + " | ".join(services) + " |")
    print("|---|" + "---:|" * len(services))
    for m in methods:
        print(f"| {m} | " + " | ".join(f"{per_service[m][s]:.3f}" for s in services) + " |")
    print()
    print(f"complete cases (no method failed): {len(complete)} of {len(cases)}: "
          + ", ".join(f"{m} {fmt(v)}" for m, v in complete_only.items()))


if __name__ == "__main__":
    main()
