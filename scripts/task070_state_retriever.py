"""TASK_070 proposed method (category 1): reasoning-state-aware evidence retrieval.

For each pair question (cause -> effect) the retriever
1. recognizes the topic and generates reasoning states dynamically: a planner
   LLM call picks, from a fixed state-type taxonomy (D-4 A), which states are
   needed and in what order, given a compact label-free overview of what the
   corpus contains for the two variables;
2. for every state, retrieves only units whose role/service/kind metadata fit
   that state, ranked by dense similarity to a state-specific query;
3. checks evidence gaps (D-4 B): a state whose pool is empty triggers its
   fallback state (e.g. no direct call relation -> indirect path).
The total evidence budget is K_EVIDENCE, the same as flat RAG. Corpus content
is shared with every method; only metadata filtering is method-specific.

Variants for ablation: "dynamic" (planner), "fixed" (all states in default
order, no planner call), "role_only" (service filter + one query, no states).
"""
import json
import re

import numpy as np

from task070_retrieval import K_EVIDENCE, FlatRetriever

STATES = {
    "STRUCTURE": "how the two variables are connected in the call graph",
    "CAUSE_BEHAVIOR": "abnormal behaviour of the cause variable",
    "EFFECT_BEHAVIOR": "abnormal behaviour of the effect variable",
    "TEMPORAL_ORDER": "whether changes in the cause start no later than changes in the effect",
    "SYMPTOM": "the user-facing symptom (frontend latency KPI)",
    "INDIRECT_PATH": "services that connect the two variables through calls",
}
DEFAULT_ORDER = ["STRUCTURE", "CAUSE_BEHAVIOR", "EFFECT_BEHAVIOR", "TEMPORAL_ORDER", "SYMPTOM"]
FALLBACK = {"STRUCTURE": "INDIRECT_PATH"}
KPI_LABEL = "KPI_frontend_latency_p90"

PLANNER_SYSTEM = "You plan evidence retrieval for causal questions about a microservice incident. Reply with JSON only."
PLANNER_TEMPLATE = """Pair question: can a change in "{cause}" cause a change in "{effect}"?

What the evidence store contains for these variables:
{overview}

Reasoning states you may use:
{states}

Choose the states needed to answer this question, most important first (at most 4). Reply with JSON: {{"states": ["STATE", ...]}}"""


def _service(label):
    return "frontend" if label == KPI_LABEL else label


def overview(units, cause, effect):
    lines = []
    for label in (cause, effect):
        svc = _service(label)
        own = [u for u in units if svc in u["services"] and u["role"] == "observation"]
        flagged = [u for u in own if u["minutes"] and u["kind"] in ("metric", "kpi")]
        lines.append(f"- {label}: {len(own)} observation units, {len(flagged)} metric series with deviations")
    calls = [u for u in units if u["kind"] == "call_graph"
             and _service(cause) in u["services"] and _service(effect) in u["services"]]
    lines.append(f"- call-graph units mentioning both: {len(calls)}")
    return "\n".join(lines)


def parse_plan(text):
    match = re.search(r"\{.*\}", text or "", re.S)
    states = json.loads(match.group(0)).get("states", []) if match else []
    states = [s for s in states if s in STATES]
    return list(dict.fromkeys(states))[:4]


class StateAwareRetriever:
    def __init__(self, encoder, client=None, variant="dynamic"):
        if variant not in ("dynamic", "fixed", "role_only"):
            raise ValueError(variant)
        self.flat = FlatRetriever(encoder)
        self.encoder = encoder
        self.client = client
        self.variant = variant

    def _rank(self, case_id, units, pool, query, k):
        if not pool or k <= 0:
            return []
        matrix = self.flat._case_matrix(case_id, units)
        q = np.asarray(self.encoder.encode([query], kind="query")[0], dtype=np.float32)
        index = {u["id"]: i for i, u in enumerate(units)}
        scored = sorted(pool, key=lambda u: -float(matrix[index[u["id"]]] @ q))
        return scored[:k]

    def _pool(self, state, units, cause, effect):
        c, e = _service(cause), _service(effect)
        obs = [u for u in units if u["role"] == "observation"]
        if state == "STRUCTURE":
            return [u for u in units if u["kind"] == "call_graph" and c in u["services"] and e in u["services"]]
        if state == "INDIRECT_PATH":
            return [u for u in units if u["kind"] == "call_graph" and (c in u["services"] or e in u["services"])]
        if state == "CAUSE_BEHAVIOR":
            return [u for u in obs if c in u["services"] and u["minutes"]] or [u for u in obs if c in u["services"]]
        if state == "EFFECT_BEHAVIOR":
            return [u for u in obs if e in u["services"] and u["minutes"]] or [u for u in obs if e in u["services"]]
        if state == "TEMPORAL_ORDER":
            flagged = [u for u in obs if u["kind"] in ("metric", "kpi") and u["minutes"]
                       and (c in u["services"] or e in u["services"])]
            return sorted(flagged, key=lambda u: min(u["minutes"]))
        if state == "SYMPTOM":
            return [u for u in obs if u["kind"] == "kpi"]
        raise ValueError(state)

    def plan(self, units, cause, effect):
        if self.variant == "fixed":
            return list(DEFAULT_ORDER), None
        states = "\n".join(f"- {k}: {v}" for k, v in STATES.items() if k != "INDIRECT_PATH")
        prompt = PLANNER_TEMPLATE.format(cause=cause, effect=effect, overview=overview(units, cause, effect),
                                         states=states)
        text = self.client.inquire_messages([{"role": "system", "content": PLANNER_SYSTEM},
                                             {"role": "user", "content": prompt}], temperature=0.0)
        chosen = parse_plan(text)
        return (chosen or list(DEFAULT_ORDER)), {"prompt": prompt, "response": text, "parsed": chosen,
                                                 "used_default": not chosen}

    def select(self, case_id, units, cause, effect, k=K_EVIDENCE):
        if self.variant == "role_only":
            c, e = _service(cause), _service(effect)
            pool = [u for u in units if c in u["services"] or e in u["services"]]
            from task070_retrieval import flat_query
            return self._rank(case_id, units, pool, flat_query(cause, effect), k), {"states": []}
        states, plan_record = self.plan(units, cause, effect)
        chosen, trace = [], []
        budget = {s: 0 for s in states}
        for i in range(k):  # round-robin budget over states in priority order
            budget[states[i % len(states)]] += 1
        for state in states:
            pool = [u for u in self._pool(state, units, cause, effect) if u not in chosen]
            used = state
            if not pool and state in FALLBACK:  # evidence gap -> fallback state
                used = FALLBACK[state]
                pool = [u for u in self._pool(used, units, cause, effect) if u not in chosen]
            query = f"{STATES[used]}: {cause} and {effect}"
            picked = pool[: budget[state]] if used == "TEMPORAL_ORDER" else self._rank(
                case_id, units, pool, query, budget[state])
            chosen.extend(picked)
            trace.append({"state": state, "used": used, "pool": len(pool), "picked": [u["id"] for u in picked]})
        if len(chosen) < k:  # unused budget goes to flat retrieval to keep K equal
            extra, _ = self.flat.select(case_id, units, cause, effect, k + len(chosen))
            chosen.extend([u for u in extra if u not in chosen][: k - len(chosen)])
        return chosen[:k], {"states": states, "trace": trace, "plan": plan_record}
