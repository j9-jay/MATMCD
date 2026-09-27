"""TASK_052: three authorized same-message trials, changing only presence penalty."""
import json
import time
import traceback
from collections import Counter
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, asset_path
from local_llm_runtime import CONFIG
from rca_local_client import RecordedLocalClient
from rca_log_evidence import read_json, sha256, within
from run_local_rca import local_server, write
from run_rca_oracle30 import snapshot
from continue_rca_oracle30 import domain_profile
from setup_graphviz import assert_original_source


def main():
    approved = domain_profile(require_review=False)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = asset_path("setup_logs") / f"rca_domain_presence_{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    evidence = PROJECT / f"docs/evidence/rca_domain_presence_{stamp}.json"
    parent = within(ASSETS, approved["failed_run"])
    originals = {n: parent / "calls" / f"call_{n:07d}.json" for n in approved["diagnostic_call_numbers"]}
    before = snapshot()
    report = {"status": "IN_PROGRESS", "profile": approved["profile_id"],
              "logs": directory.relative_to(ASSETS).as_posix(),
              "profile_sha256": sha256(PROJECT / "configs/rca_domain_sampling.json"),
              "original_call_hashes": {str(n): sha256(p) for n, p in originals.items()},
              "only_requested_change": {"presence_penalty": [0.0, 1.5]},
              "automatic_retries": 0, "trials": [], "full_experiment_started": False}
    def save():
        evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save()
    print(json.dumps({"evidence": str(evidence), "logs": str(directory)}), flush=True)
    client = None
    started = time.monotonic()
    try:
        assert_original_source()
        write(directory / "approval.json", approved)
        write(directory / "environment_before.json", before)
        with local_server(directory / "server"):
            chosen = CONFIG["smoke_test"]
            sampling = {k: chosen[k] for k in ("top_p", "top_k", "min_p", "presence_penalty")}
            client = RecordedLocalClient(directory / "calls", max_tokens=chosen["max_tokens"],
                                         seed=chosen["seed"], sampling=dict(sampling, **approved["overrides"]))
            for number, path in originals.items():
                old = read_json(path)
                if (old["model"] != CONFIG["model"] or old["server"] != CONFIG["server"]
                        or old["sampling"] != sampling or old["temperature"] != 0.5
                        or old["phase"] != "MATMCD_domain" or old["max_tokens"] != client.max_tokens
                        or old["seed"] != client.seed):
                    raise RuntimeError("Diagnostic original conditions differ")
                client.phase = f"TASK_052_trial/original_{number}/MATMCD_domain"
                content = client.inquire_messages(old["messages"], temperature=old["temperature"])
                response_path = directory / f"response_original_{number}.txt"
                response_path.write_text(content, encoding="utf-8")
                if client.last_request != dict(old["request"], **approved["overrides"]):
                    raise RuntimeError("Actual request changed beyond presence_penalty")
                lines = [s.strip() for s in content.splitlines() if s.strip()]
                counts = Counter(lines)
                item = {"original_call": number, "new_call": client.counter,
                        "actual_request_diff_only_presence_penalty": True,
                        "old_usage": old["response"]["usage"], "new_usage": client.last_response["usage"],
                        "finish_reason": client.last_response["choices"][0]["finish_reason"],
                        "response_sha256": sha256(response_path), "response": response_path.name,
                        "repeated_lines": {s: n for s, n in counts.items() if n > 1},
                        "non_parametric_occurrences": content.count("non-parametric")}
                report["trials"].append(item)
                save()
                print(json.dumps(item, ensure_ascii=False), flush=True)
        report["status"] = "GENERATED_PENDING_SEMANTIC_REVIEW"
    except Exception:
        report.update(status="FAILED", error=traceback.format_exc())
    finally:
        if client is not None:
            report["generation_attempts"] = client.counter
            client.close()
        after = snapshot()
        write(directory / "environment_after.json", after)
        report.update(seconds=time.monotonic() - started, environment_unchanged=before == after,
                      originals_unchanged=all(sha256(p) == report["original_call_hashes"][str(n)] for n, p in originals.items()))
        if not report["environment_unchanged"] or not report["originals_unchanged"]:
            report["status"] = "FAILED_PRESERVATION"
        save()
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report["status"] == "GENERATED_PENDING_SEMANTIC_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
