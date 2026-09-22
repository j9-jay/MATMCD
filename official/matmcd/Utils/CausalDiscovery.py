from typing import List

import numpy as np
from causallearn.graph.GraphClass import CausalGraph
from causallearn.search.ConstraintBased.PC import pc
from causallearn.utils.PCUtils.BackgroundKnowledge import BackgroundKnowledge
from causallearn.search.FCMBased import lingam
from causallearn.search.ScoreBased.ExactSearch import bic_exact_search


def cg2matrix(cg: CausalGraph) -> np.ndarray:
    """Convert CausalGraph object to adjacency matrix.

    Args:
        cg (CausalGraph): A CausalGraph object.

    Returns:
        np.ndarray: An adjacency matrix representing the causal graph.
    """
    num_nodes = len(cg.G.nodes)
    adj_matrix = np.zeros((num_nodes, num_nodes), dtype=int)

    for i, j in np.ndindex((num_nodes, num_nodes)):
        if cg.G.graph[i][j] == 1 and cg.G.graph[j][i] == -1:
            adj_matrix[i, j] = 1  # i <- j
        elif cg.G.graph[i][j] == -1 and cg.G.graph[j][i] == -1:
            # adj_matrix[i, j] = -1  # i -- j
            adj_matrix[j, i] = -1  # j -- i
        elif cg.G.graph[i][j] == 1 and cg.G.graph[j][i] == 1:
            # adj_matrix[i, j] = 2  # i <-> j
            adj_matrix[j, i] = 2  # j <-> i

    return adj_matrix


def matrix_to_text(matrix: np.ndarray, labels: List[str]) -> str:
    """Convert adjacency matrix to text representation.

    Args:
        matrix (np.ndarray): A numpy array representing the causal relationship matrix.
        labels (List[str]): A list of node labels.

    Returns:
        str: A text description of the graph structure.
    """
    edge_types = {1: " -> ", -1: " -- ", 2: " <-> "}
    return ", ".join(
        f"{labels[j]}{edge_types[matrix[i, j]]}{labels[i]}"
        for i, j in np.ndindex(matrix.shape)
        if matrix[i, j] in edge_types and (matrix[i, j] != -1 or i < j)
    )


def matrix2backgroundknowledge(
    matrix: np.ndarray, labels: List[str]
) -> BackgroundKnowledge:
    bk = BackgroundKnowledge()
    node_num = matrix.shape[0]
    for i in range(node_num):
        for j in range(node_num):
            if i == j:
                continue
            if matrix[i, j] == 0:
                bk.add_forbidden_by_pattern(labels[i], labels[j])
            elif matrix[i, j] == 1:
                bk.add_required_by_pattern(labels[i], labels[j])
    return bk


def causal_discovery(
    data, labels, method="pc", constraint_matrix=None, **kwargs
) -> np.ndarray:
    if method == "pc":
        if constraint_matrix is not None:
            print(f"Using constraint matrix:\n{constraint_matrix}")
            background_knowledge = matrix2backgroundknowledge(constraint_matrix, labels)
            cg = pc(
                data,
                node_names=labels,
                indep_test=kwargs.get("independence_test_method", "fisherz"),
                background_knowledge=background_knowledge,
            )
        else:
            cg = pc(
                data,
                node_names=labels,
                indep_test=kwargs.get("independence_test_method", "fisherz"),
            )
        adjacency_matrix = cg2matrix(cg)
    elif method == "Exact-Search":
        if constraint_matrix is not None:
            # Convert -1 to 0 in constraint matrix
            super_graph = constraint_matrix.copy()
            super_graph[super_graph == -1] = 0
            adjacency_matrix, _ = bic_exact_search(
                data,
                super_graph=super_graph,
                use_k_cycle_heuristic=True,
                k=1,
                max_parents=1,
            )
        else:
            adjacency_matrix, _ = bic_exact_search(
                data, use_k_cycle_heuristic=True, k=1, max_parents=1
            )
    elif method == "DirectLiNGAM":
        if constraint_matrix is not None:
            # Convert bidirectional or no-edge constraints to undirected edges (-1)
            for i in range(len(constraint_matrix)):
                for j in range(i + 1, len(constraint_matrix)):
                    if (
                        constraint_matrix[i, j] == constraint_matrix[j, i]
                        and constraint_matrix[i, j] == 1
                    ):
                        constraint_matrix[i, j] = -1
                        constraint_matrix[j, i] = -1
            model = lingam.DirectLiNGAM(
                prior_knowledge=constraint_matrix,
                apply_prior_knowledge_softly=True,
                measure="kernel",
            )
            model.fit(data)
            adjacency_matrix = (model.adjacency_matrix_ != 0).astype(int)
        else:
            model = lingam.DirectLiNGAM()
            model.fit(data)
            adjacency_matrix = (model.adjacency_matrix_ != 0).astype(int)
    return adjacency_matrix
