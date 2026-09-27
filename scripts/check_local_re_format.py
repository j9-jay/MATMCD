"""Offline checks against saved responses and the unchanged original RE parser."""
import ast
import contextlib
import hashlib
import io
import json
import traceback
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np

from local_re_response import RE_FORMAT_POLICY, REFormatClient, REFormatError, normalize_re_response
from project_paths import ASSETS, PROJECT, SOURCE
from setup_chromadb import pins
from setup_graphviz import assert_original_source, python_packages, source_hashes, system_packages, write_json
from setup_local_llm import CONFIG, asset, sha256


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    logs = asset(CONFIG["logging"]["directory"]) / (stamp + "_re_format_offline")
    logs.mkdir(parents=True)
    evidence = PROJECT / "docs/evidence/local_re_format_runtime.json"
    if evidence.exists():
        write_json(logs / "previous_report.json", json.loads(evidence.read_text()))
    report = {"timestamp_utc": stamp, "status": "IN_PROGRESS", "policy": RE_FORMAT_POLICY,
              "log_directory": logs.relative_to(ASSETS).as_posix(), "checks": [],
              "model_generation_calls": 0, "experiments_executed": False, "paper_equivalence": False}
    before_source, before_python, before_system = source_hashes(), python_packages(), system_packages()
    before_config = sha256(PROJECT / "configs/local_llm.json")
    assert_original_source()
    expected_python = pins((PROJECT / "docs/evidence/installed_freeze_with_openai_embeddings.txt").read_text())
    if before_python != expected_python or len(before_python) != 201:
        raise RuntimeError("Existing Python environment changed")
    saved_run = ASSETS / "logs/local_llm/qwen35_4b_q5km_nonthinking_provisional_v1/20260925T044215843311Z_verification"
    thinking_run = ASSETS / "logs/local_llm/qwen35_4b_q5km_thinking_provisional_v1/20260925T042550544006Z_verification"
    files = {"nonthinking_forward": saved_run / "response_04.json",
             "nonthinking_reverse": saved_run / "response_05.json", "thinking_forward": thinking_run / "response_03.json"}
    hashes = {name: sha256(path) for name, path in files.items()}
    texts = {name: json.loads(path.read_text())["choices"][0]["message"]["content"] for name, path in files.items()}
    original = SOURCE / "ConstrainAgent/ConstrainAgent.py"
    klass = next(n for n in ast.parse(original.read_text()).body if isinstance(n, ast.ClassDef) and n.name == "OnlyLLMAgent")
    method = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == "generate_constrain_matrix")
    parser_block = next(n for n in ast.walk(method) if isinstance(n, ast.If) and any(
        isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "guess_prob_pairs" for t in s.targets)
        for s in n.body))
    parser_code = compile(ast.Module(body=parser_block.body, type_ignores=[]), str(original), "exec")
    method_code = compile(ast.Module(body=[method], type_ignores=[]), str(original), "exec")

    def parse(text):
        ns = {"response": text, "self": SimpleNamespace(constrain_matrix=np.full((2, 2), -1)), "i": 0, "j": 1}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(parser_code, ns)
        return {"pairs": ns["guess_prob_pairs"], "answer": ns["answer"], "edge": int(ns["self"].constrain_matrix[0, 1])}

    def check(name, operation):
        try:
            detail = operation()
            report["checks"].append({"name": name, "passed": True, "detail": detail})
        except Exception as exc:
            report["checks"].append({"name": name, "passed": False, "error": str(exc), "traceback": traceback.format_exc()})

    def saved_case(name, should_change, expected_edge):
        raw = texts[name]
        result = normalize_re_response(raw, expected_guesses=2)
        assert result.changed is should_change
        parsed = parse(result.normalized_text)
        assert parsed["pairs"] == sorted([(float(r.probability_text), r.guess) for r in result.records], reverse=True)
        assert parsed["edge"] == expected_edge
        assert normalize_re_response(result.normalized_text, expected_guesses=2).normalized_text == result.normalized_text
        assert not normalize_re_response(result.normalized_text, expected_guesses=2).changed
        if not should_change:
            assert result.normalized_text == raw and parsed == parse(raw)
        else:
            try:
                parse(raw)
            except IndexError:
                pass
            else:
                raise AssertionError("Expected the saved raw fixture to fail the original parser")
        write_json(logs / (name + ".json"), result.audit())
        return {"changed": result.changed, "edge": parsed["edge"], "records": len(result.records)}

    check("saved_valid_response_unchanged", lambda: saved_case("nonthinking_forward", False, 1))
    check("saved_nonthinking_failure_repaired", lambda: saved_case("nonthinking_reverse", True, 0))
    check("saved_thinking_failure_repaired", lambda: saved_case("thinking_forward", True, 1))

    def exact_failed_fields():
        raw = texts["nonthinking_reverse"]
        g1, tail = raw.removeprefix("G1: ").split("\nP1: ", 1)
        p1, tail = tail.split("\n\nG2: ", 1)
        g2, p2 = tail.split("\nP2: ", 1)
        fixed = normalize_re_response(raw, expected_guesses=2)
        assert [(r.guess, r.probability_text) for r in fixed.records] == [(g1, p1), (g2, p2)]
        return {"guess_texts_and_probability_literals_exact": True}

    check("failed_response_fields_exact", exact_failed_fields)

    def tie_preservation():
        guesses = ["<Alpha has  two spaces\nand a line break. <yes>>", "<Zulu retains its wording. <no>>"]
        canonical = f"G1: {guesses[0]}\n\nP1: 0.5000\n\n---G2: {guesses[1]}\n\nP2: 0.5000"
        single = canonical.replace("\n\nP", "\nP").replace("---G2:", "G2:")
        fixed = normalize_re_response(single, expected_guesses=2)
        assert [r.guess for r in fixed.records] == guesses
        assert [r.probability_text for r in fixed.records] == ["0.5000", "0.5000"]
        assert parse(fixed.normalized_text) == parse(canonical)
        assert parse(canonical)["answer"] == guesses[1]
        return {"original_tie_winner_preserved": True, "internal_whitespace_preserved": True}

    check("tie_selection_and_internal_text_preserved", tie_preservation)
    valid = "G1: First <yes>\n\nP1: 0.95\n\n---G2: Second <no>\n\nP2: 0.05"

    def no_separator_needed():
        raw = valid.replace("---", "")
        result = normalize_re_response(raw, expected_guesses=2)
        assert not result.changed and parse(raw) == parse(result.normalized_text)
        return {"already_parseable_text_passed_through": True}

    check("parseable_response_without_separator_unchanged", no_separator_needed)

    rejected = {
        "missing_P2": valid.rsplit("\n\nP2:", 1)[0],
        "duplicate_P": valid + "\nP2: 0.1",
        "duplicate_G": valid.replace("G2:", "G1:"),
        "wrong_order": valid.replace("G1:", "G2:", 1),
        "out_of_range_probability": valid.replace("P1: 0.95", "P1: 1.5"),
        "negative_probability": valid.replace("P1: 0.95", "P1: -0.95"),
        "exponent_probability": valid.replace("P1: 0.95", "P1: 9.5e-1"),
        "probability_comment": valid.replace("P1: 0.95", "P1: 0.95 confidence"),
        "missing_answer_tag": valid.replace("First <yes>", "First unknown"),
        "internal_blank_line": valid.replace("First <yes>", "First\n\nexplanation <yes>"),
        "internal_separator": valid.replace("First <yes>", "First --- explanation <yes>"),
        "unexpected_preamble": "Here is the answer:\n" + valid,
        "unexpected_tail": valid + "\nExtra explanation",
        "indented_ambiguous_label": valid.replace("---G2:", "  G2:"),
    }

    def reject(raw):
        try:
            normalize_re_response(raw, expected_guesses=2)
        except REFormatError as exc:
            return {"rejected_without_guessing": str(exc)}
        raise AssertionError("Unrecoverable response was accepted")

    for name, raw in rejected.items():
        check(name, lambda raw=raw: reject(raw))

    class ReplayClient:
        def __init__(self, replies):
            self.replies = iter(replies)
            self.calls = []

        def inquire_LLMs(self, prompt, system_prompt, temperature=0.5):
            self.calls.append({"messages": [{"role": "system", "content": system_prompt},
                                            {"role": "user", "content": prompt}], "temperature": temperature})
            return next(self.replies)

    def method_replay():
        replay = ReplayClient([texts["nonthinking_forward"], texts["nonthinking_reverse"]])
        events = []
        client = REFormatClient(replay, expected_guesses=2, audit_callback=events.append)
        obj = SimpleNamespace(label=["synthetic_input_x", "synthetic_output_y"], node_num=2,
                              theme="a fictional deterministic system",
                              dataset_information="In this fictional system x is externally set and y is always exactly twice x. Changing y alone cannot change x. No real dataset is used.",
                              node_information=None, graph_matrix=np.zeros((2, 2)),
                              causal_discovery_algorithm="a synthetic empty graph supplied for a format test; no statistical fitting was performed",
                              use_reasoning=True, guess_number=2, client=client)
        ns = {"np": np, "tqdm": lambda x, **kwargs: x}
        exec(method_code, ns)
        with (logs / "original_method_replay.txt").open("w", encoding="utf-8") as out, contextlib.redirect_stdout(out):
            matrix = ns["generate_constrain_matrix"](obj)
        assert matrix.tolist() == [[-1, 1], [0, -1]]
        assert len(replay.calls) == 2 and [event["status"] for event in events] == ["UNCHANGED", "NORMALIZED"]
        for index, call in zip((4, 5), replay.calls):
            saved = json.loads((saved_run / f"request_{index:02d}.json").read_text())
            assert call["messages"] == saved["messages"] and call["temperature"] == saved["temperature"]
        write_json(logs / "adapter_replay_events.json", events)
        return {"matrix": matrix.tolist(), "underlying_replay_calls": 2, "extra_retries": 0,
                "original_method_unmodified": True, "prompts_and_temperature_preserved": True}

    check("unchanged_original_method_with_audited_adapter", method_replay)

    def rejected_audit():
        raw = rejected["missing_P2"]
        replay = ReplayClient([raw])
        events = []
        wrapper = REFormatClient(replay, expected_guesses=2, audit_callback=events.append)
        try:
            wrapper.inquire_LLMs("synthetic format check", "synthetic system")
        except REFormatError:
            pass
        else:
            raise AssertionError("Expected REFormatError")
        assert len(replay.calls) == 1 and len(events) == 1
        assert events[0]["raw_text"] == raw and events[0]["normalized_text"] is None
        assert events[0]["status"] == "REJECTED"
        write_json(logs / "rejected_response_audit.json", events[0])
        return {"raw_failure_preserved": True, "underlying_replay_calls": 1, "extra_retries": 0}

    check("rejection_preserved_without_retry", rejected_audit)
    report.update(official_37_files_preserved=source_hashes() == before_source,
                  python_201_packages_preserved=python_packages() == before_python,
                  system_packages_preserved=system_packages() == before_system,
                  inference_config_preserved=sha256(PROJECT / "configs/local_llm.json") == before_config,
                  saved_raw_files_preserved=all(sha256(path) == hashes[name] for name, path in files.items()),
                  original_parser_sha256=sha256(original),
                  fixture_paths={name: path.relative_to(ASSETS).as_posix() for name, path in files.items()},
                  fixture_sha256=hashes,
                  script_sha256={name: sha256(PROJECT / "scripts" / name)
                                 for name in ("local_re_response.py", "check_local_re_format.py", "check_local_llm_runtime.py")})
    report["status"] = "PASS" if all(item["passed"] for item in report["checks"]) and all(report[key] for key in
        ("official_37_files_preserved", "python_201_packages_preserved", "system_packages_preserved",
         "inference_config_preserved", "saved_raw_files_preserved")) else "FAILED"
    write_json(logs / "result.json", report)
    write_json(evidence, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
