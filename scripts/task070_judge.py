"""TASK_070 shared single-stage pairwise judgment (D-5) and parser.

Every method (no-retrieval LLM, flat RAG, proposed) uses this exact prompt; only
the evidence list differs. The answer must end with <Yes> or <No>; cited
evidence ids [E#] are recorded for the attribution metrics. A response without
a final <Yes>/<No> is a failure (no retry, no default).

D-10 sampling chosen for this binary judgment: temperature 0, seed 42,
presence_penalty 0, max_tokens 1024.
"""
import re

PROMPT_VERSION = "task070_judge_v2"
# v1 (2026-10-18 pilot, dev cases only) asked for a strictly direct effect not
# mediated by other variables; the model answered No for 152-156 of 156 pairs,
# leaving an empty constraint graph. v2 states the influence mechanisms instead.
SAMPLING = {"temperature": 0.0, "seed": 42, "max_tokens": 1024, "presence_penalty": 0.0}

SYSTEM = ("You are an expert analyst. Decide whether one variable directly causes another, "
          "using the evidence provided and general domain knowledge. Be concise.")

TEMPLATE = """Context: {context}

Variables: {variables}

Question: Can a change in "{cause}" cause a change in "{effect}" in this system? Answer Yes if "{cause}" can influence "{effect}" without first going through "{effect}" itself, for example because "{effect}" depends on "{cause}" (it calls or waits for it, so failures or slowness propagate), because "{cause}" sends requests or load to "{effect}", or because they share a resource. Answer No if they are unrelated or the influence can only go from "{effect}" to "{cause}". Use the evidence when it shows related changes at overlapping times.

Evidence:
{evidence}

Answer in at most three short sentences, citing evidence ids such as [E1] when you use them. Then write exactly <Yes> or <No> on the last line."""

_FINAL = re.compile(r"<\s*(Yes|No)\s*>", re.IGNORECASE)
_CITE = re.compile(r"\[E(\d+)\]")


def format_evidence(units):
    """units: list of dicts with 'text'. Returns (block, id map E# -> unit id)."""
    if not units:
        return "(no evidence provided)", {}
    lines, mapping = [], {}
    for i, unit in enumerate(units, 1):
        lines.append(f"[E{i}] {unit['text']}")
        mapping[f"E{i}"] = unit.get("id")
    return "\n".join(lines), mapping


def build_messages(context, variables, cause, effect, units):
    evidence, mapping = format_evidence(units)
    user = TEMPLATE.format(context=context, variables=", ".join(variables), cause=cause,
                           effect=effect, evidence=evidence)
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], mapping


def parse(response, mapping):
    matches = _FINAL.findall(response or "")
    if not matches:
        raise ValueError("No final <Yes>/<No> in response")
    answer = matches[-1].lower() == "yes"
    cited = sorted({f"E{n}" for n in _CITE.findall(response)})
    return {"yes": answer, "cited": cited, "cited_unit_ids": [mapping[c] for c in cited if c in mapping],
            "invalid_citations": [c for c in cited if c not in mapping]}
