"""Capture a read-only pre-run OS baseline; never alter update policy."""
import json
import platform
import subprocess
from datetime import datetime, timezone

from project_paths import PROJECT, asset_path
from rca_log_evidence import sha256
from setup_graphviz import assert_original_source, python_packages, source_hashes, system_packages


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = asset_path("setup_logs") / f"rca_environment_{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    assert_original_source()
    data = {"captured_utc": stamp, "status": "SNAPSHOT_RECORDED", "platform": platform.platform(),
            "python": platform.python_version(), "system_packages": system_packages(),
            "python_packages": python_packages(), "official_sources": source_hashes(),
            "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")},
            "changes_applied": False, "update_policy_changed": False,
            "author_environment_equivalence": "UNCONFIRMED"}
    for name, command in {
        "os_release": ["cat", "/etc/os-release"],
        "update_timers": ["systemctl", "list-timers", "--all", "--no-pager", "apt-daily*"],
        "update_activity": ["systemctl", "show", "apt-daily.service", "apt-daily-upgrade.service", "-p", "ActiveState", "-p", "SubState"],
        "gpu": ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used", "--format=csv,noheader"],
    }.items():
        result = subprocess.run(command, text=True, capture_output=True, timeout=30)
        data[name] = {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    path = directory / "baseline.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {k: data[k] for k in ("captured_utc", "status", "platform", "python", "changes_applied", "update_policy_changed")}
    receipt.update(path=str(path), sha256=sha256(path), system_package_count=len(data["system_packages"]),
                   python_package_count=len(data["python_packages"]), official_file_count=len(data["official_sources"]),
                   baseline_policy="record_before_and_after_runs; update_control_unselected")
    (PROJECT / f"docs/evidence/rca_environment_{stamp}.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
