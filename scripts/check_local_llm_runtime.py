"""Synthetic local inference checks; never imports or runs RCA entry points."""
import ast
import contextlib
import json
import re
import socket
import subprocess
import threading
import time
import traceback
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import numpy as np

from local_llm_client import LocalLLMClient
from local_re_response import RE_FORMAT_POLICY, REFormatClient
from local_llm_runtime import CONFIG, asset, base_url, runtime_command
from project_paths import ASSETS, PROJECT, SOURCE
from setup_chromadb import pins
from setup_graphviz import assert_original_source, python_packages, source_hashes, system_packages, write_json
from setup_local_llm import sha256


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def gpu():
    result = subprocess.check_output(["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,utilization.gpu",
                                     "--format=csv,noheader,nounits"], text=True, timeout=10)
    index, name, total, used, utilization = [x.strip() for x in result.strip().splitlines()[0].split(",")]
    return {"time": time.time(), "index": int(index), "name": name, "total_mib": int(total),
            "used_mib": int(used), "utilization_percent": int(utilization)}


def main():
    previous = PROJECT / "docs/evidence/local_llm_runtime.json"
    attempts_path = PROJECT / "docs/evidence/local_llm_runtime_attempts.json"
    if previous.exists():
        old = json.loads(previous.read_text())
        attempts = json.loads(attempts_path.read_text()) if attempts_path.exists() else []
        if not any(x["timestamp_utc"] == old["timestamp_utc"] for x in attempts):
            attempts.append(old)
            write_json(attempts_path, attempts)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    logs = asset(CONFIG["logging"]["directory"]) / (stamp + "_verification")
    logs.mkdir(parents=True)
    report = {"timestamp_utc": stamp, "status": "IN_PROGRESS", "profile": CONFIG["profile"],
              "thinking_enabled": CONFIG["server"]["thinking"],
              "re_format_policy": RE_FORMAT_POLICY,
              "log_directory": logs.relative_to(ASSETS).as_posix(), "experiments_executed": False,
              "paid_api_calls": 0, "embedding_calls": 0, "web_search_calls": 0,
              "synthetic_local_generation_calls": 0, "paper_equivalence": False, "checks": {},
              "config_sha256": sha256(PROJECT / "configs/local_llm.json")}
    proc = None
    monitor_thread = None
    stop_monitor = threading.Event()
    samples = []
    llm = None
    before_source = source_hashes()
    before_packages = python_packages()
    before_system = system_packages()
    expected_packages = pins((PROJECT / "docs/evidence/installed_freeze_with_openai_embeddings.txt").read_text())

    def checkpoint():
        write_json(logs / "result.json", report)
        write_json(PROJECT / "docs/evidence/local_llm_runtime.json", report)

    def monitor():
        while not stop_monitor.is_set():
            try:
                samples.append(gpu())
            except Exception as exc:
                samples.append({"time": time.time(), "error": str(exc)})
            stop_monitor.wait(1)

    def capture(response):
        index = report["synthetic_local_generation_calls"] + 1
        report["synthetic_local_generation_calls"] = index
        write_json(logs / f"request_{index:02d}.json", llm.last_request)
        write_json(logs / f"response_{index:02d}.json", response)
        message = response["choices"][0]["message"]
        item = {"index": index, "finish_reason": response["choices"][0]["finish_reason"],
                "final_answer": message.get("content"), "thinking_characters": len(message.get("reasoning_content") or ""),
                "usage": response.get("usage"), "timings": response.get("timings")}
        report.setdefault("responses", []).append(item)
        checkpoint()

    def capture_re_format(record):
        index = report["synthetic_local_generation_calls"]
        write_json(logs / f"response_{index:02d}_re_format.json", record)
        report.setdefault("re_format_events", []).append(
            {"response_index": index, "status": record["status"], "normalization_passes": record["normalization_passes"]})
        checkpoint()

    try:
        require(before_packages == expected_packages and len(before_packages) == 201, "Existing Python environment changed")
        assert_original_source()
        installation = json.loads((PROJECT / "docs/evidence/local_llm_install.json").read_text())
        for item in installation["installed_files"]:
            require(sha256(asset(item["path"])) == item["sha256"], f"Runtime file changed: {item['path']}")
        report["gpu_before"] = gpu()
        command, env = runtime_command()
        with socket.socket() as probe:
            probe.settimeout(1)
            require(probe.connect_ex(("127.0.0.1", CONFIG["server"]["port"])) != 0, "Port already in use; will not reuse an unverified server")
        version = subprocess.run([command[0], "--version"], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        write_json(logs / "version.json", {"exit_code": version.returncode, "output": version.stdout})
        require(version.returncode == 0, "llama-server version check failed: " + version.stdout)
        report["version_output"] = version.stdout
        write_json(logs / "launch.json", {"command": command, "profile": CONFIG,
                                         "environment_overrides": {k: env[k] for k in ("LD_LIBRARY_PATH", "CUDA_CACHE_PATH")}})
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        with (logs / "server.log").open("w", encoding="utf-8") as log, httpx.Client(trust_env=False, timeout=10) as http:
            started = time.monotonic()
            proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
            while True:
                require(proc.poll() is None, f"Server exited with code {proc.returncode}; see {logs / 'server.log'}")
                try:
                    healthy = http.get(base_url() + "/health").status_code == 200
                except httpx.HTTPError:
                    healthy = False
                if healthy:
                    break
                require(time.monotonic() - started < 240, "Server startup exceeded 240 seconds")
                time.sleep(1)
            report["startup_seconds"] = time.monotonic() - started
            report["checks"]["server_healthy"] = True
            print(f"Server ready in {report['startup_seconds']:.1f}s", flush=True)
            models = http.get(base_url() + "/v1/models").json()
            props = http.get(base_url() + "/props").json()
            write_json(logs / "models.json", models)
            write_json(logs / "props.json", props)
            require(any(x["id"] == CONFIG["model"]["server_alias"] for x in models["data"]), "Wrong model served")
            text = (logs / "server.log").read_text()
            offloads = re.findall(r"offloaded (\d+)/(\d+) layers", text)
            require(offloads and all(int(a) == int(b) and int(a) >= 32 for a, b in offloads), "Full GPU layer offload not confirmed")
            report["checks"]["gpu_layers_fully_offloaded"] = offloads
            report["gpu_loaded"] = gpu()
            smoke = CONFIG["smoke_test"]
            llm = LocalLLMClient(max_tokens=smoke["max_tokens"], seed=smoke["seed"],
                                      sampling={k: smoke[k] for k in ("top_p", "top_k", "min_p", "presence_penalty")}, response_callback=capture)
            started = time.monotonic()
            final = llm.inquire_LLMs("What is 17 multiplied by 19? Return only the integer in your final answer.",
                                    "You are a helpful assistant.", temperature=smoke["temperature"])
            require(final.strip() == "323", "Synthetic arithmetic final answer mismatch")
            report["checks"]["arithmetic_final_and_mode"] = {"passed": True, "thinking_enabled": CONFIG["server"]["thinking"],
                                                            "elapsed_seconds": time.monotonic() - started}
            print(f"Synthetic arithmetic and configured thinking={CONFIG['server']['thinking']}: PASS", flush=True)

            # Compile the exact original method without executing module imports or constructors.
            # It builds original prompts and parses final strings for two fictitious variables.
            original_path = SOURCE / "ConstrainAgent/ConstrainAgent.py"
            tree = ast.parse(original_path.read_text())
            klass = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == "OnlyLLMAgent")
            method = next(x for x in klass.body if isinstance(x, ast.FunctionDef) and x.name == "generate_constrain_matrix")
            namespace = {"np": np, "tqdm": lambda values, **kwargs: values}
            exec(compile(ast.Module(body=[method], type_ignores=[]), str(original_path), "exec"), namespace)
            for reasoning in (False, True):
                case = "original_RE_parser" if reasoning else "original_yes_no_parser"
                print(f"Checking {case} on two synthetic nodes only", flush=True)
                client = REFormatClient(llm, expected_guesses=2, audit_callback=capture_re_format) if reasoning else llm
                obj = SimpleNamespace(label=["synthetic_input_x", "synthetic_output_y"], node_num=2,
                                      theme="a fictional deterministic system",
                                      dataset_information="In this fictional system x is externally set and y is always exactly twice x. Changing y alone cannot change x. No real dataset is used.",
                                      node_information=None, graph_matrix=np.zeros((2, 2)),
                                      causal_discovery_algorithm="a synthetic empty graph supplied for a format test; no statistical fitting was performed",
                                      use_reasoning=reasoning, guess_number=2, client=client)
                try:
                    with (logs / (case + ".txt")).open("w", encoding="utf-8") as out, contextlib.redirect_stdout(out):
                        matrix = namespace["generate_constrain_matrix"](obj)
                    parsed = bool(matrix[0, 1] in (0, 1) and matrix[1, 0] in (0, 1))
                    report["checks"][case] = {"passed": parsed, "matrix": matrix.tolist(),
                                              "source_sha256": sha256(original_path), "source_method_unmodified": True,
                                              "note": "Synthetic format compatibility only; not an RCA benchmark or full agent integration"}
                except Exception as exc:
                    report["checks"][case] = {"passed": False, "error": str(exc), "traceback": traceback.format_exc()}
                checkpoint()
            oversized = " hello" * (CONFIG["server"]["context_tokens"] + 100)
            tokens = http.post(base_url() + "/tokenize", json={"content": oversized}).json()["tokens"]
            require(len(tokens) > CONFIG["server"]["context_tokens"], "Overflow fixture did not exceed context")
            overflow = http.post(base_url() + "/v1/chat/completions", json={"model": CONFIG["model"]["server_alias"],
                                      "messages": [{"role": "user", "content": oversized}], "max_tokens": 1})
            write_json(logs / "overflow_response.json", {"status": overflow.status_code, "body": overflow.json(), "input_tokens_without_template": len(tokens)})
            require(overflow.status_code == 400, "Server did not reject oversized input")
            report["checks"]["oversized_input_rejected_without_truncation"] = True
        require(all(v.get("passed", True) for v in report["checks"].values() if isinstance(v, dict)), "One or more output format tests failed; original parser and outputs preserved")
        report["status"] = "PASS"
    except Exception as exc:
        report.update(status="FAILED", error={"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
    finally:
        if llm:
            llm.close()
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        stop_monitor.set()
        if monitor_thread:
            monitor_thread.join(timeout=12)
        write_json(logs / "gpu_samples.json", samples)
        valid = [x["used_mib"] for x in samples if "used_mib" in x]
        report["gpu_peak_total_used_mib"] = max(valid) if valid else None
        report["gpu_after"] = gpu()
        report["server_stopped"] = proc is None or proc.poll() is not None
        report["official_37_files_preserved"] = source_hashes() == before_source
        report["python_201_packages_preserved"] = python_packages() == before_packages == expected_packages
        report["system_packages_preserved"] = system_packages() == before_system
        report["script_hashes"] = {name: sha256(PROJECT / "scripts" / name) for name in
                                    ("setup_local_llm.py", "local_llm_runtime.py", "local_llm_client.py", "local_re_response.py", "check_local_llm_runtime.py")}
        if not all(report[x] for x in ("official_37_files_preserved", "python_201_packages_preserved", "system_packages_preserved", "server_stopped")):
            report["status"] = "FAILED"
        checkpoint()
        print(json.dumps({k: v for k, v in report.items() if k not in ("responses", "version_output")}, ensure_ascii=False, indent=2), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
