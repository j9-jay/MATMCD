"""Audit D03/D04 on unchanged official code; synthetic examples, no real RCA.

No LLM calls, causal fitting, real log reads, scientific corrections or new
experiment seeds. This records released-code behavior, not author-run identity.
"""
import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from typing import List, Tuple
from datetime import datetime, timezone

import numpy as np
from causallearn.graph.GraphNode import GraphNode
from causallearn.utils.PCUtils.BackgroundKnowledge import BackgroundKnowledge

from project_paths import ASSETS, PROJECT, SOURCE
from rca_case_scope import active_cases, case_key, validate_input_scope
from rca_log_evidence import read_json, sha256, within
from rca_metrics import evaluate_ranks
from rca_ranking import decode_rng_state, encode_rng_state, rank_with_original_rwr
from setup_graphviz import assert_original_source, python_packages, source_hashes


def extract(relative, names, namespace=None):
    path = SOURCE / relative
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    if {n.name for n in nodes} != set(names):
        raise RuntimeError(f"Official definition set changed: {relative}")
    ns = dict(namespace or {})
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), ns)
    return ns


def literal_assignment(tree, name):
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and
             any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    if len(nodes) != 1:
        raise RuntimeError(f"Ambiguous source assignment: {name}")
    return ast.literal_eval(nodes[0].value)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = PROJECT / f"docs/evidence/rca_original_protocol_{stamp}.json"
    report = {"checked_utc": stamp, "status": "IN_PROGRESS", "checks": [],
              "actual_experiment_results": False, "inference_calls": 0,
              "scientific_corrections_applied": False, "author_run_equivalence": "UNCONFIRMED",
              "synthetic_rng_seed": 173, "synthetic_seed_is_experiment_seed": False}
    before_source, before_python = source_hashes(), python_packages()
    rng_before = np.random.get_state()
    configs_before = {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}

    def expect(name, condition):
        report["checks"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    try:
        assert_original_source()
        expect("official_archive_and_37_files_match", len(before_source) == 37)
        cd = extract("Utils/CausalDiscovery.py", {"cg2matrix", "matrix_to_text", "matrix2backgroundknowledge"},
                     {"np": np, "List": List, "CausalGraph": object, "BackgroundKnowledge": BackgroundKnowledge})
        llms = extract("ConstrainAgent/LLMs.py", {"LLMs", "DomainKnowledgeLLM"},
                       {"np": np, "List": List, "Tuple": Tuple})
        rwr = extract("Utils/RCA.py", {"random_walk_with_restart"}, {"np": np})["random_walk_with_restart"]
        # Synthetic PC endpoint representation of A -> B; no fitting/data used.
        endpoints = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 0]])
        graph = cd["cg2matrix"](SimpleNamespace(G=SimpleNamespace(nodes=[0, 1, 2], graph=endpoints)))
        expect("causal_matrix_effect_row_cause_column", graph.tolist() == [[0, 0, 0], [1, 0, 0], [0, 0, 0]])
        text = cd["matrix_to_text"](graph, ["A", "B", "Latency"])
        expect("matrix_text_preserves_A_to_B", text == "A -> B")
        agent = llms["DomainKnowledgeLLM"](None, ["A", "B", "Latency"], "synthetic graph",
                                          graph_matrix=graph, causal_discovery_algorithm="pc")
        first, _ = agent.generate_prompt(0, 1)
        second, _ = agent.generate_prompt(1, 2)
        expect("released_prompt_reverses_directed_graph_description", "B is the cause of A." in first)
        expect("released_target_checks_transposed_entry", "changes in A do not directly affect B" in first)
        expect("released_prompt_reuses_first_pair_sentence", "changes in A do not directly affect B" in second and
               "relationship between B and Latency" in second)
        ambiguous = {}
        for edge_type in (-1, 2):
            matrix = np.array([[0, edge_type], [edge_type, 0]])
            a = llms["DomainKnowledgeLLM"](None, ["A", "B"], "synthetic ambiguous edge",
                                          graph_matrix=matrix, causal_discovery_algorithm="pc")
            prompt, _ = a.generate_prompt(0, 1)
            expect(f"released_edge_type_{edge_type}_described_as_two_causes",
                   "A is the cause of B." in prompt and "B is the cause of A." in prompt)
            ambiguous[str(edge_type)] = {"matrix_text": cd["matrix_to_text"](matrix, ["A", "B"]),
                                          "released_graph_prompt": a.graph_prompt}
        constraints = np.full((3, 3), -1)
        constraints[0, 1] = 1
        bk = cd["matrix2backgroundknowledge"](constraints, ["A", "B", "Latency"])
        expect("constraint_matrix_cause_row_effect_column", bk.is_required(GraphNode("A"), GraphNode("B")) and
               not bk.is_required(GraphNode("B"), GraphNode("A")))
        report["D03_prompt_examples"] = {"labels": ["A", "B", "Latency"], "causal_matrix": graph.tolist(),
                                          "matrix_text": text, "first_prompt": first, "second_prompt": second,
                                          "ambiguous_edge_types": ambiguous}
        source_path = SOURCE / "LEMMA_experiment.py"
        experiment_tree = ast.parse(source_path.read_text(encoding="utf-8"))
        calls = sorted([n for n in ast.walk(experiment_tree) if isinstance(n, ast.Call) and
                        isinstance(n.func, ast.Name) and n.func.id == "random_walk_with_restart"], key=lambda n: n.lineno)
        expressions = [ast.unparse(c.args[0]) for c in calls]
        expect("RWR_stage_inputs_original_original_refined_refined", expressions ==
               ["adjacency_matrix", "adjacency_matrix", "adjacency_matrix_optimized", "adjacency_matrix_optimized"])
        expect("RWR_calls_use_last_column_and_defaults", all(ast.unparse(c.args[1]) == "len(labels) - 1" and
                                                            len(c.args) == 2 and not c.keywords for c in calls))
        report["RWR_calls"] = [{"line": c.lineno, "expression": ast.unparse(c)} for c in calls]
        signature = inspect.signature(rwr)
        defaults = {name: signature.parameters[name].default for name in ("steps", "rp", "max_self")}
        expect("RWR_public_defaults", defaults == {"steps": 1000, "rp": 0.05, "max_self": 10})
        report["RWR_defaults"] = defaults
        # Preserve the global RNG outside these artificial diagnostic examples.
        np.random.set_state(np.random.RandomState(173).get_state())
        chain = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        state = np.random.get_state()
        state_json = json.loads(json.dumps([state[0], state[1].tolist(), state[2], state[3], state[4]]))
        counts = rwr(chain, 2)
        np.random.set_state((state_json[0], np.array(state_json[1], dtype=np.uint32), *state_json[2:]))
        replay_counts = rwr(chain, 2)
        expect("recorded_RNG_state_replays_unchanged_RWR", np.array_equal(counts, replay_counts))
        expect("RWR_preserves_input_matrix", chain.tolist() == [[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        expect("RWR_reaches_upstream_A_without_transpose", counts[0] > 0 and counts[1] > 0)
        report["synthetic_RWR_counts"] = counts.tolist()
        sorting = next(n for n in experiment_tree.body if isinstance(n, ast.Assign) and
                       any(isinstance(t, ast.Name) and t.id == "sorted_pairs" for t in n.targets))
        ns = {"count_label_pairs": [(2, "A"), (2, "B"), (3, "Latency")]}
        exec(compile(ast.Module(body=[sorting], type_ignores=[]), str(source_path), "exec"), ns)
        expect("stable_count_descending_sort_retains_KPI", ns["sorted_pairs"] == [(3, "Latency"), (2, "A"), (2, "B")])
        report["sort_example"] = ns["sorted_pairs"]
        ranking = rank_with_original_rwr(chain, ["A", "B", "Latency"])
        state_after_wrapper = encode_rng_state(np.random.get_state())
        np.random.set_state(decode_rng_state(ranking["rng_before"]))
        direct_counts = rwr(chain, 2)
        expect("ranking_adapter_matches_direct_original_RWR", direct_counts.tolist() == ranking["counts_in_original_order"])
        expect("ranking_adapter_preserves_exact_RNG_consumption", state_after_wrapper == encode_rng_state(np.random.get_state()))
        np.random.set_state(decode_rng_state(ranking["rng_before"]))
        replay = rank_with_original_rwr(chain, ["A", "B", "Latency"])
        expect("ranking_adapter_JSON_RNG_replay_identical", ranking == replay)
        expect("ranking_adapter_keeps_all_nodes_and_assigns_no_seed", len(ranking["ranking"]) == 3 and
               {r["node"] for r in ranking["ranking"]} == {"A", "B", "Latency"} and ranking["seed_assigned"] is False)
        report["ranking_adapter"] = {"script_sha256": sha256(PROJECT / "scripts/rca_ranking.py"),
                                     "synthetic_result": ranking, "active_experiment_integration": False}
        # Human transcription of Table 4, visually checked in the provided PDF,
        # p8. These ranks are published examples, never generated predictions.
        table4 = [
            ("PC", "PC", [5, 13], [0., .25, .14]),
            ("Efficient-CDLMs", "Efficient CDLMs", [10, 10], [0., 0., .10]),
            ("SCD-LLM", "Individual LLM", [5, 13], [0., .25, .14]),
            ("ReAct", "React", [5, 12], [0., .25, .14]),
            ("LLM-KBCI", "LLM-KBCI", [4, 13], [.10, .30, .16]),
            ("LLM-KBCI-RA", "LLM-KBCI(React)", [5, 12], [0., .25, .14]),
            ("LLM-KBCI-RE", "LLM-KBCI-R", [4, 13], [.10, .30, .16]),
            ("MATMCD", "TAMCD", [2, 7], [.30, .55, .32]),
            ("MATMCD-RE", "TamCD-R", [3, 6], [.20, .55, .25]),
        ]
        published = literal_assignment(ast.parse((SOURCE / "LEMMA_Metrics.py").read_text()), "data")
        report["table4_crosscheck"] = []
        for label, source_label, ranks, displayed in table4:
            expect(f"table4_published_ranks:{label}", published[source_label] == ranks)
            metrics = evaluate_ranks(ranks)["metrics"]
            actual = [metrics[k] for k in ("MAP@5", "MAP@10", "MRR")]
            expect(f"table4_metrics_match_display_precision:{label}",
                   all(abs(a - d) < 1e-12 for a, d in zip(actual[:2], displayed[:2])) and round(actual[2], 2) == displayed[2])
            report["table4_crosscheck"].append({"paper_method": label, "code_label": source_label,
                                                "published_ranks_PR_CC": ranks, "metrics": metrics,
                                                "paper_display": displayed})
        report["rank_boundary"] = {"rank1_MAP5": evaluate_ranks([1])["metrics"]["MAP@5"],
                                    "rank5_MAP5": evaluate_ranks([5])["metrics"]["MAP@5"]}
        inputs = read_json(PROJECT / "configs/inputs.json")
        validate_input_scope(inputs)
        helper = literal_assignment(ast.parse((SOURCE / "Log_tools.py").read_text()), "dataset_info")
        report["ground_truth_candidates"] = []
        for case in active_cases():
            key = case_key(case)
            plan_path = within(ASSETS, inputs["rca_log_evidence_manifests"][key])
            plan = read_json(plan_path)
            item = helper[case["system"]]
            prefix = item["Ground_Truth"][item["day"].index(case["day"])]
            matches = [name for name in plan["columns"] if name == prefix or name.startswith(prefix + "-")]
            report["ground_truth_candidates"].append({"case": key, "official_helper_label": prefix,
                "matches": matches, "mapping": "UNIQUE_PREFIX_CANDIDATE" if len(matches) == 1 else "AMBIGUOUS",
                "mapping_is_author_ground_truth_confirmation": False, "plan_sha256": sha256(plan_path)})
        expect("selected_ground_truth_prefix_cardinalities", [len(c["matches"]) for c in report["ground_truth_candidates"]] == [1, 1, 2])
        expect("CC_not_silently_resolved", report["ground_truth_candidates"][-1]["mapping"] == "AMBIGUOUS")
        report["status"] = "PASS"
    except Exception:
        import traceback
        report.update(status="FAILED", error=traceback.format_exc())
    finally:
        np.random.set_state(rng_before)
        report["preservation"] = {"official_source": source_hashes() == before_source,
                                  "python_packages": python_packages() == before_python,
                                  "configs": configs_before == {p.name: sha256(p) for p in (PROJECT / "configs").glob("*.json")}}
        if not all(report["preservation"].values()):
            report["status"] = "FAILED"
        report["source_sha256"] = {n: before_source[n] for n in
                                    ("Utils/CausalDiscovery.py", "Utils/RCA.py", "ConstrainAgent/LLMs.py",
                                     "LEMMA_experiment.py", "LEMMA_Metrics.py", "Log_tools.py")}
        report["script_sha256"] = sha256(Path(__file__))
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "report": str(output)}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
