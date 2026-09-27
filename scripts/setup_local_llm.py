"""Download and isolate the user-approved local model/runtime; never run RCA."""
import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from project_paths import ASSETS, PROJECT

CONFIG = json.loads((PROJECT / "configs/local_llm.json").read_text(encoding="utf-8"))


def asset(relative):
    target = (ASSETS / relative).resolve()
    if not target.is_relative_to(ASSETS):
        raise ValueError(f"Asset path escapes root: {relative}")
    return target


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url, path, expected_hash=None, expected_size=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        partial = path.with_name(path.name + ".partial")
        print(f"Download: {path.name}", flush=True)
        subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                        "--retry", "2", "--continue-at", "-", "--output", str(partial), url], check=True)
        if expected_size is not None and partial.stat().st_size != expected_size:
            raise RuntimeError(f"Size mismatch: {partial}")
        if expected_hash is not None and sha256(partial) != expected_hash:
            raise RuntimeError(f"SHA-256 mismatch: {partial}")
        partial.rename(path)
    digest = sha256(path)
    if expected_hash is not None and digest != expected_hash:
        raise RuntimeError(f"Existing file SHA-256 mismatch: {path}")
    if expected_size is not None and path.stat().st_size != expected_size:
        raise RuntimeError(f"Existing file size mismatch: {path}")
    print(f"Verified: {path.name} ({path.stat().st_size} bytes)", flush=True)
    return {"path": path.relative_to(ASSETS).as_posix(), "url": url,
            "size_bytes": path.stat().st_size, "sha256": digest}


def preserve_json(url, path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    with urlopen(Request(url, headers={"User-Agent": "MATMCD-local-setup"}), timeout=60) as response:
        data = json.load(response)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    if not args.install:
        print("Requires --install; reads only approved configs/local_llm.json")
        return
    if sys.platform != "linux":
        raise SystemExit("Run with the existing WSL Python environment.")
    runtime = CONFIG["runtime"]
    model = CONFIG["model"]
    download_dir = asset(runtime["download_directory"])
    install_dir = asset(runtime["install_directory"])
    model_dir = asset(model["directory"])
    release = preserve_json(f'https://api.github.com/repos/{runtime["repository"]}/releases/tags/{runtime["binary_tag"]}', download_dir / "release.json")
    files = []
    for item in runtime["archives"]:
        upstream = next(x for x in release["assets"] if x["name"] == item["filename"])
        if upstream["digest"] != "sha256:" + item["sha256"] or upstream["size"] != item["size_bytes"]:
            raise RuntimeError("Pinned GitHub metadata mismatch")
        archive = download_dir / item["filename"]
        files.append(fetch(upstream["browser_download_url"], archive, item["sha256"], item["size_bytes"]))
        destination = install_dir / item["subdirectory"]
        marker = destination / ".extracted_sha256"
        if marker.exists():
            if marker.read_text().strip() != item["sha256"]:
                raise RuntimeError("Existing extraction differs")
        else:
            if destination.exists():
                raise RuntimeError(f"Incomplete or unrecognized install: {destination}")
            destination.mkdir(parents=True)
            with tarfile.open(archive) as tar:
                tar.extractall(destination, filter="data")
            marker.write_text(item["sha256"] + "\n")
    for remote, filename in [("tools/server/README.md", "server_README.md"), ("LICENSE", "LICENSE")]:
        files.append(fetch(f'https://raw.githubusercontent.com/{runtime["repository"]}/{runtime["commit"]}/{remote}', download_dir / filename))
    gguf_meta = preserve_json(f'https://huggingface.co/api/models/{model["repository"]}/revision/{model["revision"]}?blobs=true', model_dir / "upstream_metadata.json")
    if gguf_meta["sha"] != model["revision"]:
        raise RuntimeError("Model revision mismatch")
    pointer = next(x for x in gguf_meta["siblings"] if x["rfilename"] == model["filename"])
    if pointer["lfs"]["sha256"] != model["sha256"]:
        raise RuntimeError("Model upstream hash mismatch")
    files.append(fetch(f'https://huggingface.co/{model["repository"]}/resolve/{model["revision"]}/{model["filename"]}', model_dir / model["filename"], model["sha256"], model["size_bytes"]))
    files.append(fetch(f'https://huggingface.co/{model["repository"]}/resolve/{model["revision"]}/README.md', model_dir / "QUANTIZATION_README.md"))
    files.append(fetch(f'https://huggingface.co/{model["base_repository"]}/resolve/{model["base_revision_observed"]}/README.md', model_dir / "BASE_MODEL_README.md"))
    files.append(fetch(f'https://huggingface.co/{model["base_repository"]}/resolve/{model["base_revision_observed"]}/config.json', model_dir / "BASE_MODEL_CONFIG.json"))
    binaries = list(install_dir.rglob("llama-server"))
    if len(binaries) != 1:
        raise RuntimeError(f"Expected one llama-server, got {len(binaries)}")
    binary = binaries[0]
    binary.chmod(binary.stat().st_mode | 0o111)
    libraries = sorted({p.parent for p in install_dir.rglob("*.so*")})
    evidence = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(), "status": "INSTALLED_NOT_YET_RUNTIME_VERIFIED",
        "profile": CONFIG["profile"], "files": files,
        "executable": binary.relative_to(ASSETS).as_posix(),
        "executable_sha256": sha256(binary),
        "library_directories": [p.relative_to(ASSETS).as_posix() for p in libraries],
        "installed_files": [{"path": p.relative_to(ASSETS).as_posix(), "sha256": sha256(p)} for p in sorted(install_dir.rglob("*")) if p.is_file() and not p.is_symlink()],
        "model_calls": 0, "paid_api_calls": 0, "experiments_executed": False,
        "installer_calls_python_package_manager": False,
        "installer_calls_system_package_manager": False,
        "system_package_stability_during_download": "NOT_MEASURED; validate separately because background OS updates can run"
    }
    out = PROJECT / "docs/evidence/local_llm_install.json"
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Installed: {binary}\nEvidence: {out}", flush=True)


if __name__ == "__main__":
    main()
