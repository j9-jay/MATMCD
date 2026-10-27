"""Aggregate the head A evaluation (TASK_070), which ran in several folders.

Rows from all given run folders are merged per method and case; a case that
appears twice for one method is an error. A run folder may be given as
<dir>=m1,m2 to take only those methods from it (v3, 2026-10-27: pc_only, none and
matmcd do not read the evidence corpus, so their v1 rows are reused). A case with
no row (the runner stopped on it) or with status FAILED is scored by the frozen
failure rule: all candidates tied. The candidate count per case comes from a head B
run on the same cases.

Since 2026-10-27 the output is one table for all methods, as in
analyze_task070_head_b: per-method case-bootstrap 95% CI of mean Avg@5 (10,000
resamples, seed 0), per-service means, a complete-case table and the document share
of the selected evidence; no pairwise tests. The document share reads the roles of
the evidence ids from the current (v3) case corpus, so it is reported only for runs
given with --v3.

Usage: python -B analyze_task070_head_a.py <out json> <head B run dir> [--v3 <dir>[=m,...]]... [<dir>[=m,...]]...
"""
import json
import sys
from pathlib import Path

import numpy as np

from analyze_task070_head_b import RANK_KEYS, ROLES, SEED, n_candidates, tied_metrics
from task070_common import WORK

ORDER = ["pc_only", "none", "flat", "role_only", "state_fixed", "state_dynamic", "matmcd"]


def parse_runs(args):
    runs, v3 = [], set()
    i = 0
    while i < len(args):
        is_v3 = args[i] == "--v3"
        if is_v3:
            i += 1
        path, _, only = args[i].partition("=")
        runs.append((Path(path), set(only.split(",")) if only else None))
        if is_v3:
            v3.add(Path(path).name)
        i += 1
    return runs, v3


def document_share(run, method, case):
    pairs = run / method / f"{case}.jsonl"
    if not pairs.exists():
        return None
    corpus = WORK / "corpus/re2ob" / f"{case}.jsonl"
    role = {u["id"]: u["role"] for u in map(json.loads, corpus.read_text(encoding="utf-8").splitlines())}
    ids = [i for line in pairs.read_text(encoding="utf-8").splitlines() for i in json.loads(line)["evidence_ids"]]
    return (sum(role[i] == "document" for i in ids), len(ids)) if ids else None


def main():
    out_path, head_b = Path(sys.argv[1]), Path(sys.argv[2])
    runs, v3 = parse_runs(sys.argv[3:])
    b_methods = list(json.loads((head_b / "summary.json").read_text(encoding="utf-8"))["methods"])
    summaries = {run: (json.loads((run / "summary.json").read_text(encoding="utf-8")), only) for run, only in runs}
    cases = max((s["cases"] for s, _ in summaries.values()), key=len)
    rows = {}
    for run, (summary, only) in summaries.items():
        if summary["cases"] != cases[cases.index(summary["cases"][0]):][:len(summary["cases"])]:
            raise RuntimeError(f"{run.name}: cases are not a contiguous part of the full case list")
        for method, items in summary["methods"].items():
            if only is not None and method not in only:
                continue
            for r in items:
                key = (method, r["case"])
                if key in rows:
                    raise RuntimeError(f"Duplicate row {key}")
                rows[key] = {**r, "run": run.name, "run_dir": run}
    methods = [m for m in ORDER if any(k[0] == m for k in rows)]
    scores, table = {}, {}
    rng = np.random.default_rng(SEED)
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
        vals = np.array([s["Avg@5"] for s in per_case])
        boot = vals[rng.integers(0, len(vals), size=(10000, len(vals)))].mean(axis=1)
        entry["Avg@5_ci95"] = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
        entry.update({"failed": failed, "missing_scored_tied": missing,
                      "runs": sorted({rows[(m, c)]["run"] for c in cases if (m, c) in rows})})
        yes = [r["constraint_counts"]["yes"] for r in done if "yes" in r.get("constraint_counts", {})]
        edges = [r["graph_edges"] for r in done if "graph_edges" in r]
        if yes:
            entry["yes_mean"] = float(np.mean(yes))
        if edges:
            entry["graph_edges_mean"] = float(np.mean(edges))
        shares = [document_share(r["run_dir"], m, r["case"]) for r in done if r["run"] in v3]
        shares = [s for s in shares if s]
        if shares:
            entry["document_share"] = sum(d for d, _ in shares) / sum(n for _, n in shares)
        table[m] = entry
    import task070_rcaeval as rc
    service = {c["id"]: c["path"].split("/")[1].rsplit("_", 1)[0] for c in rc.cases()}
    services = sorted({service[c] for c in cases})
    per_service = {m: {s: float(np.mean([scores[m][i]["Avg@5"] for i, c in enumerate(cases) if service[c] == s]))
                       for s in services} for m in methods}
    failed_any = {c for m in methods for c in cases
                  if rows.get((m, c)) is None or rows[(m, c)].get("status", "COMPLETE") != "COMPLETE"}
    complete = [i for i, c in enumerate(cases) if c not in failed_any]
    complete_only = {m: float(np.mean([scores[m][i]["Avg@5"] for i in complete])) if complete else None for m in methods}
    out = {"runs": [r.name for r, _ in runs], "v3_runs": sorted(v3), "head_b_for_candidate_counts": head_b.name,
           "cases": len(cases), "failure_rule": "failed or missing run = all candidates tied",
           "roles": {m: ROLES.get(m, "comparison") for m in methods},
           "bootstrap": {"resamples": 10000, "seed": SEED, "note": "per-method CI only; no pairwise tests"},
           "methods": table, "per_service_Avg@5": per_service,
           "complete_cases": {"n": len(complete), "Avg@5": complete_only},
           "per_case": {m: dict(zip(cases, scores[m])) for m in methods}}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    fmt = lambda v: "-" if v is None else f"{v:.3f}"
    print("| method | role | Avg@5 (95% CI) | AC@1 | AC@3 | RR | failed+missing | mean Yes | mean edges | doc share |")
    print("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for m, e in table.items():
        lo, hi = e["Avg@5_ci95"]
        print(f"| {m} | {ROLES.get(m, 'comparison')} | {e['Avg@5']:.3f} [{lo:.3f}, {hi:.3f}] | {e['AC@1']:.3f} | "
              f"{e['AC@3']:.3f} | {e['RR']:.3f} | {len(e['failed']) + len(e['missing_scored_tied'])} | "
              f"{e.get('yes_mean', float('nan')):.1f} | {e.get('graph_edges_mean', float('nan')):.1f} | "
              f"{fmt(e.get('document_share'))} |")
    print()
    print("| method | " + " | ".join(services) + " |")
    print("|---|" + "---:|" * len(services))
    for m in methods:
        print(f"| {m} | " + " | ".join(f"{per_service[m][s]:.3f}" for s in services) + " |")
    print()
    print(f"complete cases (no method failed): {len(complete)} of {len(cases)}: "
          + ", ".join(f"{m} {fmt(v)}" for m, v in complete_only.items()))
    for m, e in table.items():
        for item in e["failed"] + e["missing_scored_tied"]:
            print(m, item)


if __name__ == "__main__":
    main()
