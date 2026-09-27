"""One user-approved D07 trial; preserve the failed request and all other settings."""
import json
import time
import traceback
from collections import Counter
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, asset_path
from local_llm_runtime import CONFIG
from rca_local_client import RecordedLocalClient
from rca_log_evidence import sha256
from setup_graphviz import assert_original_source, source_hashes, python_packages
from run_local_rca import local_server, write


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = asset_path("setup_logs") / f"rca_d07_presence_{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    evidence = PROJECT / f"docs/evidence/rca_d07_presence_{stamp}.json"
    old_path = ASSETS / "logs/setup/rca_real_rag_20260926T100603005620Z/calls/call_0000149.json"
    old = json.loads(old_path.read_text(encoding="utf-8"))
    before = {"sources": source_hashes(), "python": python_packages(),
              "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}
    report = {"checked_utc": stamp, "status": "IN_PROGRESS", "decision": "D07_A_USER_APPROVED",
              "logs": directory.relative_to(ASSETS).as_posix(),
              "original_call": old_path.relative_to(ASSETS).as_posix(), "original_call_sha256": sha256(old_path),
              "only_requested_change": {"presence_penalty": {"before": 0.0, "after": 1.5}},
              "automatic_retries": 0, "maximum_generation_attempts": 1,
              "adoption_requires_response_review": True, "full_pipeline_ready": False}
    def checkpoint():
        evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checkpoint()
    print(json.dumps({"evidence": str(evidence), "logs": str(directory)}), flush=True)
    client = None
    started = time.monotonic()
    try:
        assert_original_source()
        assert old["model"] == CONFIG["model"] and old["server"] == CONFIG["server"]
        assert old["temperature"] == 0.5 and old["max_tokens"] == 8192 and old["seed"] == 42
        assert old["sampling"]["presence_penalty"] == 0
        sampling = dict(old["sampling"], presence_penalty=1.5)
        write(directory / "approval.json", {"user_instruction": "권장 A안으로 진행해줘",
              "scope": "one identical failed request; only presence_penalty=1.5; if accepted use uniform log-only profile for both cases",
              "sampling": sampling, "other_stages_unchanged": True})
        with local_server(directory / "server"):
            client = RecordedLocalClient(directory / "calls", max_tokens=old["max_tokens"], seed=old["seed"], sampling=sampling)
            client.phase = "D07_A_trial/" + old["phase"]
            content = client.inquire_messages(old["messages"], temperature=old["temperature"])
            (directory / "response.txt").write_text(content, encoding="utf-8")
            expected_request = dict(old["request"], presence_penalty=1.5)
            report["request_diff_only_presence_penalty"] = client.last_request == expected_request
            if not report["request_diff_only_presence_penalty"]:
                raise RuntimeError("Unexpected request change beyond approved presence_penalty")
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            counts = Counter(lines)
            report.update(status="GENERATED_PENDING_SEMANTIC_REVIEW", usage=client.last_response.get("usage"),
                          finish_reason=client.last_response["choices"][0]["finish_reason"],
                          response_sha256=sha256(directory / "response.txt"),
                          nonempty_lines=len(lines), unique_lines=len(counts), duplicate_occurrences=len(lines)-len(counts),
                          repeated_lines={line: n for line, n in counts.items() if n > 1})
    except Exception:
        report.update(status="FAILED_D07_TRIAL", error=traceback.format_exc())
    finally:
        if client is not None:
            report["generation_attempts"] = client.counter
            if client.last_response:
                write(directory / "raw_response.json", client.last_response)
            client.close()
        report["seconds"] = time.monotonic() - started
        report["preservation"] = {"official_sources": source_hashes() == before["sources"],
                                  "python_packages": python_packages() == before["python"],
                                  "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")} == before["configs"],
                                  "original_failed_call": sha256(old_path) == report["original_call_sha256"]}
        report["script_sha256"] = sha256(PROJECT / "scripts/check_rca_d07_presence.py")
        if not all(report["preservation"].values()):
            report["status"] = "FAILED_PRESERVATION"
        checkpoint()
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report["status"] == "GENERATED_PENDING_SEMANTIC_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
