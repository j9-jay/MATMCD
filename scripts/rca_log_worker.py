"""Read one exact full log pair through the original function, then exit.

The injected client captures the untouched request; it generates no response.
The parent submits it only after the CSV worker has exited and freed memory.
"""
import argparse
import json
import os
import resource
import subprocess
import sys
import time
import traceback
from pathlib import Path

from check_rca_log_memory import MEMORY_MAX, MIN_AVAILABLE, TIMEOUT_SECONDS, cgroup_info, memory_info
from local_rca_components import official_log_summary_call
from project_paths import ASSETS, PROJECT
from rca_log_evidence import read_json, sha256, within
from setup_graphviz import assert_original_source
from rca_log_encoding import POLICY, BAD_BYTES, ApprovedReader, EncodingSelectionError, require_valid_prompt


def capture_request(request_path):
    request = read_json(request_path)
    directory = request_path.parent
    result = {"status": "IN_PROGRESS", "case": request["case"], "pod": request["pod"], "generation_calls": 0}
    try:
        limits = cgroup_info()
        if limits["memory.max"] != MEMORY_MAX or limits["memory.swap.max"] != 0:
            raise RuntimeError("Required CSV worker memory guards are inactive")
        assert_original_source()
        paths = {kind: within(ASSETS, item["path"]) for kind, item in request["sources"].items()}
        stats = {}
        for kind, path in paths.items():
            expected = request["sources"][kind]
            if path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
                raise RuntimeError(f"Source log changed: {kind}")
            if path.name != f"{request['pod']}_messages_{kind}.csv":
                raise ValueError("Unexpected exact log filename")
            stats[kind] = (path.stat().st_size, path.stat().st_mtime_ns)
        if paths["templates"].parent != paths["structured"].parent:
            raise ValueError("Original reader requires a shared exact log directory")
        import pandas as pd
        reader = pd
        if (directory / "reader.json").exists():
            policy = read_json(PROJECT / "configs/local_rca_execution.json")["log_encoding_policy"]
            if policy["id"] != POLICY or policy["status"] != "USER_APPROVED":
                raise RuntimeError("D06 reader policy is not approved")
            provenance = read_json(directory / "reader.json")
            previous = within(ASSETS, provenance["strict_failure_directory"])
            if provenance["policy"] != POLICY or sha256(previous / "result.json") != provenance["strict_failure_sha256"]:
                raise RuntimeError("Original strict failure changed")
            failure = read_json(previous / "result.json")
            if read_json(previous / "request.json") != request or failure["status"] != "FAILED" or "UnicodeDecodeError" not in failure.get("error", ""):
                raise RuntimeError("D06 only permits verified prior UTF-8 failures for the same input")
            result["reader_provenance"] = provenance
            result["reader_audit"] = []
            reader = ApprovedReader(pd, paths, result["reader_audit"])
        captured = []
        class Capture:
            def inquire_LLMs(self, prompt, system_prompt, temperature=0.5):
                message = {"prompt": prompt, "system_prompt": system_prompt, "temperature": temperature}
                try:
                    require_valid_prompt(message)
                except EncodingSelectionError:
                    diagnostic = directory / "message.diagnostic.json"
                    diagnostic.write_text(json.dumps({"diagnostic_only": True, "not_approved_for_inference": True,
                        "message": message}, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
                    result["selected_prompt_diagnostic"] = {"path": diagnostic.name, "sha256": sha256(diagnostic),
                        "invalid_bytes": len(BAD_BYTES.findall(prompt)), "characters": len(prompt),
                        "first_byte_hex": [f"{ord(char)-0xdc00:02x}" for char in BAD_BYTES.findall(prompt)[:24]],
                        "used_for_inference": False}
                    raise
                captured.append(message)
                return ""  # Unused capture sentinel, never stored as a summary.
        functions = official_log_summary_call(Capture(), reader)
        functions["generate_pod_summary"](request["theme"], request["pod"],
                                          str(paths["templates"].parent) + "/", request["columns"])
        if len(captured) != 1:
            raise RuntimeError("Expected exactly one original summary request")
        if stats != {kind: (p.stat().st_size, p.stat().st_mtime_ns) for kind, p in paths.items()}:
            raise RuntimeError("Log metadata changed during read")
        message_path = directory / "message.json"
        message_path.write_text(json.dumps(captured[0], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result.update(status="CAPTURED", message_sha256=sha256(message_path),
                      peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                      cgroup=cgroup_info(), selected_prompt_invalid_bytes=0,
                      original_csv_options="unchanged pd.read_csv defaults" if reader is pd else
                                           "D06: surrogateescape for proven UTF-8 failures; other defaults unchanged")
    except Exception:
        result.update(status="FAILED", error=traceback.format_exc())
    (directory / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result["status"] == "CAPTURED" else 1


def prepare_one(plan, node, theme, directory, *, strict_failure_directory=None):
    if node["evidence_available"] is not True:
        raise ValueError("Only known exact log pairs enter the CSV worker")
    if memory_info()["MemAvailable_bytes"] < MEMORY_MAX + MIN_AVAILABLE:
        raise RuntimeError("Insufficient memory before CSV worker; no data read or fallback")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    request = {"case": f"{plan['system']}/{plan['day']}", "pod": node["name"], "sources": node["sources"],
               "theme": theme, "columns": plan["columns"]}
    path = directory / "request.json"
    path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if strict_failure_directory is not None:
        previous = Path(strict_failure_directory)
        provenance = {"policy": POLICY, "strict_failure_directory": previous.relative_to(ASSETS).as_posix(),
                      "strict_failure_sha256": sha256(previous / "result.json")}
        (directory / "reader.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    unit = f"matmcd-csv-{os.getpid()}-{time.time_ns()}.scope"
    command = ["systemd-run", "--user", "--scope", "--quiet", "--unit", unit, "-p", f"MemoryMax={MEMORY_MAX}",
               "-p", "MemorySwapMax=0", sys.executable, "-B", str(Path(__file__).resolve()), "--capture", str(path)]
    started = time.monotonic()
    with (directory / "worker.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, cwd=PROJECT)
        try:
            while process.poll() is None:
                if memory_info()["MemAvailable_bytes"] < MIN_AVAILABLE:
                    raise RuntimeError("Available WSL memory below guard")
                if time.monotonic() - started > TIMEOUT_SECONDS:
                    raise RuntimeError("CSV worker timed out; unchanged input preserved")
                time.sleep(.5)
        finally:
            if process.poll() is None:
                subprocess.run(["systemctl", "--user", "kill", "--signal=SIGKILL", unit], stdout=log, stderr=subprocess.STDOUT, check=False)
                process.wait(timeout=30)
    result = read_json(directory / "result.json")
    if process.returncode or result["status"] != "CAPTURED":
        raise RuntimeError(f"CSV worker failed; inspect {directory}")
    if sha256(directory / "message.json") != result["message_sha256"]:
        raise RuntimeError("Captured prompt changed")
    return directory / "message.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    raise SystemExit(capture_request(parser.parse_args().capture))
