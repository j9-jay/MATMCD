"""Category-2 freeze: category 2 has no development split, so its runner and
retriever profile are frozen before the single run. Covers the category-2 files
and the shared modules they import; the G2 freeze (task070_freeze) covers the rest.
"""
import hashlib
import json
from datetime import datetime, timezone

from project_paths import PROJECT
from task070_common import write_json

OUT = PROJECT / "configs/task070_frozen_cat2.json"
FILES = ["scripts/task070_causal.py", "scripts/task070_causal_run.py", "scripts/task070_judge.py",
         "scripts/task070_output_head.py", "scripts/task070_metrics.py", "scripts/task070_retrieval.py",
         "scripts/task070_state_retriever.py", "scripts/task070_web_snapshot.py", "scripts/task070_common.py"]


def _hash(rel):
    return hashlib.sha256((PROJECT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_frozen_cat2():
    frozen = json.loads(OUT.read_text(encoding="utf-8"))
    changed = [f for f, h in frozen["sha256"].items() if _hash(f) != h]
    if changed:
        raise RuntimeError(f"Category-2 files changed after freeze: {changed}")
    return frozen["profile_id"]


if __name__ == "__main__":
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite {OUT}")
    write_json(OUT, {"profile_id": "task070_cat2_v1", "frozen_utc": datetime.now(timezone.utc).isoformat(),
                     "note": "No dev split in category 2; design fixed before the single run (head A, web snapshot corpus).",
                     "failure_rule": "A pair whose judgment fails is recorded and counted as No; failed pair counts are reported.",
                     "sha256": {f: _hash(f) for f in FILES}})
    print(OUT)
