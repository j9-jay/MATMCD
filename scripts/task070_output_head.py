"""TASK_070 shared output head: pairwise Yes/No -> constrained PC -> graph -> RWR.

Uses the unchanged official ``causal_discovery`` (PC, Fisher-Z, causal-learn
BackgroundKnowledge) and ``random_walk_with_restart`` after byte checks against
the pinned archive. Constraint convention follows the official
``matrix2backgroundknowledge``: C[i, j] = 1 requires i -> j, C[i, j] = 0 forbids
i -> j (i = cause). D-9: bidirectional Yes pairs are passed through unchanged.

RWR repetitions (D-11): fixed seeds 0..R-1 set immediately before each call,
recorded with the result. Ties keep input column order (stable sort), as in
the released per-stage sorting.
"""
import contextlib
import io

import numpy as np

from task070_common import import_official

RWR_REPETITIONS = 20


def _official():
    cd = import_official("matmcd_causal_discovery", "Utils/CausalDiscovery.py")
    rca = import_official("matmcd_rca", "Utils/RCA.py")
    return cd, rca


def constraint_matrix(labels, answers):
    """answers: {(cause, effect): True/False} for every ordered pair."""
    n = len(labels)
    index = {name: i for i, name in enumerate(labels)}
    expected = {(a, b) for a in labels for b in labels if a != b}
    if set(answers) != expected:
        missing = sorted(expected - set(answers))[:5]
        raise ValueError(f"Answers must cover every ordered pair; missing e.g. {missing}")
    matrix = np.zeros((n, n), dtype=int)
    for (a, b), yes in answers.items():
        matrix[index[a], index[b]] = 1 if yes else 0
    bidirectional = sum(1 for (a, b), yes in answers.items() if yes and answers[(b, a)] and a < b)
    return matrix, {"yes": int(sum(answers.values())), "no": int(len(answers) - sum(answers.values())),
                    "bidirectional_yes_pairs": bidirectional}


def fit_graph(values, labels, constraints=None):
    """Official PC; constraints=None gives the unconstrained PC baseline."""
    cd, _ = _official()
    # Official code prints the constraint matrix and causal-learn draws progress bars.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        graph = cd.causal_discovery(values, list(labels), method="pc", constraint_matrix=constraints)
    return np.asarray(graph)


def rwr_rankings(graph, labels, repetitions=RWR_REPETITIONS):
    """Run the official RWR from the last node (KPI) with seeds 0..R-1."""
    _, rca = _official()
    runs = []
    for seed in range(repetitions):
        np.random.seed(seed)
        counts = rca.random_walk_with_restart(graph, len(labels) - 1)
        order = sorted(range(len(labels)), key=lambda i: -counts[i])  # stable: ties keep column order
        runs.append({"seed": seed, "counts": counts.tolist(), "ranking": [labels[i] for i in order]})
    mean = np.mean([r["counts"] for r in runs], axis=0)
    order = sorted(range(len(labels)), key=lambda i: -mean[i])
    return {"repetitions": repetitions, "start_node": labels[-1], "runs": runs,
            "mean_counts": mean.tolist(), "ranking_by_mean": [labels[i] for i in order]}
