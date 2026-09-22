from typing import Literal

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def load_data_from_csv(
    name: Literal["Auto_MPG", "DWD_climate", "Sachs", "asia", "child"],
) -> tuple[np.ndarray, np.ndarray, tuple[str, ...]]:
    """Load the data from the specified dataset.

    Args:
        name: The name of the dataset. Must be one of 'Auto_MPG', 'DWD_climate', or 'Sachs'.

    Raises:
        ValueError: If the provided dataset name is not in the list of available options.

    Returns:
        tuple: A tuple containing three elements:
            - np.ndarray: The matrix of values from the dataset.
            - np.ndarray: The ground truth causal relationship matrix for the dataset.
            - tuple[str, ...]: The feature labels for the dataset.
    """
    if name not in ["Auto_MPG", "DWD_climate", "Sachs", "asia", "child"]:
        raise ValueError(
            "The name must be one of 'Auto_MPG', 'DWD_climate', 'Sachs', 'asia', 'child'."
        )

    data = pd.read_csv(f"./data/{name}_data.csv")
    scaler = StandardScaler()
    values = scaler.fit_transform(data)
    labels = tuple(data.columns)
    GTmatrix = np.array(pd.read_csv(f"./data/{name}_GTmatrix.csv", header=None).values)
    return values, GTmatrix, labels


def load_Lemma_data(system_name: str, day: str):
    data = pd.read_csv(
        f"./data/LEMMA_RCA/{system_name}/Metrics/{system_name}_{day}.csv", header=0
    )
    log_path = f"./data/LEMMA_RCA/{system_name}/Log/{day}"
    return data, log_path
