"""Reuse only the public RCA metric functions; do not run its fixed-rank script.

Ranks must already have been resolved under an explicit evaluation protocol.
This module does not decide cases, pod/service mappings, ties or repetitions.
"""
import argparse
import ast
import hashlib
import json
import math
import zipfile
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, SOURCE


def official_functions():
    path = SOURCE / "LEMMA_Metrics.py"
    code = path.read_bytes()
    with zipfile.ZipFile(ASSETS / "raw_downloads/github_d2i_matmcd/ef2c3ec.zip") as archive:
        original = archive.read("LEMMA_Metrics.py")
    if code != original:
        raise RuntimeError("Official metric source differs from pinned archive")
    tree = ast.parse(code.decode("utf-8"))
    names = {"PRK", "MAPK", "MRR"}
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in functions} != names or len(functions) != 3:
        raise RuntimeError("Official function set differs")
    module = ast.Module(body=functions, type_ignores=[])
    namespace = {}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace, hashlib.sha256(code).hexdigest()


def evaluate_ranks(ranks):
    """Compute unchanged public formulas on explicitly supplied 1-based ranks.

No actual predictions are read implicitly. A missing root cause, partial list,
or unresolved name must be resolved by the caller's protocol, not guessed here.
"""
    if not isinstance(ranks, (list, tuple)) or not ranks:
        raise ValueError("Provide nonempty, explicitly verified ranks")
    if any(type(rank) is not int or rank < 1 for rank in ranks):
        raise ValueError("Public MRR expects positive 1-based integer ranks; do not guess missing ranks")
    functions, source_hash = official_functions()
    values = {f"MAP@{k}": functions["MAPK"](k, len(ranks), ranks) for k in (5, 10)}
    values["MRR"] = functions["MRR"](ranks)
    return {"metrics": values, "count": len(ranks), "ranks": list(ranks),
            "definition": "unchanged_public_LEMMA_Metrics_functions",
            "source_sha256": source_hash, "rank_base": 1,
            "top_k_boundary": "strict rank < k, including internal k in MAPK",
            "not_standard_average_precision": True}


def self_check():
    functions, source_hash = official_functions()
    cases = [
        ("public_MATMCD_example_not_new_experiment", [2, 7], [0.30, 0.55, 9 / 28]),
        ("public_MATMCD_RE_example_not_new_experiment", [3, 6], [0.20, 0.55, 0.25]),
        ("best_rank_boundary", [1], [0.80, 0.90, 1.0]),
        ("exact_K_boundary", [5], [0.0, 0.50, 0.20]),
    ]
    checks = []
    for name, ranks, expected in cases:
        result = evaluate_ranks(ranks)
        ok = all(math.isclose(result["metrics"][metric], value, rel_tol=0, abs_tol=1e-12)
                 for metric, value in zip(("MAP@5", "MAP@10", "MRR"), expected))
        checks.append({"name": name, "ok": ok, **result})
    checks.append({"name": "strict_rank_boundary_preserved", "ok": functions["PRK"](5, 1, [5]) == 0})
    for bad in ([], [0], [-1], [2.0], [True], [None]):
        try:
            evaluate_ranks(bad)
        except ValueError:
            ok = True
        else:
            ok = False
        checks.append({"name": "reject_unresolved_or_invalid_rank", "input": bad, "ok": ok})
    report = {"checked_utc": datetime.now(timezone.utc).isoformat(), "source_sha256": source_hash,
              "status": "PASS" if all(c["ok"] for c in checks) else "FAILED", "checks": checks,
              "scope": "public-function adapter and boundary checks only; no RCA prediction/evaluation run",
              "actual_experiment_results": False, "source_functions_modified": False}
    output = PROJECT / ("docs/evidence/rca_metric_adapter_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(checks), "report": str(output)}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if not args.self_check:
        parser.error("Use --self-check for non-experimental verification; import evaluate_ranks for a reviewed evaluation pipeline")
    raise SystemExit(self_check())
