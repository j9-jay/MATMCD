# RCA 작업 현황

**GitHub 업데이트:** [TASK_054](TASK_054_github_setup_update.md)에서 현재 설정·구현·문서·검증 기록을 `origin/main`에 게시한다. 실험 자산은 MATMCD_DATA에 유지한다.

**2026-09-27 결과 분석 보고서 작성 완료:** [TASK_053](TASK_053_oracle30_result_report.md) DONE. [상세 보고서](../docs/RCA_ORACLE30_RESULT_REPORT_20260927.md)에 목적·실제 조건·논문 차이·전체 순위·원인별 증거/가설을 정리했다. MongoDB 장애 근거의 RAG 미전달, 공개 프롬프트의 첫 쌍/방향 문제, 후보 축소로 제외된 시나리오 경로를 확인했다. 추가 실험·코드/조건 교정은 하지 않았다.

**최종 개발 실행 상태(2026-09-27 05:06 KST 검증): TASK_050·051·052 DONE.** PR 20211203의 잠정 정답 포함 30 Pod + Latency MATMCD가 04:43:06 KST에 완주했다. 설명930/930·제약930/930·보정 PC/RWR·평가 완료, 실패0·환경 변경0. Pod 기준 정답 순위 PC4위/MATMCD5위, Hit@5는 모두1. 실행 `20260926T143904740470Z`, 소요 약5시간4분(재사용 부모 단계 제외). [최종 결과](../docs/RCA_ORACLE30_DEVELOPMENT.md), [전수 검증](../docs/evidence/rca_oracle30_completion_audit_20260927.json), [옵션 기록](../docs/RCA_DOMAIN_SAMPLING.md).

**현재 승인된 30 Pod 한 사례의 완주 작업에는 남은 차단 항목이 없다.** 원래 전체 후보 두 사례의 TASK_007~009·046~048과 저자 문의/API 비교 등은 별도 범위로 상태를 유지한다. CC·RE·새 사례·반복 실험은 이번 완료에 포함하지 않는다. 이 결과는 잠정 정답을 미리 포함한 단일 개발 평가이며 논문 결과 재현/전체 후보 선별 성능/통계적 유의성의 근거가 아니다. 아래 과거 시점의 실행 중·승인 대기·예상 시간은 이력이다.

완료 검증 후 `matmcd-30-pod` 자동 확인을 앱 도구로 **PAUSED** 처리했다. 실행 프로세스와 llama-server도 정상 종료를 확인했다. 추가 실행은 시작하지 않았다.

**최신 상태(2026-09-26 23:41 KST): TASK_052 적용·실제 재실행 중.**3건 진단 모두stop, 실패 요청8192→1533토큰. 새 실행`20260926T143904740470Z`에서 설명1/930부터presence1.5로 재생성 중이며4개 완료·1개 진행·실패0을 확인했다. 첫2개 실제 요청은 이전과presence_penalty만 다르다. 기존 PC·로그/RAG 유지, 제약 판단은presence0이다.10분 heartbeat ACTIVE. [변경 기록](../docs/RCA_DOMAIN_SAMPLING.md). 아래 승인 대기 및 이전 실행 중 표시는 과거 스냅샷이다.

**최신 자동 확인(2026-09-26 23:16 KST): 실행 중단·승인 대기.** MATMCD 설명40개 완료 후41번째가 `non-parametric`을1845회 반복하며8192 출력 한도에 도달했다. 입력 문맥은 수용됐으며 환경 변경·OOM이 관측된 실패가 아니다. 현재 관련 실행 프로세스는 없다. [TASK_052](TASK_052_domain_generation_repetition.md)에 설명 단계 presence_penalty0→1.5의 제한된 검증·통일 적용안을 기록했다. 새 설정은 미적용이다. 아래 실행 중/예상 시간은 실패 전 스냅샷이다.

**현재 진행(TASK_050):** PR 20211203·30 Pod + Latency·51,529행의 원본 PC/RWR가 691.12초에 완료됐다. 잠정 정답 Pod 순위4위(KPI 포함5위)。 로그20/20·RAG 생성 완료, [TASK_051](TASK_051_rag_format_continuation.md)의 응답 경계 보정 후 MATMCD 930쌍 설명을 실제 생성 중이다. 첫10개 모두 정상 종료·평균21.09초. 현재 실행 ID는 `20260926T135543690567Z`이며 최종 MATMCD 순위는 아직 없다. [작업 기록](TASK_050_oracle30_matmcd_run.md). 아래 전체 후보 실행의 차단·캐시 전용 작업은 보존된 이전 범위의 기록이며 30개 개발 실험과 구분한다.

**최신 범위:** 유료 API/외부 서버 제외. 사용자는 TASK_049 진행 승인 뒤 **스크립트 로직 변경 제외·캐시 설정만 적용**하도록 좁혔다. [TASK_049](TASK_049_local_resource_optimization.md)는 서버/요청 prompt cache 활성화와 SDK 17개 검사까지 DONE이다. 별도 RAM cache=0·단일 슬롯을 유지하며 PC 자료구조·재개·실행 순서 변경은 미적용이다. 아래 47개 Task 감사는 새 Task 작성 전 스냅샷이며, 전체 RCA 준비 완료나 재개로 표시하지 않는다.

2026-09-26 KST 기준. 현재 대상은 논문 §4.3·표 4의 마이크로서비스 RCA다. 일반 인과관계 발견 실험은 사용자 지시로 작업 범위와 TODO에서 제외했다.

**현재 실행·평가 대상: PR 20211203, CC 20231207.** TASK_044로 PR 20220606도 추가 제외했다. 데이터·기존 5개/3개 준비 이력은 보존하며 현재 활성 입력은 2개 CSV·278쌍 로그(약 8.81GB)다. 개별 사례 내부 조건은 유지한다.

DONE은 해당 조사·설치·정리 작업의 완료이며 RCA 전체 완료율을 뜻하지 않는다. **이전 전체 후보 실행 이력:** 새 로그44개 후 중단, 전체 후보 PC는OOM으로 종료했고 완주한 전체 후보 RCA 결과는 없다. 현재 30개 실행의 상태와 실제 순위는 이 문서 상단 및 TASK_050을 따른다. [47개 Task 상세 대조(이전 스냅샷)](../docs/TASK_STATUS_20260926.md).

사용자가 준비 완료 확인 후 RCA 실행을 요청했다. 실행 승인은 확인했으며 반복 요청하지 않는다. TASK_044로 두 사례를 선택했고, 후속 사용자 지시에 따라 TASK_045에서 문맥만 81,920으로 확대해 검증을 완료했다. 준비 로그의 D05 용량 문제는 해결됐으며 전체 통합 검증은 남아 있다. 전체 실행의 기존 조건부 승인은 유지한다. 현재 차단은 새 실행 승인 부족이 아니라 PC 실패와 로그/RAG 통합 미완료다. [최신 준비 점검](../docs/RCA_READINESS.md)을 참고한다.

| Task | 목적 | 상태 |
|---|---|---|
| [001](TASK_001_paper_analysis.md) | 논문·부록 분석 이력 | DONE |
| [002](TASK_002_official_code_setup.md) | 공식 소스 확보·출처 보존 | DONE — 현재 부분집합 정책은 TASK_017 |
| [003](TASK_003_dataset_download.md) | RCA 저자 원본 입력 확보 | BLOCKED — 원본 CSV·정확 전처리 동일성 미확인, 임시 준비는 TASK_020 완료 |
| [004](TASK_004_environment_setup.md) | 공통 실행 환경 구성 | DONE — Graphviz B안 포함 로컬 의존성 검증, 저자 동일성은 별도 관리 |
| [005](TASK_005_model_setup.md) | RCA 모델·서비스 접근 준비 | BLOCKED — API 접근·모델 snapshot 조건 |
| [006](TASK_006_paths_and_preflight.md) | 외부 경로 연결·사전 점검 | DONE |
| [007](TASK_007_run_original_experiments.md) | Product Review / Cloud Computing RCA 실행 | BLOCKED — 두 사례 278쌍과 문맥 검증 완료. 전체 RAG/그래프 통합 검증 후 실행 |
| [008](TASK_008_evaluate_results.md) | RCA 실제 순위·MAP@5/10·MRR 평가 | TODO |
| [009](TASK_009_compare_with_paper.md) | 논문 표 4와 비교 | TODO |
| [010](TASK_010_supplementary_artifacts.md) | 공식 전처리·비교 자료 조사 | DONE |
| [011](TASK_011_summary_output_directory.md) | CODE-03 요약 저장 경로 준비 | DONE |
| [012](TASK_012_chromadb_compatibility.md) | DEP-01 호환 조합 검증 | DONE |
| [013](TASK_013_install_chromadb.md) | DEP-01 Chroma 설치·로컬 점검 | DONE |
| [014](TASK_014_install_lxml.md) | DEP-02 lxml 설치·로컬 점검 | DONE |
| [015](TASK_015_install_openai_embeddings.md) | DEP-03 embedding 어댑터 설치·로컬 점검 | DONE |
| [017](TASK_017_scope_rca_only.md) | RCA 범위 전환·전용 파일 정리 | DONE — 삭제·원본/환경 보존·참조 검증 통과 |
| [018](TASK_018_author_clarifications.md) | RCA 미확정 조건·로컬 선택 일괄 저자 확인 | TODO — 목록·메일 초안 준비, 미발송 |
| [019](TASK_019_provisional_rca_preprocessing_plan.md) | 실제 입력 점검·임시 전처리 구체안 | DONE — 명세·설정·실물 근거·원본 보존 검증 완료 |
| [020](TASK_020_apply_provisional_rca_preprocessing.md) | 승인된 임시 전처리 구현·입력 생성 | DONE — CSV 5개 생성·별도 검증 통과, 저자 동일성 UNCONFIRMED |
| [021](TASK_021_install_system_graphviz.md) | DEP-04 Graphviz B안 설치·PNG 검증 | DONE — 시스템 9개 추가, 기존 시스템·Python·공식 소스 보존 |
| [022](TASK_022_graphviz_author_version.md) | Graphviz A안: 저자 버전 확인·전환 검토 | TODO — B안과 분리, 실제 전환은 자료 확인·변경 승인 후 |
| [023](TASK_023_local_qwen_thinking_setup.md) | Qwen3.5-4B Q5_K_M 로컬 환경 | DONE — non-thinking·GPU·인공 응답 형식 검증 완료, 실제 통합은 024 |
| [024](TASK_024_local_rca_integration.md) | 로컬 모델·로그의 RCA 연결 | BLOCKED — D07 단일 검증 PASS, 새 로그44개 후 실행 중단; PC는 D08 OOM 차단 |
| [025](TASK_025_original_api_validation.md) | 로컬 성과 이후 원본 API 조건 검증 | TODO — 호출 범위·비용 승인 후 |
| [026](TASK_026_local_thinking_output_budget.md) | LOCAL-01 thinking 생성 한도·원본 형식 검증 | DONE — 8192 실패 분석 보존. 사용자는 4096안 대신 029 non-thinking 선택 |
| [027](TASK_027_wsl_system_drift.md) | WSL 자동 업데이트·OS baseline 검토 | DONE — 현재 805개 baseline 기록, OS 설정 유지·실행 전후 변화 검사. 과거 175개 차이 이력 보존 |
| [028](TASK_028_local_re_response_format.md) | LOCAL-02 RE 응답과 원본 파서 호환 | DONE — 승인된 단회 경계 보정·원문 보존·오프라인 22개/인공 추론 PASS |
| [029](TASK_029_local_nonthinking_verification.md) | Qwen non-thinking 전환·원본 형식 검증 | DONE — 보정 전 FAILED 이력 보존, 후속 028에서 형식 보정 검증 완료 |
| [030](TASK_030_local_bge_m3_embedding.md) | BGE-M3 dense CPU 임베딩·두 검색 연결 검증 | DONE — FP32/batch 1, 기본 분할/top-k/저장·재로드 PASS, 실제 RCA 제외 |
| [031](TASK_031_rca_readiness_audit.md) | RCA 실행 준비 실물 점검·조건부 실행 요청 반영 | DONE — 판정 NOT_READY, 실행은 007 BLOCKED |
| [032](TASK_032_connect_provisional_rca_inputs.md) | 임시 CSV·정확한 원본 로그 연결 | DONE — CSV 5개 공식 로더 PASS, 로그 647쌍/44.1GB, 입력·공식 소스 보존 |
| [033](TASK_033_rca_metric_adapter.md) | 공개 RCA 지표 함수 분리·검증 | DONE — 원본 공식 유지, 11개 검사 PASS; 실제 평가는 008 |
| [034](TASK_034_official_scenario_evidence.md) | 공식 장애 시나리오·추가 CC 원자료 조사 | DONE — PPTX 5개와 원자료 설정 확인; 정확한 CC 정답은 미확정 |
| [035](TASK_035_missing_log_policy.md) | 누락 pod 로그의 처리 정책 | DONE — 후보 유지·부재 명시 승인, 근거 manifest 5개·오프라인 44개 검사 PASS; 실제 통합은 024 |
| [036](TASK_036_large_log_reading.md) | 대용량 로그 읽기 방식 | DONE — 원본 전체 읽기/프롬프트 생성 3개 PASS, 최대 RSS 2.111GiB·스왑 0; 실제 통합 024 |
| [037](TASK_037_d01_log_coverage_investigation.md) | D01 파싱 오류 가능성·원시 로그 범위 재검증 | DONE — 로컬 매칭 오류 미발견; 공개 metric/log 범위 불일치 확인, D01 정책은 미적용 |
| [038](TASK_038_d01_public_case_research.md) | D01 공개 이슈·외부 재현 사례 조사 | DONE — 직접 해결 이슈 미발견; 같은 CC 날짜의 서비스 집계 사례 확인, D01 정책 미적용 |
| [039](TASK_039_select_three_rca_cases.md) | 실행·평가를 사용자 지정 세 사례로 제한 | DONE — 활성 매핑·공통 선택 적용, 범위 39개/D01 33개 검사 PASS; 원본 자료 보존 |
| [040](TASK_040_d03_original_graph_protocol.md) | D03 원본 그래프·RWR 동작 대조 | DONE — A안 확정, 공개 동작·단계별 그래프 보존 및 별도 저자 문의 준비 |
| [041](TASK_041_d04_original_evaluation_protocol.md) | D04 원본 정답·순위·평가 규칙 | DONE — PR 잠정/CC 점수 보류·단일 호출/RNG·집계 방침과 평가 준비 코드 검증; 정확한 CC 정답은 018/008 |
| [042](TASK_042_real_prompt_capacity.md) | D05 실제 GGUF 프롬프트 길이 | DONE — 현재 81,920/all에서 278개 모두 수용, 최대 필요량 73,266. 실제 최대 입력 생성은 045 PASS |
| [043](TASK_043_log_encoding_diagnosis.md) | D06 원본 UTF-8 실패 진단·승인 어댑터 | DONE — A안 실물 23쌍 PASS, 기본 읽기 403과 합쳐 426쌍 준비; 선택 프롬프트 오류 0 |
| [044](TASK_044_select_two_rca_cases.md) | 실행·평가를 PR 20211203/CC 20231207로 제한 | DONE — 278개 준비본 검증·D01 27개/평가 25개 PASS. 후속 문맥 검증은 045 완료 |
| [045](TASK_045_validate_context_81920.md) | 문맥만 81,920으로 확대·최대 입력 실제 생성 검증 | DONE — GPU all/FP16·전체 Pod 유지. 278/278 수용, 최대 입력 65,073·출력 807토큰/60.57초 |
| [046](TASK_046_real_rca_integration.md) | 전체 입력 PC/RWR·실제 로그/RAG 통합 검증 후 전체 실행 연결 | BLOCKED — 새 로그44개 후 중단·RAG 미도달; PC는 D08 OOM으로 종료 |
| [047](TASK_047_resolve_generation_repetition.md) | D07 실제 로그 요약의 반복 생성 해결 | BLOCKED — A안 단일 검증 PASS. 새 로그44개 후 프로세스 종료, 45번째 응답 미저장·원인 미확인 |
| [048](TASK_048_resolve_pc_memory.md) | D08 원본 PC 메모리 부족 | BLOCKED — WSL OOM; swap 확대안 별도 결정 대기 |
| [049](TASK_049_local_resource_optimization.md) | 로직 변경 없이 LLM 캐시 설정 | DONE — 서버/요청 활성화·SDK 17개 PASS. PC/재개 로직 미변경, 실제 가속률 미측정 |
| [050](TASK_050_oracle30_matmcd_run.md) | 정답 포함 30 Pod 한 사례 PC→MATMCD→RWR 개발 실험 | DONE — 설명930·제약930·그래프/평가 완료. Pod 순위 PC4위/MATMCD5위 |
| [051](TASK_051_rag_format_continuation.md) | RAG 응답 경계 보정·완료 단계 연결 | DONE — 본문 보존·부모 해시 검증, 후속 MATMCD 완주 |
| [052](TASK_052_domain_generation_repetition.md) | 설명 반복 실패 진단·승인된 presence1.5 적용 | DONE — 진단3개 및 새 설명930개 정상 종료, 제약presence0 유지 |
| [053](TASK_053_oracle30_result_report.md) | 완료 결과와 논문 차이 상세 분석 보고서 | DONE — 근거 전달·후보 경로·프롬프트·그래프/순위 분석, 원인 가설과 사실 구분 |
| [054](TASK_054_github_setup_update.md) | 현재 로컬 RCA 구성과 결과 기록 GitHub 업데이트 | IN_PROGRESS — 게시 대상·자산/인증정보 제외 확인, commit/push 진행 |

작업 번호는 이력 식별자로 유지한다. 30 Pod 한 사례 개발 실행·평가는 TASK_050에서 완료했다. 아래 전체 후보 실행·평가·논문 비교는 별도 미완료 범위다.

## 원래 전체 후보 범위의 남은 차단 항목

| ID | 남은 일 | 관련 Task |
|---|---|---|
| INPUT-02 | 원본 CSV·전처리 동일성은 저자 후속 확인. 활성 CSV 2개·정확한 로그 278쌍 경로 준비. 실제 전체 로그 읽기의 D06은 승인 방침으로 해결 | 003/018 후속, 043 DONE |
| ACCESS-01 | 원본 API는 후속 025. 로컬 Qwen/BGE 연결 코드는 구성했고 실제 생성 포함 통합 검증이 남음 | 005/025 후속, 024 현재 준비 |
| D05 — 준비 로그 해결 | 문맥 81,920/all/FP16에서 278/278 수용, 최대 입력 65,073토큰의 실제 생성 PASS. 후속 RAG/그래프 입력은 024에서 확인하며 호출 직전 용량 검사를 유지 | 042/045 DONE; [구체안](../docs/RCA_CONTEXT_CAPACITY.md) |
| D06 — 해결 | 엄격한 UTF-8 읽기 실패 23쌍에 승인 A안 적용 완료. 전체 426쌍 준비, 원본·실패/저자 조건 차이 보존 | 043 DONE; [결과·영향](../docs/RCA_LOG_ENCODING.md) |
| D07 | A안 승인·동일 요청 단일 검증 PASS. 새 로그44개 후 프로세스 종료. RAG 미도달·종료 원인 미확인 | 046/047; [원인·검증](../docs/RCA_GENERATION_REPETITION.md) |
| D08 | PR 전체 PC 계산 중 WSL RAM/swap 소진·OOM. 전역 swap 확대/재시작 미승인 | 046/048; [자원 대안](../docs/RCA_PC_MEMORY.md) |
| 실제 통합 검증 | 원본 worker → 로그 요약 → RAG → Agent → PC/RWR/평가 연결 코드 구성. 최대 로그 요약 1건 생성은 완료했지만 RAG·그래프·전체 실행은 미검증. CC 점수는 계속 보류 | 024/007/008; [실행기·호출 규모](../docs/LOCAL_RCA_RUNTIME.md) |
| CODE-01 (조건부) | 웹 수집 경로를 선택할 때만 검색 응답 키 불일치를 처리. RCA 공통 필수 Blocker가 아님 | 024; 저자 확인 018 |

기존 승인된 전처리·모델·보정·설치 선택과 실행 요청은 반복 승인받지 않는다. 새 과학적 조건 변경이 실제로 필요할 때만 근거·영향을 설명하여 결정받는다. 누락 입력이나 코드 차이를 문서 분류 변경만으로 해결 처리하지 않는다.

2026-09-26 D03은 사용자 선택 A안, D04는 제안한 방침으로 구성했다. [승인 프로필](../configs/rca_protocol.json), [23개 인공 검사](../docs/evidence/rca_approved_protocol_20260926T055338403913Z.json), [저자 일괄 문의 준비](../docs/AUTHOR_QUESTIONS_D03_D04.md). 같은 선택을 다시 묻지 않는다. TASK_024 연결 코드와 당시 426쌍의 입력 준비를 완료했다. TASK_044의 현재 두 사례는 그중 278쌍을 사용한다. D06과 준비 로그의 D05 용량 문제는 해결했다. TASK_045에서 최대 입력 생성 1건을 완료했으며 실제 RAG/그래프를 포함한 전체 통합 검증과 RCA 실행은 남아 있다. CC 정답 미확정은 CC 점수/전체 집계 보류로 처리하며 예측 실행 자체의 승인 대기로 두지 않는다.

## 원래 전체 후보 범위의 준비 및 미완료 이력

- 공식 RCA 소스 37파일, Python 201개와 승인 호환 조합, Graphviz B안, Qwen non-thinking, BGE-M3 CPU FP32/batch 1 준비를 유지한다.
- 승인된 임시 CSV 2개, 정확한 로그 278쌍, Pod 후보 414개·부재 표시 136개·KPI 2개를 대상으로 한다. 과거 5개/647쌍 및 3개/426쌍 준비는 각 Task의 이력이며 현재 실행 범위가 아니다.
- D01 후보 유지/부재 명시, D02 순차 전체 읽기, D03 공개 동작 A, D04 잠정 평가/CC 점수 보류는 확정됐다. 같은 선택을 다시 승인받지 않는다.
- 로컬 실행기·요청/원문 기록·D03/D04 연결 코드를 구성했다. 연결 21개, 호출 보호 17개, 기존 RE 22개 인공/오프라인 검사는 실제 성능 결과가 아니다. [현재 구현과 검증](../docs/LOCAL_RCA_RUNTIME.md).
- D06 손실 없는 읽기 A안의 이전 실물 23쌍 검증을 포함해 현재 278쌍이 준비됐다. D05는 사용자 승인으로 문맥만 81,920으로 확대했고 입력 수용 및 최대 입력 실제 생성에 성공했다. 새 로그44개 후 실행 중단 원인·재개 준비와 실제 RAG/그래프의 통합 검증이 남았다. 준비 완료 전 TASK_007 실제 실행을 시작하지 않는다.
- 실제 결과가 생기면 TASK_008/009를 진행한다. CC 정답 미확정은 두 후보 순위 보존과 점수/전체 집계 보류로 처리한다.

저자 문의 TASK_018, 원본 API TASK_025, 저자 Graphviz A안 TASK_022는 별도 후속이다. 원본 CSV/전처리·API·정확 CC 정답을 확보하지 못했다는 사실은 계속 명시하되, 이미 승인된 임시 경로를 다시 승인받는 이유로 사용하지 않는다. 메일은 미발송이다.

최초 조사·실패·설치 수치와 시점별 변경 내용은 각 Task와 근거 문서에 보존한다. 이 INDEX는 현재 상태를 나타내며 이전의 '미연결/미승인' 문구를 현재 상태로 반복하지 않는다. RISK-001~003은 [기록된 조건](../docs/FOLLOW_UP_RISKS.md)이 실제 발생할 때만 재검토한다.

## 이전 검사 이력

아래는 TASK_045 이전 설정·범위에서의 기록이며 현재 상태는 위 표를 따른다.

2026-09-26 [최종 준비 무결성 확인](../docs/evidence/rca_preparation_final_20260926T073506481692Z.json): 공식 37파일·426개 프롬프트/승인 이력·스크립트 54개 구문·JSON 80개·문서 링크 478개 PASS. 현재 16,384/all과 실행 보류 유지, 서버 종료·실제 실행 폴더 없음 확인. 준비 자료의 무결성 검사이며 전체 실험 준비 완료 판정은 아니다.

2026-09-26 재부팅 후 [D05 재검증·대안 비교](../docs/RCA_REBOOT_RETEST.md) 완료: 현재 서버 정상 구동, 426개 토큰/판정 동일·207개 초과. 설정 변경·RCA 실행 없이 4개 후속 후보를 정리했다. TASK_042의 차단 상태는 유지한다.
