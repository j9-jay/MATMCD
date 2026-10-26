"""TASK_070 evidence corpus for RCAEval RE2-OB cases (label-free).

One case -> list of evidence units. Content is shared by every method; the
role/service/time fields are metadata that only the proposed method may use
for filtering. Nothing here reads the case path labels, inject_time,
fault_description or cases metadata; times are relative to the case start.

Units
- metric (observation): per metric column, per-minute means and minutes whose
  mean deviates by |z| >= 3 from the first 5 minutes of the case.
- kpi (observation): the same summary for the KPI column.
- log_template (observation): per (container, masked template), per-minute counts.
- trace_perf (observation): per (service, operation), per-minute span count and
  p90 duration.
- trace_error (observation): per (service, operation) with error spans, per-minute
  error span counts and gRPC status codes.
- call_graph (structure): per caller service, callee services and call counts
  derived from parent/child spans.
"""
import json
import re

import numpy as np
import pandas as pd

import task070_rcaeval as rc
from task070_common import WORK

Z_THRESHOLD = 3.0
BASELINE_SECONDS = 300
TOP_OPERATIONS = 40  # every RE2-OB case has 37 operations, so nothing is cut (audit 2026-10-25)
GRPC_CODES = {1: "CANCELLED", 2: "UNKNOWN", 4: "DEADLINE_EXCEEDED", 13: "INTERNAL", 14: "UNAVAILABLE"}


_MASKS = [
    (re.compile(r"\d{1,2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2}(\.\d+)?"), "<TS>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?Z?"), "<TS>"),
    (re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"), "<UUID>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<EMAIL>"),
    (re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b"), "<IP>"),
    (re.compile(r"\{.*\}"), "{<*>}"),
    (re.compile(r"\[[^\]]*\]"), "[<*>]"),
    (re.compile(r"\"[^\"]*\""), "\"<*>\""),
    (re.compile(r"'[^']*'"), "'<*>'"),
    (re.compile(r"\b(?=[A-Z0-9]*\d)[A-Z0-9]{8,}\b"), "<ID>"),
    (re.compile(r"\d+(\.\d+)?"), "<NUM>"),
]


def log_template(message):
    """Label-free masking template applied identically to every case.

    RCAEval's own log_template column exists in only 24 of 90 RE2-OB cases
    (none in repetitions 2-3), so it is not used.
    """
    text = str(message).strip()
    for pattern, token in _MASKS:
        text = pattern.sub(token, text)
    return re.sub(r"\s+", " ", text)[:200]


def _minute_index(seconds_from_start):
    return (np.asarray(seconds_from_start) // 60).astype(int)


def _fmt_minutes(values, fmt="{:.3g}"):
    return ", ".join(f"m{int(m):02d}={fmt.format(v)}" for m, v in values.items())


def _service_names(trace_name, services):
    if trace_name in services:
        return trace_name
    if trace_name.endswith("service") and trace_name[: -len("service")] in services:
        return trace_name[: -len("service")]  # e.g. frontendservice -> frontend
    return trace_name


def _series_unit(uid, kind, service, column, seconds, values):
    """Deviation is measured against the first BASELINE_SECONDS of the case (a fixed,
    label-free reference window; inject_time is not used). Whole-window z-scores
    would cap a half-window level shift near |z| = 1 and hide it."""
    values = pd.Series(np.asarray(values, dtype=float))
    seconds = np.asarray(seconds)
    base = values[seconds < BASELINE_SECONDS]
    std = base.std(ddof=0)
    if not std > 0:
        std = values.std(ddof=0)
    z = (values - base.mean()) / std if std > 0 else values * 0
    minutes = _minute_index(seconds)
    per_minute_mean = values.groupby(minutes).mean()
    per_minute_z = z.groupby(minutes).mean()
    flagged = [int(m) for m, v in per_minute_z.items() if abs(v) >= Z_THRESHOLD]
    peak = int(np.argmax(np.abs(z.to_numpy()))) if std > 0 else 0
    text = (f"Metric {column} of service {service}. Per-minute mean: {_fmt_minutes(per_minute_mean)}. "
            f"Minutes whose mean deviates by |z| >= {Z_THRESHOLD:g} from the first {BASELINE_SECONDS // 60} minutes: "
            f"{', '.join(f'm{m:02d}' for m in flagged) if flagged else 'none'}. "
            f"Largest deviation z={float(z.iloc[peak]):.2f} at t={int(seconds[peak]) // 60:02d}:{int(seconds[peak]) % 60:02d}.")
    return {"id": uid, "role": "observation", "kind": kind, "services": [service],
            "minutes": flagged, "text": text}


def build_case_corpus(path):
    services_info = rc.node_table(path)[2]
    services = set(services_info["services"])
    metrics = rc.load_metrics(path)
    t0 = int(metrics["time"].iloc[0])
    seconds = (metrics["time"] - t0).to_numpy()
    units = []

    def add(unit):
        unit["id"] = f"u{len(units):04d}"
        units.append(unit)

    for column in metrics.columns:
        if column == "time":
            continue
        kind = "kpi" if column == rc.KPI_COLUMN else "metric"
        if metrics[column].std(ddof=0) == 0:
            continue
        add(_series_unit(None, kind, rc.service_of(column), column, seconds, metrics[column]))

    logs = rc.read_csv(path, "logs.csv")
    logs["sec"] = logs["timestamp"].astype("int64") // 1_000_000_000 - t0
    logs["minute"] = _minute_index(logs["sec"])
    logs["masked_template"] = logs["message"].map(log_template)
    for (container, template), group in logs.groupby(["container_name", "masked_template"], dropna=False):
        counts = group.groupby("minute").size()
        levels = ", ".join(f"{k}={v}" for k, v in group["level"].fillna("none").value_counts().items())
        example = str(group["message"].iloc[0])[:200]
        add({"id": None, "role": "observation", "kind": "log_template", "services": [str(container)],
             "minutes": [int(m) for m in counts.index],
             "text": (f"Log template of {container}: \"{template}\". Total {len(group)} lines ({levels}). "
                      f"Per-minute count: {_fmt_minutes(counts, '{:d}')}. Example: \"{example}\".")})

    traces = rc.read_csv(path, "traces.csv")
    traces["service"] = traces["serviceName"].map(lambda s: _service_names(str(s), services))
    traces["sec"] = traces["startTimeMillis"] // 1000 - t0
    traces["minute"] = _minute_index(traces["sec"])
    # Some cases repeat spanIDs; keep the first occurrence for the parent lookup.
    parent = traces.drop_duplicates("spanID").set_index("spanID")["service"]
    traces["parent_service"] = traces["parentSpanID"].map(parent)
    edges = traces.dropna(subset=["parent_service"])
    edges = edges[edges["parent_service"] != edges["service"]]
    for caller, group in edges.groupby("parent_service"):
        calls = group.groupby(["service", "operationName"]).size().sort_values(ascending=False)
        listing = "; ".join(f"{callee} via {op}: {n} calls" for (callee, op), n in calls.items())
        add({"id": None, "role": "structure", "kind": "call_graph",
             "services": sorted({caller, *group["service"].unique()}), "minutes": [],
             "text": f"Observed calls from {caller} (trace parent/child spans): {listing}."})

    volume = traces.groupby(["service", "operationName"]).size().sort_values(ascending=False)
    for (service, operation), _ in volume.head(TOP_OPERATIONS).items():
        group = traces[(traces["service"] == service) & (traces["operationName"] == operation)]
        per_min = group.groupby("minute")["duration"].agg(["size", lambda d: np.percentile(d, 90) / 1000.0])
        per_min.columns = ["count", "p90_ms"]
        text = (f"Trace operation {operation} of {service}. Per-minute spans: "
                f"{_fmt_minutes(per_min['count'], '{:d}')}. Per-minute p90 duration (ms): "
                f"{_fmt_minutes(per_min['p90_ms'])}.")
        add({"id": None, "role": "observation", "kind": "trace_perf", "services": [service],
             "minutes": [int(m) for m in per_min.index], "text": text})

    # Span error status (gRPC code != 0). RCAEval's own multi-source inputs include trace
    # errors (tracets_err.csv); trace_perf above carries only counts and latency, so error
    # spans get their own unit per (service, operation). Added 2026-10-25 (data audit).
    status = pd.to_numeric(traces["statusCode"], errors="coerce")
    errors = traces[status.notna() & (status != 0)].assign(code=status.astype("Int64"))
    for (service, operation), group in errors.groupby(["service", "operationName"]):
        per_min = group.groupby("minute").size()
        codes = ", ".join(f"{GRPC_CODES.get(int(c), 'code')}({int(c)})={n}" for c, n in group["code"].value_counts().items())
        add({"id": None, "role": "observation", "kind": "trace_error", "services": [service],
             "minutes": [int(m) for m in per_min.index],
             "text": (f"Trace errors of operation {operation} of {service}: {len(group)} error spans "
                      f"(status {codes}). Per-minute error spans: {_fmt_minutes(per_min, '{:d}')}.")})

    # The case directory name (service_fault) equals an ordinary metric column name
    # present in every case (e.g. checkoutservice_cpu), so only the full path is a leak.
    for unit in units:
        if path in unit["text"]:
            raise RuntimeError("Case path leaked into corpus")
    return units


WIKI_CHARS = 1500  # D3: a wiki section longer than this is split at line boundaries (never cut mid-line)


def _wiki_pieces(lines):
    """Split one section's lines into pieces of at most WIKI_CHARS characters at line
    boundaries. The latest sub-heading and, inside a table, the table's header and
    separator rows are repeated at the start of every continuation piece."""
    pieces, current, table_head, subheading = [], [], [], None
    for i, line in enumerate(lines):
        if line.startswith("#"):
            subheading = line
        if line.startswith("|") and i + 1 < len(lines) and re.fullmatch(r"\|(-+\|)+", lines[i + 1].replace(" ", "")):
            table_head = [line, lines[i + 1]]
        elif not line.startswith("|"):
            table_head = [] if line.strip() else table_head
        if current and len("\n".join(current + [line])) > WIKI_CHARS:
            pieces.append(current)
            current = [subheading] if subheading and line != subheading else []
            if line.startswith("|") and line not in table_head:
                current += table_head
        current.append(line)
    if any(l.strip() for l in current):
        pieces.append(current)
    return ["\n".join(p).strip() for p in pieces if "\n".join(p).strip()]


def wiki_units(services):
    """Online Boutique team wiki (v3 corpus, 2026-10-27): one unit per document section
    (long sections split by _wiki_pieces). Identical in every case (`shared`), role
    'document'. The provenance header stays in the documents and in the unit metadata."""
    from task070_ob_wiki_common import OUT, WIKI
    names = sorted(set(services) | {"redis"}, key=len, reverse=True)
    units = []
    for number, (folder, stem, title) in sorted(WIKI.items()):
        path = OUT / folder / f"{stem}.md"
        if not path.exists():
            raise RuntimeError(f"Wiki document missing: {path}")
        sections, name, body = [], None, []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                if name is not None:
                    sections.append((name, body))
                name, body = line[3:].strip(), []
            elif name is not None:
                body.append(line)
        if name is not None:
            sections.append((name, body))
        for section, body in sections:
            for k, piece in enumerate(_wiki_pieces(body)):
                mentioned = [s for s in names if re.search(rf"(?<![\w-]){re.escape(s)}(?![\w-])", piece)]
                units.append({"id": None, "role": "document", "kind": "wiki", "services": sorted(mentioned),
                              "minutes": [], "shared": True, "wiki_doc": number, "wiki_section": section,
                              "wiki_file": f"{folder}/{stem}.md", "wiki_piece": k,
                              "text": f"Wiki {number:02d} {title} / {section}:\n{piece}"})
    return units


def write_case_corpus(case):
    units = build_case_corpus(case["path"])
    services = rc.node_table(case["path"])[2]["services"]
    for unit in wiki_units(services):  # v3: telemetry + team wiki (shared by every case)
        unit["id"] = f"u{len(units):04d}"
        units.append(unit)
    out = WORK / "corpus/re2ob" / f"{case['id']}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(u, ensure_ascii=False) + "\n" for u in units), encoding="utf-8")
    return out, units
