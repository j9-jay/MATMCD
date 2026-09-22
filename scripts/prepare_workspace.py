"""외부 작업공간에 원본 코드와 확보된 입력만 연결한다. 실험을 실행하지 않는다."""
import json
import os
import sys

from project_paths import ASSETS, PROJECT, SOURCE, asset_path


def link(source, target):
    if not source.exists():
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        if target.resolve() != source.resolve():
            raise RuntimeError(f"기존 링크가 다른 곳을 가리킵니다: {target}")
    elif target.exists():
        raise RuntimeError(f"기존 파일을 덮어쓰지 않습니다: {target}")
    else:
        target.symlink_to(os.path.relpath(source, target.parent), target_is_directory=source.is_dir())


def main():
    if sys.platform != "linux":
        raise SystemExit("WSL Ubuntu에서 실행하세요.")
    workspace = asset_path("runtime_workspace")
    inputs = json.loads((PROJECT / "configs" / "inputs.json").read_text(encoding="utf-8"))
    for source in sorted(SOURCE.glob("*.py")):
        link(source, workspace / source.name)
    for name in ("Client", "ConstrainAgent", "Utils", "web_utils"):
        link(SOURCE / name, workspace / name)
    link(SOURCE / "data" / "SampleFromBIF.py", workspace / "data" / "SampleFromBIF.py")
    for name, path in inputs["benchmark_files"].items():
        link(ASSETS / path, workspace / "data" / name)
    for name in ("asia", "child"):
        source = ASSETS / f"datasets/bnlearn_{name}_network/{name}.bif"
        if source.exists():
            link(source, workspace / "data" / "BIF" / source.name)
    print(f"작업공간: {workspace}")
    print("원본 코드/확보된 입력만 링크했습니다. 누락 CSV, 캐시, 결과 폴더는 생성하지 않았습니다.")


if __name__ == "__main__":
    main()
