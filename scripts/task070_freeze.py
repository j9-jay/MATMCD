"""G2: freeze the TASK_070 methods before any evaluation-case run.

Writes configs/task070_frozen.json with the method settings and the SHA-256 of
every TASK_070 script and config. Evaluation runners compare against it and stop
on any difference. Refuses to overwrite an existing freeze.
"""
from datetime import datetime, timezone

import task070_direct as td
import task070_judge as tj
import task070_retrieval as tr
import task070_state_retriever as ts
from project_paths import PROJECT
from task070_common import sha256_file, write_json

OUT = PROJECT / "configs/task070_frozen.json"
FILES = sorted([p for p in (PROJECT / "scripts").glob("task070_*.py") if p.name != "task070_freeze.py"]) + [
    PROJECT / "configs/task070_decisions.json", PROJECT / "configs/task070_testset.json"]


def current_hashes():
    return {p.relative_to(PROJECT).as_posix(): sha256_file(p) for p in FILES}


def verify_frozen():
    import json
    frozen = json.loads(OUT.read_text(encoding="utf-8"))
    now = current_hashes()
    changed = sorted(k for k in frozen["sha256"] if now.get(k) != frozen["sha256"][k])
    if changed:
        raise RuntimeError(f"Files changed after G2 freeze: {changed}")
    return frozen["profile_id"]


def main():
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite {OUT}")
    write_json(OUT, {
        "profile_id": "task070_g2_v1",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "basis": "development split only (RE2-OB repetition 1, 10 cases); evaluation cases not used",
        "primary_head_B": {"prompt_version": td.PROMPT_VERSION, "k_evidence": td.K_DIRECT,
                           "order_repeats": td.ORDER_REPEATS, "sampling": td.SAMPLING,
                           "state_budget": td.STATE_BUDGET, "flat_query": td.FLAT_QUERY},
        "auxiliary_head_A": {"judge_prompt_version": tj.PROMPT_VERSION, "judge_sampling": tj.SAMPLING,
                             "k_evidence": tr.K_EVIDENCE, "state_retriever": ts.RETRIEVER_VERSION},
        "methods": {"proposed": "state_dynamic", "core_baseline": "flat",
                    "ablations": ["role_only", "state_fixed"], "references": ["none", "pc_only", "matmcd"]},
        "failure_scoring": ("A failed case-method run (no complete ranking) is scored as all candidates tied "
                            "(expected value under random order) and the failure count is reported."),
        "dev_results_head_B": "MATMCD_DATA/task070/head_b/dev_20261019T115801Z",
        "sha256": current_hashes(),
    })
    print(OUT)


if __name__ == "__main__":
    main()
