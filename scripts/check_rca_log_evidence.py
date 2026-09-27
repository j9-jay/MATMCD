"""Offline D01 routing/integrity checks; no log parsing, LLM or RCA execution."""
import argparse
import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from project_paths import ASSETS, PROJECT, SOURCE, asset_path
from rca_case_scope import case_key, select_active_cases
from rca_log_evidence import (
    build_plans, check_node_files, dispatch_summary, finalize_node_information,
    prepare_plans, read_json, sha256, verify_prepared_plans,
)


def check(prepare=False):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report_path = PROJECT / f"docs/evidence/rca_log_policy_{stamp}.json"
    report = {"checked_utc": stamp, "status": "IN_PROGRESS", "checks": [],
              "inference_calls": 0, "experiments_executed": False,
              "real_log_csvs_parsed": False, "D02_implemented": False,
              "author_equivalence": "UNCONFIRMED", "full_rca_ready": False}
    source_before = {str(p.relative_to(SOURCE)): sha256(p) for p in SOURCE.rglob("*") if p.is_file()}
    inputs_before = read_json(PROJECT / "configs/inputs.json")
    def expect(name, condition):
        report["checks"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)
    def rejects(name, callback, errors):
        try:
            callback()
        except errors:
            expect(name, True)
        else:
            expect(name, False)
    try:
        scope = read_json(PROJECT / "configs/scope.json")
        with zipfile.ZipFile(ASSETS / "raw_downloads/github_d2i_matmcd/ef2c3ec.zip") as archive:
            expected = {n for n in archive.namelist() if not n.endswith("/")} - set(scope["excluded_official_files"])
            expect("official_file_set_preserved", set(source_before) == expected)
            expect("official_source_byte_identical", all((SOURCE / n).read_bytes() == archive.read(n) for n in expected))
        plans = build_plans()
        report["cases"] = [{"case": key, "counts": plan["counts"],
                            "csv_sha256": plan["csv_sha256"],
                            "input_manifest_sha256": plan["input_manifest_sha256"]} for key, plan in plans.items()]
        report["totals"] = {key: sum(p["counts"][key] for p in plans.values())
                            for key in ("pods", "available", "missing", "kpi")}
        connection = read_json(PROJECT / inputs_before["connection_evidence"])
        selected = select_active_cases(connection["cases"])
        expected_available = sum(len(c["files"]) // 2 for c in selected)
        expected_missing = sum(len(c["missing_pods"]) for c in selected)
        expect("verified_actual_coverage", report["totals"] == {
            "pods": expected_available + expected_missing, "available": expected_available,
            "missing": expected_missing, "kpi": len(selected)})
        expect("selected_cases_only_in_approved_order", list(plans) == [case_key(c) for c in selected])
        report["case_scope_sha256"] = sha256(PROJECT / "configs/scope.json")
        calls = []
        def synthetic_summary(name, sources):
            calls.append(name)
            if not all(PurePosixPath(value["path"]).name == f"{name}_messages_{kind}.csv"
                       for kind, value in sources.items()):
                raise AssertionError(f"Borrowed/nonexact source: {name}")
            return f"SYNTHETIC ROUTING TEST ONLY: {name}"
        for key, plan in plans.items():
            calls.clear()
            routed = {name: dispatch_summary(plan, name, synthetic_summary) for name in plan["columns"]}
            present = {n["name"] for n in plan["nodes"] if n["evidence_available"] is True}
            expect(f"callbacks_only_for_exact_pairs:{key}", set(calls) == present and len(calls) == len(present))
            generated = {name: routed[name] for name in plan["columns"] if name in present}
            final = finalize_node_information(plan, generated)
            expect(f"all_candidates_and_order_preserved:{key}", list(final) == plan["columns"])
            fixed = [n for n in plan["nodes"] if n["evidence_available"] is not True]
            expect(f"absence_and_kpi_text_immutable:{key}", all(final[n["name"]] == n["fixed_information"] for n in fixed))
            missing = next(n["name"] for n in fixed if n["node_kind"] == "pod")
            rejects(f"reject_generated_missing_pod:{key}",
                    lambda: finalize_node_information(plan, {**generated, missing: "invented event"}), ValueError)
            rejects(f"reject_unknown_service_alias:{key}",
                    lambda: finalize_node_information(plan, {**generated, "UNVERIFIED_SERVICE_ALIAS": "borrowed log"}), ValueError)
            removed = dict(generated)
            removed.pop(next(iter(removed)))
            rejects(f"reject_incomplete_present_summaries:{key}", lambda: finalize_node_information(plan, removed), ValueError)
        # Files below are artificial routing fixtures in setup scratch space.
        # No real dataset/log is changed and no generated summary is persisted.
        with tempfile.TemporaryDirectory(prefix="d01_policy_check_", dir=asset_path("setup_logs")) as folder:
            directory = Path(folder)
            expected_paths = {k: str((directory / f"fixture_messages_{k}.csv").relative_to(ASSETS))
                              for k in ("templates", "structured")}
            missing_node = {"name": "fixture", "node_kind": "pod", "evidence_available": False,
                            "expected_paths": expected_paths, "sources": {}, "fixed_information": "ABSENT"}
            present_node = {**missing_node, "evidence_available": True, "fixed_information": None,
                            "sources": {k: {"path": path, "bytes": 4} for k, path in expected_paths.items()}}
            rejects("known_pair_disappearance_is_error_not_absence", lambda: check_node_files(present_node), RuntimeError)
            (ASSETS / expected_paths["templates"]).write_bytes(b"test")
            rejects("partial_pair_is_error", lambda: check_node_files(present_node), RuntimeError)
            rejects("new_file_for_missing_pod_requires_review", lambda: check_node_files(missing_node), RuntimeError)
            (ASSETS / expected_paths["structured"]).write_bytes(b"wrong_size")
            rejects("changed_file_size_is_error", lambda: check_node_files(present_node), RuntimeError)
        one = next(iter(plans.values()))
        one_name = next(n["name"] for n in one["nodes"] if n["evidence_available"] is True)
        rejects("empty_summary_is_error_not_absence", lambda: dispatch_summary(one, one_name, lambda *_: ""), ValueError)
        def failed_callback(*_):
            raise OSError("Synthetic reader failure; must not be hidden as no logs")
        rejects("reader_failure_propagates", lambda: dispatch_summary(one, one_name, failed_callback), OSError)
        if prepare:
            report["prepared_manifests"] = prepare_plans(plans)
        report["prepared_plan_verification"] = verify_prepared_plans(plans)
        source_after = {str(p.relative_to(SOURCE)): sha256(p) for p in SOURCE.rglob("*") if p.is_file()}
        expect("official_source_unchanged_after_checks", source_before == source_after)
        inputs_after = read_json(PROJECT / "configs/inputs.json")
        for field in ("rca_files", "rca_log_directories", "input_profile", "connection_evidence"):
            expect(f"input_mapping_unchanged:{field}", inputs_before[field] == inputs_after[field])
        report.update(status="PASS", official_files_preserved=len(source_before),
                      scripts_sha256={name: sha256(PROJECT / f"scripts/{name}.py")
                                      for name in ("rca_log_evidence", "check_rca_log_evidence")})
    except Exception as error:
        report.update(status="FAILED", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "report": str(report_path)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    check(parser.parse_args().prepare)
