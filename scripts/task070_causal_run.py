"""TASK_070 category 2 run: MATMCD causal-discovery benchmarks with output head A.

For every dataset: official PC baseline, then each method answers the shared
pairwise judgment (task070_judge) for every ordered variable pair with evidence
from the fixed web snapshot corpus, then official PC with the constraints and the
official graph metrics against the ground-truth matrix. Run once, after the
category-2 freeze (task070_freeze_cat2).

Usage: python -B task070_causal_run.py --methods none flat role_only state_fixed state_dynamic
"""
import argparse
import json
import time
from datetime import datetime, timezone

import task070_causal as tcd
import task070_judge as tj
import task070_metrics as tm
import task070_output_head as oh
from local_llm_client import LocalLLMClient
from task070_common import WORK, write_json
from task070_pilot import start_server, stop_server
from task070_retrieval import K_EVIDENCE, FlatRetriever

DATASETS = ["Auto_MPG", "DWD_climate", "Sachs", "asia", "child"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--methods", nargs="+", default=["none", "flat", "role_only", "state_fixed", "state_dynamic"])
    parser.add_argument("--datasets", nargs="+", default=DATASETS)
    args = parser.parse_args()
    from task070_freeze_cat2 import verify_frozen_cat2
    verify_frozen_cat2()
    out = WORK / "causal_run" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True)
    from local_embedding import DenseBGE
    flat = FlatRetriever(DenseBGE())
    proc, log = start_server(out / "server.log")
    client = LocalLLMClient(max_tokens=tj.SAMPLING["max_tokens"], seed=tj.SAMPLING["seed"],
                            sampling={"presence_penalty": tj.SAMPLING["presence_penalty"]})
    planner = LocalLLMClient(max_tokens=256, seed=tj.SAMPLING["seed"], sampling={"presence_penalty": 0.0})
    summary = {"datasets": {}}
    try:
        for name in args.datasets:
            values, truth, labels = tcd.load(name)
            labels = list(labels)
            units = tcd.corpus(name)
            key = f"cd-{name}"
            result = {"pc_only": tm.graph_metrics(oh.fit_graph(values, labels), truth)}
            for method in args.methods:
                retriever = tcd.CausalStateRetriever(flat, planner, method.replace("state_", "")) \
                    if method in ("role_only", "state_fixed", "state_dynamic") else None
                answers, records, started = {}, [], time.monotonic()
                failed = None
                for a in labels:
                    for b in labels:
                        if a == b:
                            continue
                        if method == "none":
                            evidence, info = [], {}
                        elif method == "flat":
                            evidence, info = flat.select(key, units, a, b, K_EVIDENCE)
                        else:
                            evidence, info = retriever.select(key, units, a, b, labels)
                        messages, mapping = tj.build_messages(tcd.context(name, labels), labels, a, b, evidence)
                        try:
                            text = client.inquire_messages(messages, temperature=tj.SAMPLING["temperature"])
                            parsed = tj.parse(text, mapping)
                        except Exception as error:  # recorded; the pair counts as "No" under the failure rule
                            text, parsed = None, {"yes": False, "error": f"{type(error).__name__}: {error}"}
                            failed = (failed or 0) + 1
                        answers[(a, b)] = parsed["yes"]
                        records.append({"cause": a, "effect": b, "evidence_ids": [u["id"] for u in evidence],
                                        "info": info, "response": text, "parsed": parsed})
                constraints, counts = oh.constraint_matrix(labels, answers)
                graph = oh.fit_graph(values, labels, constraints)
                result[method] = {**tm.graph_metrics(graph, truth), "constraint_counts": counts,
                                  "failed_pairs": failed or 0, "seconds": time.monotonic() - started}
                mdir = out / method
                mdir.mkdir(exist_ok=True)
                (mdir / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
                                                    encoding="utf-8")
                summary["datasets"][name] = result
                write_json(out / "summary.json", summary)
                print(name, method, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in result[method].items()}, flush=True)
    finally:
        client.close()
        planner.close()
        stop_server(proc, log)
    print(out)


if __name__ == "__main__":
    main()
