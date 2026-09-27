"""Synthetic local wiring checks plus one unchanged real CSV-request replay."""
import contextlib
import json
import os
import traceback
from datetime import datetime, timezone

import numpy as np

from local_rca_components import official_agent_class, original_dataset_summary
from local_re_response import normalize_re_response, REFormatError
from project_paths import ASSETS, PROJECT, asset_path
from rca_local_client import llamaindex_local_llm
from rca_log_evidence import read_json, sha256, within, finalize_node_information
from rca_log_worker import prepare_one
from setup_graphviz import assert_original_source, python_packages, source_hashes


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    logs = asset_path("setup_logs") / f"local_rca_components_{stamp}"
    logs.mkdir(parents=True, exist_ok=False)
    report = {"status": "IN_PROGRESS", "checks": [], "actual_experiment_results": False,
              "generation_calls": 0, "logs": logs.relative_to(ASSETS).as_posix()}
    original, packages = source_hashes(), python_packages()
    configs = {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}
    def check(name, condition):
        report["checks"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)
    try:
        assert_original_source()
        class ReplayClient:
            max_tokens = 8192
            def __init__(self):
                self.calls = []
            def inquire_LLMs(self, prompt, system_prompt, temperature=0.5):
                self.calls.append((prompt, system_prompt, temperature))
                if "G1:" in prompt:
                    return "G1: Synthetic relation <Yes>\nP1: 0.8\nG2: Synthetic alternative <No>\nP2: 0.2"
                if "Please answer this question with <Yes> or <No>" in prompt:
                    return "<Yes>"
                return "Synthetic explanation used only for local wiring verification."
            def inquire_messages(self, messages, *, temperature):
                self.calls.append((messages, temperature))
                return "Dataset Summary: Synthetic dataset\n---\nSummary of the A: Synthetic A\n---\nSummary of the B: Synthetic B"
        client, re_events = ReplayClient(), []
        Agent = official_agent_class(client, re_audit=re_events.append)
        matrix = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        for reasoning in (False, True):
            client.calls.clear()
            agent = Agent(["A", "B", "Latency"], "synthetic", graph_matrix=matrix,
                          causal_discovery_algorithm="pc", use_reasoning=reasoning)
            with (logs / f"agent_{reasoning}.log").open("w") as out, contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                constraint = agent.run(use_cache=False)
            check(f"original_all_ordered_pairs:{reasoning}", len(client.calls) == 12)
            check(f"original_stage_temperatures:{reasoning}", [c[2] for c in client.calls] == [.5] * 6 + [.8] * 6)
            check(f"original_constraint_orientation:{reasoning}", constraint.tolist() == [[-1, 1, 1], [1, -1, 1], [1, 1, -1]])
            check(f"D03_A_reversed_prompt_preserved:{reasoning}", "B is the cause of A." in client.calls[0][0])
            check(f"D03_A_first_pair_cache_preserved:{reasoning}", "changes in A do not directly affect B" in client.calls[1][0])
        check("RE_uppercase_content_and_probability_preserved", len(re_events) == 6 and all(
            e["records"][0]["guess"] == "Synthetic relation <Yes>" and e["records"][0]["probability_text"] == "0.8"
            for e in re_events))
        lower = normalize_re_response("G1: Original lower <yes>\nP1: 0.8\nG2: Lower alternative <no>\nP2: 0.2", expected_guesses=2)
        check("earlier_lowercase_RE_policy_preserved", lower.records[0].terminal_answer == "yes" and "<Yes>" not in lower.normalized_text)
        try:
            normalize_re_response("G1: Invalid case <yes>\nP1: 1", expected_guesses=1, terminal_answers=("Yes", "No"))
        except REFormatError:
            check("no_silent_answer_recase", True)
        else:
            check("no_silent_answer_recase", False)

        # Use actual installed LlamaIndex with fake embeddings and response. No
        # model/API calls, and no changes to default chunking/top-k or templates.
        os.environ["TIKTOKEN_CACHE_DIR"] = str(ASSETS / "caches/tiktoken")
        from llama_index.core.embeddings import MockEmbedding
        from llama_index.core import Settings
        from llama_index.core.node_parser import SentenceSplitter
        llm = llamaindex_local_llm(client, context_window=16384)
        functions = original_dataset_summary(MockEmbedding(embed_dim=8), llm)
        corpus = logs / "synthetic_corpus" / "synthetic_case"
        corpus.mkdir(parents=True)
        (corpus / "A.txt").write_text("A has a synthetic database event.", encoding="utf-8")
        (corpus / "B.txt").write_text("B has a synthetic frontend event.", encoding="utf-8")
        client.calls.clear()
        summary = functions["generate_dataset_summary"]("synthetic_case", ["A", "B"], database_path=str(corpus.parent))
        dataset, nodes = functions["split_summary_into_sub_questions"](summary)
        check("original_summary_query_and_strict_parser", dataset.strip() == "Synthetic dataset" and set(nodes) == {"A", "B"})
        check("llamaindex_default_temperature_preserved", all(c[1] == .1 for c in client.calls))
        check("chat_messages_and_actual_model_identity", llm.metadata.is_chat_model and llm.metadata.model_name.startswith("qwen35-") and
              any("Please provide a summary of the dataset synthetic_case" in m["content"] for call in client.calls for m in call[0]))
        check("default_splitter_preserved", isinstance(Settings.node_parser, SentenceSplitter) and
              (Settings.node_parser.chunk_size, Settings.node_parser.chunk_overlap) == (1024, 200))
        plan = read_json(within(ASSETS, read_json(PROJECT / "configs/inputs.json")["rca_log_evidence_manifests"]["Cloud_Computing/20231207"]))
        generated = {n["name"]: "Synthetic node summary" for n in plan["nodes"] if n["evidence_available"] is True}
        finalized = finalize_node_information(plan, generated)
        check("D01_fixed_missing_and_KPI_preserved", list(finalized) == plan["columns"] and all(
            finalized[n["name"]] == n["fixed_information"] for n in plan["nodes"] if n["evidence_available"] is not True))

        previous = next(c for c in read_json(PROJECT / "docs/evidence/rca_log_memory_20260925T131346346807Z.json")["cases"]
                        if c["case"] == "Cloud_Computing/20231207")
        request = read_json(within(ASSETS, previous["details_directory"]) / "request.json")
        node = next(n for n in plan["nodes"] if n["name"] == request["pod"])
        path = prepare_one(plan, node, request["theme"], logs / "original_request_replay")
        captured = read_json(path)
        original_prompt = within(ASSETS, previous["prompt"]["path"]).read_text(encoding="utf-8")
        check("real_full_CSV_request_same_as_D02", captured["prompt"] == original_prompt and captured["temperature"] == .5)
        check("real_system_prompt_captured_from_original_function", captured["system_prompt"] ==
              f"You are expert in the field of {request['theme']}, and you are able to analyze the log file and provide the summary of the entity.")
        check("CSV_worker_exited_before_generation", read_json(path.parent / "result.json")["generation_calls"] == 0)
        report["status"] = "PASS"
    except Exception:
        report.update(status="FAILED", error=traceback.format_exc())
    report["preservation"] = {"official_sources": source_hashes() == original, "python_packages": python_packages() == packages,
                              "configs": configs == {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}
    if not all(report["preservation"].values()):
        report["status"] = "FAILED"
    report["script_sha256"] = {p: sha256(PROJECT / "scripts" / p) for p in
                              ("local_rca_components.py", "local_re_response.py", "local_llm_client.py", "rca_local_client.py", "rca_log_worker.py")}
    evidence = PROJECT / f"docs/evidence/local_rca_components_{stamp}.json"
    evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "evidence": str(evidence), "error": report.get("error")}), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
