"""Record unchanged released RWR/sorting behavior for later RCA integration.

No CLI, graph fitting, seed selection, ground-truth matching or evaluation.
D03 graph/prompt choice and D04 evaluation decisions remain separate gates.
"""
import ast
import hashlib
import inspect
import json
import numpy as np

from project_paths import PROJECT, SOURCE
from rca_log_evidence import sha256
from setup_graphviz import assert_original_source


def encode_rng_state(state):
    return {"generator": state[0], "keys": state[1].tolist(), "position": int(state[2]),
            "has_gauss": int(state[3]), "cached_gaussian": float(state[4])}


def decode_rng_state(value):
    return (value["generator"], np.array(value["keys"], dtype=np.uint32), int(value["position"]),
            int(value["has_gauss"]), float(value["cached_gaussian"]))


def original_ranking_functions():
    assert_original_source()
    rwr_path = SOURCE / "Utils/RCA.py"
    rwr_tree = ast.parse(rwr_path.read_text(encoding="utf-8"))
    definitions = [n for n in rwr_tree.body if isinstance(n, ast.FunctionDef) and n.name == "random_walk_with_restart"]
    if len(definitions) != 1:
        raise RuntimeError("Official RWR function changed")
    namespace = {"np": np}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(rwr_path), "exec"), namespace)
    experiment_path = SOURCE / "LEMMA_experiment.py"
    tree = ast.parse(experiment_path.read_text(encoding="utf-8"))
    assignments = [n for n in tree.body if isinstance(n, ast.Assign) and
                   any(isinstance(t, ast.Name) and t.id == "sorted_pairs" for t in n.targets)]
    if len(assignments) != 4 or len({ast.dump(n, include_attributes=False) for n in assignments}) != 1:
        raise RuntimeError("Official per-stage sorting expressions changed")
    sorter = compile(ast.Module(body=[assignments[0]], type_ignores=[]), str(experiment_path), "exec")
    return namespace["random_walk_with_restart"], sorter


def rank_with_original_rwr(matrix, labels):
    """Use the current global NumPy RNG; record it without inventing a seed.

Caller must select the graph under the approved D03 protocol. The start node is
the last input column, as in all four public entrypoint calls. All labels remain
ranked, including the KPI; ties retain input column order. No real RCA caller is
wired by this module. Supplying a matrix is not evidence that its protocol or
ground truth was approved.
"""
    if not isinstance(matrix, np.ndarray) or matrix.ndim != 2 or matrix.shape != (len(labels), len(labels)):
        raise ValueError("Matrix and complete ordered labels must have matching square dimensions")
    if not labels or len(labels) != len(set(labels)) or any(not isinstance(n, str) for n in labels):
        raise ValueError("Provide nonempty unique ordered node names")
    rwr, sorter = original_ranking_functions()
    before_matrix = matrix.copy()
    before = encode_rng_state(np.random.get_state())
    counts = rwr(matrix, len(labels) - 1)  # No parameter overrides or seed call.
    after = encode_rng_state(np.random.get_state())
    if not np.array_equal(matrix, before_matrix):
        raise RuntimeError("Official RWR modified the input graph")
    namespace = {"count_label_pairs": list(zip(counts, labels))}
    exec(sorter, namespace)
    params = inspect.signature(rwr).parameters
    return {
        "implementation": "unchanged_released_RWR_and_stable_count_sort",
        "author_run_equivalence": "UNCONFIRMED", "ground_truth_applied": False,
        "start_node": {"index": len(labels) - 1, "name": labels[-1]},
        "parameters": {k: params[k].default for k in ("steps", "rp", "max_self")},
        "seed_assigned": False, "rng_before": before, "rng_after": after,
        "graph": {"shape": list(matrix.shape), "dtype": str(matrix.dtype),
                  "sha256_c_order_bytes": hashlib.sha256(matrix.tobytes(order="C")).hexdigest()},
        "labels_in_original_order": list(labels), "counts_in_original_order": counts.tolist(),
        "ranking": [{"rank": i + 1, "node": name, "visits": float(count)}
                    for i, (count, name) in enumerate(namespace["sorted_pairs"])],
        "source_sha256": {p: sha256(SOURCE / p) for p in ("Utils/RCA.py", "LEMMA_experiment.py")},
        "limits": "Graph selection, actual fault labels, repetitions and three-case aggregation are not decided here",
    }


def rank_stage_with_original_rwr(stage, initial_graph, refined_graph, labels):
    """Apply approved D03 A routing; retain the first CC stage's initial graph.

    A stage is a method call, not a choice of ground truth. This helper does not
    generate graphs, alter prompts, select cases or run the full RCA pipeline.
    """
    path = PROJECT / "configs/rca_protocol.json"
    protocol = json.loads(path.read_text(encoding="utf-8"))
    d03 = protocol["d03"]
    if protocol["status"] != "APPROVED" or d03["choice"] != "A" or d03["scientific_corrections_applied"]:
        raise ValueError("This adapter only implements approved released-code profile A")
    role = d03["rwr_graph_by_stage"].get(stage)
    if role not in ("initial", "refined"):
        raise ValueError(f"Unknown stage: {stage}")
    graph = initial_graph if role == "initial" else refined_graph
    if graph is None:
        raise ValueError(f"Missing {role} graph for {stage}; no fallback")
    result = rank_with_original_rwr(graph, labels)
    result.update(protocol_id=protocol["profile_id"], protocol_sha256=sha256(path),
                  stage=stage, graph_role=role, d03_choice="A")
    return result
