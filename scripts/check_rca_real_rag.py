"""Validate full-case log summaries and original RAG using approved local models.

All active nodes and exact prepared prompts are retained. No retries, prompt
rewrites, parser repairs, truncation or automatic changes. Diagnostics only.
"""
import contextlib
import gc
import json
import subprocess
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from project_paths import ASSETS, PROJECT, asset_path
from local_llm_runtime import CONFIG
from local_embedding import DenseBGE, llamaindex_embedding
from local_rca_components import original_dataset_summary
from rca_local_client import RecordedLocalClient, llamaindex_local_llm, approved_log_summary_sampling
from rca_log_evidence import build_plans, verify_prepared_plans, sha256, finalize_node_information
from setup_graphviz import assert_original_source, source_hashes, python_packages
from run_local_rca import local_server, verified_prompt, write


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = asset_path("setup_logs") / f"rca_real_rag_{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    evidence = PROJECT / f"docs/evidence/rca_real_rag_{stamp}.json"
    report = {"checked_utc": stamp, "status": "IN_PROGRESS", "phase": "preflight",
              "logs": directory.relative_to(ASSETS).as_posix(), "cases": {},
              "generation_attempts": 0, "full_pipeline_ready": False,
              "automatic_retries": 0, "scientific_changes": ["D07 user-approved log-only presence_penalty 0 to 1.5"],
              "log_sampling_profile": "d07_log_presence_1_5_v1",
              "result_scope": "full_case_real_RAG_integration_diagnostic"}
    before = {"sources": source_hashes(), "python": python_packages(),
              "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}
    stop = threading.Event()
    monitor_thread = None
    client = None

    def checkpoint():
        evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def monitor():
        with (directory / "resources.jsonl").open("x", encoding="utf-8") as stream:
            while not stop.is_set():
                try:
                    mem = {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines()
                           if line.split(":")[0] in ("MemAvailable", "SwapTotal", "SwapFree")}
                    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used,memory.free", "--format=csv,noheader,nounits"], text=True, timeout=10).strip()
                    sample = {"utc": datetime.now(timezone.utc).isoformat(), "phase": report["phase"], "memory_kib": mem, "gpu_used_free_mib": gpu}
                except Exception as error:
                    sample = {"error": str(error)}
                stream.write(json.dumps(sample) + "\n")
                stream.flush()
                stop.wait(5)

    checkpoint()
    print(json.dumps({"evidence": str(evidence), "logs": str(directory)}), flush=True)
    try:
        assert_original_source()
        if CONFIG["server"]["context_tokens"] != 81920:
            raise RuntimeError("Expected approved 81920 context")
        plans = build_plans()
        verify_prepared_plans(plans)
        write(directory / "input_plans.json", plans)
        write(directory / "config_snapshot.json", {p.name: json.loads(p.read_text()) for p in (PROJECT / "configs").glob("*.json")})
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        chosen = CONFIG["smoke_test"]
        sampling = {k: chosen[k] for k in ("top_p", "top_k", "min_p", "presence_penalty")}
        # One server and one request at a time. PC diagnostics, if still running,
        # are a separate CPU process and do not share RNG/model state.
        with local_server(directory / "server"):
            client = RecordedLocalClient(directory / "calls", max_tokens=chosen["max_tokens"], seed=chosen["seed"], sampling=sampling)
            for key, plan in plans.items():
                name = key.replace("/", "_")
                case_dir = directory / name
                case_dir.mkdir()
                item = {"status": "IN_PROGRESS", "node_count": len(plan["columns"]),
                        "required_generated_summaries": sum(n["evidence_available"] is True for n in plan["nodes"]),
                        "completed_summaries": 0, "fixed_notices": 0}
                report["cases"][key] = item
                report.update(phase="pod_log_summary", case=key)
                corpus = case_dir / "summaries" / name
                corpus.mkdir(parents=True)
                with approved_log_summary_sampling(client):
                    for node in plan["nodes"]:
                        item["current_node"] = node["name"]
                        checkpoint()
                        if node["evidence_available"] is True:
                            message = verified_prompt(plan, node)
                            client.phase = f"{key}/pod_log_summary/{node['name']}"
                            started = time.monotonic()
                            text = client.inquire_LLMs(message["prompt"], message["system_prompt"], message["temperature"])
                            item["completed_summaries"] += 1
                            item["last_call_seconds"] = time.monotonic() - started
                            usage = client.last_response.get("usage", {})
                            print(json.dumps({"case": key, "completed": item["completed_summaries"], "total": item["required_generated_summaries"], "seconds": item["last_call_seconds"], "usage": usage}), flush=True)
                        else:
                            text = node["fixed_information"]
                            item["fixed_notices"] += 1
                        (corpus / f"{node['name']}_summary.txt").write_text(text, encoding="utf-8")
                        report["generation_attempts"] = client.counter
                        checkpoint()
                report["phase"] = "BGE_load_and_original_RAG"
                checkpoint()
                print(json.dumps({"case": key, "phase": report["phase"]}), flush=True)
                index_dir = case_dir / "rag_index"
                index_dir.mkdir()
                def embedding_event(event):
                    with (index_dir / "encoding.jsonl").open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(event) + "\n")
                client.phase = f"{key}/dataset_RAG_summary"
                with (case_dir / "rag_execution.log").open("x", encoding="utf-8") as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                    engine = DenseBGE(audit_callback=embedding_event)
                    functions = original_dataset_summary(llamaindex_embedding(engine), llamaindex_local_llm(client, context_window=CONFIG["server"]["context_tokens"]))
                    output = case_dir / "dataset_summary"
                    output.mkdir()
                    summary = functions["generate_dataset_summary"](name, plan["columns"], database_path=str(corpus.parent), output_dir=str(output), embeddings_path=str(index_dir), save_embeddings=True)
                    report["phase"] = "original_summary_parser"
                    checkpoint()
                    data_info, parsed = functions["split_summary_into_sub_questions"](summary)
                    available = {n["name"] for n in plan["nodes"] if n["evidence_available"] is True}
                    item["parsed_nodes"] = list(parsed)
                    item["missing_available_nodes"] = sorted(available - set(parsed))
                    item["unknown_nodes"] = sorted(set(parsed) - set(plan["columns"]))
                    checkpoint()
                    if not available <= set(parsed) or set(parsed) - set(plan["columns"]):
                        raise RuntimeError("Original summary parser did not return every available pod exactly; no invented summary")
                    node_info = finalize_node_information(plan, {n: parsed[n] for n in plan["columns"] if n in available})
                    data_info += "\n\n" + plan["system_coverage_notice"]
                    write(case_dir / "node_information.json", {"dataset_information": data_info, "node_information": node_info})
                    del functions, engine
                    gc.collect()
                item["status"] = "PASS"
                report["generation_attempts"] = client.counter
                checkpoint()
                print(json.dumps({"case": key, "status": "PASS"}), flush=True)
        report["status"] = "REAL_RAG_PASS_AGENT_INTEGRATION_PENDING"
    except Exception:
        report.update(status="BLOCKED_REAL_RAG", failed_phase=report["phase"], error=traceback.format_exc())
        if report.get("case") in report["cases"]:
            report["cases"][report["case"]]["status"] = "FAILED"
        (directory / "failure.txt").write_text(report["error"], encoding="utf-8")
    finally:
        if client is not None:
            report["generation_attempts"] = client.counter
            client.close()
        stop.set()
        if monitor_thread is not None:
            monitor_thread.join(timeout=15)
        report["preservation"] = {"official_sources": source_hashes() == before["sources"],
                                  "python_packages": python_packages() == before["python"],
                                  "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")} == before["configs"]}
        report["script_sha256"] = sha256(PROJECT / "scripts/check_rca_real_rag.py")
        if not all(report["preservation"].values()):
            report["status"] = "FAILED_PRESERVATION"
        checkpoint()
    print(json.dumps({"status": report["status"], "evidence": str(evidence), "phase": report.get("failed_phase")}), flush=True)
    return 0 if report["status"] == "REAL_RAG_PASS_AGENT_INTEGRATION_PENDING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
