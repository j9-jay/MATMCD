"""WSL에서 원본 requirements를 그대로 설치한다. 실험은 실행하지 않는다.

Python 3.11의 패치 버전은 저자 미공개다. uv가 선택한 로컬 설치본을
기록하며 저자의 정확한 Python 빌드라고 주장하지 않는다.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from project_paths import ASSETS, SOURCE, asset_path


def main():
    if sys.platform != "linux":
        raise SystemExit("공식 CUDA 의존성을 유지하기 위해 WSL Ubuntu에서 실행하세요.")
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("uv 실행 파일이 없습니다. 의존성 버전을 변경하지 않고 중단합니다.")
    log_dir = asset_path("setup_logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"environment_{stamp}.log"
    env = os.environ.copy()
    env.update({
        "UV_PYTHON_INSTALL_DIR": str(ASSETS / "environments" / "uv_cpython"),
        "UV_CACHE_DIR": str(ASSETS / "caches" / "uv_packages"),
        "UV_LINK_MODE": "copy",
        "UV_NO_PROGRESS": "1",
    })
    venv = asset_path("environment")
    python = venv / "bin" / "python"
    commands = []
    if not python.exists():
        commands.append([uv, "venv", "--python", "3.11", str(venv)])
    commands += [
        [str(python), "--version"],
        [uv, "pip", "install", "--python", str(python), "-r", str(SOURCE / "requirements.txt")],
        [uv, "pip", "check", "--python", str(python)],
    ]
    result = {"started_utc": stamp, "platform": platform.platform(), "commands": [], "log": str(log_path)}
    code = 0
    with log_path.open("w", encoding="utf-8") as log:
        for cmd in commands:
            header = json.dumps(cmd, ensure_ascii=False)
            print(header, flush=True)
            log.write(header + "\n")
            log.flush()
            proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            code = proc.wait()
            result["commands"].append({"argv": cmd, "exit_code": code})
            if code:
                break
    result["success"] = code == 0
    (log_dir / "environment_status.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if code == 0:
        freeze = subprocess.run([uv, "pip", "freeze", "--python", str(python)], env=env, text=True, capture_output=True, check=True)
        (log_dir / "installed_freeze.txt").write_text(freeze.stdout, encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
