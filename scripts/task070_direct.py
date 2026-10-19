"""TASK_070 primary output head B: case-level evidence retrieval and direct ranking.

For each case and method, evidence units (shared corpus, same budget K_DIRECT for
every method) are selected, then the LLM ranks ALL candidate services with
citations. Position bias control: the judgment is repeated with ORDER_REPEATS
fixed candidate orders (seeds 0..R-1) and positions are averaged; ties are
scored as expected values (task070_metrics tie-aware).

Methods (identical judge prompt; only evidence selection differs)
- none: no evidence.
- flat: dense top-K for one case-level query.
- role_only: same role budget as the state methods (structure / observation) but
  observation units picked by the flat query, no states.
- state_fixed: reasoning states SYMPTOM -> STRUCTURE -> CANDIDATES -> VERIFY with
  VERIFY on the services whose first deviation is earliest.
- state_dynamic: an LLM planner reads a label-free overview (deviation onsets per
  service, call edges) and chooses which candidates to verify and the state order.
"""
import json
import random
import re

import numpy as np

from task070_state_retriever import KPI_LABEL, _calls, _first_deviation

PROMPT_VERSION = "task070_direct_v1"
K_DIRECT = 24
ORDER_REPEATS = 3
SAMPLING = {"temperature": 0.0, "seed": 42, "max_tokens": 1536}
STATE_BUDGET = {"SYMPTOM": 4, "STRUCTURE": 4, "CANDIDATES": 8, "VERIFY": 8}
FLAT_QUERY = ("Which service caused the incident that increased frontend latency? Errors, failures, "
              "abnormal resource usage, slow or failing calls.")

SYSTEM = "You are an expert site reliability engineer. Base your answer on the evidence. Be concise."
TEMPLATE = """Context: {context}

Candidate root-cause services: {candidates}

Evidence:
{evidence}

Task: Rank ALL candidate services from most to least likely root cause of the incident. Briefly justify the top three, citing evidence ids such as [E1]. On the last line write the full ranking exactly as:
RANKING: service > service > ... (every candidate exactly once)"""

PLANNER_SYSTEM = "You plan evidence retrieval for diagnosing a microservice incident. Reply with JSON only."
PLANNER_TEMPLATE = """Incident: frontend latency increased.

Label-free overview of the evidence store:
{overview}

Reasoning states: SYMPTOM (user-facing latency), STRUCTURE (call relations), CANDIDATES (services with early deviations), VERIFY (detailed logs/traces of chosen services).

Choose up to three services to VERIFY and the order of states. Reply with JSON:
{{"verify": ["service", ...], "states": ["SYMPTOM", "STRUCTURE", "CANDIDATES", "VERIFY"]}}"""


def case_overview(units, services):
    lines = []
    onsets = {s: _first_deviation(units, s) for s in services}
    for s in sorted(services, key=lambda x: (onsets[x] is None, onsets[x] if onsets[x] is not None else 0, x)):
        lines.append(f"- {s}: first metric deviation at minute {onsets[s]}" if onsets[s] is not None
                     else f"- {s}: no metric deviation flagged")
    kpi = _first_deviation(units, KPI_LABEL)
    lines.append(f"- frontend latency KPI: first deviation at minute {kpi}" if kpi is not None
                 else "- frontend latency KPI: no deviation flagged")
    edges = [f"{a}->{b}" for a in services for b in services if a != b and _calls(units, a, b)]
    lines.append("- calls: " + (", ".join(edges) if edges else "none observed"))
    return "\n".join(lines), onsets


def parse_ranking(text, candidates):
    line = [l for l in (text or "").splitlines() if l.strip().upper().startswith("RANKING:")]
    if not line:
        raise ValueError("No RANKING line")
    names, seen = [], set()
    for token in re.split(r">|,", line[-1].split(":", 1)[1]):
        name = token.strip().strip("*`'\". ")
        if name in candidates and name not in seen:
            names.append(name)
            seen.add(name)
    if not names:
        raise ValueError("RANKING line names no candidate")
    return names, [c for c in candidates if c not in seen]


class DirectSelector:
    def __init__(self, flat, client=None):
        self.flat, self.client = flat, client

    def _rank(self, key, units, pool, query, k):
        if not pool or k <= 0:
            return []
        matrix = self.flat._case_matrix(key, units)
        q = np.asarray(self.flat.encoder.encode([query], kind="query")[0], dtype=np.float32)
        index = {u["id"]: i for i, u in enumerate(units)}
        return sorted(pool, key=lambda u: -float(matrix[index[u["id"]]] @ q))[:k]

    def select(self, method, key, units, services):
        info = {"method": method}
        if method == "none":
            return [], info
        if method == "flat":
            return self._rank(key, units, units, FLAT_QUERY, K_DIRECT), info
        structure = [u for u in units if u["role"] == "structure"]
        observation = [u for u in units if u["role"] == "observation"]
        if method == "role_only":
            s = self._rank(key, units, structure, FLAT_QUERY, STATE_BUDGET["STRUCTURE"])
            return s + self._rank(key, units, observation, FLAT_QUERY, K_DIRECT - len(s)), info
        overview, onsets = case_overview(units, services)
        early = [s for s in sorted(services, key=lambda x: (onsets[x] is None, onsets[x] or 0, x))
                 if onsets[s] is not None][:3]
        states, verify = ["SYMPTOM", "STRUCTURE", "CANDIDATES", "VERIFY"], early
        if method == "state_dynamic":
            text = self.client.inquire_messages(
                [{"role": "system", "content": PLANNER_SYSTEM},
                 {"role": "user", "content": PLANNER_TEMPLATE.format(overview=overview)}], temperature=0.0)
            info["planner_response"] = text
            try:
                plan = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
                chosen_v = [s for s in plan.get("verify", []) if s in services][:3]
                chosen_s = [s for s in plan.get("states", []) if s in STATE_BUDGET]
                if chosen_v:
                    verify = chosen_v
                if chosen_s:
                    states = list(dict.fromkeys(chosen_s))
                info["plan_used_default"] = not (chosen_v and chosen_s)
            except (AttributeError, json.JSONDecodeError):
                info["plan_used_default"] = True
        elif method != "state_fixed":
            raise ValueError(method)
        chosen, trace = [], []
        for state in states:
            if state == "SYMPTOM":
                pool = [u for u in observation if "frontend" in u["services"] and (u["kind"] == "kpi" or u["minutes"])]
                picked = self._rank(key, units, pool, "frontend latency increase and failing requests", STATE_BUDGET[state])
            elif state == "STRUCTURE":
                picked = structure[: STATE_BUDGET[state]]
            elif state == "CANDIDATES":
                picked = []
                for s in sorted(services, key=lambda x: (onsets[x] is None, onsets[x] or 0, x)):
                    first = sorted([u for u in observation if s in u["services"] and u["kind"] == "metric" and u["minutes"]],
                                   key=lambda u: min(u["minutes"]))
                    picked += first[:1]
                picked = picked[: STATE_BUDGET[state]]
            elif state == "VERIFY":
                picked = []
                per = max(1, STATE_BUDGET[state] // max(1, len(verify)))
                for s in verify:
                    pool = [u for u in observation if s in u["services"] and u["kind"] in ("log_template", "trace_perf", "metric") and u not in picked]
                    picked += self._rank(key, units, pool, f"errors, failures or abnormal behaviour of {s}", per)
            picked = [u for u in picked if u not in chosen]
            chosen += picked
            trace.append({"state": state, "picked": [u["id"] for u in picked]})
        if len(chosen) < K_DIRECT:  # keep the same evidence budget as flat
            extra = self._rank(key, units, [u for u in units if u not in chosen], FLAT_QUERY, K_DIRECT - len(chosen))
            chosen += extra
        info.update(states=states, verify=verify, trace=trace)
        return chosen[:K_DIRECT], info


def judge(client, context, services, units, case_key):
    """ORDER_REPEATS rankings with different fixed candidate orders; returns mean positions."""
    evidence = "\n".join(f"[E{i}] {u['text']}" for i, u in enumerate(units, 1)) or "(no evidence provided)"
    mapping = {f"E{i}": u["id"] for i, u in enumerate(units, 1)}
    runs, positions = [], {s: [] for s in services}
    for r in range(ORDER_REPEATS):
        order = list(services)
        random.Random(f"{case_key}:{r}").shuffle(order)
        user = TEMPLATE.format(context=context, candidates=", ".join(order), evidence=evidence)
        text = client.inquire_messages([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                                       temperature=SAMPLING["temperature"])
        named, missing = parse_ranking(text, services)
        tail = len(named) + (len(missing) + 1) / 2  # missing names share the bottom positions (expected value)
        for i, s in enumerate(named, 1):
            positions[s].append(i)
        for s in missing:
            positions[s].append(tail)
        cited = sorted({c for c in re.findall(r"\[(E\d+)\]", text)})
        runs.append({"order": order, "response": text, "named": named, "missing": missing,
                     "cited_unit_ids": [mapping[c] for c in cited if c in mapping]})
    mean = {s: float(np.mean(p)) for s, p in positions.items()}
    return mean, runs
