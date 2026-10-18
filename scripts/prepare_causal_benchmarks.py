"""TASK_070 category 2: prepare causal-discovery benchmark inputs in the layout read by
official Utils/data.py:load_data_from_csv (./data/{name}_data.csv, ./data/{name}_GTmatrix.csv).

- Auto_MPG / DWD_climate / Sachs: byte copies of mas-takayama/LLM-and-SCD (commit pinned in
  COMMIT.txt). Not modified; renamed only.
- asia / child: official data/SampleFromBIF.py logic, with the user-approved seed 42
  (2026-10-18). The original script passes no seed, so the authors' samples cannot be
  reproduced; this is a recorded local condition.

Writes to a new directory and refuses to overwrite.
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pgmpy
from pgmpy.readwrite import BIFReader

ASSETS = Path("/mnt/e/연구/MATMCD_DATA")
TAKAYAMA = ASSETS / "raw_downloads/github_mas_takayama_llm_and_scd"
BIF_DIR = ASSETS / "raw_downloads/github_superkaiba_causal_llm_bfs/data"
OUT = ASSETS / "datasets/causal_benchmarks_task070_v1"
SEED = 42
SAMPLE_NUM = 1000

COPIES = {
    "Auto_MPG": ("Auto MPG data.csv", "GTmatrix_Auto MPG data.csv"),
    "DWD_climate": ("DWD climate data.csv", "GTmatrix_DWD climate data.csv"),
    "Sachs": ("Sachs data.csv", "GTmatrix_Sachs data.csv"),
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sample_from_bif(data_name, data_dir):
    # Same steps as official data/SampleFromBIF.py, plus seed=SEED.
    reader = BIFReader(str(BIF_DIR / f"{data_name}.bif"))
    model = reader.get_model()
    n = len(model.nodes())
    adj_matrix = np.zeros((n, n))
    name_list = list(model.nodes())
    node_to_idx = {node: idx for idx, node in enumerate(model.nodes())}
    for edge in model.edges():
        i = node_to_idx[edge[0]]
        j = node_to_idx[edge[1]]
        adj_matrix[j][i] = 1
    sample = model.simulate(n_samples=SAMPLE_NUM, seed=SEED, show_progress=False)
    sample = sample[name_list]
    mappings = {}
    for col in sample.columns:
        unique_values = sample[col].unique()
        value_map = {val: idx for idx, val in enumerate(sorted(unique_values))}
        mappings[col] = {str(k): v for k, v in value_map.items()}
        sample[col] = sample[col].map(value_map)
    sample.to_csv(data_dir / f"{data_name}_data.csv", index=False)
    np.savetxt(data_dir / f"{data_name}_GTmatrix.csv", adj_matrix, delimiter=",", fmt="%d")
    return {"nodes": name_list, "edges": int(adj_matrix.sum()), "value_maps": mappings}


def main():
    if OUT.exists():
        sys.exit(f"Refusing to overwrite existing {OUT}")
    data_dir = OUT / "data"
    data_dir.mkdir(parents=True)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "authorization": "2026-10-18 user approval: Takayama CSV download with attribution; asia/child seed 42, n=1000, shared by all methods",
        "loader": "official/matmcd/Utils/data.py:load_data_from_csv (reads ./data/{name}_data.csv and {name}_GTmatrix.csv)",
        "gt_convention": "A[effect, cause] = 1 (SampleFromBIF sets adj[j][i] for edge i->j)",
        "pgmpy": pgmpy.__version__,
        "numpy": np.__version__,
        "datasets": {},
    }
    takayama_commit = (TAKAYAMA / "COMMIT.txt").read_text().strip()
    for name, (data_src, gt_src) in COPIES.items():
        src_data = TAKAYAMA / "benchmark datasets" / data_src
        src_gt = TAKAYAMA / "ground truth matrix" / gt_src
        shutil.copyfile(src_data, data_dir / f"{name}_data.csv")
        shutil.copyfile(src_gt, data_dir / f"{name}_GTmatrix.csv")
        manifest["datasets"][name] = {
            "source": f"https://github.com/mas-takayama/LLM-and-SCD (commit {takayama_commit}); license not stated",
            "source_files": [str(src_data), str(src_gt)],
            "byte_identical_copy": sha256(src_data) == sha256(data_dir / f"{name}_data.csv")
            and sha256(src_gt) == sha256(data_dir / f"{name}_GTmatrix.csv"),
        }
    for name in ("asia", "child"):
        info = sample_from_bif(name, data_dir)
        manifest["datasets"][name] = {
            "source": "BIF from superkaiba/causal-llm-bfs commit 80c9f5d1eb49b74335ec178798671b34c3742776 (local raw_downloads)",
            "bif_sha256": sha256(BIF_DIR / f"{name}.bif"),
            "procedure": "official data/SampleFromBIF.py steps with simulate(seed=42); original script has no seed",
            "seed": SEED,
            "n_samples": SAMPLE_NUM,
            **info,
        }
    manifest["outputs_sha256"] = {p.name: sha256(p) for p in sorted(data_dir.iterdir())}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, value in manifest["outputs_sha256"].items():
        print(name, value)


if __name__ == "__main__":
    main()
