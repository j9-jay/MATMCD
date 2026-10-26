"""Run output head B on RCAEval RE2-OB cases (development or, after G2, evaluation).

Usage: python -B task070_direct_run.py --split dev --start 0 --cases 10 --methods none flat role_only state_fixed state_dynamic
"""
import argparse
import json
import time
from datetime import datetime, timezone

import numpy as np

import task070_direct as td
import task070_metrics as tm
import task070_rcaeval as rc
from local_llm_client import LocalLLMClient
from task070_common import WORK, write_json
from task070_corpus import write_case_corpus
from task070_pilot import CONTEXT, start_server, stop_server
from task070_retrieval import FlatRetriever


def silver(units, root):
    return {u["id"] for u in units if u["role"] == "observation" and root in u["services"] and u["minutes"]}


def silver_strict(units, root):
    """Stricter variant (added 2026-10-25): only root-service units that mark an anomaly,
    i.e. metric/KPI series with flagged minutes or error spans. In silver(), log and trace
    units count whenever the service logged at all, so they are not anomaly evidence."""
    return {u["id"] for u in units if root in u["services"] and u["minutes"]
            and u["kind"] in ("metric", "kpi", "trace_error")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--cases", type=int, default=10)
    parser.add_argument("--methods", nargs="+", default=["none", "flat", "role_only", "state_fixed", "state_dynamic"])
    args = parser.parse_args()
    if args.split == "test":
        rc.verify_testset()
        from task070_freeze import verify_frozen
        verify_frozen()
    cases = rc.cases(args.split)[args.start: args.start + args.cases]
    out = WORK / "head_b" / f"{args.split}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    out.mkdir(parents=True)
    from local_embedding import DenseBGE
    flat = FlatRetriever(DenseBGE())
    proc, log = start_server(out / "server.log")
    client = LocalLLMClient(max_tokens=td.SAMPLING["max_tokens"], seed=td.SAMPLING["seed"], sampling={"presence_penalty": td.SAMPLING["presence_penalty"]})
    selector = td.DirectSelector(flat, client)
    summary = {"prompt_version": td.PROMPT_VERSION, "k": td.K_DIRECT, "order_repeats": td.ORDER_REPEATS,
               "split": args.split, "cases": [c["id"] for c in cases], "methods": {m: [] for m in args.methods}}
    try:
        for case in cases:
            _, units = write_case_corpus(case)
            _, labels, _ = rc.node_table(case["path"])
            services = labels[:-1]
            for method in args.methods:
                started = time.monotonic()
                try:
                    evidence, info = selector.select(method, case["id"], units, services)
                    mean_pos, runs = td.judge(client, CONTEXT, services, evidence, case["id"])
                except Exception as error:  # recorded as a failed case; no retry
                    row = {"case": case["id"], "status": "FAILED", "error": f"{type(error).__name__}: {error}"}
                    last = (client.last_response or {}).get("choices", [{}])[0].get("message", {}).get("content")
                    fdir = out / method / "failed"
                    fdir.mkdir(parents=True, exist_ok=True)
                    (fdir / f"{case['id']}.txt").write_text(last or "", encoding="utf-8")
                    summary["methods"][method].append(row)
                    write_json(out / "summary.json", summary)
                    print(method, row, flush=True)
                    continue
                seconds = time.monotonic() - started
                answer = rc.evaluation_label(case["path"])["root_cause_service"]
                metrics = tm.rca_case_metrics_tie_aware(services, [-mean_pos[s] for s in services], answer, "__none__")
                gold = silver(units, answer)
                strict = silver_strict(units, answer)
                ev_ids = [u["id"] for u in evidence]
                cited = [c for r in runs for c in r["cited_unit_ids"]]
                row = {"case": case["id"], "status": "COMPLETE", "seconds": seconds, **{k: metrics[k] for k in ("AC@1", "AC@3", "AC@5", "Avg@5", "RR")},
                       "silver_precision": float(np.mean([e in gold for e in ev_ids])) if ev_ids else None,
                       "silver_recall": float(len(gold & set(ev_ids)) / len(gold)) if gold and ev_ids else None,
                       "attribution_precision": float(np.mean([c in gold for c in cited])) if cited else None,
                       "strict_precision": float(np.mean([e in strict for e in ev_ids])) if ev_ids else None,
                       "strict_recall": float(len(strict & set(ev_ids)) / len(strict)) if strict and ev_ids else None,
                       "strict_attribution_precision": float(np.mean([c in strict for c in cited])) if cited else None,
                       "missing_names": sum(len(r["missing"]) for r in runs),
                       "evidence_roles": [u["role"] for u in evidence]}
                summary["methods"][method].append(row)
                mdir = out / method
                mdir.mkdir(exist_ok=True)
                (mdir / f"{case['id']}.json").write_text(json.dumps(
                    {"evidence_ids": ev_ids, "info": info, "runs": runs, "mean_positions": mean_pos, "row": row},
                    ensure_ascii=False, indent=2), encoding="utf-8")
                write_json(out / "summary.json", summary)
                print(method, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    finally:
        client.close()
        stop_server(proc, log)
    print(out)


if __name__ == "__main__":
    main()
