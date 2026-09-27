"""승인된 호환 lock을 설치한다. 원본 패키지 버전과 공식 코드는 보존한다."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, SOURCE, asset_path


def pins(text):
    return {re.sub(r"[-_.]+", "-", name.lower()): version
            for name, version in re.findall(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)", text, re.M)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if sys.platform != "linux":
        raise SystemExit("기존 WSL Ubuntu에서 실행하세요.")
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("WSL 로그인 환경에서 uv를 찾을 수 없습니다.")
    lock = PROJECT / "docs/evidence/chromadb_1.0.11.proposed.lock.txt"
    expected_hash = "b3bd3f4e3cae5eb5f56840612366f0cebf5ee57234315384859f382110ce8f31"
    if sha(lock) != expected_hash:
        raise SystemExit("승인안 lock 해시가 달라 설치하지 않습니다.")
    python = asset_path("environment") / "bin/python"
    env = os.environ.copy()
    env.update(UV_CACHE_DIR=str(ASSETS / "caches/uv_packages"), UV_NO_PROGRESS="1",
               UV_LINK_MODE="copy", UV_PYTHON_DOWNLOADS="never", PYTHONDONTWRITEBYTECODE="1")
    before_text = subprocess.check_output([uv, "pip", "freeze", "--python", str(python)], env=env, text=True)
    before, target = pins(before_text), pins(lock.read_text())
    baseline = pins((PROJECT / "docs/evidence/installed_freeze.txt").read_text())
    if any(before.get(k) != v or target.get(k) != v for k, v in baseline.items()):
        raise SystemExit("기존 141개 패키지의 버전이 기준과 달라 설치하지 않습니다.")
    if any(k not in target or target[k] != v for k, v in before.items()):
        raise SystemExit("승인안 외의 기존 패키지/버전이 있어 설치하지 않습니다.")
    original = {str(p.relative_to(SOURCE)): sha(p) for p in SOURCE.rglob("*") if p.is_file()}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = ASSETS / "logs/chromadb_install" / stamp
    log_dir.mkdir(parents=True, exist_ok=False)
    (log_dir / "before.txt").write_text(before_text, encoding="utf-8")
    report = {"checked_utc": stamp, "lock_sha256": expected_hash,
              "accepted_risk": "RISK-001", "log_directory": str(log_dir.relative_to(ASSETS)),
              "experiments_executed": False, "model_api_calls": False, "commands": []}
    command = [uv, "pip", "install", "--require-hashes", "--python", str(python), "-r", str(lock)]
    commands = [("install", command), ("pip_check", [uv, "pip", "check", "--python", str(python)])]
    code = 0
    for name, cmd in commands:
        print(name, flush=True)
        with (log_dir / f"{name}.log").open("w", encoding="utf-8") as log:
            proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            code = proc.wait()
        report["commands"].append({"name": name, "argv": cmd, "exit_code": code})
        if code:
            break
    after_text = subprocess.check_output([uv, "pip", "freeze", "--python", str(python)], env=env, text=True)
    after = pins(after_text)
    (log_dir / "after.txt").write_text(after_text, encoding="utf-8")
    report.update(installed_count=len(after),
                  added={k: v for k, v in sorted(after.items()) if k not in baseline},
                  changed_baseline={k: {"before": v, "after": after.get(k)} for k, v in baseline.items() if after.get(k) != v},
                  lock_matches=after == target,
                  official_source_unchanged=all(sha(SOURCE / k) == v for k, v in original.items()))
    report["success"] = code == 0 and report["lock_matches"] and not report["changed_baseline"] and report["official_source_unchanged"]
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (log_dir / "report.json").write_text(text, encoding="utf-8")
    (PROJECT / "docs/evidence/chromadb_install.json").write_text(text, encoding="utf-8")
    (PROJECT / "docs/evidence/installed_freeze_with_chromadb.txt").write_text(after_text, encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("success", "installed_count", "changed_baseline", "lock_matches", "official_source_unchanged")}, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
