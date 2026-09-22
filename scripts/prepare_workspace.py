"""외부 작업공간에 원본 코드·입력을 연결하고 필수 저장 경로를 준비한다."""
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
    # 원본 두 실험 진입점이 이 경로를 지정하지만 저장 함수는 부모를 만들지 않는다.
    summary_dir = workspace / "cache" / "Summarized_info"
    if not summary_dir.resolve().is_relative_to(workspace):
        raise RuntimeError(f"요약 저장 경로가 작업공간 밖을 가리킵니다: {summary_dir}")
    summary_dir.mkdir(parents=True, exist_ok=True)
    print(f"작업공간: {workspace}")
    print(f"원본 코드가 요구하는 요약 저장 폴더: {summary_dir}")
    print("코드/입력 링크와 필수 경로만 준비했습니다. 실험·API 호출·캐시 내용 생성은 수행하지 않았습니다.")


if __name__ == "__main__":
    main()
