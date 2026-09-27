"""Connect approved provisional CSVs and byte-preserved exact-name pod logs.

No new pod mapping, filtering, log template generation, inference or RCA run.
"""
import csv
import gc
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath

from project_paths import ASSETS, PROJECT, SOURCE, asset_path
from prepare_workspace import main as prepare_workspace
from rca_case_scope import select_active_cases, validate_input_scope


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def export_member(archive, member, destination, required):
    name = PurePosixPath(member)
    if name.parent.name != "pod_removed" or name.name in ("", ".", ".."):
        raise ValueError(f"Unexpected source member: {member}")
    info = archive.getinfo(member)
    with archive.open(info) as stream:
        header = next(csv.reader([stream.readline().decode("utf-8-sig").rstrip("\r\n")]))
    if not set(required) <= set(header):
        raise ValueError(f"Missing official columns in {member}: {header}")
    target = destination / name.name
    destination.mkdir(parents=True, exist_ok=True)
    existed = target.exists()
    output = None if existed else target.open("xb")
    digest = hashlib.sha256()
    length = 0
    try:
        with archive.open(info) as stream:
            for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
                length += len(chunk)
                if output:
                    output.write(chunk)
    finally:
        if output:
            output.close()
    if length != info.file_size or target.stat().st_size != length:
        raise RuntimeError(f"Size mismatch: {member}")
    expected = digest.hexdigest()
    if existed and sha256(target) != expected:
        raise RuntimeError(f"Existing file differs; not overwritten: {target}")
    return {"member": member, "path": str(target.relative_to(ASSETS)), "bytes": length,
            "sha256": expected, "zip_crc32": f"{info.CRC:08x}", "zip_crc_verified_by_full_read": True,
            "header": header, "created": not existed}


def main():
    if sys.platform != "linux" or sys.prefix != str(asset_path("environment")):
        raise SystemExit("Use the existing pinned WSL environment")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = PROJECT / f"docs/evidence/rca_input_connection_{stamp}.json"
    report = {"checked_utc": stamp, "status": "IN_PROGRESS", "cases": [],
              "script_sha256": sha256(PROJECT / "scripts/connect_rca_inputs.py"),
              "experiments_executed": False, "inference_calls": 0, "scientific_conditions_changed": False,
              "author_equivalence": "UNCONFIRMED", "profile": "lemma_rca_provisional_v1"}
    source_before = {str(p.relative_to(SOURCE)): sha256(p) for p in SOURCE.rglob("*") if p.is_file()}
    validation = read_json(PROJECT / "docs/evidence/rca_preprocessing_validation.json")
    config_path = PROJECT / "configs/inputs.json"
    report["input_config_before"] = read_json(config_path)
    validate_input_scope(report["input_config_before"])
    files, directories = {}, {}
    try:
        for case in select_active_cases(validation["cases"]):
            system, day = case["system"], case["day"]
            source_dir = ASSETS / case["output_directory"]
            manifest_path = source_dir / "manifest.json"
            if sha256(manifest_path) != case["manifest_sha256"]:
                raise RuntimeError(f"Manifest changed: {system}/{day}")
            manifest = read_json(manifest_path)
            for name, expected in case["outputs"].items():
                if sha256(source_dir / name) != expected["sha256"]:
                    raise RuntimeError(f"Prepared input changed: {name}")
            log_spec = manifest["logs"]
            archive_path = ASSETS / log_spec["archive"]
            if sha256(archive_path) != log_spec["archive_sha256"]:
                raise RuntimeError(f"Original log archive changed: {archive_path}")
            relative_logs = f"datasets/huggingface_lemma_rca_{system.lower()}_pod_logs/{day}"
            destination = ASSETS / relative_logs
            result = {"system": system, "day": day, "csv": case["output_directory"] + f"/{system}_{day}.csv",
                      "manifest_sha256": case["manifest_sha256"], "archive": log_spec["archive"],
                      "archive_sha256_verified": log_spec["archive_sha256"], "files": [],
                      "missing_pods": [], "log_directory": relative_logs}
            report["cases"].append(result)
            with zipfile.ZipFile(archive_path) as archive:
                bytes_needed = sum(archive.getinfo(member).file_size
                    for entry in log_spec["pods"].values() if entry["exact_unique_pair"]
                    for members in entry["members"].values() for member in members)
                if shutil.disk_usage(ASSETS).free < bytes_needed:
                    raise RuntimeError(f"Insufficient asset disk space: {system}/{day}")
                for pod, entry in log_spec["pods"].items():
                    if not entry["exact_unique_pair"]:
                        result["missing_pods"].append(pod)
                        continue
                    for kind, required in (("templates", ("EventId", "EventTemplate", "Occurrence")),
                                           ("structured", ("EventId", "Time", "Content"))):
                        members = entry["members"][kind]
                        if len(members) != 1 or PurePosixPath(members[0]).name != f"{pod}_messages_{kind}.csv":
                            raise ValueError(f"Nonexact log mapping: {pod}")
                        item = export_member(archive, members[0], destination, required)
                        item.update(pod=pod, kind=kind)
                        result["files"].append(item)
            result["exact_pairs"] = len(result["files"]) // 2
            result["bytes"] = sum(f["bytes"] for f in result["files"])
            result["full_log_coverage"] = not result["missing_pods"]
            files[f"LEMMA_RCA/{system}/Metrics/{system}_{day}.csv"] = result["csv"]
            directories[f"LEMMA_RCA/{system}/Log/{day}"] = relative_logs
            print(f"Prepared {system}/{day}: {result['exact_pairs']} exact log pairs; {len(result['missing_pods'])} missing", flush=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        updated = dict(report["input_config_before"])
        updated.update(input_profile="lemma_rca_provisional_v1", author_equivalence="UNCONFIRMED",
                       rca_files=files, rca_log_directories=directories,
                       expected_rca_inputs=list(files), missing_rca_inputs=[],
                       connection_evidence=str(output.relative_to(PROJECT)),
                       notes=["RCA §4.3/Table 4 only. These are approved provisional inputs, not verified author CSVs.",
                              "User authorized clear remaining preparation work; CSV values and candidate pods are unchanged.",
                              "Only exact pod-name log pairs were extracted byte-for-byte; approved D01 retains missing pods with explicit absence, cause UNKNOWN.",
                              "Connected files alone do not establish RCA readiness or authorize scientific condition changes."])
        config_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        prepare_workspace()
        report["loader_checks"] = []
        env = os.environ.copy()
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(SOURCE))
        for case in report["cases"]:
            code = ("import json; from Utils.data import load_Lemma_data; "
                    f"data,logs=load_Lemma_data({case['system']!r},{case['day']!r}); "
                    "print(json.dumps({'shape':list(data.shape),'last_column':data.columns[-1],'logs':logs}))")
            result = subprocess.run([sys.executable, "-B", "-c", code], cwd=asset_path("runtime_workspace"),
                                    env=env, capture_output=True, text=True, timeout=180)
            record = {"system": case["system"], "day": case["day"], "exit_code": result.returncode,
                      "stdout": result.stdout, "stderr": result.stderr}
            report["loader_checks"].append(record)
            if result.returncode:
                raise RuntimeError(f"Original loader failed: {record}")
            loaded = json.loads(result.stdout)
            manifest = read_json(ASSETS / PurePosixPath(case["csv"]).parent / "manifest.json")
            if loaded["shape"] != [manifest["aligned_rows"], len(manifest["columns"])] or loaded["last_column"] != "Latency":
                raise RuntimeError(f"Original loader shape/header mismatch: {case['system']}/{case['day']}")
            print(f"Official loader PASS: {case['system']}/{case['day']} {loaded['shape']}", flush=True)
            gc.collect()
        prepare_workspace()  # Verifies already-created links without replacing them.
        report["source_unchanged"] = source_before == {str(p.relative_to(SOURCE)): sha256(p) for p in SOURCE.rglob("*") if p.is_file()}
        if not report["source_unchanged"]:
            raise RuntimeError("Official source changed")
        report.update(status="CONNECTED_PROVISIONAL_INPUTS_PARTIAL_LOGS", input_config_after_sha256=sha256(config_path),
                      total_log_files=sum(len(c["files"]) for c in report["cases"]),
                      total_log_bytes=sum(c["bytes"] for c in report["cases"]),
                      full_rca_ready=False, repeated_link_check="PASS")
    except Exception as error:
        report.update(status="FAILED", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Evidence: {output}", flush=True)
    print(json.dumps({k: report[k] for k in ("status", "total_log_files", "total_log_bytes", "full_rca_ready")}), flush=True)


if __name__ == "__main__":
    main()
