"""Read published RCA ZIP contents for a proposal; never preprocess or run RCA."""
import argparse
import csv
import hashlib
import importlib
import io
import json
import pickle
import platform
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath

import numpy as np

from project_paths import ASSETS, PROJECT

CORE_METRICS = {"cpu_usage", "memory_usage", "rate_received_packets",
                "rate_transmitted_packets", "received_bandwidth", "transmit_bandwidth"}


class NumpyOnlyUnpickler(pickle.Unpickler):
    """Published NPYs contain object dictionaries; disallow arbitrary globals."""
    def find_class(self, module, name):
        if module == "numpy" and name in {"ndarray", "dtype"}:
            return getattr(np, name)
        if module in {"numpy.core.multiarray", "numpy._core.multiarray"} and name in {"_reconstruct", "scalar"}:
            return getattr(importlib.import_module("numpy._core.multiarray"), name)
        if module in {"numpy.core.numeric", "numpy._core.numeric"} and name == "_frombuffer":
            return getattr(importlib.import_module("numpy._core.numeric"), name)
        raise pickle.UnpicklingError(f"Unapproved pickle global: {module}.{name}")


def read_npy(handle):
    version = np.lib.format.read_magic(handle)
    if version == (1, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(handle)
    elif version == (2, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_2_0(handle)
    else:
        raise ValueError(f"Unsupported NPY header: {version}")
    if not dtype.hasobject or shape != ():
        raise ValueError(f"Expected scalar object NPY; got {shape}, {dtype}")
    value = NumpyOnlyUnpickler(handle).load()
    if not isinstance(value, np.ndarray) or value.shape != ():
        raise ValueError("Unexpected NPY payload")
    result = value.item()
    if not isinstance(result, dict):
        raise ValueError("Expected mapping of KPI cases")
    if handle.read(1):
        raise ValueError("Unexpected trailing NPY data")
    return result


def array_hash(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def numeric_summary(value):
    data = np.asarray(value)
    if data.ndim != 2 or not np.issubdtype(data.dtype, np.number):
        raise ValueError(f"Unexpected Sequence: {data.shape}, {data.dtype}")
    finite = np.isfinite(data)
    all_finite = finite.all(axis=0)
    constants = [int(i) for i in np.flatnonzero(all_finite & (np.ptp(data, axis=0) == 0))]
    return {"shape": list(data.shape), "dtype": str(data.dtype),
            "nonfinite_per_column": np.count_nonzero(~finite, axis=0).astype(int).tolist(),
            "constant_columns": constants}


def inspect_logs(archive_path):
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.namelist()
        pod_members = [p for p in members if PurePosixPath(p).parent.name == "pod_removed"]
        templates = {PurePosixPath(p).name.removesuffix("_messages_templates.csv")
                     for p in pod_members if p.endswith("_messages_templates.csv")}
        structured = {PurePosixPath(p).name.removesuffix("_messages_structured.csv")
                      for p in pod_members if p.endswith("_messages_structured.csv")}
        header_examples = []
        for suffix in ("_messages_structured.csv", "_messages_templates.csv"):
            candidates = [p for p in pod_members if p.endswith(suffix)]
            for member in candidates[:1]:
                with archive.open(member) as handle:
                    header = next(csv.reader(io.TextIOWrapper(handle, encoding="utf-8-sig")), [])
                    header_examples.append({"member": member, "header": header})
        inventory = {"members": len(members), "scope": "pod_removed only; node_removed excluded",
                     "header_examples": header_examples, "template_pod_names": len(templates),
                     "structured_pod_names": len(structured)}
        return inventory, templates, structured


def inspect_case(asset_record, log_record):
    archive_path = ASSETS / asset_record["path"]
    day = archive_path.stem
    system = "Cloud_Computing" if "cloud_computing" in asset_record["path"] else "Product_Review"
    log_inventory, template_names, structured_names = inspect_logs(ASSETS / log_record["path"])
    result = {"system": system, "day": day, "archive": asset_record["path"],
              "archive_sha256_from_download_manifest": asset_record["sha256"],
              "revision": asset_record["revision"], "metrics": [],
              "log_archive": log_record["path"],
              "log_inventory": log_inventory}
    alignment_rows = {}
    with zipfile.ZipFile(archive_path) as archive:
        result["members"] = [{"name": item.filename, "bytes": item.file_size, "crc32": f"{item.CRC:08x}"}
                             for item in archive.infolist() if not item.is_dir()]
        for item in archive.infolist():
            name = PurePosixPath(item.filename).name
            if not name.startswith("pod_level_data") or not name.endswith(".npy"):
                continue
            with archive.open(item) as handle:
                payload = read_npy(handle)
            metric = {"member": item.filename, "cases": []}
            for key, entry in payload.items():
                required = {"Pod_Name", "KPI_Feature", "Sequence", "time"}
                if not isinstance(entry, dict) or not required <= entry.keys():
                    metric["cases"].append({"key": str(key), "supported_schema": False,
                                            "keys": sorted(entry.keys()) if isinstance(entry, dict) else [],
                                            "missing_fields": sorted(required - entry.keys()) if isinstance(entry, dict) else sorted(required),
                                            "note": "Recorded without guessing field names or modifying the source"})
                    continue
                pods = list(entry["Pod_Name"])
                features = list(entry["KPI_Feature"])
                sequence = np.asarray(entry["Sequence"])
                time_values = np.asarray(entry.get("time", []))
                item_summary = {"key": str(key), "supported_schema": True, "keys": sorted(entry.keys()), "kpi_label": str(entry.get("KPI_Label")),
                                "kpi_features": features, "pod_count": len(pods), "pod_names": pods,
                                "duplicate_pod_names": len(pods) != len(set(pods)),
                                "sequence": numeric_summary(sequence),
                                "columns_match_pods_plus_kpi": sequence.shape[1] == len(pods) + len(features),
                                "time_count": len(time_values), "time_dtype": str(time_values.dtype),
                                "time_matches_rows": len(time_values) == len(sequence),
                                "time_hash": array_hash(time_values),
                                "time_bounds": [str(time_values[0]), str(time_values[-1])] if len(time_values) else [],
                                "time_strictly_increasing": bool(np.all(time_values[1:] > time_values[:-1])) if len(time_values) else None,
                                "kpi_hash": array_hash(sequence[:, len(pods):]),
                                "pods_without_template": sorted(set(pods) - template_names),
                                "pods_without_structured_log": sorted(set(pods) - structured_names)}
                if len(time_values) > 1 and np.issubdtype(time_values.dtype, np.number):
                    intervals, counts = np.unique(np.diff(time_values), return_counts=True)
                    item_summary["time_intervals"] = [{"delta": float(d), "count": int(c)} for d, c in zip(intervals, counts)]
                metric["cases"].append(item_summary)
                selected = CORE_METRICS | ({"rate_storage_iops"} if system == "Cloud_Computing" else set())
                metric_name = name.removeprefix("pod_level_data_").removesuffix(".npy")
                if metric_name in selected:
                    alignment_rows.setdefault(str(key), []).append({
                        "metric": metric_name, "time": time_values.copy(),
                        "kpi": sequence[:, len(pods):].copy(), "pods": pods,
                        "features": features})
            result["metrics"].append(metric)
            print(f"{system}/{day}: {name}: " + str([(c["key"], c.get("sequence", {}).get("shape", "schema recorded only")) for c in metric["cases"]]), flush=True)
            del payload
    # Equality here is diagnostic; no alignment, filling, or feature merging occurs.
    groups = {}
    for metric in result["metrics"]:
        for case in metric["cases"]:
            if case["supported_schema"]:
                groups.setdefault(case["key"], []).append((metric["member"], case))
    result["cross_metric_checks"] = []
    for label, entries in groups.items():
        sets = [set(case["pod_names"]) for _, case in entries]
        result["cross_metric_checks"].append({
            "label": label, "metric_files": len(entries),
            "all_time_hashes_equal": len({case["time_hash"] for _, case in entries}) == 1,
            "all_kpi_hashes_equal": len({case["kpi_hash"] for _, case in entries}) == 1,
            "all_pod_orders_equal": all(entries[0][1]["pod_names"] == case["pod_names"] for _, case in entries),
            "common_pods": len(set.intersection(*sets)) if sets else 0,
            "union_pods": len(set.union(*sets)) if sets else 0})
    result["alignment_diagnostics"] = []
    for label, entries in alignment_rows.items():
        times = [entry["time"] for entry in entries]
        common = times[0]
        for time in times[1:]:
            common = np.intersect1d(common, time)
        valid = all(len(np.unique(time)) == len(time) and np.all(time[1:] > time[:-1]) for time in times)
        matched = []
        if valid and len(common):
            for entry in entries:
                matched.append(entry["kpi"][np.searchsorted(entry["time"], common)])
        pod_union = sorted(set.union(*(set(entry["pods"]) for entry in entries)))
        coverage = {pod: [entry["metric"] for entry in entries if pod in entry["pods"]] for pod in pod_union}
        result["alignment_diagnostics"].append({
            "label": label, "metric_files": [entry["metric"] for entry in entries],
            "unique_increasing_timestamps": valid, "intersection_rows": len(common),
            "intersection_bounds": [str(common[0]), str(common[-1])] if len(common) else [],
            "intersection_time_hash": array_hash(common),
            "kpi_equal_after_timestamp_alignment": all(np.array_equal(matched[0], value) for value in matched[1:]) if matched else None,
            "kpi_features": [entry["features"] for entry in entries],
            "rows_removed_by_intersection": {entry["metric"]: len(entry["time"]) - len(common) for entry in entries},
            "pod_union": len(pod_union), "pod_intersection": len(set.intersection(*(set(entry["pods"]) for entry in entries))),
            "metric_coverage_per_pod": coverage,
            "note": "Index/equality diagnostics only; no transformed input file created"})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", nargs="*", help="Inspect only these archive dates; omitted means all downloaded cases")
    parser.add_argument("--refresh-logs-only", action="store_true", help="Refresh log metadata of saved inventory, without re-reading NPYs")
    args = parser.parse_args()
    output = PROJECT / "docs/evidence/rca_input_inventory.json"
    if args.refresh_logs_only:
        report = json.loads(output.read_text(encoding="utf-8-sig"))
        for case in report["cases"]:
            info, templates, structured = inspect_logs(ASSETS / case["log_archive"])
            case["log_inventory"] = info
            for metric in case["metrics"]:
                for item in metric["cases"]:
                    if item.get("supported_schema"):
                        item["pods_without_template"] = sorted(set(item["pod_names"]) - templates)
                        item["pods_without_structured_log"] = sorted(set(item["pod_names"]) - structured)
        report["logs_rechecked_utc"] = datetime.now(timezone.utc).isoformat()
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Updated pod-only log inventories; no NPY reread, preprocessing, or experiment.")
        return 0
    files = json.loads((PROJECT / "docs/evidence/downloads.json").read_text(encoding="utf-8-sig"))["files"]
    metric_files = [item for item in files if "/Metrics Data/" in item["path"] and item["path"].endswith(".zip")]
    if args.days:
        metric_files = [item for item in metric_files if PurePosixPath(item["path"]).stem in args.days]
    report = {"checked_utc": datetime.now(timezone.utc).isoformat(), "purpose": "provisional RCA preprocessing proposal",
              "inspection_python": sys.version, "inspection_numpy": np.__version__, "inspection_platform": platform.platform(),
              "method": "stream ZIP; restricted NumPy dictionary decode; metadata and numeric validity only",
              "case_filter": args.days, "experiments_executed": False, "preprocessing_applied": False,
              "api_calls": False, "cases": [], "errors": []}
    if output.exists():
        previous = json.loads(output.read_text(encoding="utf-8-sig"))
        report["previous_inspection_errors"] = previous.get("previous_inspection_errors", []) + previous.get("errors", [])
        report["inspection_fix"] = "Generic pod_level_data.npy has another schema; record its keys and inspect named metric files independently."
    for item in metric_files:
        log_path = item["path"].replace("/Metrics Data/", "/Log Data/")
        log_record = next(record for record in files if record["path"] == log_path)
        try:
            report["cases"].append(inspect_case(item, log_record))
        except Exception as error:
            report["errors"].append({"archive": item["path"], "error": f"{type(error).__name__}: {error}"})
            print(report["errors"][-1], flush=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Cases: {len(report['cases'])}; errors: {len(report['errors'])}", flush=True)
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
