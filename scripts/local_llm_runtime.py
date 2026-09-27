"""Pinned, loopback-only llama.cpp launch configuration (no RCA entry point)."""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, asset_path
from setup_local_llm import CONFIG, asset, sha256


def runtime_command(verify_model=True):
    if sys.platform != "linux" or sys.prefix != str(asset_path("environment")):
        raise RuntimeError("Use the existing pinned WSL Python environment")
    installation = json.loads((PROJECT / "docs/evidence/local_llm_install.json").read_text(encoding="utf-8"))
    executable = asset(installation["executable"])
    if sha256(executable) != installation["executable_sha256"]:
        raise RuntimeError("llama-server executable changed")
    model = CONFIG["model"]
    model_path = asset(model["directory"]) / model["filename"]
    if model_path.stat().st_size != model["size_bytes"] or (verify_model and sha256(model_path) != model["sha256"]):
        raise RuntimeError("Pinned model changed")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("LLAMA_ARG_", "GGML_"))}
    env["LD_LIBRARY_PATH"] = ":".join(str(asset(p)) for p in installation["library_directories"]) + ":/usr/lib/wsl/lib"
    cuda_cache = asset(CONFIG["runtime"]["cuda_cache_directory"])
    cuda_cache.mkdir(parents=True, exist_ok=True)
    env["CUDA_CACHE_PATH"] = str(cuda_cache)
    server = CONFIG["server"]
    if server["host"] != "127.0.0.1" or type(server["thinking"]) is not bool:
        raise RuntimeError("This approved profile requires loopback and an explicit thinking mode")
    command = [str(executable), "--model", str(model_path),
               "--alias", model["server_alias"], "--host", server["host"], "--port", str(server["port"]),
               "--ctx-size", str(server["context_tokens"]), "--parallel", str(server["parallel_slots"]),
               "--n-gpu-layers", str(server["gpu_layers"]), "--fit", "off",
               "--batch-size", str(server["batch_tokens"]), "--ubatch-size", str(server["microbatch_tokens"]),
               "--cache-type-k", server["cache_type_k"], "--cache-type-v", server["cache_type_v"],
               "--no-context-shift", "--jinja", "--chat-template-kwargs", json.dumps({"enable_thinking": server["thinking"]}),
               "--reasoning", "on" if server["thinking"] else "off", "--reasoning-format", server["reasoning_format"],
               "--reasoning-budget", "-1", "--offline", "--no-webui", "--cache-prompt", "--cache-ram", "0",
               "--log-verbosity", str(server["log_verbosity"])]
    return command, env


def base_url():
    return f'http://127.0.0.1:{CONFIG["server"]["port"]}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help="Run local server in foreground; Ctrl+C stops it")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    command, env = runtime_command()
    if args.version:
        return subprocess.call([command[0], "--version"], env=env)
    if not args.serve:
        print(json.dumps({"command": command, "base_url": base_url() + "/v1"}, ensure_ascii=False, indent=2))
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    logs = asset(CONFIG["logging"]["directory"]) / stamp
    logs.mkdir(parents=True)
    (logs / "launch.json").write_text(json.dumps({"command": command, "profile": CONFIG,
                                                "environment_overrides": {k: env[k] for k in ("LD_LIBRARY_PATH", "CUDA_CACHE_PATH")}}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Local server: {base_url()}\nLog: {logs / 'server.log'}\nCtrl+C stops the server. No RCA job is started.", flush=True)
    with (logs / "server.log").open("w", encoding="utf-8") as out:
        proc = subprocess.Popen(command, env=env, stdout=out, stderr=subprocess.STDOUT)
        try:
            return proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            return 130


if __name__ == "__main__":
    raise SystemExit(main())
