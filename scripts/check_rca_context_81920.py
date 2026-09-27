"""Approved 81920-context validation; one real log summary, never full RCA."""
import argparse
import contextlib
import copy
import hashlib
import json
import socket
import subprocess
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import httpx

import check_rca_context
from local_llm_runtime import CONFIG, base_url
from project_paths import ASSETS, PROJECT, asset_path
from rca_local_client import RecordedLocalClient
from rca_log_evidence import build_plans, read_json, sha256, verify_prepared_plans
from run_local_rca import local_server, verified_prompt
from setup_graphviz import assert_original_source, python_packages, source_hashes


def main(change_evidence):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = asset_path("setup_logs") / f"rca_context81920_{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    evidence = PROJECT / f"docs/evidence/rca_context81920_validation_{stamp}.json"
    report = {"checked_utc": stamp, "status": "IN_PROGRESS", "phase": "preflight",
              "change_evidence": change_evidence, "logs": directory.relative_to(ASSETS).as_posix(),
              "generation_attempts": 0, "actual_RCA_experiment": False, "automatic_retries": 0,
              "full_pipeline_ready": False, "client_timeout_seconds_unchanged": 300}
    before = {"source": source_hashes(), "packages": python_packages(),
              "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}
    samples, stop = [], threading.Event()
    monitor_thread = None

    def checkpoint():
        evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def monitor():
        with (directory / "resources.jsonl").open("x", encoding="utf-8") as stream:
            while not stop.is_set():
                try:
                    mem = {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines()
                           if line.split(":")[0] in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree")}
                    raw = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free,utilization.gpu",
                                                   "--format=csv,noheader,nounits"], text=True, timeout=10).strip()
                    total, used, free, utilization = map(int, raw.splitlines()[0].split(","))
                    sample = {"utc": datetime.now(timezone.utc).isoformat(), "phase": report["phase"],
                              "gpu_total_mib": total, "gpu_used_mib": used, "gpu_free_mib": free,
                              "gpu_utilization": utilization, "wsl_memory_kib": mem}
                except Exception as error:
                    sample = {"utc": datetime.now(timezone.utc).isoformat(), "error": str(error)}
                samples.append(sample)
                stream.write(json.dumps(sample) + "\n")
                stream.flush()
                stop.wait(1)

    checkpoint()
    try:
        change = read_json(PROJECT / change_evidence)
        expected = copy.deepcopy(change["llm_before"])
        expected["server"]["context_tokens"] = 81920
        if CONFIG != expected:
            raise RuntimeError("Expected only the approved context change, no other LLM setting change")
        profile = read_json(PROJECT / "configs/local_rca_execution.json")
        if profile["capacity_decision"]["choice"] != "USER_APPROVED_CONTEXT_81920_VALIDATION_ONLY":
            raise RuntimeError("81920 verification approval missing")
        assert_original_source()
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        report["phase"] = "all_prompt_capacity"
        checkpoint()
        print(f"Checking all 278 prompts at 81920/all. Report: {evidence}", flush=True)
        old = set((PROJECT / "docs/evidence").glob("rca_context_*.json"))
        with (directory / "capacity_stdout.log").open("x", encoding="utf-8") as stream, contextlib.redirect_stdout(stream):
            exit_code = check_rca_context.main(all_prepared=True)
        paths = set((PROJECT / "docs/evidence").glob("rca_context_*.json")) - old
        if len(paths) != 1:
            raise RuntimeError("Expected exactly one new capacity evidence report")
        capacity_path = paths.pop()
        capacity = read_json(capacity_path)
        report["capacity_evidence"] = capacity_path.relative_to(PROJECT).as_posix()
        report["capacity_summary"] = capacity.get("summary")
        if exit_code or capacity["status"] != "PASS" or capacity["summary"]["prompt_count"] != 278:
            raise RuntimeError(f"Full prompt admission failed: {capacity['status']}; no generation attempted")
        previous = read_json(PROJECT / "docs/evidence/rca_context_20260926T074401590811Z.json")
        lookup = {(c["case"], c["pod"]): c for c in previous["cases"]}
        fields = ("prompt_sha256", "prompt_tokens", "formatted_prompt_sha256", "reserved_output_tokens")
        if not all(all(c[k] == lookup[c["case"], c["pod"]][k] for k in fields) for c in capacity["cases"]):
            raise RuntimeError("Prompt content/tokenization/output budget differs from previous measurement")
        report["all_278_prompt_contents_and_token_counts_unchanged"] = True
        target = max(capacity["cases"], key=lambda c: c["prompt_tokens"])
        report["target"] = target
        plans = build_plans()
        verify_prepared_plans(plans)
        plan = plans[target["case"]]
        node = next(n for n in plan["nodes"] if n["name"] == target["pod"])
        message = verified_prompt(plan, node)
        if hashlib.sha256(message["prompt"].encode()).hexdigest() != target["prompt_sha256"]:
            raise RuntimeError("Maximum prompt content changed")
        report["phase"] = "maximum_input_server_start"
        checkpoint()
        print(f"All 278 prompts fit. Testing maximum input: {target['case']}/{target['pod']} ({target['prompt_tokens']} tokens).", flush=True)
        with local_server(directory / "generation_server"):
            with httpx.Client(trust_env=False, timeout=10) as http:
                response = http.get(base_url() + "/props")
                response.raise_for_status()
                props = response.json()
                (directory / "generation_props.json").write_text(json.dumps(props, indent=2) + "\n")
                if props["default_generation_settings"]["n_ctx"] != 81920:
                    raise RuntimeError("Generation server context mismatch")
            chosen = CONFIG["smoke_test"]
            sampling = {k: chosen[k] for k in ("top_p", "top_k", "min_p", "presence_penalty")}
            client = RecordedLocalClient(directory / "calls", max_tokens=chosen["max_tokens"], seed=chosen["seed"], sampling=sampling)
            try:
                client.phase = "maximum_real_log_summary_validation"
                report["phase"] = "maximum_input_generation"
                report["generation_attempts"] = 1
                checkpoint()
                print("Generation started: unchanged request, temperature 0.5, output limit 8192, no retry; existing 300-second client timeout.", flush=True)
                started = time.monotonic()
                content = client.inquire_LLMs(message["prompt"], message["system_prompt"], message["temperature"])
                report["generation_seconds"] = time.monotonic() - started
                (directory / "maximum_input_response.txt").write_text(content, encoding="utf-8")
                report["response"] = {"characters": len(content), "sha256": hashlib.sha256(content.encode()).hexdigest(),
                    "finish_reason": client.last_response["choices"][0]["finish_reason"],
                    "usage": client.last_response.get("usage"), "timings": client.last_response.get("timings"),
                    "response_file": (directory / "maximum_input_response.txt").relative_to(ASSETS).as_posix()}
                lower = content.lower()
                report["format_observation"] = {"pod_name_present": node["name"] in content,
                    "role_heading_present": "role of" in lower,
                    "key_events_heading_present": "key events" in lower,
                    "status_heading_present": "status" in lower,
                    "relationships_heading_present": "relationships" in lower,
                    "note": "Observational check only; original Log_tools returns raw summary with no strict parser. Semantic accuracy is not established."}
            finally:
                client.close()
                report["generation_record"] = (directory / "calls/call_0000001.json").relative_to(ASSETS).as_posix()
        report.update(status="CAPACITY_AND_ONE_REAL_GENERATION_PASS", phase="completed")
    except Exception:
        report.update(status="FAILED", failed_phase=report["phase"], error=traceback.format_exc(), phase="failed")
    finally:
        stop.set()
        if monitor_thread is not None:
            monitor_thread.join(timeout=12)
        good = [s for s in samples if "gpu_used_mib" in s]
        report["resources"] = {"sample_count": len(samples),
            "gpu_peak_used_mib": max((s["gpu_used_mib"] for s in good), default=None),
            "gpu_min_free_mib": min((s["gpu_free_mib"] for s in good), default=None),
            "wsl_min_available_kib": min((s["wsl_memory_kib"]["MemAvailable"] for s in good), default=None),
            "swap_peak_used_kib": max((s["wsl_memory_kib"]["SwapTotal"] - s["wsl_memory_kib"]["SwapFree"] for s in good), default=None)}
        report["preservation"] = {"official_source": source_hashes() == before["source"],
            "python_packages": python_packages() == before["packages"],
            "configs_during_verification": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")} == before["configs"]}
        with socket.socket() as sock:
            sock.settimeout(1)
            report["server_port_closed"] = sock.connect_ex(("127.0.0.1", CONFIG["server"]["port"])) != 0
        report["script_sha256"] = sha256(Path(__file__))
        if not all(report["preservation"].values()):
            report["status"] = "FAILED_PRESERVATION"
        checkpoint()
    print(json.dumps({"status": report["status"], "evidence": str(evidence), "resources": report["resources"],
                      "failed_phase": report.get("failed_phase")}, ensure_ascii=False), flush=True)
    return 0 if report["status"] == "CAPACITY_AND_ONE_REAL_GENERATION_PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--change-evidence", required=True)
    raise SystemExit(main(parser.parse_args().change_evidence))
