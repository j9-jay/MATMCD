"""Measure existing D02 real prompts with pinned GGUF; no generation or RCA."""
import json
import argparse
import socket
import subprocess
import time
import traceback
from datetime import datetime, timezone

import httpx

from local_llm_runtime import CONFIG, base_url, runtime_command
from local_prompt_capacity import measure_messages
from project_paths import ASSETS, PROJECT, asset_path
from rca_case_scope import active_cases, case_key
from rca_log_evidence import read_json, sha256, within
from setup_graphviz import assert_original_source, python_packages, source_hashes


def main(all_prepared=False, allow_unprepared=False):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = asset_path("setup_logs") / f"rca_context_{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    evidence = PROJECT / f"docs/evidence/rca_context_{stamp}.json"
    report = {"status": "IN_PROGRESS", "checked_utc": stamp, "cases": [], "unprepared": [], "inference_calls": 0,
              "actual_experiment_results": False, "logs": directory.relative_to(ASSETS).as_posix(),
              "scope": "Available exact-pod log prompts; missing ones listed, not an execution subset; graph/RAG not covered" if allow_unprepared else
                       "All prepared exact-pod log prompts; graph/RAG prompts not covered" if all_prepared else
                       "Existing D02 representative prompts from active cases only; not all pairs or graph/RAG prompts"}
    source_before, packages_before = source_hashes(), python_packages()
    config_before = {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}
    proc = None
    try:
        assert_original_source()
        with socket.socket() as check:
            if check.connect_ex(("127.0.0.1", CONFIG["server"]["port"])) == 0:
                raise RuntimeError("Configured port occupied; will not use/stop an unrelated server")
        command, env = runtime_command()
        report["command"] = command
        with (directory / "server.log").open("w", encoding="utf-8") as log, httpx.Client(base_url=base_url(), trust_env=False, timeout=60) as client:
            proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 240
            while True:
                if proc.poll() is not None:
                    raise RuntimeError(f"Pinned server exited {proc.returncode}; see server.log")
                try:
                    if client.get("/health").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError("Server readiness timed out")
                time.sleep(.5)
            props = client.get("/props")
            props.raise_for_status()
            (directory / "server_props.json").write_text(json.dumps(props.json(), indent=2) + "\n")
            if props.json()["default_generation_settings"]["n_ctx"] != CONFIG["server"]["context_tokens"]:
                raise RuntimeError("Runtime context differs from configured context")
            requests = []
            if all_prepared:
                from rca_log_evidence import build_plans, verify_prepared_plans
                from run_local_rca import verified_prompt
                plans = build_plans()
                verify_prepared_plans(plans)
                for key, plan in plans.items():
                    for node in plan["nodes"]:
                        if node["evidence_available"] is True:
                            try:
                                message = verified_prompt(plan, node)
                            except Exception as error:
                                if not allow_unprepared:
                                    raise
                                report["unprepared"].append({"case": key, "pod": node["name"],
                                                              "error": f"{type(error).__name__}: {error}"})
                                continue
                            requests.append((key, node["name"], message["prompt"], message["system_prompt"]))
            else:
                memory_report = read_json(PROJECT / "docs/evidence/rca_log_memory_20260925T131346346807Z.json")
                active_keys = {case_key(c) for c in active_cases()}
                for case in memory_report["cases"]:
                    if case["case"] not in active_keys:
                        continue
                    request = read_json(within(ASSETS, case["details_directory"]) / "request.json")
                    prompt_path = within(ASSETS, case["prompt"]["path"])
                    if sha256(prompt_path) != case["prompt"]["sha256"]:
                        raise RuntimeError("Saved original prompt changed")
                    system = f"You are expert in the field of {request['theme']}, and you are able to analyze the log file and provide the summary of the entity."
                    requests.append((case["case"], case["pod"], prompt_path.read_text(encoding="utf-8"), system))
                if {key for key, _, _, _ in requests} != active_keys:
                    raise RuntimeError("Representative prompts missing an active case")
            import hashlib
            for key, pod, prompt, system in requests:
                messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
                item = {"case": key, "pod": pod, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                        **measure_messages(messages, max_tokens=CONFIG["smoke_test"]["max_tokens"], client=client)}
                report["cases"].append(item)
                print(json.dumps(item), flush=True)
            report["status"] = "PASS" if report["cases"] and all(c["fits"] for c in report["cases"]) else "BLOCKED_CAPACITY"
            if report["unprepared"] and report["status"] == "PASS":
                report["status"] = "BLOCKED_UNPREPARED_INPUTS"
            report["summary"] = {"prompt_count": len(requests), "fits": sum(c["fits"] for c in report["cases"]),
                                 "unprepared_count": len(report["unprepared"]),
                                 "max_input_tokens": max((c["prompt_tokens"] for c in report["cases"]), default=None),
                                 "max_required_context": max((c["required_with_one_token_guard"] for c in report["cases"]), default=None)}
    except Exception:
        report.update(status="FAILED", error=traceback.format_exc())
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=20)
        report["owned_server_stopped"] = proc is None or proc.poll() is not None
        report["preservation"] = {"official_source": source_hashes() == source_before,
                                  "python_packages": python_packages() == packages_before,
                                  "configs": config_before == {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}
        if not all(report["preservation"].values()):
            report["status"] = "FAILED"
        report["script_sha256"] = {p: sha256(PROJECT / "scripts" / p) for p in ("check_rca_context.py", "local_prompt_capacity.py")}
        evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "evidence": str(evidence)}), flush=True)
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all-prepared", action="store_true")
    group.add_argument("--available-prepared", action="store_true", help="Diagnose independent available inputs; report incomplete coverage explicitly")
    args = parser.parse_args()
    raise SystemExit(main(args.all_prepared or args.available_prepared, args.available_prepared))
