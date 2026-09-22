# 현재 재현 작업 규칙

상위 `E:\연구\AGENTS.md`를 따른다. 현재 상태는 `README.md`, `tasks/INDEX.md`, `docs/ORIGINAL_LOCAL_ISSUES.md`에서 확인한다.

- 사용자 Git 저장소의 `.git`을 보존한다. origin은 j9-jay/MATMCD, upstream은 D2I-Group/matmcd다.
- `official/matmcd`는 `configs/upstream.json`에 고정한 저자 원본이다. 코드·프롬프트·requirements를 수정해 실행 문제를 우회하지 않는다.
- 논문 제공본은 arXiv:2412.13667v2다. 실제로 확인하지 못한 값은 미확정으로 기록한다.
- 실험 자산과 환경은 `configs/paths.json`이 가리키는 MATMCD_DATA에서 관리한다. 경로를 코드에 반복 하드코딩하지 않는다.
- 실제 파일을 저장/연결할 때만 폴더를 만든다. 예시 구조를 빈 폴더로 미리 만들지 않는다.
- 누락된 CSV, BIF 샘플링 seed, RCA 전처리 조건, 모델 snapshot을 추측하지 않는다. 로컬 모델로 대체하지 않는다.
- 별도 과금 API를 호출하지 않는다. 계정 자격정보를 탐색하거나 Git에 넣지 않는다.
- 현재 범위는 환경 준비까지다. 별도 실행 지시 전 TASK_007/008/009를 실행하지 않고 TODO로 유지한다.
- 발견한 원본 문제는 한국어 문서에 기록한다. 설치 성공을 전체 재현 실행 가능으로 과장하지 않는다.
- 파일 변경 전에 무엇을 왜 바꾸는지 알린다. 현재 사용자가 허용한 준비 범위 내 작업은 중간 확인을 요구하지 않고 진행한다.
