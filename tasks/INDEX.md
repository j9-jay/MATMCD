# 작업 현황

2026-10-18 재계획. 이전 상태 기록은 Git 커밋 `2f0d66a`(재계획 전 스냅샷)에 보존했다.

## 현재 목표

**현재 PC 환경에서 정답 정보를 사용하지 않는 MATMCD 기준선을 만든다.** 작업 상세는 [TASK_069](TASK_069_blind_baseline.md)를 따른다.

- 주 실험에서 정답 포함(oracle) 후보는 사용하지 않는다. 기존 30 Pod 결과는 "정답이 후보에 있을 때의 조건부 분석"으로만 쓴다.
- 원 논문 표 4 수치 일치는 목표가 아니다. 공식 구현에 충실하게 실행하고 원 논문과 다른 조건을 모두 명시한다.
- 연구의 최종 방향은 NLP/RAG(ACL·EMNLP·NAACL·EACL·COLING)다. RCA는 검증 과제로 사용하며 엔지니어링 확장은 하지 않는다. 장기 계획은 [연구 로드맵](../docs/RESEARCH_ROADMAP.md)에 있다.

## 활성 TODO — TASK_069

| ID | 작업 | 상태 |
|---|---|---|
| B0 | 기준선 명세서와 원 논문 대비 차이 표 작성 | TODO |
| B1 | 정답을 사용하지 않는 후보 선정 규칙 결정·고정 | **사용자 결정 필요** |
| B2 | 사례 범위 결정 (PR 20211203, CC 20231207 순위 기록·점수 보류) | **사용자 결정 필요** |
| B3 | D03 처리 방식(공개 코드 그대로 / 교정판 / 둘 다)과 MATMCD-RE 포함 여부 결정 | **사용자 결정 필요** |
| B4 | RWR 반복 횟수·seed 규칙 사전 고정 | TODO |
| B5 | 새 프로필로 PC → 로그 요약/RAG → MATMCD → RWR 실행 | TODO (B1~B4 이후) |
| B6 | 평가: end-to-end, 후보 recall, 기존 30 Pod 조건부 분석 | TODO |
| B7 | 기준선 결과 보고서 | TODO |

## 보류 — 현재 목표 범위 밖

| 항목 | 이유 | 관련 |
|---|---|---|
| 전체 후보(218/196 Pod) 실행 | PC 메모리 부족(D08)과 LLM 호출 규모. 엔지니어링 확장은 하지 않음 | [TASK_046](TASK_046_real_rca_integration.md), [TASK_048](TASK_048_resolve_pc_memory.md), [D08](../docs/RCA_PC_MEMORY.md) |
| 전체 후보 로그 요약 중단 원인 | 원인 UNKNOWN. 전체 후보를 재개할 때만 조사 | [TASK_047](TASK_047_resolve_generation_repetition.md) |
| 웹 검색 경로 | 외부 API·정답 누출 위험. 사용자 결정 전까지 미사용 | [TASK_024](TASK_024_local_rca_integration.md) |
| 원본 API 검증 | 유료 API 미사용 방침. `gpt-4`·`gpt-3.5-turbo`는 2026-10-23, `gpt-4o-mini-2024-07-18`은 2027-01-14 종료 예정(OpenAI deprecations 페이지, 2026-10-17 확인) | [TASK_025](TASK_025_original_api_validation.md) |
| Graphviz 저자 버전 | 순위 입력이 아님 | [TASK_022](TASK_022_graphviz_author_version.md) |

## 계속 진행

| 항목 | 상태 | 관련 |
|---|---|---|
| 저자 문의 | **발송 여부 사용자 확인 필요.** 최종 문안 5문항, 23개 내부 목록 보존 | [TASK_018](TASK_018_author_clarifications.md) |

## 백로그 — NLP/RAG 연구 (현재 미착수)

상세는 [연구 로드맵](../docs/RESEARCH_ROADMAP.md).

| ID | 작업 |
|---|---|
| R1 | 연구 질문(RQ1~RQ4)과 주장 확정, 지도교수 합의 |
| R2 | 벤치마크 조사·재선정 (LEMMA-RCA, RCAEval, OpenRCA 등) |
| R3 | 역할 태그·근거 자료(corpus) 설계 |
| R4 | 평가 설계: 근거 recall/사슬 완결성, 최종 과제 지표, 비용, 통계 검정 |
| R5 | 정답 근거 주석(gold/silver evidence) 방식 결정 |
| R6 | NLP 기준선 구현: 검색 없는 LLM, flat RAG, 반복 검색, 질의 분해, 그래프 RAG, 역할 태그만 쓰는 RAG |
| R7 | 제안 방법 구현(추론 상태 5단계)과 ablation |
| R8 | 여러 LLM 실험과 오염(contamination) 분석 |
| R9 | 오류 분석·정성 사례 (flat RAG의 MongoDB 근거 누락 사례 포함) |
| R10 | ARR 형식 논문 작성 (Limitations, Responsible NLP 체크리스트) |

## 완료·이력 Task

| Task | 내용 | 상태 |
|---|---|---|
| [001](TASK_001_paper_analysis.md) | 논문·부록 분석 | DONE |
| [002](TASK_002_official_code_setup.md) | 공식 소스 확보 (커밋 `ef2c3ec`) | DONE |
| [003](TASK_003_dataset_download.md) | RCA 저자 원본 입력 확보 | 미해결 — 원본 CSV·전처리 동일성 미확인, 임시 전처리로 대체 |
| [004](TASK_004_environment_setup.md) | 공통 실행 환경 | DONE |
| [005](TASK_005_model_setup.md) | 원본 API 모델 접근 | 보류 — 유료 API 미사용 |
| [006](TASK_006_paths_and_preflight.md) | 외부 경로 연결·사전 점검 | DONE |
| [007](TASK_007_run_original_experiments.md) | 전체 후보 2사례 실행 | 대체 — 현재 목표는 TASK_069 |
| [008](TASK_008_evaluate_results.md) | 실제 순위 평가 | TODO — TASK_069 B6에서 수행 |
| [009](TASK_009_compare_with_paper.md) | 논문 표 4 비교 | TODO — TASK_069 B7에서 차이 중심으로 수행 |
| [010](TASK_010_supplementary_artifacts.md) | 공식 전처리·비교 자료 조사 | DONE |
| [011](TASK_011_summary_output_directory.md)~[015](TASK_015_install_openai_embeddings.md) | 요약 경로, Chroma·lxml·embedding 어댑터 설치 | DONE |
| [017](TASK_017_scope_rca_only.md) | RCA 범위 전환 | DONE |
| [018](TASK_018_author_clarifications.md) | 저자 문의 | 진행 — 발송 여부 확인 필요 |
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
| [040](TASK_040_d03_original_graph_protocol.md)·[041](TASK_041_d04_original_evaluation_protocol.md) | D03 그래프 규약, D04 평가 규약 | DONE — D03은 TASK_069 B3에서 재결정 |
| [042](TASK_042_real_prompt_capacity.md)·[045](TASK_045_validate_context_81920.md) | D05 문맥 용량 → 81,920 | DONE |
| [043](TASK_043_log_encoding_diagnosis.md) | D06 로그 UTF-8 처리 | DONE |
| [044](TASK_044_select_two_rca_cases.md) | 두 사례 선택 (PR 20211203, CC 20231207) | DONE |
| [046](TASK_046_real_rca_integration.md)~[048](TASK_048_resolve_pc_memory.md) | 전체 후보 통합, D07 반복 생성, D08 메모리 | 보류 |
| [049](TASK_049_local_resource_optimization.md) | LLM prompt cache 설정 | DONE |
| [050](TASK_050_oracle30_matmcd_run.md)~[052](TASK_052_domain_generation_repetition.md) | 정답 포함 30 Pod 실행 | DONE — **조건부 분석 전용, 주 실험 제외** |
| [053](TASK_053_oracle30_result_report.md) | 30 Pod 결과 분석 보고서 | DONE |
| [054](TASK_054_github_setup_update.md) | GitHub 업데이트 (`3fe751c`) | DONE |

삭제(2026-10-18, `2f0d66a`에 보존): 미팅·발표 자료 Task 054(교수님 보고 기획)·055·057~068, 저자 문의 목록 작업 056(TASK_018에 통합), 10월 2일 브리핑, 시점 스냅샷 문서 4개(`TASK_STATUS_20260926`, `RCA_READINESS`, `RCA_REBOOT_RETEST`, `LOCAL_COMPLETION_PROPOSAL`). 016은 이전 범위 정리에서 삭제했으며 번호를 재사용하지 않는다.
