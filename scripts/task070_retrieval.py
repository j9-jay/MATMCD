"""TASK_070 evidence selection for the shared judgment prompt.

- none: no evidence (no-retrieval LLM baseline).
- flat: dense similarity (approved BGE-M3, CPU FP32, batch 1) between one pair
  query and every unit text of the case; top-K units. Uses text only.
The proposed state-aware retriever is added in P4 and must use the same K.
"""
import json

import numpy as np

from task070_common import WORK

K_EVIDENCE = 6


def flat_query(cause, effect):
    return (f"Evidence on whether {cause} directly affects {effect}: anomalies, errors, latency changes "
            f"or call relations involving {cause} and {effect}.")


class FlatRetriever:
    def __init__(self, encoder):
        self.encoder = encoder
        self.cache = {}

    def _case_matrix(self, case_id, units):
        if case_id not in self.cache:
            path = WORK / "embeddings/re2ob" / f"{case_id}.npy"
            ids_path = path.with_suffix(".ids.json")
            ids = [u["id"] for u in units]
            if path.exists() and json.loads(ids_path.read_text()) == ids:
                matrix = np.load(path)
            else:
                matrix = np.asarray(self.encoder.encode([u["text"] for u in units], kind="document"), dtype=np.float32)
                path.parent.mkdir(parents=True, exist_ok=True)
                np.save(path, matrix)
                ids_path.write_text(json.dumps(ids))
            self.cache[case_id] = matrix
        return self.cache[case_id]

    def select(self, case_id, units, cause, effect, k=K_EVIDENCE):
        matrix = self._case_matrix(case_id, units)
        query = np.asarray(self.encoder.encode([flat_query(cause, effect)], kind="query")[0], dtype=np.float32)
        scores = matrix @ query
        order = np.argsort(-scores, kind="stable")[:k]
        return [units[i] for i in order], [float(scores[i]) for i in order]
