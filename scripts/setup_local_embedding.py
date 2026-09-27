"""Install the approved BGE-M3 assets and isolated loader; do not run RCA."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from project_paths import ASSETS, PROJECT, asset_path
from setup_chromadb import pins
from setup_graphviz import assert_original_source, python_packages, source_hashes, system_packages, write_json
from setup_local_llm import asset, fetch, preserve_json, sha256

CONFIG_PATH = PROJECT / "configs/local_embedding.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", required=True)
    parser.parse_args()
    if sys.platform != "linux" or Path(sys.prefix) != asset_path("environment"):
        raise RuntimeError("Use the pinned WSL Python environment")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    logs = asset(CONFIG["storage"]["log_directory"]) / (stamp + "_install")
    logs.mkdir(parents=True, exist_ok=False)
    report = {"status": "IN_PROGRESS", "timestamp_utc": stamp, "profile": CONFIG["profile"],
              "config_sha256": sha256(CONFIG_PATH), "installer_sha256": sha256(Path(__file__)),
              "log_directory": logs.relative_to(ASSETS).as_posix(), "files": [],
              "experiments_executed": False, "model_calls": 0, "paper_equivalence": False}
    before_python, before_source, before_system = python_packages(), source_hashes(), system_packages()
    expected = pins((PROJECT / "docs/evidence/installed_freeze_with_openai_embeddings.txt").read_text())
    try:
        assert_original_source()
        if before_python != expected or len(before_python) != 201:
            raise RuntimeError("Base environment differs from the recorded 201 packages")
        model, runtime = CONFIG["model"], CONFIG["runtime"]
        # Preserve LlamaIndex's original splitting tokenizer in the external cache.
        # Its exact data is already bundled with the installed llama-index-core wheel.
        tokenizer = runtime["splitter_tokenizer"]
        cache_name = hashlib.sha1(tokenizer["url"].encode()).hexdigest()
        bundled = Path(importlib.metadata.distribution("llama-index-core").locate_file("llama_index/core/_static/tiktoken_cache")) / cache_name
        cache_file = asset(runtime["splitter_cache_directory"]) / cache_name
        if not bundled.is_file() or sha256(bundled) != tokenizer["sha256"]:
            raise RuntimeError("Existing bundled splitter tokenizer does not match the official tiktoken hash")
        if not cache_file.exists():
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(bundled, cache_file)
        if sha256(cache_file) != tokenizer["sha256"]:
            raise RuntimeError("External splitter tokenizer cache differs; refusing to overwrite")
        report["splitter_tokenizer"] = {"url": tokenizer["url"], "sha256": tokenizer["sha256"],
                                       "path": cache_file.relative_to(ASSETS).as_posix(),
                                       "copied_from_existing_wheel": "llama-index-core==0.12.37", "downloaded": False}
        model_dir, downloads = asset(model["directory"]), asset(runtime["download_directory"])
        metadata = preserve_json(f'https://huggingface.co/api/models/{model["repository"]}/revision/{model["revision"]}?blobs=true', model_dir / "upstream_metadata.json")
        if metadata["sha"] != model["revision"]:
            raise RuntimeError("Model revision mismatch")
        for name in model["files"]:
            item = next(x for x in metadata["siblings"] if x["rfilename"] == name)
            upstream_hash = item.get("lfs", {}).get("sha256")
            if name == "pytorch_model.bin" and (upstream_hash != model["weights_sha256"] or item["size"] != model["weights_size_bytes"]):
                raise RuntimeError("Pinned weights metadata mismatch")
            if name == "tokenizer.json" and upstream_hash != model["tokenizer_sha256"]:
                raise RuntimeError("Pinned tokenizer metadata mismatch")
            target = model_dir / name
            entry = fetch(f'https://huggingface.co/{model["repository"]}/resolve/{model["revision"]}/{name}', target, upstream_hash, item["size"])
            if upstream_hash is None:
                data = target.read_bytes()
                git_sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                if git_sha != item["blobId"]:
                    raise RuntimeError(f"Pinned Git blob mismatch: {name}")
                entry["upstream_git_blob_sha1"] = git_sha
            report["files"].append(entry)
        wheels, proposals = [], {}
        for package in runtime["packages"]:
            meta = preserve_json(f'https://pypi.org/pypi/{package["name"]}/{package["version"]}/json', downloads / (package["name"] + "_metadata.json"))
            release = next(x for x in meta["urls"] if x["filename"] == package["filename"])
            if release["digests"]["sha256"] != package["sha256"]:
                raise RuntimeError("Pinned wheel hash mismatch")
            wheel = downloads / package["filename"]
            report["files"].append(fetch(release["url"], wheel, package["sha256"], release["size"]))
            wheels.append(str(wheel))
            proposals[package["name"]] = package["version"]
        # Validate requirements without allowing a resolver to upgrade the base environment.
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name
        import zipfile
        import email
        available = {**before_python, **proposals}
        checked = []
        for wheel in wheels:
            with zipfile.ZipFile(wheel) as archive:
                metadata_name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
                wheel_meta = email.message_from_bytes(archive.read(metadata_name))
            for declaration in wheel_meta.get_all("Requires-Dist", []):
                req = Requirement(declaration)
                if req.marker is not None and not req.marker.evaluate({"extra": ""}):
                    continue
                version = available.get(canonicalize_name(req.name))
                if version is None or version not in req.specifier:
                    raise RuntimeError(f"Unsatisfied existing dependency: {declaration}; found {version}")
                checked.append({"requirement": declaration, "resolved": version})
        report["requirements_checked"] = checked
        overlay = asset(runtime["overlay_directory"])
        marker = overlay / "matmcd_overlay_manifest.json"
        if marker.exists():
            previous = json.loads(marker.read_text())
            if previous["packages"] != proposals:
                raise RuntimeError("Existing overlay differs")
        elif overlay.exists():
            raise RuntimeError("Unrecognized existing overlay; refusing to overwrite")
        else:
            uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
            if not Path(uv).is_file():
                raise RuntimeError("Existing uv executable was not found")
            command = [uv, "pip", "install", "--python", sys.executable, "--target", str(overlay),
                       "--no-deps", "--no-index", *wheels]
            report["install_command"] = command
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    env={**os.environ, "UV_CACHE_DIR": str(ASSETS / "caches/uv_packages"),
                                         "UV_LINK_MODE": "copy", "UV_PYTHON_DOWNLOADS": "never", "PYTHONDONTWRITEBYTECODE": "1"})
            (logs / "install.log").write_text(result.stdout)
            if result.returncode:
                raise RuntimeError(f"Overlay installation failed: {result.stdout}")
            installed = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions(path=[str(overlay)])}
            if installed != proposals:
                raise RuntimeError(f"Overlay differs: {installed}")
            files = {p.relative_to(overlay).as_posix(): sha256(p) for p in sorted(overlay.rglob("*")) if p.is_file()}
            write_json(marker, {"packages": proposals, "files": files})
        current = json.loads(marker.read_text())
        if any(not (overlay / name).is_file() or sha256(overlay / name) != digest for name, digest in current["files"].items()):
            raise RuntimeError("Overlay file verification failed")
        report["overlay_packages"] = current["packages"]
        report["overlay_manifest_sha256"] = sha256(marker)
        report["status"] = "INSTALLED_NOT_YET_RUNTIME_VERIFIED"
    except Exception:
        report["status"] = "FAILED"
        report["error"] = traceback.format_exc()
    report["preservation"] = {"base_python_201_unchanged": before_python == python_packages(),
                              "official_37_unchanged": before_source == source_hashes(),
                              "system_packages_unchanged": before_system == system_packages()}
    if not all(report["preservation"].values()):
        report["status"] = "FAILED"
    write_json(logs / "report.json", report)
    evidence = PROJECT / "docs/evidence/local_embedding_install.json"
    if evidence.exists():
        (logs / "previous_report.json").write_bytes(evidence.read_bytes())
    write_json(evidence, report)
    print(json.dumps({k: report[k] for k in ("status", "log_directory", "preservation")}), flush=True)
    if "error" in report:
        print(report["error"], flush=True)
    return int(report["status"] == "FAILED")


if __name__ == "__main__":
    raise SystemExit(main())
