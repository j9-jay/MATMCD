"""승인된 lxml 5.4.0 wheel만 추가한다. 기존 패키지/공식 코드를 변경하지 않는다."""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename

from project_paths import ASSETS, PROJECT, SOURCE, asset_path
from setup_chromadb import pins, sha


def main():
    if sys.platform != "linux" or sys.prefix != str(asset_path("environment")):
        raise SystemExit("기존 WSL 실험 환경의 Python으로 실행하세요.")
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("WSL 로그인 환경의 uv가 필요합니다.")
    env = os.environ.copy()
    env.update(UV_CACHE_DIR=str(ASSETS / "caches/uv_packages"), UV_NO_PROGRESS="1",
               UV_LINK_MODE="copy", UV_PYTHON_DOWNLOADS="never", PYTHONDONTWRITEBYTECODE="1")
    freeze_cmd = [uv, "pip", "freeze", "--python", sys.executable]
    before_text = subprocess.check_output(freeze_cmd, env=env, text=True)
    before = pins(before_text)
    baseline = pins((PROJECT / "docs/evidence/installed_freeze_with_chromadb.txt").read_text())
    expected = {**baseline, "lxml": "5.4.0"}
    if before not in (baseline, expected):
        raise SystemExit("현재 환경이 승인 기준과 달라 변경하지 않습니다.")
    original = {str(p.relative_to(SOURCE)): sha(p) for p in SOURCE.rglob("*") if p.is_file()}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = ASSETS / "logs/lxml_install" / stamp
    log_dir.mkdir(parents=True, exist_ok=False)
    metadata_dir = ASSETS / "raw_downloads/pypi_lxml_5.4.0"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_url = "https://pypi.org/pypi/lxml/5.4.0/json"
    with urllib.request.urlopen(metadata_url, timeout=60) as response:
        raw = response.read()
    metadata = json.loads(raw)
    (metadata_dir / "metadata.json").write_bytes(raw)
    tags = list(sys_tags())
    candidates = []
    for entry in metadata["urls"]:
        if entry["filename"].endswith(".whl") and not entry["yanked"]:
            compatible = parse_wheel_filename(entry["filename"])[3].intersection(tags)
            if compatible:
                candidates.append((min(tags.index(tag) for tag in compatible), entry))
    if not candidates:
        raise SystemExit("호환 wheel이 없어 원본 조건을 변경하지 않고 중단합니다.")
    wheel = min(candidates, key=lambda item: item[0])[1]
    wheel_path = metadata_dir / wheel["filename"]
    if not wheel_path.exists():
        with urllib.request.urlopen(wheel["url"], timeout=60) as response:
            wheel_path.write_bytes(response.read())
    if sha(wheel_path) != wheel["digests"]["sha256"]:
        raise SystemExit("wheel 해시 불일치로 설치하지 않습니다.")
    lock = PROJECT / "docs/evidence/lxml_5.4.0.lock.txt"
    lock.write_text(f"lxml==5.4.0 --hash=sha256:{wheel['digests']['sha256']}\n", encoding="utf-8")
    constraint = log_dir / "before.txt"
    constraint.write_text(before_text, encoding="utf-8")
    report = {"checked_utc": stamp, "accepted_risk": "RISK-002", "metadata_url": metadata_url,
              "metadata_sha256": sha(metadata_dir / "metadata.json"), "wheel": wheel,
              "lock_sha256": sha(lock), "log_directory": str(log_dir.relative_to(ASSETS)),
              "experiments_executed": False, "model_api_calls": False, "commands": []}
    install = [uv, "pip", "install", "--python", sys.executable, "--require-hashes",
               "--only-binary", ":all:", "--no-index", "--find-links", str(metadata_dir),
               "--constraint", str(constraint), "-r", str(lock)]
    code = 0
    for name, cmd in (("dry_run", install + ["--dry-run"]), ("install", install),
                      ("pip_check", [uv, "pip", "check", "--python", sys.executable])):
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        (log_dir / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        print(name, result.stdout + result.stderr, flush=True)
        code = result.returncode
        report["commands"].append({"name": name, "argv": cmd, "exit_code": code})
        if code:
            break
    after_text = subprocess.check_output(freeze_cmd, env=env, text=True)
    after = pins(after_text)
    (log_dir / "after.txt").write_text(after_text, encoding="utf-8")
    report.update(installed_count=len(after), added={k: v for k, v in after.items() if k not in baseline},
                  changed_baseline={k: {"before": v, "after": after.get(k)} for k, v in baseline.items() if after.get(k) != v},
                  exact_expected_packages=after == expected,
                  official_source_unchanged=all(sha(SOURCE / k) == v for k, v in original.items()))
    report["success"] = code == 0 and report["exact_expected_packages"] and report["official_source_unchanged"]
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (log_dir / "report.json").write_text(text, encoding="utf-8")
    (PROJECT / "docs/evidence/lxml_install.json").write_text(text, encoding="utf-8")
    (PROJECT / "docs/evidence/installed_freeze_with_lxml.txt").write_text(after_text, encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("success", "installed_count", "added", "changed_baseline", "official_source_unchanged")}, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
