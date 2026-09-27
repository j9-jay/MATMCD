"""D02: sequential, bounded full-CSV/prompt probes; no LLM or RCA execution.

Use the existing WSL Python and --run. Each active case contributes its largest
available structured log and matching template. CSV options and the two official
prompt functions are unchanged. A fresh systemd scope/process handles each pair.
The 4 GiB / zero cgroup swap limits are local test guards, not paper parameters.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, SOURCE, asset_path
from rca_log_evidence import build_plans, read_json, sha256, verify_prepared_plans, within
from setup_graphviz import assert_original_source, python_packages, source_hashes

MEMORY_MAX = 4 * 1024**3
MIN_AVAILABLE = 1024**3
TIMEOUT_SECONDS = 1800


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def memory_info():
    fields = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            fields[key + "_bytes"] = int(value.split()[0]) * 1024
    return fields


def cgroup_info():
    relative = next(line.split(":", 2)[2] for line in Path("/proc/self/cgroup").read_text().splitlines()
                    if line.startswith("0::"))
    root = Path("/sys/fs/cgroup") / relative.lstrip("/")
    fields = {"path": str(root)}
    for name in ("memory.max", "memory.peak", "memory.current", "memory.swap.max", "memory.swap.current"):
        value = (root / name).read_text().strip()
        fields[name] = int(value) if value.isdigit() else value
    fields["memory.events"] = dict((key, int(value)) for key, value in
                                   (line.split() for line in (root / "memory.events").read_text().splitlines()))
    return fields


def official_prompt_functions(pd):
    # This extracts unchanged function ASTs, avoiding OpenAI/config imports and
    # the upstream __main__ experiment loop. The complete source is ZIP-checked.
    assert_original_source()
    path = SOURCE / "Log_tools.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {"generate_log_text", "generate_log_prompt"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if len(functions) != 2 or {node.name for node in functions} != names:
        raise RuntimeError("Official log prompt function set changed")
    namespace = {"pd": pd}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def worker(request_path):
    request = read_json(request_path)
    result_path = request_path.with_name("result.json")
    progress_path = request_path.with_name("progress.json")
    result = {"case": request["case"], "pod": request["pod"], "status": "IN_PROGRESS", "phases": []}
    started = time.monotonic()

    def phase(name):
        result["stage"] = name
        result["phases"].append({"stage": name, "elapsed_seconds": time.monotonic() - started,
                                "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                                "wsl_memory": memory_info(), "cgroup": cgroup_info()})
        write_json(progress_path, result)
        print(json.dumps({"case": request["case"], "stage": name}), flush=True)

    try:
        limits = cgroup_info()
        if limits["memory.max"] != MEMORY_MAX or limits["memory.swap.max"] != 0:
            raise RuntimeError("Required per-worker memory/swap guards are not active")
        phase("import_pandas")
        import pandas as pd
        if pd.__version__ != "2.2.3":
            raise RuntimeError("Expected the existing pandas 2.2.3 environment")
        functions = official_prompt_functions(pd)
        result["python"] = sys.version
        result["pandas"] = pd.__version__
        result["source_sha256"] = sha256(SOURCE / "Log_tools.py")
        paths = {kind: within(ASSETS, record["path"]) for kind, record in request["sources"].items()}
        phase("verify_input_hashes_before")
        for kind, path in paths.items():
            if path.stat().st_size != request["sources"][kind]["bytes"] or sha256(path) != request["sources"][kind]["sha256"]:
                raise RuntimeError(f"Input drift: {kind}")
        input_stats = {kind: (p.stat().st_size, p.stat().st_mtime_ns) for kind, p in paths.items()}
        phase("read_templates")
        read_start = time.monotonic()
        templates = pd.read_csv(paths["templates"])
        result["template_read_seconds"] = time.monotonic() - read_start
        phase("read_structured_full")
        read_start = time.monotonic()
        structured = pd.read_csv(paths["structured"])
        result["structured_read_seconds"] = time.monotonic() - read_start
        result["rows"] = {"templates": len(templates), "structured": len(structured)}
        result["structured_dtypes"] = {str(k): str(v) for k, v in structured.dtypes.items()}
        phase("generate_official_prompt")
        prompt_start = time.monotonic()
        # Omit record_num: use the upstream default, preserving all selection,
        # event order, stopping condition, formatting and pod-list contents.
        prompt = functions["generate_log_prompt"](request["theme"], request["pod"],
                                                   request["columns"], templates, structured)
        result["prompt_generation_seconds"] = time.monotonic() - prompt_start
        result["read_and_prompt_seconds"] = (result["template_read_seconds"] +
                                             result["structured_read_seconds"] +
                                             result["prompt_generation_seconds"])
        phase("prompt_complete")
        prompt_bytes = prompt.encode("utf-8")
        prompt_path = request_path.with_name("prompt.txt")
        prompt_path.write_bytes(prompt_bytes)
        result["prompt"] = {"path": prompt_path.relative_to(ASSETS).as_posix(), "bytes": len(prompt_bytes),
                            "characters": len(prompt), "sha256": hashlib.sha256(prompt_bytes).hexdigest(),
                            "tokens": "NOT_MEASURED; model not loaded"}
        result["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        result["cgroup_at_completion"] = cgroup_info()
        if result["cgroup_at_completion"]["memory.events"]["oom"]:
            raise RuntimeError("Memory guard was hit")
        if input_stats != {kind: (p.stat().st_size, p.stat().st_mtime_ns) for kind, p in paths.items()}:
            raise RuntimeError("Input metadata changed during read")
        result["input_integrity"] = "Both files full SHA256 before read; size/mtime unchanged after prompt"
        result["status"] = "PASS"
    except Exception:
        result.update(status="FAILED", error=traceback.format_exc())
    result["total_worker_seconds"] = time.monotonic() - started
    write_json(result_path, result)
    print(json.dumps({"case": request["case"], "status": result["status"],
                      "peak_rss_bytes": result.get("peak_rss_bytes")}), flush=True)
    return 0 if result["status"] == "PASS" else 1


def run():
    if sys.platform != "linux" or sys.prefix != str(asset_path("environment")):
        raise RuntimeError("Use the existing WSL experiment Python")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    logs = asset_path("setup_logs") / f"rca_log_memory_{stamp}"
    logs.mkdir(parents=True, exist_ok=False)
    evidence = PROJECT / f"docs/evidence/rca_log_memory_{stamp}.json"
    report = {"started_utc": stamp, "status": "IN_PROGRESS", "cases": [],
              "inference_calls": 0, "experiments_executed": False, "full_rca_ready": False,
              "scope": "Largest exact structured log per active case, in ascending file-size order",
              "guard": {"memory_max_bytes": MEMORY_MAX, "memory_swap_max_bytes": 0,
                        "minimum_wsl_available_bytes": MIN_AVAILABLE, "timeout_seconds_per_case": TIMEOUT_SECONDS,
                        "paper_parameter": False},
              "script_sha256": sha256(Path(__file__)), "logs": logs.relative_to(ASSETS).as_posix()}
    before_source = source_hashes()
    before_python = python_packages()
    before_configs = {name: sha256(PROJECT / "configs" / name) for name in
                      ("scope.json", "inputs.json", "rca_log_policy.json", "local_llm.json", "local_embedding.json")}
    try:
        assert_original_source()
        plans = build_plans()
        report["prepared_input_verification"] = verify_prepared_plans(plans)
        requests = []
        themes = {"Product_Review": "Microservice System for Product Review", "Cloud_Computing": "Cloud Computing System"}
        for key, plan in plans.items():
            node = max((n for n in plan["nodes"] if n["evidence_available"] is True),
                       key=lambda n: n["sources"]["structured"]["bytes"])
            requests.append({"case": key, "pod": node["name"], "sources": node["sources"],
                             "columns": plan["columns"], "theme": themes[plan["system"]]})
        requests.sort(key=lambda r: r["sources"]["structured"]["bytes"])
        report["selected"] = [{"case": r["case"], "pod": r["pod"], "sources": r["sources"]} for r in requests]
        write_json(evidence, report)
        for index, request in enumerate(requests):
            if memory_info()["MemAvailable_bytes"] < MEMORY_MAX + MIN_AVAILABLE:
                raise RuntimeError("Insufficient WSL headroom for guarded probe; no read attempted")
            directory = logs / request["case"].replace("/", "_")
            directory.mkdir()
            request_path = directory / "request.json"
            write_json(request_path, request)
            unit = f"matmcd-log-{stamp.lower()}-{index}.scope"
            command = ["systemd-run", "--user", "--scope", "--quiet", "--unit", unit,
                       "-p", f"MemoryMax={MEMORY_MAX}", "-p", "MemorySwapMax=0",
                       sys.executable, "-B", str(Path(__file__).resolve()), "--worker", str(request_path)]
            before_memory = memory_info()
            print(json.dumps({"case": request["case"], "stage": "START", "bytes": request["sources"]["structured"]["bytes"]}), flush=True)
            begin = time.monotonic()
            samples = []
            guard_stop = None
            with (directory / "worker.log").open("w", encoding="utf-8") as output:
                process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, cwd=PROJECT,
                                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                try:
                    while process.poll() is None:
                        mem = memory_info()
                        samples.append({"elapsed_seconds": time.monotonic() - begin, **mem})
                        if mem["MemAvailable_bytes"] < MIN_AVAILABLE:
                            guard_stop = "WSL available memory below 1 GiB"
                        elif time.monotonic() - begin > TIMEOUT_SECONDS:
                            guard_stop = "Per-case 30 minute guard reached"
                        if guard_stop:
                            break
                        time.sleep(0.5)
                finally:
                    if process.poll() is None:
                        subprocess.run(["systemctl", "--user", "kill", "--signal=SIGKILL", unit], check=False,
                                       stdout=output, stderr=subprocess.STDOUT)
                    process.wait(timeout=30)
            result_path = directory / "result.json"
            result = read_json(result_path) if result_path.exists() else {
                "case": request["case"], "pod": request["pod"], "status": "FAILED",
                "error": "Worker exited without final result; inspect progress.json and worker.log"}
            result.update(exit_code=process.returncode, guard_stop=guard_stop, before_memory=before_memory,
                          after_memory=memory_info(), wall_seconds=time.monotonic() - begin,
                          minimum_wsl_available_bytes=min(s["MemAvailable_bytes"] for s in samples) if samples else None,
                          maximum_wsl_swap_used_bytes=max(s["SwapTotal_bytes"] - s["SwapFree_bytes"] for s in samples) if samples else None,
                          details_directory=directory.relative_to(ASSETS).as_posix())
            write_json(directory / "memory_samples.json", samples)
            if process.returncode != 0 or guard_stop:
                result["status"] = "FAILED"
            report["cases"].append(result)
            write_json(evidence, report)
            print(json.dumps({"case": request["case"], "status": result["status"],
                              "peak_rss_bytes": result.get("peak_rss_bytes"),
                              "read_and_prompt_seconds": result.get("read_and_prompt_seconds")}), flush=True)
            if result["status"] != "PASS":
                raise RuntimeError("Probe failed; do not retry with changed reader/data or start larger files")
        report["status"] = "PASS"
    except Exception:
        report.update(status="FAILED", error=traceback.format_exc())
    finally:
        report["preservation"] = {"official_source_unchanged": before_source == source_hashes(),
                                  "python_packages_unchanged": before_python == python_packages(),
                                  "configs_unchanged": before_configs == {n: sha256(PROJECT / "configs" / n) for n in before_configs},
                                  "official_file_count": len(before_source)}
        if not all(report["preservation"][k] for k in ("official_source_unchanged", "python_packages_unchanged", "configs_unchanged")):
            report["status"] = "FAILED"
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        report["limits"] = ["Three representative files only; other files may have different memory expansion",
                            "No models loaded or inference called; concurrent model memory not validated",
                            "Prompt token count/context fit and full RCA integration remain unvalidated",
                            "Disk reads may benefit from cache; no cache flushing or performance extrapolation"]
        write_json(evidence, report)
    print(json.dumps({"status": report["status"], "report": str(evidence)}), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", action="store_true")
    group.add_argument("--worker", type=Path)
    args = parser.parse_args()
    raise SystemExit(worker(args.worker) if args.worker else run())
