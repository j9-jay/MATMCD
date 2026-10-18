"""TASK_070 evaluation. The only module that combines predictions with labels.

Category 1 (RCAEval): service-level AC@k / Avg@k as in RCAEval's Evaluator
(single answer: AC@k = 1 if the answer is in the top k), reciprocal rank, and
the unchanged public LEMMA MAP@K/MRR on the same service ranks. The KPI node is
not a candidate. Chance level min(k, n)/n is reported.

Category 2 (causal discovery): unchanged official Utils/metrics.py Metrics.
"""
import numpy as np

from rca_metrics import evaluate_ranks
from task070_common import import_official

KS = (1, 2, 3, 4, 5)


def service_rank(ranking, answer, kpi_label):
    candidates = [s for s in ranking if s != kpi_label]
    if answer not in candidates:
        return None, len(candidates)
    return candidates.index(answer) + 1, len(candidates)


def rca_case_metrics(ranking, answer, kpi_label):
    rank, n = service_rank(ranking, answer, kpi_label)
    ac = {f"AC@{k}": int(rank is not None and rank <= k) for k in KS}
    return {"rank": rank, "n_candidates": n, **ac,
            "Avg@5": sum(ac.values()) / len(KS),
            "RR": 0.0 if rank is None else 1.0 / rank,
            "chance_AC@1": min(1, n) / n if n else 0.0,
            "chance_Avg@5": sum(min(k, n) / n for k in KS) / len(KS) if n else 0.0}


def rca_aggregate(case_results):
    keys = [f"AC@{k}" for k in KS] + ["Avg@5", "RR", "chance_AC@1", "chance_Avg@5"]
    out = {k: float(np.mean([c[k] for c in case_results])) for k in keys}
    ranks = [c["rank"] for c in case_results]
    out["cases"] = len(case_results)
    out["answer_in_candidates"] = sum(r is not None for r in ranks)
    if all(r is not None for r in ranks):
        out["public_LEMMA_metrics"] = evaluate_ranks(ranks)["metrics"]
    return out


def graph_metrics(predicted, truth):
    metrics = import_official("matmcd_metrics", "Utils/metrics.py")
    m = metrics.Metrics(np.asarray(predicted), np.asarray(truth))
    values = m.calc_all_metrics()
    return {k: float(v) for k, v in values.items()}
