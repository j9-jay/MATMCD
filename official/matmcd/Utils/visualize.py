import os
import numpy as np
import pydot
from typing import List


def visualize_graph(
    matrix: np.ndarray, labels: List[str], filename: str = "causal_graph.png"
) -> None:
    """Visualize causal graph using pydot and matrix representation.

    Args:
        matrix (np.ndarray): A numpy array representing the causal relationship matrix.
        labels (List[str]): A list of node labels.
        filename (str, optional): Filename for the output image. Defaults to "causal_graph.png".

    Returns:
        None: The function saves the graph as an image file.
    """

    output_dir = os.path.dirname(filename)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    graph = pydot.Dot(graph_type="digraph", rankdir="LR")

    # Add nodes
    for i, label in enumerate(labels):
        graph.add_node(pydot.Node(str(i), label=label))

    # Add edges
    edge_styles = {1: ("", ""), -1: ("none", "dashed"), 2: ("both", "")}
    for i, j in np.ndindex(matrix.shape):
        if matrix[i, j] in edge_styles:
            dir, style = edge_styles[matrix[i, j]]
            graph.add_edge(
                pydot.Edge(
                    str(j if matrix[i, j] == 1 else i),
                    str(i if matrix[i, j] == 1 else j),
                    dir=dir,
                    style=style,
                )
            )

    graph.write_png(filename)
    print(f"Causal graph has been saved as {filename}")
