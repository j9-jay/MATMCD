"""TASK_070 shared helpers: paths, decisions, official-source checks, JSON output.

Official functions are executed only after their file bytes match the pinned
archive. Nothing here reads ground truth.
"""
import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

from project_paths import ASSETS, PROJECT, SOURCE

ARCHIVE = ASSETS / "raw_downloads/github_d2i_matmcd/ef2c3ec.zip"
DECISIONS_PATH = PROJECT / "configs/task070_decisions.json"
RCAEVAL_OB_ZIP = ASSETS / "raw_downloads/zenodo_rcaeval_14590730/RE2-OB.zip"
CAUSAL_DATA_DIR = ASSETS / "datasets/causal_benchmarks_task070_v1"
WORK = ASSETS / "task070"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def decisions():
    return json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))


def assert_official_files(relpaths):
    """Each listed official file must be byte-identical to the pinned archive."""
    with zipfile.ZipFile(ARCHIVE) as archive:
        for rel in relpaths:
            if (SOURCE / rel).read_bytes() != archive.read(rel):
                raise RuntimeError(f"Official file differs from pinned archive: {rel}")
    return {rel: sha256_file(SOURCE / rel) for rel in relpaths}


def import_official(module_name, relpath):
    """Import an official module from its file after the byte check."""
    assert_official_files([relpath])
    if str(SOURCE) not in sys.path:
        sys.path.insert(0, str(SOURCE))
    spec = importlib.util.spec_from_file_location(module_name, SOURCE / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=_default) + "\n", encoding="utf-8")


def _default(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Not JSON serializable: {type(value)}")
