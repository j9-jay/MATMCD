import numpy as np


class Metrics:
    def __init__(self, adjacency_matrix: np.ndarray, true_matrix: np.ndarray):
        self.adjacency_matrix = adjacency_matrix
        self.true_matrix = true_matrix
        self.adjacency_matrix_0or1 = None

    def create_0or1_causal_matrix(self):
        self.adjacency_matrix_0or1 = (self.adjacency_matrix != 0).astype(int)

        ## Convert any values that are not 0 or 1 to 0
        # self.adjacency_matrix_0or1 = np.where(
        #     (self.adjacency_matrix == 0) | (self.adjacency_matrix == 1),
        #     self.adjacency_matrix,
        #     0,
        # )

    def calc_FPR(self) -> float:
        if self.adjacency_matrix_0or1 is None:
            self.create_0or1_causal_matrix()

        TN = np.sum((self.true_matrix == 0) & (self.adjacency_matrix_0or1 == 0))
        FP = np.sum((self.adjacency_matrix_0or1 == 1) & (self.true_matrix == 0))

        self.FPR = FP / (TN + FP)
        return self.FPR

    def calc_FNR(self) -> float:
        if self.adjacency_matrix_0or1 is None:
            self.create_0or1_causal_matrix()

        TP = np.sum((self.true_matrix == 1) & (self.adjacency_matrix_0or1 == 1))
        FN = np.sum((self.adjacency_matrix_0or1 == 0) & (self.true_matrix == 1))

        self.FNR = FN / (TP + FN)
        return self.FNR

    def calc_precision(self) -> float:
        if self.adjacency_matrix_0or1 is None:
            self.create_0or1_causal_matrix()

        TP = np.sum((self.true_matrix == 1) & (self.adjacency_matrix_0or1 == 1))
        FP = np.sum((self.adjacency_matrix_0or1 == 1) & (self.true_matrix == 0))

        self.precision = TP / (TP + FP)
        return self.precision

    def calc_F1score(self) -> float:
        if self.adjacency_matrix_0or1 is None:
            self.create_0or1_causal_matrix()

        TP = np.sum((self.true_matrix == 1) & (self.adjacency_matrix_0or1 == 1))
        FP = np.sum((self.adjacency_matrix_0or1 == 1) & (self.true_matrix == 0))
        FN = np.sum((self.adjacency_matrix_0or1 == 0) & (self.true_matrix == 1))

        self.F1score = 2 * TP / (2 * TP + FN + FP)
        return self.F1score

    def calc_SHD(self) -> int:
        if self.adjacency_matrix_0or1 is None:
            self.create_0or1_causal_matrix()

        A = np.sum(
            (self.true_matrix == 0)
            & (self.true_matrix.T == 0)
            & (self.adjacency_matrix_0or1 == 1)
        )
        D = np.sum(
            (self.adjacency_matrix_0or1 == 0)
            & (self.adjacency_matrix_0or1.T == 0)
            & (self.true_matrix == 1)
        )
        R = np.sum(
            (self.adjacency_matrix_0or1 == 0)
            & (self.adjacency_matrix_0or1.T == 1)
            & (self.true_matrix == 1)
            & (self.true_matrix.T == 0)
        )

        self.SHD = A + D + R
        return self.SHD

    def calc_NHD(self) -> float:
        if self.SHD is None:
            self.calc_SHD()

        self.NHD = self.SHD / self.true_matrix.size
        return self.NHD

    def calc_all_metrics(self) -> dict:
        self.calc_FPR()
        self.calc_FNR()
        self.calc_precision()
        self.calc_F1score()
        self.calc_SHD()
        self.calc_NHD()

        return {
            "FPR": self.FPR,
            "FNR": self.FNR,
            "Precision": self.precision,
            "F1 Score": self.F1score,
            "SHD": self.SHD,
            "NHD": self.NHD,
        }

    def show_metrics(self) -> None:
        metrics = self.calc_all_metrics()
        for metric, value in metrics.items():
            print(f"{metric}: {value}")
        return metrics
