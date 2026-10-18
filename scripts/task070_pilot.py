"""TASK_070 P2 pilot: run baselines on a few development cases and measure cost.

Starts the pinned local llama-server, runs the shared judgment for every ordered
pair with each method, applies the shared output head, and stops the server.
Development split only. All requests/responses are written to disk.

Usage (pinned WSL env): python -B task070_pilot.py --cases 2 --methods none flat
"""
import argparse
import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np

import task070_judge as tj
import task070_metrics as tm
import task070_output_head as oh
import task070_rcaeval as rc
from local_llm_client import LocalLLMClient
from local_llm_runtime import base_url, runtime_command
from task070_common import WORK, write_json
from task070_corpus import write_case_corpus
from task070_retrieval import K_EVIDENCE, FlatRetriever
from task070_state_retriever import StateAwareRetriever

STATE_VARIANTS = {"state_dynamic": "dynamic", "state_fixed": "fixed", "role_only": "role_only"}

CONTEXT = ("Online Boutique, an e-commerce microservice application on Kubernetes, had a performance incident "
           "during a 24-minute observation window. Each service variable is the standardized average of that "
           "service's resource and latency metrics; KPI_frontend_latency_p90 is the p90 request latency of the "
           "frontend.")


def start_server(log_path):
    command, env = runtime_command()
    log = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(600):
        try:
            with urllib.request.urlopen(base_url() + "/health", timeout=2) as r:
                if r.status == 200:
                    return proc, log
        except Exception:
            pass
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited early; see {log_path}")
        time.sleep(1)
    proc.terminate()
    raise RuntimeError("llama-server did not become healthy")


def stop_server(proc, log):
    proc.terminate()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
    log.close()


def run_case(method, case, units, labels, client, retriever, out_dir, state_retrievers=None):
    answers, records = {}, []
    started = time.monotonic()
    for cause in labels:
        for effect in labels:
            if cause == effect:
                continue
            if method == "none":
                evidence, scores = [], []
            elif method == "flat":
                evidence, scores = retriever.select(case["id"], units, cause, effect, K_EVIDENCE)
            elif method in STATE_VARIANTS:
                evidence, info = state_retrievers[method].select(case["id"], units, cause, effect, K_EVIDENCE)
                scores = info
            else:
                raise ValueError(method)
            messages, mapping = tj.build_messages(CONTEXT, labels, cause, effect, evidence)
            t = time.monotonic()
            text = client.inquire_messages(messages, temperature=tj.SAMPLING["temperature"])
            usage = (client.last_response or {}).get("usage", {})
            parsed = tj.parse(text, mapping)
            answers[(cause, effect)] = parsed["yes"]
            records.append({"cause": cause, "effect": effect, "evidence_ids": [u["id"] for u in evidence],
                            "evidence_scores": scores, "response": text, "parsed": parsed,
                            "seconds": time.monotonic() - t, "usage": usage})
    judge_seconds = time.monotonic() - started
    (out_dir / f"{case['id']}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    return answers, records, judge_seconds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=2)
    parser.add_argument("--start", type=int, default=0, help="offset into the development cases")
    parser.add_argument("--methods", nargs="+", default=["none", "flat"])
    args = parser.parse_args()
    out = WORK / "p2_pilot" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True)
    cases = rc.cases("dev")[args.start: args.start + args.cases]
    retriever = None
    if "flat" in args.methods or any(m in STATE_VARIANTS for m in args.methods):
        from local_embedding import DenseBGE
        retriever = FlatRetriever(DenseBGE())
    proc, log = start_server(out / "server.log")
    client = LocalLLMClient(max_tokens=tj.SAMPLING["max_tokens"], seed=tj.SAMPLING["seed"],
                            sampling={"presence_penalty": tj.SAMPLING["presence_penalty"]})
    state_retrievers = {}
    if any(m in STATE_VARIANTS for m in args.methods):
        if retriever is None:
            from local_embedding import DenseBGE
            retriever = FlatRetriever(DenseBGE())
        planner = LocalLLMClient(max_tokens=256, seed=tj.SAMPLING["seed"], sampling={"presence_penalty": 0.0})
        for m in args.methods:
            if m in STATE_VARIANTS:
                state_retrievers[m] = StateAwareRetriever(retriever.encoder, planner, STATE_VARIANTS[m])
                state_retrievers[m].flat = retriever
    summary = {"prompt_version": tj.PROMPT_VERSION, "sampling": tj.SAMPLING, "k_evidence": K_EVIDENCE,
               "cases": [c["id"] for c in cases], "methods": {}}
    try:
        for method in args.methods:
            mdir = out / method
            mdir.mkdir()
            results = []
            for case in cases:
                _, units = write_case_corpus(case)
                values, labels, _ = rc.node_table(case["path"])
                if method == "pc_only":
                    answers, records, judge_seconds = None, [], 0.0
                    constraints, counts = None, {}
                else:
                    answers, records, judge_seconds = run_case(method, case, units, labels, client, retriever, mdir, state_retrievers)
                    constraints, counts = oh.constraint_matrix(labels, answers)
                ranking = oh.rwr_rankings(oh.fit_graph(values, labels, constraints), labels)
                answer = rc.evaluation_label(case["path"])["root_cause_service"]
                per_rep = [tm.rca_case_metrics_tie_aware(labels, r["counts"], answer, labels[-1]) for r in ranking["runs"]]
                per_rep_stable = [tm.rca_case_metrics(r["ranking"], answer, labels[-1]) for r in ranking["runs"]]
                tokens_in = sum(r["usage"].get("prompt_tokens", 0) for r in records)
                tokens_out = sum(r["usage"].get("completion_tokens", 0) for r in records)
                results.append({"case": case["id"], "pairs": len(records), "judge_seconds": judge_seconds,
                                "seconds_per_call": judge_seconds / len(records) if records else 0.0,
                                "prompt_tokens": tokens_in, "completion_tokens": tokens_out,
                                "constraint_counts": counts,
                                "invalid_citations": sum(len(r["parsed"]["invalid_citations"]) for r in records),
                                "graph_edges": int((oh.fit_graph(values, labels, constraints) != 0).sum()),
                                **{k: float(np.mean([p[k] for p in per_rep])) for k in ("AC@1", "AC@3", "AC@5", "Avg@5", "RR")},
                                "stable_order_Avg@5": float(np.mean([p["Avg@5"] for p in per_rep_stable]))})
                write_json(out / "summary.json", summary | {"methods": summary["methods"] | {method: results}})
                print(method, results[-1], flush=True)
            summary["methods"][method] = results
    finally:
        client.close()
        stop_server(proc, log)
    write_json(out / "summary.json", summary)
    print(out)


if __name__ == "__main__":
    main()
