"""TASK_070 primary output head B: case-level evidence retrieval and direct ranking.

For each case and method, evidence units (shared corpus, same budget K_DIRECT for
every method) are selected, then the LLM ranks ALL candidate services with
citations. Position bias control: the judgment is repeated with ORDER_REPEATS
fixed candidate orders (seeds 0..R-1) and positions are averaged; ties are
scored as expected values (task070_metrics tie-aware).

Methods (identical judge prompt; only evidence selection differs)
- none: no evidence.
- flat: dense top-K for one case-level query.
- role_only: role buckets without states (structure, wiki documents, observation),
  each bucket ranked by the flat query (v3 adds the document bucket).
- state_fixed (PROPOSED, DEV_V3 5-stage design, 2026-10-27): S1 telemetry (KPI, most-flagged
  metric of the strongest-deviation services, trace errors) -> S2 structure (call graph and
  wiki topology/call-flow sections of the suspects) -> S3 hypotheses (service, mechanism) by a
  fixed label-free rule over the S1 selection -> S4 evidence per hypothesis (the service's
  telemetry and mechanism-specific wiki sections, ranked by a state query naming the
  mechanism) -> S5 the unchanged judge.
- state_dynamic (REFERENCE): the same design, but S3 is a planner LLM call that reads the
  S1+S2 evidence texts; an unparsable reply falls back to the state_fixed rule.
(STATE_DEV_V2 design, replaced by DEV_V3: SYMPTOM -> STRUCTURE -> CANDIDATES -> VERIFY.)
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
ROLE_DOCUMENT_BUDGET = 4  # role_only baseline, v3: same size as its structure bucket
FLAT_QUERY = ("Which service caused the incident that increased frontend latency? Errors, failures, "
              "abnormal resource usage, slow or failing calls.")

SYSTEM = "You are an expert site reliability engineer. Base your answer on the evidence. Be concise."
TEMPLATE = """Context: {context}

Candidate root-cause services: {candidates}

Evidence:
{evidence}

Task: Rank ALL candidate services from most to least likely root cause of the incident. Justify the top three in at most five short sentences in total, citing evidence ids such as [E1]. On the last line write the full ranking exactly as:
RANKING: service > service > ... (every candidate exactly once)"""

# --- DEV_V3 5-stage reasoning-state design (state_fixed / state_dynamic), 2026-10-27 ---
# Per-stage budgets (sum = K_DIRECT); a stage whose pool is short leaves its budget unused and
# the unused budget is filled with the flat query, as for the earlier designs.
S1_BUDGET = {"kpi": 1, "metric": 3, "trace_error": 3}  # 7: symptom + anomalous services
N_SUSPECTS = 3                                         # strongest-deviation services in S1
S2_BUDGET = {"call_graph": 2, "wiki": 3}               # 5: structure of the suspects
S2_WIKI_DOCS = (3, 4, 7, 10)                           # topology, communication, provider/consumer, call flow
N_HYPOTHESES = 3
S4_BUDGET = 12                                         # split evenly over the hypotheses
S4_TELEMETRY_KINDS = ("metric", "log_template", "trace_perf", "trace_error")
S4_ANOMALY_KINDS = ("metric", "trace_error")  # iteration 1: in S4 pools metrics are flagged ones only
# mechanism key -> (phrase used in the state query, wiki docs searched in S4)
MECHANISMS = {
    "cpu": ("CPU saturation", (18, 19)),
    "memory": ("memory exhaustion", (18, 14, 19)),
    "disk": ("disk I/O pressure", (14, 15, 18)),
    "network": ("network or connection failure", (11, 17, 20)),
    "latency": ("slow responses", (11, 24, 19)),
    "load": ("abnormal request load", (18, 11)),
    "errors": ("failing requests and errors", (11, 5, 6, 24)),
}
METRIC_MECHANISM = {"cpu": "cpu", "mem": "memory", "diskio": "disk", "socket": "network",
                    "latency-90": "latency", "workload": "load", "error": "errors"}
S1_QUERY = "frontend latency increase and failing requests"
S2_QUERY = ("Dependencies and call flow of {suspects}: which services call them, which services they call, "
            "upstream and downstream paths from frontend.")
S4_QUERY = ("Hypothesis: {service} caused the incident through {phrase}. Evidence of {phrase} in {service}: "
            "abnormal metrics, error logs, failing or slow calls, related configuration and error handling.")
PLANNER3_SYSTEM = "You form root-cause hypotheses for a microservice incident. Reply with JSON only."
PLANNER3_TEMPLATE = """Incident: frontend latency increased.

Candidate root-cause services: {candidates}

Evidence gathered so far (telemetry: user-facing symptom, anomalous services, trace errors; then system structure: call graph and wiki):
{evidence}

Mechanisms: cpu (CPU saturation), memory (memory exhaustion), disk (disk I/O pressure), network (network or connection failure), latency (slow responses), load (abnormal request load), errors (failing requests and errors).

Form up to three root-cause hypotheses, most likely first. Each names one candidate service and one mechanism from the list. Reply with JSON:
{{"hypotheses": [{{"service": "<candidate>", "mechanism": "<mechanism>"}}]}}"""

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


def _metric_mechanism(unit):
    """Mechanism key of a metric unit from its column suffix (e.g. checkoutservice_cpu -> cpu)."""
    column = re.match(r"Metric (\S+) of service", unit["text"]).group(1)
    return METRIC_MECHANISM.get(column.split("_", 1)[1] if "_" in column else "")


def _error_spans(unit):
    found = re.search(r": (\d+) error spans", unit["text"])
    return int(found.group(1)) if found else 0


def _flagged_metrics(observation, service):
    """The service's metric units with flagged minutes, most-flagged first (label-free)."""
    return sorted([u for u in observation if service in u["services"] and u["kind"] == "metric" and u["minutes"]],
                  key=lambda u: (-len(u["minutes"]), min(u["minutes"]), u["id"]))


def mechanisms_of(selected, service):
    """S3 mechanism keys of a service from the given evidence: its flagged metrics (most-flagged
    first, mapped by column suffix), then 'errors' if a trace_error unit of it is present."""
    keys = [_metric_mechanism(u) for u in _flagged_metrics(selected, service)]
    if any(u["kind"] == "trace_error" and service in u["services"] for u in selected):
        keys.append("errors")
    return list(dict.fromkeys(k for k in keys if k))


def fixed_hypotheses(s1_units, suspects):
    """S3 state_fixed rule (label-free): one hypothesis per S1 suspect in deviation-strength order;
    mechanism from that service's S1 evidence (its most-flagged metric, trace errors)."""
    return [{"service": s, "mechanisms": mechanisms_of(s1_units, s) or ["latency"]} for s in suspects[:N_HYPOTHESES]]


def parse_hypotheses(text, services, s1_units, observation):
    """state_dynamic S3: planner JSON -> hypotheses; None if nothing usable parses. A valid service
    with a missing/unknown mechanism takes the state_fixed mechanism rule (its S1 evidence, else its
    flagged metrics over the whole case)."""
    try:
        plan = json.loads(re.search(r"\{.*\}", text or "", re.S).group(0))
        items = plan.get("hypotheses", []) if isinstance(plan, dict) else []
    except (AttributeError, json.JSONDecodeError):
        return None
    hyps, seen = [], set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or item.get("service") not in services or item["service"] in seen:
            continue
        s = item["service"]
        mech = str(item.get("mechanism", "")).strip().lower()
        mechs = [mech] if mech in MECHANISMS else (mechanisms_of(s1_units, s) or mechanisms_of(observation, s) or ["latency"])
        hyps.append({"service": s, "mechanisms": mechs, "planner_mechanism": item.get("mechanism")})
        seen.add(s)
    return hyps[:N_HYPOTHESES] or None


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
        document = [u for u in units if u["role"] == "document"]
        if method == "role_only":
            # v3 (2026-10-27, fixed before development): role buckets without states: structure
            # units, wiki documents (ROLE_DOCUMENT_BUDGET), observations for the rest, each bucket
            # ranked by the flat query.
            s = self._rank(key, units, structure, FLAT_QUERY, STATE_BUDGET["STRUCTURE"])
            d = self._rank(key, units, document, FLAT_QUERY, ROLE_DOCUMENT_BUDGET)
            return s + d + self._rank(key, units, observation, FLAT_QUERY, K_DIRECT - len(s) - len(d)), info
        if method not in ("state_fixed", "state_dynamic"):
            raise ValueError(method)
        # DEV_V3 5-stage design. Each stage draws only units no earlier stage chose.
        onsets = {s: _first_deviation(units, s) for s in services}
        strength = {s: deviation_strength(units, s) for s in services}
        order = strength_order(services, strength, onsets)
        chosen, trace = [], []

        def take(stage, picked):
            seen, new = {u["id"] for u in chosen}, []
            for u in picked:
                if u["id"] not in seen:
                    seen.add(u["id"])
                    new.append(u)
            chosen.extend(new)
            trace.append({"stage": stage, "picked": [u["id"] for u in new]})
            return new

        def free(pool):
            return [u for u in pool if u not in chosen]

        # S1 telemetry: user-facing symptom (KPI), strongest-deviation services and their most-flagged
        # metric, trace errors (most error spans first).
        suspects = [s for s in order if strength[s][0] > 0][:N_SUSPECTS]
        kpi = [u for u in observation if u["kind"] == "kpi"]
        s1 = self._rank(key, units, kpi, S1_QUERY, S1_BUDGET["kpi"])
        s1 += [m for s in suspects for m in _flagged_metrics(observation, s)[:1]][: S1_BUDGET["metric"]]
        errors = sorted([u for u in observation if u["kind"] == "trace_error"],
                        key=lambda u: (-_error_spans(u), -len(u["minutes"]), u["id"]))
        s1 += errors[: S1_BUDGET["trace_error"]]
        s1 = take("S1_telemetry", s1)
        # S2 structure of the suspects: observed call graph and wiki topology/call-flow sections.
        focus = suspects or list(dict.fromkeys(s for u in s1 if u["kind"] == "trace_error" for s in u["services"]))
        q2 = S2_QUERY.format(suspects=", ".join(focus) if focus else "frontend")
        calls = [u for u in structure if not focus or set(focus) & set(u["services"])]
        wiki2 = [u for u in document if u["wiki_doc"] in S2_WIKI_DOCS and set(focus) & set(u["services"])]
        s2 = self._rank(key, units, free(calls), q2, S2_BUDGET["call_graph"])
        s2 += self._rank(key, units, free(wiki2), q2, S2_BUDGET["wiki"])
        s2 = take("S2_structure", s2)
        # S3 hypotheses (no retrieval), built from what S1/S2 selected.
        fixed = fixed_hypotheses(s1, suspects)
        hypotheses, info["plan_used_default"] = fixed, None
        if method == "state_dynamic":
            evidence = "\n".join(f"[{i}] {u['text']}" for i, u in enumerate(s1 + s2, 1)) or "(no evidence selected)"
            text = self.client.inquire_messages(
                [{"role": "system", "content": PLANNER3_SYSTEM},
                 {"role": "user", "content": PLANNER3_TEMPLATE.format(candidates=", ".join(services), evidence=evidence)}],
                temperature=0.0)
            info["planner_response"] = text
            parsed = parse_hypotheses(text, services, s1, observation)
            info["plan_used_default"] = parsed is None
            hypotheses = parsed if parsed is not None else fixed
        trace.append({"stage": "S3_hypotheses", "hypotheses": hypotheses})
        # S4 evidence per hypothesis: the service's telemetry and mechanism-specific wiki sections,
        # both ranked by a state query naming the service and mechanism.
        if hypotheses:
            # DEV_V3 iteration 2 (REJECTED, reverted): budget left unused by S1/S2 given to S4 instead of
            # the flat fill. state_fixed 0.965 -> 0.955, recommendationservice 1.000 -> 0.875.
            per = S4_BUDGET // len(hypotheses)
            wiki_k = max(1, per // 4)
            for h in hypotheses:
                s = h["service"]
                phrase = " and ".join(MECHANISMS[m][0] for m in h["mechanisms"])
                docs = list(dict.fromkeys(d for m in h["mechanisms"] for d in MECHANISMS[m][1]))
                q4 = S4_QUERY.format(service=s, phrase=phrase)
                tel = [u for u in observation if s in u["services"] and u["kind"] in S4_TELEMETRY_KINDS
                       and (u["kind"] != "metric" or u["minutes"])]  # metrics only when flagged
                wiki4 = [u for u in document if u["wiki_doc"] in docs and s in u["services"]]
                # DEV_V3 iteration 1: anomaly-marked telemetry (flagged metrics, trace errors) first,
                # each group ranked by the state query (start run: one ranking over all kinds picked
                # normal log templates and health-check traces).
                marked = [u for u in free(tel) if u["kind"] in S4_ANOMALY_KINDS]
                picked = self._rank(key, units, marked, q4, per - wiki_k)
                picked += self._rank(key, units, [u for u in free(tel) if u["kind"] not in S4_ANOMALY_KINDS], q4,
                                     per - wiki_k - len(picked))
                picked += self._rank(key, units, [u for u in free(wiki4) if u not in picked], q4, wiki_k)
                take(f"S4_{s}", picked)
        info["stage_units"] = {t["stage"]: len(t.get("picked", [])) for t in trace if "picked" in t}
        if len(chosen) < K_DIRECT:  # keep the same evidence budget as flat
            extra = self._rank(key, units, free(units), FLAT_QUERY, K_DIRECT - len(chosen))
            take("flat_fill", extra)
        info.update(suspects=suspects, hypotheses=hypotheses, trace=trace)
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
