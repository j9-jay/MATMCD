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
  VERIFY on the three services with the largest deviation strength (flagged
  metric-minutes; STATE_DEV_V2, was: earliest first deviation).
- state_dynamic: an LLM planner reads a label-free overview (deviation strength and
  onset per service, call edges) and chooses which candidates to verify and the state order.
"""
import json
import random
import re

import numpy as np

from task070_state_retriever import KPI_LABEL, _calls, _first_deviation

PROMPT_VERSION = "task070_direct_v3"
# v2 (dev): 14 of 50 case-method runs still hit 4096 tokens at temperature 0; v3 adds
# presence_penalty 1.5, the setting approved for long LEMMA explanations (TASK_052).
# v1 (dev): max_tokens 1536 was exhausted on the first flat case (finish_reason=length);
# v2 raises the budget and caps the justification length.
K_DIRECT = 24
ORDER_REPEATS = 3
SAMPLING = {"temperature": 0.0, "seed": 42, "max_tokens": 4096, "presence_penalty": 1.5}
STATE_BUDGET = {"SYMPTOM": 4, "STRUCTURE": 4, "CANDIDATES": 8, "VERIFY": 8}
FLAT_QUERY = ("Which service caused the incident that increased frontend latency? Errors, failures, "
              "abnormal resource usage, slow or failing calls.")

SYSTEM = "You are an expert site reliability engineer. Base your answer on the evidence. Be concise."
TEMPLATE = """Context: {context}

Candidate root-cause services: {candidates}

Evidence:
{evidence}

Task: Rank ALL candidate services from most to least likely root cause of the incident. Justify the top three in at most five short sentences in total, citing evidence ids such as [E1]. On the last line write the full ranking exactly as:
RANKING: service > service > ... (every candidate exactly once)"""

PLANNER_SYSTEM = "You plan evidence retrieval for diagnosing a microservice incident. Reply with JSON only."
# STATE_DEV_V2 iteration 1 (30 dev cases, 2026-10-25): the v1 planner chose exactly frontend,
# checkoutservice and currencyservice for VERIFY in 25 of 30 cases regardless of the case (root in VERIFY
# 13/30), and the earliest-onset rule (state_fixed) put the root-cause service in VERIFY in only 10 of the
# 26 completed cases: one noisy early
# deviation (minutes 5-9) outranks a sustained one. v2 orders services by a label-free deviation
# strength (flagged metric-minutes summed over the service's metric units, see deviation_strength)
# and shows it to the planner; CANDIDATES/VERIFY of state_fixed use the same order.
# STATE_DEV_V2 iteration 2 (REJECTED, reverted): excluding the symptom service frontend from VERIFY
# lowered state_dynamic from 0.925 to 0.883 on the 30 dev cases.
# STATE_DEV_V2 iteration 3 (REJECTED, reverted): state pools excluding units an earlier state chose,
# and unused budget filled round-robin with further VERIFY units before the flat query. state_fixed rose
# 0.892 -> 0.962 but state_dynamic fell 0.925 -> 0.898 (emailservice -0.133).
# STATE_DEV_V2 iteration 4 (REJECTED, reverted): iteration 3 + the strongest-deviation service always in
# VERIFY, planner choosing up to two more. state_dynamic 0.920 (< 0.925); state_fixed 0.962.
# Final STATE_DEV_V2 design = iteration 1.
PLANNER_TEMPLATE = """Incident: frontend latency increased.

Label-free overview of the evidence store (services ordered by deviation strength = number of flagged metric-minutes summed over the service's metrics):
{overview}

Reasoning states: SYMPTOM (user-facing latency), STRUCTURE (call relations), CANDIDATES (services with strong, sustained deviations), VERIFY (detailed metrics/logs/traces of chosen services).

Choose up to three services to VERIFY and the order of states. Reply with JSON:
{{"verify": ["service", ...], "states": ["SYMPTOM", "STRUCTURE", "CANDIDATES", "VERIFY"]}}"""


def deviation_strength(units, service):
    """Label-free: flagged metric-minutes and flagged metric count of one service (v2)."""
    flagged = [u for u in units if service in u["services"] and u["kind"] == "metric" and u["minutes"]]
    return sum(len(u["minutes"]) for u in flagged), len(flagged)


def strength_order(services, strength, onsets):
    return sorted(services, key=lambda x: (-strength[x][0], onsets[x] is None, onsets[x] or 0, x))


def case_overview(units, services):
    lines = []
    onsets = {s: _first_deviation(units, s) for s in services}
    strength = {s: deviation_strength(units, s) for s in services}
    for s in strength_order(services, strength, onsets):
        lines.append(f"- {s}: {strength[s][0]} flagged metric-minutes over {strength[s][1]} metrics, "
                     f"first deviation at minute {onsets[s]}" if onsets[s] is not None
                     else f"- {s}: no metric deviation flagged")
    kpi = _first_deviation(units, KPI_LABEL)
    lines.append(f"- frontend latency KPI: first deviation at minute {kpi}" if kpi is not None
                 else "- frontend latency KPI: no deviation flagged")
    edges = [f"{a}->{b}" for a in services for b in services if a != b and _calls(units, a, b)]
    lines.append("- calls: " + (", ".join(edges) if edges else "none observed"))
    return "\n".join(lines), onsets, strength


_MARKUP = re.compile(r"[*_`#]")


def parse_ranking(text, candidates):
    """Last line starting with 'RANKING:'. 2026-10-27 (shared, all methods, decided before
    development): markdown around the label is ignored ('**RANKING:** a > b', '### Ranking:'),
    and a label alone on its line takes the next non-empty line as the ranking."""
    lines = [_MARKUP.sub("", l).strip() for l in (text or "").splitlines()]
    hits = [i for i, l in enumerate(lines) if l.upper().startswith("RANKING:")]
    if not hits:
        raise ValueError("No RANKING line")
    i = hits[-1]
    body = lines[i].split(":", 1)[1].strip()
    if not body:
        body = next((l for l in lines[i + 1:] if l), "")
    names, seen = [], set()
    for token in re.split(r">|,", body):
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
        overview, onsets, strength = case_overview(units, services)
        order = strength_order(services, strength, onsets)  # v2: was earliest-onset order
        strong = [s for s in order if strength[s][0] > 0][:3]
        states, verify = ["SYMPTOM", "STRUCTURE", "CANDIDATES", "VERIFY"], strong
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
                for s in order:  # v2: strongest service first, its most-flagged metric (was earliest)
                    first = sorted([u for u in observation if s in u["services"] and u["kind"] == "metric" and u["minutes"]],
                                   key=lambda u: (-len(u["minutes"]), min(u["minutes"]), u["id"]))
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
