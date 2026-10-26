"""Validation record for the wiki (not a corpus document): compare the service edges in
wiki 03 "(b) Client edges" (from source code) with caller -> callee pairs observed in
RE2-OB traces (parent/child spans, all 90 cases; no labels are read). Differences are
recorded, not resolved.

Usage: python -B task070_ob_wiki_crosscheck.py
"""
import json
import re

import task070_rcaeval as rc
from task070_corpus import _service_names
from task070_ob_wiki_common import OUT

DOC = OUT / "01_Architecture/03_Service_Dependency_Topology.md"


def code_edges():
    text = DOC.read_text(encoding="utf-8").split("### Client edges", 1)[1].split("###", 1)[0]
    rows = [l for l in text.splitlines() if l.startswith("| ") and not l.startswith("| Caller")]
    return sorted({tuple(c.strip() for c in r.strip("|").split("|")[:2]) for r in rows})


def observed_edges():
    seen = {}
    for case in rc.cases():
        services = set(rc.node_table(case["path"])[2]["services"])
        tr = rc.read_csv(case["path"], "traces.csv", usecols=["spanID", "parentSpanID", "serviceName"])
        tr["service"] = tr["serviceName"].map(lambda s: _service_names(str(s), services))
        parent = tr.drop_duplicates("spanID").set_index("spanID")["service"]
        tr["parent"] = tr["parentSpanID"].map(parent)
        pairs = tr.dropna(subset=["parent"])
        for a, b in set(zip(pairs["parent"], pairs["service"])):
            if a != b:
                seen[(a, b)] = seen.get((a, b), 0) + 1
    return seen


def main():
    code = set(code_edges())
    obs = observed_edges()
    report = {"code_edges": sorted(map(list, code)),
              "observed_edges_case_counts": {f"{a}->{b}": n for (a, b), n in sorted(obs.items())},
              "in_code_not_observed": sorted(f"{a}->{b}" for a, b in code - set(obs)),
              "observed_not_in_code": sorted(f"{a}->{b}" for a, b in set(obs) - code),
              "cases": len(rc.cases())}
    (OUT / "topology_crosscheck.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "observed_edges_case_counts"}, indent=1))
    print(report["observed_edges_case_counts"])


if __name__ == "__main__":
    main()
