"""승인 전 ChromaDB 메타데이터/의존성 조사. compile만 사용하며 설치하지 않는다."""
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, SOURCE, asset_path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pins(text):
    return {re.sub(r"[-_.]+", "-", name.lower()): version
            for name, version in re.findall(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)", text, re.M)}


def main():
    if sys.platform != "linux":
        raise SystemExit("기존 WSL 환경에서 실행하세요.")
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("WSL 로그인 환경의 uv가 필요합니다.")
    python = asset_path("environment") / "bin/python"
    env = os.environ.copy()
    env.update(UV_CACHE_DIR=str(ASSETS / "caches/uv_packages"), UV_NO_PROGRESS="1",
               PYTHONDONTWRITEBYTECODE="1", UV_PYTHON_DOWNLOADS="never")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ASSETS / "logs/chromadb_compatibility" / stamp
    output.mkdir(parents=True, exist_ok=False)
    metadata_dir = ASSETS / "raw_downloads/pypi_chromadb_compatibility"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    freeze_cmd = [uv, "pip", "freeze", "--python", str(python)]
    before = subprocess.run(freeze_cmd, env=env, capture_output=True, text=True, check=True).stdout
    frozen = output / "existing-141.txt"
    frozen.write_text(before, encoding="utf-8")
    existing = pins(before)
    official = pins((SOURCE / "requirements.txt").read_text())
    assert all(existing.get(k) == v for k, v in official.items())
    original_hashes = {str(p.relative_to(SOURCE)): sha(p) for p in SOURCE.rglob("*") if p.is_file()}
    report = {"checked_utc": stamp, "uv": subprocess.check_output([uv, "--version"], text=True).strip(),
              "python": subprocess.check_output([str(python), "--version"], text=True).strip(),
              "official_pin_count": len(official), "existing_pin_count": len(existing),
              "installed_packages": False, "experiments_executed": False, "model_api_calls": False,
              "runtime_compatibility_tested": False, "author_chromadb_version_known": False,
              "log_directory": str(output.relative_to(ASSETS)), "candidates": {}, "resolutions": {}}
    for version in ("0.5.23", "0.6.3", "1.0.11"):
        url = f"https://pypi.org/pypi/chromadb/{version}/json"
        with urllib.request.urlopen(url, timeout=60) as response:
            raw = response.read()
        path = metadata_dir / f"chromadb-{version}.json"
        path.write_bytes(raw)
        data = json.loads(raw)
        report["candidates"][version] = {
            "metadata_url": url, "metadata_sha256": sha(path),
            "first_upload": min(f["upload_time_iso_8601"] for f in data["urls"]),
            "requires_python": data["info"]["requires_python"],
            "requires_dist": data["info"]["requires_dist"],
            "yanked": data["info"]["yanked"]}

    def resolve(version, historical=False):
        key = version + ("_at_requirements_commit" if historical else "_current_index")
        request = output / f"{key}.in"
        request.write_text(before + f"chromadb=={version}\n", encoding="utf-8")
        lock = output / f"{key}.txt"
        cmd = [uv, "pip", "compile", str(request), "--python", str(python),
               "--no-build", "--no-header", "--no-annotate", "--generate-hashes",
               "--output-file", str(lock)]
        if historical:
            # 공식 requirements 커밋의 UTC 시각. setuptools는 기존 로컬 버전 유지 예외다.
            cmd += ["--exclude-newer", "2025-05-29T00:03:08Z",
                    "--exclude-newer-package", "setuptools=" + datetime.now(timezone.utc).isoformat()]
        print(f"Resolving {key}; installation disabled", flush=True)
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=240)
            (output / f"{key}.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
            record = {"command": cmd, "exit_code": result.returncode,
                      "log": str((output / f"{key}.log").relative_to(ASSETS))}
            if result.returncode == 0:
                resolved = pins(lock.read_text())
                changed = {k: {"before": v, "after": resolved.get(k)} for k, v in existing.items()
                           if resolved.get(k) != v}
                record.update(resolved_count=len(resolved), changed_existing=changed,
                              added={k: v for k, v in sorted(resolved.items()) if k not in existing},
                              lock=str(lock.relative_to(ASSETS)), lock_sha256=sha(lock))
                assert not changed
            else:
                record["error"] = result.stderr[-10000:]
        except subprocess.TimeoutExpired:
            record = {"command": cmd, "exit_code": None, "error": "240-second resolver timeout"}
        print(f"Finished {key}: {record['exit_code']}", flush=True)
        return key, record

    jobs = [(version, False) for version in report["candidates"]] + [("1.0.11", True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for key, record in pool.map(lambda item: resolve(*item), jobs):
            report["resolutions"][key] = record
    after = subprocess.run(freeze_cmd, env=env, capture_output=True, text=True, check=True).stdout
    report["environment_unchanged"] = before == after
    report["official_source_unchanged"] = all(sha(SOURCE / k) == v for k, v in original_hashes.items())
    assert report["environment_unchanged"] and report["official_source_unchanged"]
    report["limitations"] = ["Resolution and source review only; no candidate installed/imported",
                             "No author version evidence; no equivalence to paper retrieval results"]
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (output / "report.json").write_text(text, encoding="utf-8")
    # 이후 승인용 종합 보고서를 초기 조사 재실행으로 덮어쓰지 않는다.
    (PROJECT / "docs/evidence/chromadb_compatibility_initial.json").write_text(text, encoding="utf-8")
    print(json.dumps({"resolutions": {k: v["exit_code"] for k, v in report["resolutions"].items()},
                      "environment_unchanged": report["environment_unchanged"]}, indent=2))


if __name__ == "__main__":
    main()
