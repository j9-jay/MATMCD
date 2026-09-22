# TASK_011 - CODE-03 요약 저장 경로 준비

## 목적

공식 코드의 요약 저장 경로가 없어 발생하는 파일 저장 오류를 환경 준비 단계에서 해소한다. 실험 조건이나 공식 코드를 변경하지 않는다.

## 작업 항목

- [x] 벤치마크/RCA 진입점의 output_dir와 저장 함수 확인
- [x] 기존 prepare_workspace.py에 필수 경로 준비 추가
- [x] WSL 외부 작업공간에서 준비 스크립트 실행
- [x] 경로 존재·쓰기 가능·원본 보존 확인
- [x] blocker 및 실행 문서 갱신

## 확인 사항

공식 `GTdatasets_experiment.py`와 `LEMMA_experiment.py`는 `output_dir="./cache/Summarized_info"`를 전달한다. `Web_tools.py`의 `generate_dataset_summary`는 부모 생성 없이 `open(..., "w")`를 호출한다. 이 상대경로는 공개 코드에서 확인되므로 임의의 실험값을 결정하지 않는다.

예시용 폴더를 미리 만드는 작업이 아니다. 원본 저장 함수가 직접 요구하며 스스로 생성하지 않는 경로 하나만 준비한다. 요약 텍스트·embedding·domain knowledge 캐시는 만들지 않는다.

## 결과

`python3 -B scripts/prepare_workspace.py`를 기존 WSL Ubuntu에서 실행했다. 외부 자산 루트의 `workspaces/d2i_matmcd_original/cache/Summarized_info`를 생성했고, WSL에서 임시 파일 쓰기 후 자동 제거가 성공했다. 요약 저장 폴더는 비어 있다. 공식 43개 파일은 보관한 ZIP과 바이트 단위로 동일하며 준비 스크립트의 문법 검사도 통과했다.

최초 WSL 호출은 sandbox에서 `Wsl/Service/E_ACCESSDENIED`로 차단되었다. 실행 코드의 오류가 아니며, 도구의 권한 확장 후 동일 명령이 성공했다. 원본이나 실험 조건을 수정하여 우회하지 않았다.

CODE-03은 RESOLVED다. [검증 기록](../docs/evidence/code03_directory_check.json)에 결과를 보존했다. 실험/API/요약 생성은 실행하지 않았고, 다른 blocker와 TASK_007~009의 TODO 상태는 유지한다.

## 상태

DONE
