"""TASK_070 category 2: causal discovery benchmarks with the shared output head.

Same judgment prompt (task070_judge) and output head (official PC with
constraints) as category 1; evaluation with the official graph metrics.
Evidence comes from the fixed web snapshot corpus (task070_web_snapshot).
Category 2 has no dev/test split, so it is run once after the method is frozen
(G2); do not tune on these results.

State taxonomy for variable pairs (D-4): DEFINITION_CAUSE, DEFINITION_EFFECT,
MECHANISM (relation passages naming both), DIRECTION (relation passages naming
both with causal wording), CONFOUNDER (relation passages naming one of them and
another dataset variable). MECHANISM falls back to passages naming either.
"""
import json
import os
import re

import numpy as np

from task070_common import CAUSAL_DATA_DIR, WORK, import_official
from task070_retrieval import K_EVIDENCE
from task070_state_retriever import parse_plan

THEMES = {"Auto_MPG": "Gasoline consumption", "DWD_climate": "Climate change", "Sachs": "Biology",
          "asia": "Lung Cancer", "child": "Infant Health Status"}
CD_STATES = {
    "DEFINITION_CAUSE": "what the cause variable measures",
    "DEFINITION_EFFECT": "what the effect variable measures",
    "MECHANISM": "a known mechanism linking the two variables",
    "DIRECTION": "which of the two variables drives the other",
    "CONFOUNDER": "other variables that may explain both",
}
CD_DEFAULT = ["MECHANISM", "DIRECTION", "DEFINITION_CAUSE", "DEFINITION_EFFECT", "CONFOUNDER"]
CD_FALLBACK = {"MECHANISM": "EITHER"}
CAUSAL_WORDS = re.compile(r"\b(caus|lead|result|increas|decreas|affect|influenc|depend|driv|activat|inhibit|regulat)", re.I)


def load(name):
    data_mod = import_official("matmcd_data", "Utils/data.py")
    cwd = os.getcwd()
    os.chdir(CAUSAL_DATA_DIR)
    try:
        return data_mod.load_data_from_csv(name)
    finally:
        os.chdir(cwd)


def corpus(name):
    path = WORK / "corpus/causal" / f"{name}.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]


def context(name, labels):
    return (f"Dataset {name} about {THEMES[name]}. Each variable is an observed quantity: "
            f"{', '.join(labels)}. Decide relations between these quantities in the real world.")


class CausalStateRetriever:
    """Category-2 profile of the state-aware retriever (same K, same embeddings)."""

    def __init__(self, flat, client=None, variant="dynamic"):
        self.flat, self.client, self.variant = flat, client, variant

    def _pool(self, state, units, a, b, labels):
        rel = [u for u in units if u["role"] == "relation"]
        if state == "DEFINITION_CAUSE":
            return [u for u in units if u["role"] == "definition" and a in u["services"]]
        if state == "DEFINITION_EFFECT":
            return [u for u in units if u["role"] == "definition" and b in u["services"]]
        if state == "MECHANISM":
            return [u for u in rel if a in u["services"] and b in u["services"]]
        if state == "DIRECTION":
            return [u for u in rel if a in u["services"] and b in u["services"] and CAUSAL_WORDS.search(u["text"])]
        if state == "CONFOUNDER":
            return [u for u in rel if (a in u["services"]) != (b in u["services"])
                    and len(set(u["services"]) - {a, b}) > 0]
        if state == "EITHER":
            return [u for u in rel if a in u["services"] or b in u["services"]]
        raise ValueError(state)

    def plan(self, units, a, b, labels):
        if self.variant == "fixed":
            return list(CD_DEFAULT), None
        counts = {s: len(self._pool(s, units, a, b, labels)) for s in CD_STATES}
        overview = "\n".join(f"- {s}: {n} passages available" for s, n in counts.items())
        states = "\n".join(f"- {k}: {v}" for k, v in CD_STATES.items())
        prompt = (f'Pair question: can a change in "{a}" cause a change in "{b}"?\n\nEvidence store:\n{overview}\n\n'
                  f"Reasoning states you may use:\n{states}\n\nChoose the states needed, most important first "
                  f'(at most 4). Reply with JSON: {{"states": ["STATE", ...]}}')
        text = self.client.inquire_messages(
            [{"role": "system", "content": "You plan evidence retrieval for causal questions. Reply with JSON only."},
             {"role": "user", "content": prompt}], temperature=0.0)
        chosen = [s for s in parse_plan_cd(text) if s in CD_STATES]
        return (chosen or list(CD_DEFAULT)), {"response": text, "parsed": chosen, "used_default": not chosen}

    def select(self, key, units, a, b, labels, k=K_EVIDENCE):
        if self.variant == "role_only":
            pool = [u for u in units if a in u["services"] or b in u["services"]]
            from task070_retrieval import flat_query
            return self.flat_rank(key, units, pool, flat_query(a, b), k), {"states": []}
        states, record = self.plan(units, a, b, labels)
        budget = {s: 0 for s in states}
        for i in range(k):
            budget[states[i % len(states)]] += 1
        chosen, trace = [], []
        for state in states:
            used = state
            pool = [u for u in self._pool(state, units, a, b, labels) if u not in chosen]
            if not pool and state in CD_FALLBACK:
                used = CD_FALLBACK[state]
                pool = [u for u in self._pool(used, units, a, b, labels) if u not in chosen]
            picked = self.flat_rank(key, units, pool, f"{CD_STATES.get(state, state)}: {a} and {b}", budget[state])
            chosen.extend(picked)
            trace.append({"state": state, "used": used, "pool": len(pool), "picked": [u["id"] for u in picked]})
        if len(chosen) < k:
            extra, _ = self.flat.select(key, units, a, b, k + len(chosen))
            chosen.extend([u for u in extra if u not in chosen][: k - len(chosen)])
        return chosen[:k], {"states": states, "trace": trace, "plan": record}

    def flat_rank(self, key, units, pool, query, k):
        if not pool or k <= 0:
            return []
        matrix = self.flat._case_matrix(key, units)
        q = np.asarray(self.flat.encoder.encode([query], kind="query")[0], dtype=np.float32)
        index = {u["id"]: i for i, u in enumerate(units)}
        return sorted(pool, key=lambda u: -float(matrix[index[u["id"]]] @ q))[:k]


def parse_plan_cd(text):
    match = re.search(r"\{.*\}", text or "", re.S)
    try:
        states = json.loads(match.group(0)).get("states", []) if match else []
    except json.JSONDecodeError:
        states = []
    return list(dict.fromkeys(s for s in states if isinstance(s, str)))[:4]
