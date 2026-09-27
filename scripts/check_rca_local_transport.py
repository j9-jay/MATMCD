"""Offline SDK/guard tests: no server, inference, data reading or RCA fitting."""
import json
import traceback
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
from openai import OpenAI

import rca_local_client
from local_llm_client import LocalLLMClient
from local_llm_runtime import CONFIG
from local_prompt_capacity import measure_messages, PromptCapacityError
from project_paths import ASSETS, PROJECT, asset_path
from rca_local_client import RecordedLocalClient
from rca_log_evidence import sha256
from setup_graphviz import assert_original_source, source_hashes, python_packages


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = asset_path("setup_logs") / f"rca_local_transport_{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    report = {"status": "IN_PROGRESS", "checks": [], "network_requests": 0,
              "generation_calls": 0, "actual_experiment_results": False,
              "logs": directory.relative_to(ASSETS).as_posix()}
    before = {"source": source_hashes(), "python": python_packages(),
              "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}
    def check(name, condition):
        report["checks"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)
    payloads, response_changes = [], {}
    def respond(request):
        payloads.append(json.loads(request.content))
        message = {"role": "assistant", "content": "Synthetic response", **response_changes.get("message", {})}
        return httpx.Response(200, json={"id": "offline", "object": "chat.completion", "created": 0,
            "model": CONFIG["model"]["server_alias"], "choices": [{"index": 0, "message": message,
            "finish_reason": response_changes.get("finish_reason", "stop")}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}})
    def attach_mock(client):
        client.client.close()
        client.client = OpenAI(base_url="http://127.0.0.1:1/v1", api_key="offline-test", max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(respond), trust_env=False))
    chosen = CONFIG["smoke_test"]
    parameters = {"max_tokens": chosen["max_tokens"], "seed": chosen["seed"],
                  "sampling": {k: chosen[k] for k in ("top_p", "top_k", "min_p", "presence_penalty")}}
    client = recorded = None
    try:
        assert_original_source()
        client = LocalLLMClient(**parameters)
        attach_mock(client)
        messages = [{"role": "system", "content": "Synthetic system"},
                    {"role": "user", "content": "First question"},
                    {"role": "assistant", "content": "Prior answer"},
                    {"role": "user", "content": "Unchanged follow-up\n<Yes>"}]
        check("valid_response_returned", client.inquire_messages(messages, temperature=.1) == "Synthetic response")
        body = payloads[-1]
        check("all_chat_roles_order_and_content_preserved", body["messages"] == messages)
        check("actual_Qwen_identity", body["model"] == CONFIG["model"]["server_alias"])
        check("output_seed_temperature_preserved", (body["max_tokens"], body["seed"], body["temperature"]) ==
              (chosen["max_tokens"], chosen["seed"], .1))
        check("sampling_preserved", all(body[k] == v for k, v in parameters["sampling"].items()))
        check("nonthinking_and_prompt_cache_enabled", body["chat_template_kwargs"] == {"enable_thinking": False}
              and body["cache_prompt"] is True)
        check("SDK_automatic_retries_disabled", client.client.max_retries == 0)
        client.inquire_LLMs("Raw original prompt", "Raw original system", .8)
        check("original_two_message_API_unchanged", payloads[-1]["messages"] == [
            {"role": "system", "content": "Raw original system"}, {"role": "user", "content": "Raw original prompt"}]
            and payloads[-1]["temperature"] == .8)
        response_changes["finish_reason"] = "length"
        previous = len(payloads)
        try:
            client.inquire_messages(messages, temperature=.1)
        except RuntimeError:
            check("incomplete_response_preserved_without_retry", len(payloads) == previous + 1 and
                  client.last_response["choices"][0]["finish_reason"] == "length")
        else:
            check("incomplete_response_rejected", False)
        response_changes.clear()
        response_changes["message"] = {"reasoning_content": "Unexpected reasoning"}
        try:
            client.inquire_messages(messages, temperature=.1)
        except RuntimeError:
            check("unexpected_thinking_rejected", True)
        else:
            check("unexpected_thinking_rejected", False)
        response_changes.clear()

        recorded = RecordedLocalClient(directory / "synthetic_calls", **parameters)
        attach_mock(recorded)
        previous = len(payloads)
        with patch.object(rca_local_client, "measure_messages", return_value={"fits": False, "diagnostic": "synthetic overcapacity"}):
            try:
                recorded.inquire_messages(messages, temperature=.5)
            except PromptCapacityError:
                saved = json.loads((recorded.directory / "call_0000001.json").read_text())
                check("overcapacity_blocks_before_SDK", len(payloads) == previous)
                check("overcapacity_record_preserved", saved["status"] == "BLOCKED_CAPACITY" and
                      saved["messages"] == messages and saved["request"] is None and saved["response"] is None)
            else:
                check("overcapacity_rejected", False)
        with patch.object(rca_local_client, "measure_messages", return_value={"fits": True}):
            recorded.inquire_messages(messages, temperature=.5)
        saved = json.loads((recorded.directory / "call_0000002.json").read_text())
        check("complete_record_has_request_raw_response_and_timestamp", saved["status"] == "COMPLETE" and
              saved["request"]["messages"] == messages and saved["response"]["choices"][0]["message"]["content"] ==
              "Synthetic response" and bool(saved["started_utc"]))

        # The real server tokenizer is covered by TASK_042. This checks only
        # the exact boundary arithmetic and absence of prompt rewriting.
        api_calls, count = [], [CONFIG["server"]["context_tokens"] - chosen["max_tokens"] - 1]
        def tokens(request):
            api_calls.append((request.url.path, json.loads(request.content)))
            result = {"prompt": "unchanged synthetic template"} if request.url.path == "/apply-template" else {"tokens": [1] * count[0]}
            return httpx.Response(200, json=result)
        with httpx.Client(base_url="http://127.0.0.1:1", transport=httpx.MockTransport(tokens)) as mock:
            measured = measure_messages(messages, max_tokens=chosen["max_tokens"], client=mock)
            check("exact_context_guard_boundary_fits", measured["fits"] and
                  measured["required_with_one_token_guard"] == CONFIG["server"]["context_tokens"])
            count[0] += 1
            check("one_token_over_boundary_blocks", not measure_messages(messages, max_tokens=chosen["max_tokens"], client=mock)["fits"])
        check("capacity_meter_preserves_messages_and_special_tokens", api_calls[0][1]["messages"] == messages and
              api_calls[1][1] == {"content": "unchanged synthetic template", "add_special": True, "parse_special": True})

        import run_local_rca
        with patch.object(run_local_rca, "read_json", return_value={"status": "PREPARED_PENDING_CAPACITY_VALIDATION"}):
            try:
                run_local_rca.run()
            except RuntimeError as error:
                check("pending_execution_profile_blocks_before_real_run", str(error).startswith("Actual RCA is gated:"))
            else:
                check("pending_execution_profile_blocks_before_real_run", False)
        report["status"] = "PASS"
    except Exception:
        report.update(status="FAILED", error=traceback.format_exc())
    finally:
        for instance in (client, recorded):
            if instance is not None:
                instance.close()
        after = {"source": source_hashes(), "python": python_packages(),
                 "configs": {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}
        report["preservation"] = {k: before[k] == after[k] for k in before}
        if not all(report["preservation"].values()):
            report["status"] = "FAILED"
        report["script_sha256"] = {p: sha256(PROJECT / "scripts" / p) for p in
            ("check_rca_local_transport.py", "local_llm_client.py", "rca_local_client.py", "local_prompt_capacity.py")}
        evidence = PROJECT / f"docs/evidence/rca_local_transport_{stamp}.json"
        evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "evidence": str(evidence),
                      "error": report.get("error")}), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
