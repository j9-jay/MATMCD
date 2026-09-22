"""네트워크/API/실험 실행 없이 원본 파일, 입력, 패키지 준비 상태를 조사한다."""
import ast
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, SOURCE, asset_path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(code, timeout=45):
    # 점검 프로세스에서만 네트워크를 차단한다. 원본 파일은 수정하지 않는다.
    preamble = "import socket\ndef denied(*a,**k): raise RuntimeError('setup audit: network disabled')\nsocket.socket.connect=denied\nsocket.create_connection=denied\n"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(SOURCE)
    env["XDG_CACHE_HOME"] = str(ASSETS / "caches" / "library_cache")
    env["MPLCONFIGDIR"] = str(ASSETS / "caches" / "matplotlib")
    env["TIKTOKEN_CACHE_DIR"] = str(ASSETS / "caches" / "tiktoken")
    try:
        result = subprocess.run([sys.executable, "-B", "-c", preamble + code],
                                cwd=SOURCE, env=env, text=True, capture_output=True, timeout=timeout)
        return {"ok": result.returncode == 0, "exit_code": result.returncode,
                "stdout": result.stdout[-8000:], "stderr": result.stderr[-8000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"{timeout}초 import 점검 시간 초과; 실험 미실행"}


def main():
    evidence = PROJECT / "docs" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    report = {"checked_utc": datetime.now(timezone.utc).isoformat(),
              "platform": platform.platform(), "python": sys.version,
              "python_executable": sys.executable, "experiments_executed": False,
              "api_calls": False}
    archive = ASSETS / "raw_downloads/github_d2i_matmcd/ef2c3ec.zip"
    source_files = []
    with zipfile.ZipFile(archive) as original:
        for entry in original.infolist():
            if not entry.is_dir():
                local = SOURCE / entry.filename
                expected = hashlib.sha256(original.read(entry)).hexdigest()
                source_files.append({"path": entry.filename, "sha256": expected,
                                     "matches": local.is_file() and digest(local) == expected})
    report["official_source"] = {"commit": "ef2c3ecad0f5ddb9c3d20a8523c2c1043d213190",
                                  "all_match": all(x["matches"] for x in source_files),
                                  "files": source_files}
    syntax = []
    for path in sorted(SOURCE.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            syntax.append({"path": str(path.relative_to(SOURCE)), "ok": True})
        except SyntaxError as error:
            syntax.append({"path": str(path.relative_to(SOURCE)), "ok": False, "error": str(error)})
    report["source_syntax"] = syntax
    inputs = json.loads((PROJECT / "configs/inputs.json").read_text(encoding="utf-8"))
    csvs = []
    for name, location in inputs["benchmark_files"].items():
        path = ASSETS / location
        if not path.exists():
            csvs.append({"name": name, "exists": False})
            continue
        rows = list(csv.reader(path.open(encoding="utf-8-sig", newline="")))
        has_header = name.endswith("_data.csv")
        values = rows[1:] if has_header else rows
        csvs.append({"name": name, "source": location, "exists": True, "sha256": digest(path),
                     "rows": len(values), "columns": len(rows[0]),
                     "labels": rows[0] if has_header else None,
                     "numeric": all(all(float(value) == float(value) for value in row) for row in values),
                     "rectangular": all(len(row) == len(rows[0]) for row in values)})
    report["benchmark_csvs"] = csvs
    workspace = asset_path("runtime_workspace")
    report["missing_inputs"] = [name for name in inputs["missing_benchmark_inputs"] + inputs["missing_rca_inputs"]
                                if not (workspace / "data" / name).is_file()]
    requirements = {}
    for line in (SOURCE / "requirements.txt").read_text().splitlines():
        if "==" in line:
            name, version = line.split("==", 1)
            requirements[name] = version
    pinned = []
    for name, expected in requirements.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        pinned.append({"name": name, "expected": expected, "installed": actual, "matches": expected == actual})
    report["pinned_packages"] = pinned
    report["all_pins_match"] = all(x["matches"] for x in pinned)
    normalized = {name.lower().replace("_", "-") for name in requirements}
    report["unlisted_installed_packages"] = sorted(
        [{"name": dist.metadata["Name"], "version": dist.version} for dist in importlib.metadata.distributions()
         if dist.metadata["Name"].lower().replace("_", "-") not in normalized], key=lambda x: x["name"])
    checks = {
        "core_imports": "import numpy,pandas,sklearn,scipy,torch,pgmpy,openai; print('core imports OK')",
        "causal_imports": "from Utils.CausalDiscovery import causal_discovery; from Utils.metrics import Metrics; from Utils.data import load_data_from_csv; print('causal imports OK; no fit executed')",
        "agent_imports": "from ConstrainAgent.ConstrainAgent import ConstrainNormalAgent; from Web_tools import collect_web_content; print('agent module imports OK; no client constructed')",
        "chromadb": "import chromadb; print(chromadb.__version__)",
        "lxml_parser": "from bs4 import BeautifulSoup; print(BeautifulSoup('<p>environment probe</p>', 'lxml').get_text())",
        "llama_embeddings": "from llama_index.embeddings.openai import OpenAIEmbedding; print('embedding module import OK; no embedding called')",
        "cuda": "import torch; print({'torch':torch.__version__,'cuda_build':torch.version.cuda,'cuda_available':torch.cuda.is_available(),'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None})",
        "pc_defaults": "import inspect; from causallearn.search.ConstraintBased.PC import pc; print(inspect.signature(pc))",
    }
    previous = {}
    if "--retry-timeouts" in sys.argv:
        previous = json.loads((evidence / "setup_audit.json").read_text(encoding="utf-8"))["import_checks"]
    report["import_checks"] = {}
    for name, code in checks.items():
        if previous and "시간 초과" not in previous[name].get("error", ""):
            report["import_checks"][name] = previous[name]
            continue
        report["import_checks"][name] = probe(code, timeout=180 if previous else 45)
        print(name, report["import_checks"][name]["ok"], flush=True)
    report["graphviz_dot"] = shutil.which("dot")
    report["ready_for_original_experiments"] = False
    report["readiness_note"] = "누락 입력·API 접근·논문/공개코드 차이 해소 전 실행 준비 완료로 판정하지 않는다."
    (evidence / "setup_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_matches": report["official_source"]["all_match"],
                      "pinned_packages": len(pinned), "all_pins_match": report["all_pins_match"],
                      "missing_inputs": len(report["missing_inputs"]), "ready": False}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
