"""Real full-input PC/RWR integration check before expensive local LLM stages.

No data reduction, parameter override, retry or scientific correction. Outputs
are diagnostic artifacts, not completed MATMCD experiment results.
"""
import contextlib
import json
import time
import traceback
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from project_paths import ASSETS, PROJECT, asset_path
from local_rca_components import official_pc, official_visualize
from rca_log_evidence import build_plans, verify_prepared_plans, sha256, within
from rca_ranking import rank_stage_with_original_rwr, encode_rng_state
from rca_evaluation import evaluate_case
from setup_graphviz import assert_original_source, source_hashes, python_packages
from run_local_rca import write


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = asset_path("setup_logs") / f"rca_real_integration_{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    evidence = PROJECT / f"docs/evidence/rca_real_integration_{stamp}.json"
    report = {"checked_utc": stamp, "status": "IN_PROGRESS", "phase": "full_input_PC_RWR",
              "logs": directory.relative_to(ASSETS).as_posix(), "cases": {},
              "full_pipeline_ready": False, "LLM_calls": 0, "scientific_changes": [],
              "automatic_retries": 0, "result_scope": "diagnostic_PC_baseline_only"}
    before = {"sources": source_hashes(), "python": python_packages(),
              "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}

    def checkpoint():
        evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checkpoint()
    print(json.dumps({"evidence": str(evidence), "logs": str(directory)}), flush=True)
    try:
        assert_original_source()
        plans = build_plans()
        verify_prepared_plans(plans)
        write(directory / "input_plans.json", plans)
        write(directory / "config_snapshot.json", {p.name: json.loads(p.read_text()) for p in (PROJECT / "configs").glob("*.json")})
        discover, visualize = official_pc(), official_visualize()
        for key, plan in plans.items():
            started = time.monotonic()
            case_dir = directory / key.replace("/", "_")
            case_dir.mkdir()
            item = {"status": "IN_PROGRESS", "phase": "read_complete_CSV", "node_count": len(plan["columns"])}
            report["cases"][key] = item
            checkpoint()
            print(json.dumps({"case": key, **item}), flush=True)
            try:
                csv_path = within(ASSETS, plan["csv"])
                if sha256(csv_path) != plan["csv_sha256"]:
                    raise RuntimeError("Metric CSV hash changed")
                frame = pd.read_csv(csv_path)
                if frame.columns.tolist() != plan["columns"]:
                    raise RuntimeError("Full column order differs")
                item.update(shape=list(frame.shape), csv_sha256=sha256(csv_path),
                            nonfinite_values=int((~np.isfinite(frame.values)).sum()),
                            constant_columns=frame.columns[frame.nunique(dropna=False) <= 1].tolist(),
                            phase="original_PC")
                write(case_dir / "rng_before_PC.json", encode_rng_state(np.random.get_state()))
                checkpoint()
                with (case_dir / "execution.log").open("x", encoding="utf-8") as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                    graph = discover(frame.values, plan["columns"], method="pc")
                    np.save(case_dir / "PC.npy", graph)
                    item.update(phase="original_RWR", graph_shape=list(graph.shape))
                    checkpoint()
                    ranking = rank_stage_with_original_rwr("PC", graph, None, plan["columns"])
                    write(case_dir / "PC_ranking.json", ranking)
                    write(case_dir / "PC_evaluation.json", evaluate_case(key, ranking))
                    visualize(graph, plan["columns"], str(case_dir / "PC.png"))
                item.update(status="PASS", phase="PC_RWR_complete")
            except Exception:
                item.update(status="FAILED", failed_phase=item["phase"], error=traceback.format_exc())
                (case_dir / "failure.txt").write_text(item["error"], encoding="utf-8")
            finally:
                item["seconds"] = time.monotonic() - started
                checkpoint()
                print(json.dumps({"case": key, "status": item["status"], "phase": item["phase"], "seconds": item["seconds"]}), flush=True)
        report["status"] = "PC_RWR_PASS_INTEGRATION_PENDING" if all(c["status"] == "PASS" for c in report["cases"].values()) else "BLOCKED_REAL_PC_RWR"
    except Exception:
        report.update(status="FAILED_PREFLIGHT", error=traceback.format_exc())
    finally:
        report["preservation"] = {"official_sources": source_hashes() == before["sources"],
                                  "python_packages": python_packages() == before["python"],
                                  "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")} == before["configs"]}
        report["script_sha256"] = sha256(PROJECT / "scripts/check_rca_real_integration.py")
        if not all(report["preservation"].values()):
            report["status"] = "FAILED_PRESERVATION"
        checkpoint()
    print(json.dumps({"status": report["status"], "evidence": str(evidence)}), flush=True)
    return 0 if report["status"] == "PC_RWR_PASS_INTEGRATION_PENDING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
