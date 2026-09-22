def PRK(K, A, rank_list):
    true_number = 0
    for rank in rank_list:
        if rank < K:
            true_number += 1
    return true_number / A


def MAPK(K, A, rank_list):
    result = 0
    for k in range(1, K + 1):
        result += PRK(k, A, rank_list)
    return result / K


def MRR(rank_list):
    result = 0
    for rank in rank_list:
        result += 1 / rank
    return result / len(rank_list)


data = {
    "PC": [5, 13],
    "Exact Search": [6, 3],
    "DirectLiNGAM": [5, 2],
    "Efficient CDLMs": [10, 10],
    "Individual LLM": [5, 13],
    "React": [5, 12],
    "LLM-KBCI": [4, 13],
    "LLM-KBCI(React)": [5, 12],
    "LLM-KBCI-R": [4, 13],
    "TAMCD": [2, 7],
    "TamCD-R": [3, 6],
}

import pandas as pd

metrics = {}
for method, ranks in data.items():
    metrics[method] = {
        "PR@3": PRK(3, len(ranks), ranks),
        "PR@5": PRK(5, len(ranks), ranks),
        "PR@10": PRK(10, len(ranks), ranks),
        "MAP@3": MAPK(3, len(ranks), ranks),
        "MAP@5": MAPK(5, len(ranks), ranks),
        "MAP@10": MAPK(10, len(ranks), ranks),
        "MRR": MRR(ranks),
    }

df = pd.DataFrame.from_dict(metrics, orient="index")
df.to_csv("metrics_results.csv")
print(df)
