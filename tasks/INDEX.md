# 작업 현황

2026-10-18 재계획. 이전 상태 기록은 Git 커밋 `2f0d66a`(재계획 전 스냅샷)에 보존했다.

## 현재 목표

**2026-11-18 계획 A로 전환.** 사용자의 처음 아이디어(추론 상태 기반 근거 검색)를 명세서로 쓰고, 그대로 새로 구현해, 한 번 평가한다. 단계, 태스크, 결정 사항, 진행 로그는 [MASTER_PLAN](../docs/research_log/MASTER_PLAN.md)을 따른다.

- MATMCD는 논문에 실린 공식 지표와 점수만 비교에 쓴다. 재현 실험은 하지 않는다.
- LEMMA-RCA 원자료는 새 방법의 실험에 쓴다.
- TASK_070(2026-10의 방법과 실험)은 2026-11-18에 삭제했다. 저장소 파일은 git 이력 `2296ea6`에 남아 있다.

## 활성 TODO

현재 작업의 태스크는 이 문서가 아니라 MASTER_PLAN 6절에서 관리한다.

## 보류 — 현재 목표 범위 밖

| 항목 | 이유 | 관련 |
|---|---|---|
| LEMMA-RCA 전체 후보(218/196 Pod) 실행 | PC 메모리 부족(D08)과 LLM 호출 규모 | [TASK_046](TASK_046_real_rca_integration.md), [TASK_048](TASK_048_resolve_pc_memory.md), [D08](../docs/RCA_PC_MEMORY.md) |
| LEMMA 전체 후보 로그 요약 중단 원인 | 원인 UNKNOWN | [TASK_047](TASK_047_resolve_generation_repetition.md) |
| MATMCD 원본 API 검증 | 유료 API 미사용. `gpt-4`·`gpt-3.5-turbo`는 2026-10-23, `gpt-4o-mini-2024-07-18`은 2027-01-14 종료 예정(OpenAI deprecations 페이지, 2026-10-17 확인) | [TASK_025](TASK_025_original_api_validation.md) |
| Graphviz 저자 버전 | 순위 입력이 아님 | [TASK_022](TASK_022_graphviz_author_version.md) |

## 저자 문의 — 종료

메일은 발송했으나 2026-10-18 기준 답신이 없어 사용자 결정으로 Task를 종료·삭제했다(TASK_018). 답신을 기대하지 않고 진행한다. 미확정 조건 목록은 기준선 차이 표의 근거로 보존한다: [23개 문의 목록](../docs/AUTHOR_QUESTIONS_RCA.md), [최종 메일 본문](../docs/AUTHOR_INQUIRY_RCA_SHORT.md), [D03/D04 문의 자료](../docs/AUTHOR_QUESTIONS_D03_D04.md).

## 백로그

2026-10의 백로그(R1~R14)는 연구 로드맵 문서와 함께 2026-11-18에 삭제했다(git 이력 `fa1572a`). 새 백로그가 생기면 MASTER_PLAN에 적는다.

## 완료·이력 Task

| Task | 내용 | 상태 |
|---|---|---|
| [001](TASK_001_paper_analysis.md) | 논문·부록 분석 | DONE |
| [002](TASK_002_official_code_setup.md) | 공식 소스 확보 (커밋 `ef2c3ec`) | DONE |
| [003](TASK_003_dataset_download.md) | RCA 저자 원본 입력 확보 | 미해결 — 원본 CSV·전처리 동일성 미확인, 임시 전처리로 대체 |
| [004](TASK_004_environment_setup.md) | 공통 실행 환경 | DONE |
| [005](TASK_005_model_setup.md) | 원본 API 모델 접근 | 보류 — 유료 API 미사용 |
| [006](TASK_006_paths_and_preflight.md) | 외부 경로 연결·사전 점검 | DONE |
| [007](TASK_007_run_original_experiments.md) | 전체 후보 2사례 실행 | 대체 — 당시 목표는 TASK_070(삭제됨 2026-11-18) |
| [008](TASK_008_evaluate_results.md) | 실제 순위 평가 | 이력 — LEMMA 평가는 TASK_069 종료로 미수행. 새 평가는 TASK_070(삭제됨 2026-11-18) T9 |
| [009](TASK_009_compare_with_paper.md) | 논문 표 4 비교 | 이력 — 표 4 비교는 수행하지 않음(TASK_069 종료). MATMCD는 TASK_070(삭제됨 2026-11-18)에서 참고 기준선 |
| [010](TASK_010_supplementary_artifacts.md) | 공식 전처리·비교 자료 조사 | DONE |
| [011](TASK_011_summary_output_directory.md)~[015](TASK_015_install_openai_embeddings.md) | 요약 경로, Chroma·lxml·embedding 어댑터 설치 | DONE |
| [017](TASK_017_scope_rca_only.md) | RCA 범위 전환 | DONE |
| [019](TASK_019_provisional_rca_preprocessing_plan.md)·[020](TASK_020_apply_provisional_rca_preprocessing.md) | 임시 전처리 설계·적용 (저자 동일성 UNCONFIRMED) | DONE |
| [021](TASK_021_install_system_graphviz.md) | Graphviz B안 설치 | DONE |
| [022](TASK_022_graphviz_author_version.md) | Graphviz 저자 버전 | 보류 |
| [023](TASK_023_local_qwen_thinking_setup.md) | Qwen3.5-4B Q5_K_M 로컬 환경 | DONE |
| [024](TASK_024_local_rca_integration.md) | 전체 후보 로컬 RCA 연결 | 보류 — 연결 코드는 30 Pod 실행에서 사용 |
| [025](TASK_025_original_api_validation.md) | 원본 API 검증 | 보류 |
| [026](TASK_026_local_thinking_output_budget.md)·[029](TASK_029_local_nonthinking_verification.md) | thinking 실패 분석, non-thinking 전환 | DONE |
| [027](TASK_027_wsl_system_drift.md) | WSL 시스템 변화 기록 | DONE |
| [028](TASK_028_local_re_response_format.md) | RE 응답 형식 보정 | DONE |
| [030](TASK_030_local_bge_m3_embedding.md) | BGE-M3 로컬 임베딩 | DONE |
| [031](TASK_031_rca_readiness_audit.md) | 실행 준비 점검 (당시 NOT_READY) | DONE — 이력 |
| [032](TASK_032_connect_provisional_rca_inputs.md)~[034](TASK_034_official_scenario_evidence.md) | 입력 연결, 지표 함수, 공식 시나리오 조사 | DONE |
| [035](TASK_035_missing_log_policy.md)~[038](TASK_038_d01_public_case_research.md) | D01 로그 부재 정책, D02 대용량 로그 읽기 | DONE |
| [039](TASK_039_select_three_rca_cases.md) | 세 사례 선택 | 대체 — TASK_044 |
| [040](TASK_040_d03_original_graph_protocol.md)·[041](TASK_041_d04_original_evaluation_protocol.md) | D03 그래프 규약, D04 평가 규약 | DONE — 30 Pod 실행에 적용. TASK_070(삭제됨 2026-11-18)에서는 공통 출력부를 쓰므로 해당 없음 |
| [042](TASK_042_real_prompt_capacity.md)·[045](TASK_045_validate_context_81920.md) | D05 문맥 용량 → 81,920 | DONE |
| [043](TASK_043_log_encoding_diagnosis.md) | D06 로그 UTF-8 처리 | DONE |
| [044](TASK_044_select_two_rca_cases.md) | 두 사례 선택 (PR 20211203, CC 20231207) | DONE |
| [046](TASK_046_real_rca_integration.md)~[048](TASK_048_resolve_pc_memory.md) | 전체 후보 통합, D07 반복 생성, D08 메모리 | 보류 |
| [049](TASK_049_local_resource_optimization.md) | LLM prompt cache 설정 | DONE |
| [050](TASK_050_oracle30_matmcd_run.md)~[052](TASK_052_domain_generation_repetition.md) | 정답 포함 30 Pod 실행 | DONE — **조건부 분석 전용, 주 실험 제외** |
| [053](TASK_053_oracle30_result_report.md) | 30 Pod 결과 분석 보고서 | DONE |
| [054](TASK_054_github_setup_update.md) | GitHub 업데이트 (`3fe751c`) | DONE |
| [069](TASK_069_blind_baseline.md) | LEMMA-RCA 정답 미사용 기준선 | 종료 — 후보 recall 0/5, 점수 포화 확인. TASK_070으로 대체 |
| 070 | 추론 상태 기반 근거 검색 실험 (2026-10의 방법과 실험) | 삭제(2026-11-18, 사용자 결정) — 결과를 보며 여러 번 고친 버전이라 쓰지 않음. git 이력 `2296ea6` |

삭제(2026-10-18, `2f0d66a`에 보존): 미팅·발표 자료 Task 054(교수님 보고 기획)·055·057~068, 저자 문의 목록 작업 056, 저자 문의 018(메일 발송 후 답신 없음, 2026-10-18 종료), 10월 2일 브리핑, 시점 스냅샷 문서 4개(`TASK_STATUS_20260926`, `RCA_READINESS`, `RCA_REBOOT_RETEST`, `LOCAL_COMPLETION_PROPOSAL`). 016은 이전 범위 정리에서 삭제했으며 번호를 재사용하지 않는다.
