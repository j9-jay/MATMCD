"""RCAEval RE2-OB access for TASK_070 (category 1). Reads directly from the zip.

Case paths contain the ground truth (``{service}_{fault}/{rep}``). Everything a
method sees is keyed by an opaque case id; the path-to-label mapping is only
exposed through ``evaluation_label`` for the evaluation step.

Preprocessing follows RCAEval main.py where it is label-free (drop *_latency-50,
inf -> NaN, forward fill, fill 0). Its label-dependent parts (SLI = root-cause
service latency, inject_time windows) are not used (D-2, D-3).
"""
import hashlib
import io
import zipfile

import numpy as np
import pandas as pd

from task070_common import RCAEVAL_OB_ZIP

SUITE = "RE2-OB"
KPI_COLUMN = "frontend_latency-90"  # D-2
NON_CASE_PARTS = {"multi-source-data"}


def _zip():
    return zipfile.ZipFile(RCAEVAL_OB_ZIP)


def case_paths():
    with _zip() as zf:
        paths = sorted({n.rsplit("/", 1)[0] for n in zf.namelist() if n.endswith("/simple_metrics.csv")})
    return [p for p in paths if not NON_CASE_PARTS & set(p.split("/"))]


def case_id(path):
    """Opaque, stable id that does not reveal service or fault."""
    return "ob-" + hashlib.sha256(path.encode("utf-8")).hexdigest()[:10]


def split(path):
    """D-6: repetition 1 is development, repetitions 2-3 are test."""
    rep = path.rsplit("/", 1)[1]
    return {"1": "dev", "2": "test", "3": "test"}[rep]


def cases(which=None):
    out = [{"path": p, "id": case_id(p), "split": split(p)} for p in case_paths()]
    return [c for c in out if which is None or c["split"] == which]


def evaluation_label(path):
    """Ground truth: root-cause service. Call only from evaluation code."""
    service_fault = path.split("/")[1]
    service, fault = service_fault.rsplit("_", 1)
    return {"root_cause_service": service, "fault": fault}


def read_csv(path, name, **kwargs):
    with _zip() as zf, zf.open(f"{path}/{name}") as fh:
        return pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8"), **kwargs)


def load_metrics(path):
    data = read_csv(path, "simple_metrics.csv")
    if "time.1" in data:
        data = data.drop(columns=["time.1"])
    data = data.loc[:, ~data.columns.str.endswith("_latency-50")]
    data = data.replace([np.inf, -np.inf], np.nan).ffill().fillna(0)
    return data


def service_of(column):
    return column.split("_", 1)[0]


def node_table(path):
    """D-1: one node per service = equal-weight mean of z-scored non-constant
    metric columns (ddof=0, whole case window). KPI column kept raw and last.

    Returns (values[n_rows, n_nodes], labels, info). Services with no
    non-constant metric are dropped and listed in info.
    """
    data = load_metrics(path)
    if KPI_COLUMN not in data:
        raise RuntimeError(f"KPI column missing in {case_id(path)}")
    metric_cols = [c for c in data.columns if c not in ("time", KPI_COLUMN)]
    services = list(dict.fromkeys(service_of(c) for c in metric_cols))
    columns, labels, used, dropped = [], [], {}, []
    for service in services:
        cols = [c for c in metric_cols if service_of(c) == service]
        frame = data[cols].astype(float)
        std = frame.std(ddof=0)
        keep = [c for c in cols if std[c] > 0]
        if not keep:
            dropped.append(service)
            continue
        z = (frame[keep] - frame[keep].mean()) / std[keep]
        columns.append(z.mean(axis=1).to_numpy())
        labels.append(service)
        used[service] = keep
    kpi = data[KPI_COLUMN].astype(float).to_numpy()
    if np.std(kpi) == 0:
        raise RuntimeError(f"Constant KPI in {case_id(path)}")
    values = np.column_stack(columns + [kpi])
    labels.append("KPI_frontend_latency_p90")
    info = {"rows": int(values.shape[0]), "services": labels[:-1], "dropped_constant_services": dropped,
            "metric_columns_used": used, "kpi_column": KPI_COLUMN, "time_start": int(data["time"].iloc[0])}
    return values, labels, info
