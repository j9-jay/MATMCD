# 작업 현황

2026-09-22 KST 기준. DONE은 해당 조사·구성 작업의 완료를 뜻하며 전체 논문 재현 준비 완료를 뜻하지 않는다.

| Task | 목적 | 상태 |
|---|---|---|
| [001](TASK_001_paper_analysis.md) | 논문/부록 분석 | DONE |
| [002](TASK_002_official_code_setup.md) | 공식 소스/이력 보존과 감사 | DONE |
| [003](TASK_003_dataset_download.md) | 실제 실험 입력 준비 | BLOCKED — 원본 표본/EVT 입력 누락 |
| [004](TASK_004_environment_setup.md) | 의존성 환경 구성 | BLOCKED — 누락 패키지/Graphviz 버전 |
| [005](TASK_005_model_setup.md) | 모델 및 서비스 구성 | BLOCKED — snapshot/접근 조건 |
| [006](TASK_006_paths_and_preflight.md) | 경로 연결·실험 없는 점검 | DONE |
| [007](TASK_007_run_original_experiments.md) | 실제 실험 | TODO — 사용자 지시로 미실행 |
| [008](TASK_008_evaluate_results.md) | 실제 결과 평가 | TODO — 사용자 지시로 미실행 |
| [009](TASK_009_compare_with_paper.md) | 논문 수치 비교 | TODO — 사용자 지시로 미실행 |
| [010](TASK_010_supplementary_artifacts.md) | 추가 발견된 공식 전처리/비교 자료 | DONE |

새로 발견한 별도 목적의 조사는 마지막 번호 010으로 추가했다. 007~009는 실행 순서를 뜻하는 후속 의존 작업이며 실제 수행하지 않았다.

## 사용자 완료 기준과 현재 상태

| 기준 | 상태 |
|---|---|
| 논문/공식 자료 분석 | 완료 |
| 공식 코드/구성 요소 정리 | 완료 |
| 출처·역할에 따른 외부 자산 저장/연결 | 완료; 실제 파일이 있는 경로만 구성 |
| 필요한 데이터/모델 전부 준비 | 미완료; TASK_003/005 |
| 실행 환경/Dependency 완성 | 원본 pin 설치 완료, 누락분 때문에 미완료 |
| 동일 조건 실험 실행 가능 | 미완료; 코드 불일치/접근/입력 등 차단 사유 있음 |
| 번호 기반 Task 기록 | 완료 |
| 실제 실험/평가 TODO 유지 | 완료 |
| 미확정 사항/차이 기록 | 완료 |
