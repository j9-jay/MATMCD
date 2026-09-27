"""Inspect current RCA assets and wiring without fitting, inference, or API calls.

The automated checks establish necessary conditions, not sufficient conditions
for paper reproduction. Scientific/integration findings require separate review.
"""
import argparse
import ast
import csv
import hashlib
import importlib.metadata
import io
import json
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import PurePosixPath

from audit_setup import probe
from project_paths import ASSETS, PROJECT, SOURCE, asset_path
from rca_log_evidence import verify_prepared_plans
from rca_case_scope import active_cases, select_active_cases, validate_input_scope


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def file_check(path, expected):
    present = path.is_file()
    result = {"path": str(path.relative_to(ASSETS)), "exists": present}
    if present:
        result.update(bytes=path.stat().st_size, sha256=sha256(path))
    result["matches"] = present and result.get("sha256") == expected
    return result


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def runtime_code():
    return "\n".join([
        "import numpy,pandas; print('numpy/pandas imported', flush=True)",
        "import torch; print('torch imported', flush=True)",
        "from Utils.CausalDiscovery import causal_discovery; from Utils.RCA import random_walk_with_restart; print('RCA functions imported without execution', flush=True)",
        "from ConstrainAgent.ConstrainAgent import ConstrainNormalAgent; print('agent imported', flush=True)",
        "import Log_tools,Web_tools; print('log/web modules imported without calls', flush=True)",
        "print({'numpy':numpy.__version__,'pandas':pandas.__version__,'torch':torch.__version__,'cuda_available':torch.cuda.is_available(),'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}, flush=True)",
    ])


def log_inventory(path, pods):
    """Inspect all ZIP folders; do not treat similar names as the same pod."""
    by_parent = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = PurePosixPath(info.filename)
            for kind, suffix in (("templates", "_messages_templates.csv"),
                                 ("structured", "_messages_structured.csv")):
                if name.name.endswith(suffix):
                    by_parent[str(name.parent)][name.name[:-len(suffix)]][kind].append(info.filename)
        matched, extra, absent = {}, {}, []
        for pod in pods:
            locations = []
            for parent, entries in by_parent.items():
                entry = entries.get(pod, {})
                if len(entry.get("templates", [])) == len(entry.get("structured", [])) == 1:
                    locations.append({"parent": parent, "templates": entry["templates"][0],
                                      "structured": entry["structured"][0]})
            approved = [x for x in locations if PurePosixPath(x["parent"]).name == "pod_removed"]
            if len(approved) == 1:
                matched[pod] = approved[0]
            elif locations:
                extra[pod] = locations
            else:
                absent.append(pod)
        samples = []
        if matched:
            pod, pair = next(iter(matched.items()))
            for kind in ("templates", "structured"):
                with archive.open(pair[kind]) as stream:
                    header = next(csv.reader(io.TextIOWrapper(stream, encoding="utf-8-sig")))
                samples.append({"pod": pod, "kind": kind, "member": pair[kind], "header": header})
    return {"archive": str(path.relative_to(ASSETS)), "archive_hash_rechecked": False,
            "zip_folders_inspected": sorted(by_parent), "metric_pods": len(pods),
            "approved_folder_exact_pairs": len(matched),
            "missing_in_approved_folder": len(pods) - len(matched),
            "other_or_ambiguous_exact_locations": extra,
            "no_exact_pair_anywhere_in_archive": absent, "schema_examples": samples,
            "note": "ZIP directory entries and example headers checked; not all log rows or ZIP CRCs."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry-runtime", type=str, help="Recheck only a timed-out runtime probe; retain the original report")
    args = parser.parse_args()
    if sys.platform != "linux" or sys.prefix != str(asset_path("environment")):
        raise SystemExit("Run with the existing pinned WSL Python environment.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if args.retry_runtime:
        from pathlib import Path
        prior_path = Path(args.retry_runtime).resolve()
        if not prior_path.is_relative_to(PROJECT / "docs/evidence"):
            raise ValueError("The previous audit must be in the project's evidence directory.")
        prior = read_json(prior_path)
        if "시간 초과" not in prior.get("runtime_probe", {}).get("error", ""):
            raise ValueError("Only a timed-out import probe is eligible for this recheck.")
        print("Rechecking only timed-out imports, with stage output and a 180-second diagnostic timeout", flush=True)
        retry = {"checked_utc": stamp, "previous_report": prior_path.name,
                 "previous_sha256": sha256(prior_path), "previous_probe": prior["runtime_probe"],
                 "script_sha256": sha256(PROJECT / "scripts/audit_rca_readiness.py"),
                 "runtime_probe": probe(runtime_code(), timeout=180),
                 "diagnostic_timeout_changed": "60 to 180 seconds; no experiment or inference parameter changed",
                 "experiments_executed": False, "packages_changed": False}
        output = PROJECT / f"docs/evidence/rca_runtime_recheck_{stamp}.json"
        output.write_text(json.dumps(retry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"report": str(output), "runtime_probe": retry["runtime_probe"]}, ensure_ascii=False), flush=True)
        return 0 if retry["runtime_probe"]["ok"] else 2
    report = {"checked_utc": stamp, "python": sys.version, "platform": platform.platform(),
              "python_executable": sys.executable, "experiments_executed": False,
              "inference_or_paid_api_calls": 0, "input_or_model_changes": False,
              "execution_request": "User authorized RCA execution if setup is complete; no repeat execution approval required.",
              "script_sha256": sha256(PROJECT / "scripts/audit_rca_readiness.py")}
    config_names = ("paths", "scope", "inputs", "local_llm", "local_embedding", "rca_preprocessing_proposal")
    report["configuration_hashes"] = {name: sha256(PROJECT / f"configs/{name}.json") for name in config_names}
    scope = read_json(PROJECT / "configs/scope.json")
    excluded = set(scope["excluded_official_files"])
    original = ASSETS / "raw_downloads/github_d2i_matmcd/ef2c3ec.zip"
    expected_files, unchanged = {}, []
    with zipfile.ZipFile(original) as archive:
        for info in archive.infolist():
            if not info.is_dir() and info.filename not in excluded:
                expected_files[info.filename] = hashlib.sha256(archive.read(info)).hexdigest()
    for name, expected in expected_files.items():
        path = SOURCE / name
        unchanged.append(path.is_file() and sha256(path) == expected)
    actual = {p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob("*") if p.is_file()}
    report["official_source"] = {"files": len(expected_files), "all_match": all(unchanged) and actual == set(expected_files),
                                 "unexpected": sorted(actual - set(expected_files)),
                                 "missing": sorted(set(expected_files) - actual)}
    print("Official source checked", flush=True)

    validation = read_json(PROJECT / "docs/evidence/rca_preprocessing_validation.json")
    report["provisional_cases"] = []
    workspace = asset_path("runtime_workspace")
    for case in select_active_cases(validation["cases"]):
        directory = ASSETS / case["output_directory"]
        manifest_path = directory / "manifest.json"
        manifest = read_json(manifest_path)
        files = [file_check(directory / name, spec["sha256"]) for name, spec in case["outputs"].items()]
        manifest_ok = sha256(manifest_path) == case["manifest_sha256"]
        system, day = case["system"], case["day"]
        csv_path = directory / f"{system}_{day}.csv"
        with csv_path.open(encoding="utf-8", newline="") as stream:
            columns = next(csv.reader(stream))
        pods = [name for name in columns if name != "Latency"]
        logs = log_inventory(ASSETS / manifest["logs"]["archive"], pods)
        runtime_csv = workspace / f"data/LEMMA_RCA/{system}/Metrics/{system}_{day}.csv"
        log_dir = workspace / f"data/LEMMA_RCA/{system}/Log/{day}"
        missing_runtime = [pod for pod in pods if not all((log_dir / f"{pod}_messages_{kind}.csv").is_file()
                                                        for kind in ("templates", "structured"))]
        report["provisional_cases"].append({"system": system, "day": day, "files": files,
            "manifest_hash_matches": manifest_ok, "header_matches_manifest": columns == manifest["columns"],
            "latency_last": columns[-1] == "Latency", "logs": logs,
            "runtime_csv_present": runtime_csv.is_file(), "runtime_csv_path": str(runtime_csv),
            "runtime_log_pairs_missing": len(missing_runtime),
            "runtime_summary_present": (workspace / f"cache/Summarized_info/{system}_{day}_info.txt").is_file()})
        print(f"Input and log inventory checked: {system}/{day}", flush=True)

    llm = read_json(PROJECT / "configs/local_llm.json")
    embedding = read_json(PROJECT / "configs/local_embedding.json")
    installation = read_json(PROJECT / "docs/evidence/local_llm_install.json")
    report["models"] = {
        "qwen": file_check(ASSETS / llm["model"]["directory"] / llm["model"]["filename"], llm["model"]["sha256"]),
        "llama_server": file_check(ASSETS / installation["executable"], installation["executable_sha256"]),
        "bge_m3": file_check(ASSETS / embedding["model"]["directory"] / "pytorch_model.bin", embedding["model"]["weights_sha256"])}
    print("Model hashes checked", flush=True)
    baseline = {}
    for line in (PROJECT / "docs/evidence/installed_freeze_with_openai_embeddings.txt").read_text().splitlines():
        if "==" in line:
            name, version = line.split("==", 1)
            baseline[normalize(name)] = version
    installed = {normalize(d.metadata["Name"]): d.version for d in importlib.metadata.distributions() if d.metadata["Name"]}
    report["packages"] = {"baseline_count": len(baseline),
        "changed_or_missing": {k: {"expected": v, "actual": installed.get(k)} for k, v in baseline.items() if installed.get(k) != v},
        "added": {k: v for k, v in installed.items() if k not in baseline}}
    report["runtime_probe"] = probe(runtime_code(), timeout=60)
    dot = shutil.which("dot")
    report["graphviz"] = {"path": dot}
    if dot:
        version = subprocess.run([dot, "-V"], text=True, capture_output=True, timeout=10)
        report["graphviz"].update(exit_code=version.returncode, version=(version.stdout + version.stderr).strip())
    first_case = active_cases()[0]
    report["original_loader_probe"] = probe("from Utils.data import load_Lemma_data\ntry:\n"
        f" load_Lemma_data({first_case['system']!r},{first_case['day']!r})\n"
        "except Exception as error:\n print(type(error).__name__ + ': ' + str(error))\n raise", timeout=30)
    # The probe helper uses SOURCE as cwd. Inspect the actual workspace paths
    # separately above rather than interpreting this error as a workspace run.
    report["original_loader_probe"]["cwd"] = str(SOURCE)
    report["original_loader_probe"]["note"] = "Original source loader only, not an RCA execution; workspace presence checked separately."
    inputs = read_json(PROJECT / "configs/inputs.json")
    report["active_rca_cases"] = validate_input_scope(inputs)
    report["input_mapping_entries"] = len(inputs["rca_files"])
    entry = (SOURCE / "LEMMA_experiment.py").read_text(encoding="utf-8")
    tree = ast.parse(entry)
    calls = [node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    config_tree = ast.parse((SOURCE / "config.py").read_text())
    model = next(ast.literal_eval(n.value) for n in config_tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "MODEL" for t in n.targets))
    report["entrypoint_observations"] = {"sha256": sha256(SOURCE / "LEMMA_experiment.py"),
        "official_model": model, "calls_collect_web_content": "collect_web_content" in calls,
        "calls_generate_pod_summary": "generate_pod_summary" in calls,
        "imports_local_adapter": any(isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("local_") for n in ast.walk(tree)),
        "local_inference_config_sections": list(llm), "actual_rca_inference_profile_present": "rca_inference" in llm}
    report["manual_review_findings"] = [
        {"id": "RCA-LOG", "status": "OPEN", "finding": "Original RCA entrypoint uses web collection; log-summary integration is not implemented in the inspected local scripts.", "source": "official/matmcd/LEMMA_experiment.py:80; tasks/TASK_024_local_rca_integration.md"},
        {"id": "RCA-MODEL", "status": "OPEN", "finding": "Qwen/BGE installation and synthetic checks are complete; stage clients and real prompt budgets are not connected or verified for RCA.", "source": "scripts/local_llm_client.py; configs/local_llm.json; tasks/TASK_024_local_rca_integration.md"},
        {"id": "RCA-SCIENCE", "status": "OPEN", "finding": "First constrained RWR uses original graph; graph-direction and log-sampling discrepancies await resolution. No correction applied.", "source": "docs/ORIGINAL_LOCAL_ISSUES.md"},
        {"id": "RCA-EVAL", "status": "OPEN", "finding": "Official metrics script uses hardcoded ranks; fresh prediction/ground-truth mapping and aggregation are not finalized.", "source": "official/matmcd/LEMMA_Metrics.py; tasks/TASK_008_evaluate_results.md"}]
    try:
        report["log_evidence_policy"] = verify_prepared_plans()
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        report["log_evidence_policy"] = {"status": "FAILED", "error": str(error)}
    # Full coverage remains a factual diagnostic. Approved D01 permits absence,
    # but only when exact known pairs and the prepared routing plans are intact.
    report["log_coverage_diagnostics"] = {
        "exact_log_pairs_complete": all(c["logs"]["missing_in_approved_folder"] == 0 for c in report["provisional_cases"]),
        "runtime_logs_complete": all(c["runtime_log_pairs_missing"] == 0 for c in report["provisional_cases"])}
    necessary = {"official_source_intact": report["official_source"]["all_match"],
        "provisional_files_intact": all(c["manifest_hash_matches"] and c["header_matches_manifest"] and all(f["matches"] for f in c["files"]) for c in report["provisional_cases"]),
        "models_intact": all(x["matches"] for x in report["models"].values()),
        "base_packages_preserved": not report["packages"]["changed_or_missing"] and not report["packages"]["added"],
        "runtime_imports_pass": report["runtime_probe"]["ok"],
        "runtime_csvs_present": all(c["runtime_csv_present"] for c in report["provisional_cases"]),
        "approved_log_evidence_policy_ready": report["log_evidence_policy"]["status"] == "PASS"}
    report["necessary_checks"] = necessary
    report["configuration_unchanged"] = all(sha256(PROJECT / f"configs/{name}.json") == value for name, value in report["configuration_hashes"].items())
    report["status"] = "NOT_READY" if not all(necessary.values()) else "REQUIRES_INTEGRATION_REVIEW"
    report["ready_for_local_rca"] = False
    report["ready_for_exact_paper_reproduction"] = False
    report["readiness_scope"] = "No sufficient automatic READY verdict: integration/scientific findings above remain open."
    output = PROJECT / f"docs/evidence/rca_readiness_{stamp}.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(output), "necessary_checks": necessary,
                      "experiments_executed": False}, ensure_ascii=False), flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
