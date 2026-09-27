# MATMCD RCA 로컬 실험 환경

**최신 상태(2026-09-27): PR 20211203의 잠정 정답 포함 30 Pod + Latency 개발 실험을 완료했다.** 로컬 Qwen3.5-4B Q5_K_M(non-thinking)·BGE-M3 환경에서 PC → 로그/RAG → MATMCD → RWR/평가를 연결했고, 설명 930개와 제약 판단 930개가 모두 정상 완료됐다. Pod 기준 잠정 정답 순위는 PC 4위, MATMCD 5위이며 Hit@5는 둘 다 1이다. [상세 결과 보고서](docs/RCA_ORACLE30_RESULT_REPORT_20260927.md), [실행 조건·결과](docs/RCA_ORACLE30_DEVELOPMENT.md), [완료 검증](docs/evidence/rca_oracle30_completion_audit_20260927.json).

**대상은 논문 §4.3·표 4의 마이크로서비스 근본 원인 분석(RCA)이다.** 완료된 실험은 정답을 미리 포함한 단일 사례의 조건부 개발 평가다. 논문과 모델·전처리·후보 수 등이 다르므로 논문 결과 재현이나 전체 후보 선별 성능을 입증하지 않는다. 원본 코드의 확인된 문제, 승인된 변경, 실패 이력과 미확정 조건은 별도로 보존한다. 유료 API는 사용하지 않았다.

사용자 요청에 따라 일반 인과관계 발견 실험의 전용 파일·외부 자산을 제거하고 TODO에서 제외했다. 범위 변경은 [TASK_017](tasks/TASK_017_scope_rca_only.md), 공식 제외 목록은 [scope.json](configs/scope.json)에 기록한다.

**전체 후보 실험의 준비 범위는 PR 20211203과 CC 20231207의 2개이며, 이 범위의 실행은 아직 미완료다.** 전체 후보 PC의 메모리 부족 등 과거 차단 기록은 [Task 대조](docs/TASK_STATUS_20260926.md)에 남아 있다. 이후 승인된 30 Pod 개발 실험은 별도 프로필로 완료했으며 CC·RE·반복 실험은 실행하지 않았다. 선택 범위와 보존 정책은 [TASK_044](tasks/TASK_044_select_two_rca_cases.md), 현재 작업별 상태는 [Task 목록](tasks/INDEX.md)을 따른다. 아래 날짜별 연결·설치 기록은 당시 상태를 보존한 이력이다.

## 문서

- [30 Pod 개발 실험 상세 결과·논문과 다른 이유](docs/RCA_ORACLE30_RESULT_REPORT_20260927.md)
- [30 Pod 실행 프로필·결과·부모 실행 계보](docs/RCA_ORACLE30_DEVELOPMENT.md)
- [설명 단계 presence_penalty 변경·검증 기록](docs/RCA_DOMAIN_SAMPLING.md)
- [RCA 재현 명세](docs/REPRODUCTION_SPEC.md)
- [외부 자산·모델·출처](docs/ASSETS.md)
- [공통 Python 환경과 점검 이력](docs/ENVIRONMENT.md)
- [현재 Blocker와 원본 조건 차이](docs/ORIGINAL_LOCAL_ISSUES.md)
- [문제 발생 시 재확인할 위험](docs/FOLLOW_UP_RISKS.md)
- [RCA 준비·실행·평가 절차](docs/RUNBOOK.md)
- [승인된 임시 RCA 전처리 명세](docs/PROVISIONAL_RCA_PREPROCESSING.md)
- [임시 입력 5개 생성·검증 결과](docs/PROVISIONAL_RCA_PREPROCESSING_RESULT.md)
- [승인된 임시 Qwen 로컬 환경·현재 non-thinking](docs/LOCAL_LLM.md)
- [승인된 BGE-M3 로컬 임베딩·인공 검색 검증](docs/LOCAL_EMBEDDING.md)
- [작업 현황과 TODO](tasks/INDEX.md)
- [현재 RCA 실행 준비 점검](docs/RCA_READINESS.md)
- [입력 연결·공식 로더 검증](docs/RCA_INPUT_CONNECTION.md)
- [공개 평가 함수·정의](docs/RCA_METRIC_ADAPTER.md)
- [공식 장애 시나리오 조사](docs/RCA_SCENARIO_EVIDENCE.md)
- [RCA 결정·승인 상태와 다음 작업](docs/RCA_DECISIONS.md)
- [D03/D04 저자 일괄 문의 준비 — 미발송](docs/AUTHOR_QUESTIONS_D03_D04.md)

## 경로

| 위치 | 역할 |
|---|---|
| official/matmcd/ | 공식 RCA 작업용 부분집합. 승인된 6개 파일 제외, 남은 37개 파일의 원본 바이트 보존 |
| configs/ | 외부 루트·RCA 입력·출처·활성 범위 |
| scripts/ | 공통 환경 설치·RCA 다운로드·링크·점검 |
| docs/ | RCA 명세·차이·검증 증거 |
| tasks/ | 번호 기반 작업 상태 |

Git 프로젝트는 E:/연구/MATMCD, 외부 자산은 E:/연구/MATMCD_DATA다. configs/paths.json 한 곳에서 외부 경로를 관리한다.

저자 소스는 D2I-Group/matmcd 커밋 ef2c3ecad0f5ddb9c3d20a8523c2c1043d213190에 고정한다. 남은 공식 파일의 과학적 동작은 변경하지 않았다. 전체 ZIP·논문·저자 소개 자료와 과거 공통 점검은 출처 이력으로 보존한다. 공식 README에는 제외한 실험 안내가 남을 수 있으므로 현재 실행 안내는 RUNBOOK을 따른다.

origin은 https://github.com/j9-jay/MATMCD.git 이며 .git과 기존 이력을 유지한다.

## 2026-09-26 후속 연결·검증

[로컬 실행기](scripts/run_local_rca.py)를 구성하여 원본 로그 요청·Qwen/BGE·D03 A·D04 RWR/평가 경로를 연결했다. 원본 함수/파서를 보존한 연결 검사 21개, 로컬 메시지·한도/응답 차단 검사 17개가 통과했다. 실제 생성·RCA 성능 검증과는 다르며 **실행 프로필은 아직 차단 상태**다. [구현·호출 규모·한계](docs/LOCAL_RCA_RUNTIME.md).

- [D05 문맥 검증 완료](docs/RCA_CONTEXT_CAPACITY.md): 사용자 승인으로 문맥만 81,920으로 확대했다. GPU all/FP16·전체 Pod 유지, 278/278 입력 수용 및 최대 입력 65,073토큰의 실제 응답 807토큰 생성 PASS(약 60.57초). 준비 로그의 문맥 차단은 해결됐고 RAG/그래프/전체 통합 검증은 남아 있다. [TASK_045](tasks/TASK_045_validate_context_81920.md).
- [D06 로그 UTF-8](docs/RCA_LOG_ENCODING.md): 실패 파일에만 손실 없는 읽기를 적용하고 선택 필드/프롬프트가 정상일 때만 사용하는 A안 승인. 인공 10개 검사 및 실물 실패 23쌍 처리 PASS. 당시 기본 성공 403과 합쳐 426쌍 전부 준비했다. 현재 두 사례는 기본 258 + 승인 처리 20 = 278쌍이며 선택 프롬프트 오류 바이트는 0개다.
- TASK_027: 현 OS 설정 유지, 현재 baseline과 실행 전후 변화 기록 방침 완료. 업데이트 중지·rollback은 하지 않았다.
- 실제 2사례 실행·평가·비교는 준비 차단 해결 이후다. 이전 실행 승인과 D01~D04, 모델 선택을 다시 요청하지 않는다.

## 설치·준비 이력

- WSL Ubuntu / Python 3.11.13과 패키지 201개 유지. 공식 140개 pin 및 승인된 호환 조합을 바꾸지 않았다.
- LEMMA-RCA 공개 코드의 5개 날짜에 해당하는 로그·메트릭 ZIP 10개와 공식 전처리 자료 확보.
- 2026-09-24: 승인된 임시 전처리로 metric CSV 5개 생성·검증 완료. 외부 processed_data/lemma_rca_provisional_v1에 보관하며 저자 동일성은 UNCONFIRMED다. 모든 후보 pod가 유지됐고 로그 쌍 누락은 별도 기록했다.
- RCA 코드·공통 agent·RAG·RWR 및 외부 작업공간 연결 유지.
- 2026-09-24: Graphviz B안 설치·일반 사용자 PNG 검증 완료. 시스템 9개만 추가했고 기존 시스템·Python·공식 소스를 유지했다. A안의 저자 버전 확인·전환 검토는 [TASK_022](tasks/TASK_022_graphviz_author_version.md) TODO로 분리했다.
- 2026-09-25: TASK_032에서 임시 CSV 5개 실행 연결·공식 로더 PASS, 정확한 원본 로그 647쌍(약 44.1GB) 연결 완료. 후보 pod·원본 로그 바이트·공식 소스는 보존했다. TASK_033은 공개 지표 함수 11개 점검 PASS, TASK_034는 공식 시나리오·추가 CC 원자료 조사를 완료했다.
- D01은 전체 후보 유지·로그 부재 명시, D02는 원본 전체 읽기·대표 3개 검증을 완료했다. D03 A안 공개 동작 보존과 D04 PR 잠정 평가/CC 점수 보류·단일 호출/RNG·집계 방침도 [설정](configs/rca_protocol.json)과 준비 코드에 반영했다. 실제 순차 읽기/요약 전달·Qwen/BGE·RWR/평가 호출 연결은 TASK_024에 남는다. 원본 CSV·API·CC 정확 정답은 후속 확인한다. CODE-01은 웹 경로를 사용할 때의 조건부 항목이다.
- 승인된 Qwen3.5-4B Q5_K_M / llama.cpp를 **non-thinking**으로 전환하고 [TASK_028](tasks/TASK_028_local_re_response_format.md)의 단회 RE 형식 보정을 적용했다. 최신 인공 검증은 산술·Yes/No·RE 양방향 모두 PASS다. RE 원문 2개 중 1개만 경계를 정규화했으며 내용·확률·공식 파서는 보존했다. [TASK_023](tasks/TASK_023_local_qwen_thinking_setup.md)의 설치·인공 점검은 완료했다. 이전 [thinking](tasks/TASK_026_local_thinking_output_budget.md)/[non-thinking](tasks/TASK_029_local_nonthinking_verification.md) 실패는 유지하며, [TASK_024](tasks/TASK_024_local_rca_integration.md)의 실제 연결과 [TASK_025](tasks/TASK_025_original_api_validation.md)의 후속 API 검증은 남아 있다.
- 로그 활용 경로, RWR 그래프 선택, 실제 순위의 평가 연결, 모델·전처리·집계 조건 확인도 남아 있다.
- 2026-09-25: [TASK_030](tasks/TASK_030_local_bge_m3_embedding.md)의 BGE-M3 dense CPU/FP32/batch 1 설치·인공 검색 검증 PASS. 웹 top-10 및 LlamaIndex top-2와 기존 분할·저장/재로드를 유지했다. 기존 Python 201개는 보존하고 별도 경로에 로더 2개를 추가했다. 원본 ada-002와 다른 임시 조건이며 실제 RCA에 자동 연결하지 않았다.
- 사용자가 준비 완료 확인 후 RCA 실행을 요청했다. 동일 실행 승인을 다시 요구하지 않는다. TASK_007은 기술적 준비 미완료로 BLOCKED이며 TASK_008 평가·TASK_009 비교는 실제 결과가 없어 TODO다. 실물 준비 점검은 TASK_031이다.
- 모델 검증 전 WSL 자동 업데이트 이력과 과거 OS snapshot 대비 패키지 175개 차이를 확인했다. 공식 코드·Python 가상환경은 보존됐으며 OS 차이와 후속 방침은 [TASK_027](tasks/TASK_027_wsl_system_drift.md)에 기록했다.
