"""Apply the user-selected RCA cases; historical preparations stay intact."""
import json
import re

from project_paths import PROJECT


def case_key(case):
    system, day = case["system"], case["day"]
    if system not in ("Product_Review", "Cloud_Computing") or not isinstance(day, str) or not re.fullmatch(r"\d{8}", day):
        raise ValueError(f"Invalid RCA case: {system}/{day}")
    return f"{system}/{day}"


def active_cases():
    scope = json.loads((PROJECT / "configs/scope.json").read_text(encoding="utf-8"))
    selection = scope["rca_case_selection"]
    cases = selection["active_cases"]
    keys = [case_key(c) for c in cases]
    excluded = [case_key(c) for c in selection["excluded_cases"]]
    if not keys or len(keys) != len(set(keys)) or len(excluded) != len(set(excluded)) or set(keys) & set(excluded):
        raise ValueError("Empty, duplicate or conflicting RCA case selection")
    return cases


def select_active_cases(records, key=lambda record: record):
    """Select metadata before opening case assets; reject absent/duplicate cases."""
    lookup = {}
    for record in records:
        name = case_key(key(record))
        if name in lookup:
            raise ValueError(f"Duplicate case metadata: {name}")
        lookup[name] = record
    return [lookup[case_key(case)] for case in active_cases()]


def validate_input_scope(inputs):
    cases = active_cases()
    csv_keys = [f"LEMMA_RCA/{c['system']}/Metrics/{c['system']}_{c['day']}.csv" for c in cases]
    log_keys = [f"LEMMA_RCA/{c['system']}/Log/{c['day']}" for c in cases]
    if set(inputs["rca_files"]) != set(csv_keys) or set(inputs["rca_log_directories"]) != set(log_keys):
        raise ValueError("Active CSV/log mappings differ from approved case selection")
    if inputs["expected_rca_inputs"] != csv_keys:
        raise ValueError("Expected input order differs from approved case selection")
    if "rca_log_evidence_manifests" in inputs and set(inputs["rca_log_evidence_manifests"]) != {case_key(c) for c in cases}:
        raise ValueError("Evidence plans differ from approved case selection")
    return cases
