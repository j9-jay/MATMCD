"""Synthetic D06 invariants; never decodes experiment files or calls a model."""
import json
import traceback
from datetime import datetime, timezone

import pandas as pd

from project_paths import ASSETS, PROJECT, asset_path
from local_rca_components import official_log_summary_call
from rca_log_encoding import ApprovedReader, EncodingSelectionError, require_valid_prompt
from rca_log_evidence import sha256
from setup_graphviz import assert_original_source, source_hashes, python_packages


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = asset_path("setup_logs") / f"rca_encoding_tests_{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    report = {"status": "IN_PROGRESS", "checks": [], "generation_calls": 0,
              "actual_experiment_results": False, "logs": directory.relative_to(ASSETS).as_posix()}
    before = source_hashes(), python_packages()
    def check(name, condition):
        report["checks"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)
    def fixture(name, *, bad_row=None, bad_key=False):
        root = directory / name
        root.mkdir()
        templates = root / "A_messages_templates.csv"
        structured = root / "A_messages_structured.csv"
        templates.write_bytes(b"EventId,EventTemplate,Occurrence\nE1,Synthetic event,21\n")
        rows = []
        for i in range(21):
            content = f"Synthetic line {i}".encode()
            event = b"E1"
            if i == bad_row:
                if bad_key:
                    event = b"E\xc3"
                else:
                    content = b"Invalid source byte \xc3"
            rows.append(str(i).encode() + b"," + content + b"," + event + b"\n")
        structured.write_bytes(b"Time,Content,EventId\n" + b"".join(rows))
        return {"templates": templates, "structured": structured}
    def capture(paths, reader):
        captured = []
        class Client:
            def inquire_LLMs(self, prompt, system_prompt, temperature):
                message = {"prompt": prompt, "system_prompt": system_prompt, "temperature": temperature}
                require_valid_prompt(message)
                captured.append(message)
                return ""
        function = official_log_summary_call(Client(), reader)["generate_pod_summary"]
        function("synthetic", "A", str(paths["templates"].parent) + "/", ["A", "Latency"])
        return captured[0]
    try:
        assert_original_source()
        valid = fixture("strict_valid")
        expected = capture(valid, pd)
        audit = []
        check("valid_original_prompt_identical", capture(valid, ApprovedReader(pd, valid, audit)) == expected)
        check("valid_files_use_strict_defaults_only", all(a["mode"] == "strict_utf8" for a in audit))
        unselected = fixture("invalid_unselected_content", bad_row=1)
        initial_hashes = {k: sha256(p) for k, p in unselected.items()}
        audit = []
        check("unselected_bad_byte_does_not_change_original_prompt", capture(unselected, ApprovedReader(pd, unselected, audit)) == expected)
        record = next(a for a in audit if a["kind"] == "structured")
        check("all_rows_and_invalid_byte_recorded", record["rows"] == 21 and record["invalid_bytes"] == 1 and
              record["invalid_bytes_by_column"] == {"Content": {"invalid_bytes": 1, "rows": 1}})
        check("selection_fields_validated", record["selection_fields_valid"] is True)
        raw = unselected["structured"].read_bytes()
        check("surrogateescape_byte_roundtrip", raw.decode("utf8", "surrogateescape").encode("utf8", "surrogateescape") == raw)
        check("source_files_unchanged", {k: sha256(p) for k, p in unselected.items()} == initial_hashes)
        for name, options in (("selected_content", {"bad_row": 0}), ("selection_key", {"bad_row": 1, "bad_key": True})):
            paths = fixture(name, **options)
            try:
                capture(paths, ApprovedReader(pd, paths, []))
            except EncodingSelectionError:
                check(f"reject_{name}_without_replacement_or_model_call", True)
            else:
                check(f"reject_{name}_without_replacement_or_model_call", False)
        reader = ApprovedReader(pd, valid, [])
        try:
            reader.read_csv(valid["structured"], nrows=1)
        except ValueError:
            check("reject_unapproved_reader_options", True)
        else:
            check("reject_unapproved_reader_options", False)
        report["status"] = "PASS"
    except Exception:
        report.update(status="FAILED", error=traceback.format_exc())
    report["preservation"] = {"source": source_hashes() == before[0], "python": python_packages() == before[1]}
    if not all(report["preservation"].values()):
        report["status"] = "FAILED"
    report["scripts"] = {p: sha256(PROJECT / "scripts" / p) for p in ("rca_log_encoding.py", "check_rca_log_encoding.py", "rca_log_worker.py")}
    evidence = PROJECT / f"docs/evidence/rca_log_encoding_tests_{stamp}.json"
    evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "report": str(evidence), "error": report.get("error")}), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
