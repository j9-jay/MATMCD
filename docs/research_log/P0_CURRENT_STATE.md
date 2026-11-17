# P0 현황 파악 보고서

- 작성일: 2026-11-18
- 범위: 읽기만 했다. 코드, 설정, 결과 파일은 바꾸지 않았다. 평가 데이터의 사례 원본(메트릭, 로그, trace)은 열지 않았다. 기존 문서에 이미 적혀 있던 집계 수치와 사례 설명만 읽었다.
- 표기: **확인됨** = 원문을 직접 읽음(출처 표시). **추정** = 근거는 있으나 원문으로 확정하지 못함. **확인 불가** = 이유 표시.
- 상태: 사용자 검토 대기 (P0-G1)
- 주의 (2026-11-18 추가): 사용자 결정 K12에 따라 MATMCD 재현 결과(0.407, LEMMA-RCA 30 Pod 결과 등)는 앞으로 비교와 보고에 쓰지 않는다. 이 보고서의 해당 수치는 P0 시점의 사실 기록으로만 남긴다.

---

## 0. 가장 중요한 발견 7가지

1. **0.407은 MATMCD 논문의 공식 기록이 아니다.** MATMCD를 논문과 다른 데이터셋(RCAEval RE2-OB)에, 논문과 다른 모델(Qwen3.5-4B)로 돌린 이 저장소의 값이다. MATMCD 논문에는 이 데이터셋의 수치가 없다.
2. **미팅 표에서 MATMCD(0.407)와 제안 방법(0.927)은 판단 경로가 달랐다.** MATMCD는 출력부 A(쌍별 판단 → 그래프 → 순위), 제안 방법은 출력부 B(근거를 모아 순위를 직접 출력)였다. 같은 출력부 A에서는 제안 방법이 0.502였다.
3. **기존 방법(v0)은 이미 RCA 답을 생성하고 RCA 점수(Avg@5)를 측정했다.** 미팅 표에는 검색 지표와 RCA 지표가 함께 있었다.
4. **교수님이 물은 숫자의 정체가 확인됐다.** "24"는 근거 개수, "754"로 들린 것은 단계별 개수 7·5·12, "4416"은 role_only의 4·4·16, "S1, S2 다음 S4"는 S3이 검색 없는 가설 단계라서였다. 이 값들을 왜 그렇게 정했는지의 **근거 기록은 없다.**
5. **한 번도 평가에 쓰지 않은 데이터가 있다.** RE2-OB 반복 3의 30사례다. 반대로 평가에 쓴 반복 2의 30사례는 방법을 바꿔 가며 세 번 평가했다.

6. **처음 계획의 주 실험은 "LEMMA-RCA에서 MATMCD와 1대1 비교, 지표는 MATMCD와 같은 MAP@10"이었다** (문서 B 9.1절). 조건도 같은 입력, 같은 후보 범위, 같은 LLM으로 맞추기로 했다. v0는 연산량 문제로 이 실험을 하지 못하고 확장 실험(RCAEval)만 했다. 교수님이 요구한 "공식 기록과 같은 경기장"은 처음 계획에 이미 있던 것이다.
7. **처음 계획의 "정답 evidence" 지표는 Indicator Hit@K였다** (문서 B 9.2절). 문서 B는 RCAEval이 root-cause indicator를 제공한다고 적었다. v0는 이것 대신 코드 규칙으로 만든 silver 근거를 썼다. RCAEval의 indicator 라벨이 실제로 어떤 형태인지는 이번에 확인하지 않았다.

---

## 1. P0-T1 지금까지의 실험 이력

출처: `tasks/TASK_070_state_aware_retrieval_experiments.md`, `docs/TASK070_HANDOFF.md`, `docs/EXPERIMENT_PLAN_TASK070.md`, `docs/RESEARCH_ROADMAP.md`, PR 목록 1~40.

### 1.1 흐름 (확인됨)

| 시기 | 내용 | 출처 |
|---|---|---|
| 2026-09 | MATMCD 논문을 LEMMA-RCA로 재현 시도. 30 Pod 부분집합(정답 Pod를 강제로 포함) 실행 | TASK_050~053, 미팅 자료 1절 |
| 2026-10-18 | 연구 재계획. 작은 공개 벤치마크 RCAEval RE2-OB로 전환, 방법을 "추론 상태 기반 근거 검색"으로 정의 | PR 1, RESEARCH_ROADMAP.md |
| 10-18~19 | 개발(v1). 출력부 A에서 제안 방법이 flat보다 낮자 출력부 B를 새로 만들고 주 출력부로 변경. 동결 후 평가 | TASK_070:110-134 |
| 10-25 | 감사. v1 개발이 30사례 중 앞 10사례(서비스 2개)만 썼음을 발견. v2 재개발, 재평가 | TASK_070:250-303 |
| 10-26~27 | v3. 근거 풀에 Online Boutique 정적 분석 위키 502단위 추가. 5단계 상태 설계. v1·v2는 무효 처리. 평가 | TASK_070:183-249 |
| 10-29 | 미팅 자료 작성 | PR 34~39 |

### 1.2 방법 이름과 뜻 (확인됨, 출처: 미팅 자료 "Ablation에서 검증하는 요소")

| 이름 | 내용 |
|---|---|
| none | 근거 없이 LLM만 |
| flat | 질의 하나로 유사도 상위 24개 |
| role_only | 근거 종류별 할당만: 구조 4 + 문서 4 + 관측 16 |
| state_fixed | 역할 + 5단계 추론 상태(규칙). v3의 제안 방법 |
| state_dynamic | state_fixed에서 가설 단계만 LLM이 결정. v1·v2에서는 제안 방법, v3에서는 참고 |
| pc_only | 데이터만으로 PC 그래프 |
| matmcd | MATMCD 방식을 이 데이터에 실행한 참고 기준선 |

### 1.3 두 가지 출력부 (확인됨, 출처: TASK_070:16-26, 115-116)

- **출력부 A**: 서비스 쌍마다 Yes/No 판단(156쌍) → 제약 PC → 그래프 → RWR로 순위. MATMCD와 같은 경로.
- **출력부 B**: 사례 하나에 근거 24개를 모아 LLM이 후보 서비스 12개의 순위를 직접 출력. 후보 순서를 바꿔 3회 반복해 평균.
- 출력부 B는 개발 중에 출력부 A에서 제안 방법이 flat보다 낮게 나온 뒤(0.298 vs 0.462) 새로 만들어 주 출력부로 정했다(2026-10-19 사용자 결정). 다만 처음 계획(문서 B 4절)은 원래 "검색된 근거로 root cause를 직접 판단"하는 방식이었다(7.1절).

### 1.4 최종(v3) 결과 (확인됨)

출력부 B, 반복 2의 30사례 (`head_b/test_20261026T184535Z`, TASK_070:196-202)

| 방법 | Avg@5 [95% CI] | AC@1 | 엄격 근거 재현율 | 실패 |
|---|---|---:|---:|---:|
| none | 0.116 [0.029, 0.220] | 0.033 | — | 0 |
| flat | 0.480 [0.343, 0.620] | 0.250 | 0.000 | 0 |
| role_only | 0.795 [0.668, 0.910] | 0.675 | 0.333 | 3 |
| state_fixed | 0.927 [0.850, 0.990] | 0.856 | 0.964 | 2 |
| state_dynamic | 0.907 [0.823, 0.977] | 0.806 | 0.952 | 2 |

출력부 A, 같은 30사례 (`head_a_test/analysis_v3.json`, TASK_070:227-235)

| 방법 | Avg@5 [95% CI] | 실패 |
|---|---|---:|
| PC만 | 0.369 [0.244, 0.497] | 0 |
| none | 0.270 [0.168, 0.387] | 0 |
| flat | 0.524 [0.397, 0.642] | 0 |
| role_only | 0.461 [0.342, 0.575] | 1 |
| state_fixed | 0.502 [0.373, 0.631] | 0 |
| state_dynamic | 0.536 [0.402, 0.667] | 2 |
| MATMCD | 0.407 [0.275, 0.544] | 4 |

- 출력부 A의 상태 검색기는 v3의 5단계 설계가 아니다(TASK_070:219, 249). 그래서 출력부 A의 state_fixed 0.502는 v3 제안 방법을 평가한 값이 아니다.

---

## 2. P0-T2 미팅 표의 수치

출처: `docs/TASK070_MEETING_BRIEF.html` (2026-10-29), 2.2절 결과 표.

### 2.1 0.407 (확인됨)
- MATMCD 참고 기준선의 Avg@5. 출력부 A, RE2-OB 반복 2의 30사례, 실패 4건(동점 채점). 실패 없는 사례만 보면 0.488.
- 실행: `head_a_test/20261020T190645Z`. 모델 Qwen3.5-4B, 임베딩 BGE-M3, 웹 검색 Serper.
- 미팅 표에서는 출력부 B 결과 표 아래에 "PC만 ※", "MATMCD ※" 행으로 들어갔고, 각주에 "판단 경로가 다르므로 차이에는 근거 선택과 판단 방식의 효과가 함께 들어 있다"고 적혀 있었다 (PR 36에서 추가).

### 2.2 교수님이 언급한 숫자 (확인됨 / 추정 구분)

| 미팅 로그의 표현 | 정체 | 구분 | 출처 |
|---|---|---|---|
| "907", "V7이니까 더 잘한" | state_dynamic의 Avg@5 0.907로 보임 | 추정 (음성 인식) | 미팅 자료 결과 표 |
| "24였다가 44" | 24 = 출력부 B의 근거 개수 K. "44"는 role_only의 4, 4로 보임 | 추정 | `select_state_fixed(case, K=24)` |
| "754" | S1 7개, S2 5개, S4 12개(가설 3개 × 4)로 보임 | 추정 | 미팅 자료 2.1절 의사코드 |
| "4416" | role_only의 구조 4 + 문서 4 + 관측 16 | 확인됨 | 미팅 자료 2.3절 "top4 + top4 + top16" |
| "S1 S2 다음에 왜 S4" | S3은 가설을 세우는 단계로 검색을 하지 않아, 검색 단계 표에 S1, S2, S4만 나옴 | 확인됨 | 미팅 자료 "단계별 검색 질문" 표 |
| "0.987" | 표에서 찾지 못함. 실패 없는 23사례의 state_fixed 0.978일 가능성 | 확인 불가 | — |

### 2.3 이 값들의 근거 (확인됨: 근거 기록 없음)
- 7·5·12, K=24, 의심 서비스 3개, 가설 3개, 메커니즘별 위키 문서 번호(예: memory → 18·14·19)는 `docs/TASK070_DEV_V3.md` 1절에 "start run"의 설계로 적혀 있으나, **왜 그 값인지는 적혀 있지 않다.**
- 4·4·16은 PR 28에서 role_only에 문서 묶음 4개를 추가하며 생긴 값이다. 이유 기록은 찾지 못했다.
- v3 설계는 "평가 결과를 모르는 서브에이전트"가 개발 사례 30개로 만들었다(TASK_070:190).

---

## 3. P0-T3 MATMCD 논문의 공식 수치

출처: `E:\연구\MATMCD.pdf` 본문 4.3절, 표 4, 부록 B.1 (pdftotext로 추출한 원문).

### 3.1 RCA 실험 (확인됨)
- 데이터: LEMMA-RCA의 Product Review(변수 216개, Pod당 메트릭 6개, 길이 131,329)와 Cloud Computing(변수 168개, 메트릭 7개, 길이 109,351).
- 방식: 인과 그래프를 만들고 그 위에서 RWR로 원인 순위를 매김. 사전에 EVT 기반으로 무관한 Pod를 걸러냄.
- 지표: MAP@5, MAP@10, MRR, 그리고 각 데이터셋에서 정답의 순위(RK).

표 4 (원문 그대로)

| 방법 | MAP@5 | MAP@10 | MRR | RK (PR) | RK (CC) |
|---|---:|---:|---:|---:|---:|
| PC | 0.0% | 25.0% | 0.14 | 5 | 13 |
| Efficient-CDLMs | 0.0% | 0.0% | 0.10 | 10 | 10 |
| SCD-LLM | 0.0% | 25.0% | 0.14 | 5 | 13 |
| ReAct | 0.0% | 25.0% | 0.14 | 5 | 12 |
| LLM-KBCI | 10.0% | 30.0% | 0.16 | 4 | 13 |
| LLM-KBCI-RA | 0.0% | 25.0% | 0.14 | 5 | 12 |
| LLM-KBCI-RE | 10.0% | 30.0% | 0.16 | 4 | 13 |
| MATMCD | 30.0% | 55.0% | 0.32 | 2 | 7 |
| MATMCD-RE | 20.0% | 55.0% | 0.25 | 3 | 6 |

- 사례 수: 데이터셋당 1사례씩, 합계 2사례 (RK 열이 데이터셋당 순위 하나).
- 설정: GPT-4o mini, temperature 0.5, 임베딩 text-embedding-ada-002, 웹 검색 Serper(부족하면 Tavily), 로그 이벤트는 무작위 표본 10개까지.
- 반복 실행 횟수, 시드: 논문에 없음.

### 3.2 이 저장소의 실험과 비교 (확인됨)

| 항목 | MATMCD 논문 | 이 저장소의 v0 실험 |
|---|---|---|
| 데이터셋 | LEMMA-RCA PR, CC | RCAEval RE2-OB |
| 사례 수 | 2 | 30 |
| 후보 수 | 약 200개 Pod (필터 전) | 서비스 12개 |
| 지표 | MAP@5, MAP@10, MRR, 순위 | Avg@5, AC@1, AC@3, RR |
| LLM | GPT-4o mini | Qwen3.5-4B (로컬) |
| 임베딩 | ada-002 | BGE-M3 |

**따라서 MATMCD의 "공식 기록"과 이 저장소의 0.407 사이에는 같은 것이 하나도 없다.** 교수님의 질문 "0.407이 공식 기록인가"에 대한 답은 "아니다, 이 데이터셋에는 MATMCD의 공식 기록이 없다"이다.

### 3.3 LEMMA-RCA 재현 결과 (확인됨, 출처: 미팅 자료 1절, `docs/RCA_ORACLE30_RESULT_REPORT_20260927.md`는 이번에 읽지 않음)
- 논문 그대로의 재현은 로컬에서 불가능했다 (쌍별 판단만 약 19일 이상 예상, PC는 메모리 부족).
- 30 Pod 부분집합(정답 Pod를 강제로 포함)에서 PC 4위, MATMCD 5위. 논문(PC 5위 → MATMCD 2위)과 반대 방향.
- 정답을 쓰지 않고 상위 30개를 고르면 5사례 중 정답이 포함된 경우가 0이었다.

---

## 4. P0-T4 데이터셋과 평가

출처: TASK_070:84-91, 102, `configs/task070_testset.json`, 미팅 자료.

- **데이터셋 (확인됨)**: RCAEval RE2-OB (Online Boutique). Zenodo record 14590730, CC BY 4.0. 90사례 = 서비스 5개 × 장애 6종 × 반복 3회. 서비스 11개 + redis.
- **사례 하나 (확인됨)**: 장애를 하나 주입하고 약 24분 기록. 메트릭, 로그, trace.
- **지표 (확인됨)**: Avg@5 = AC@1~AC@5의 평균. 정답이 1위면 1.0, 3위면 0.6, 5위 밖이면 0. `scripts/task070_metrics.py`.
- **RCAEval 논문의 기준선 수치와 직접 비교할 수 없다 (확인됨, TASK_070:91)**:
  - RCAEval 공식 평가 코드는 원인 서비스(정답)의 지연 시간을 기준 지표로 고르고, 장애 주입 시각(`inject_time`)으로 정상·이상 구간을 자른다.
  - 이 저장소는 정답을 쓰지 않는다는 원칙에 따라 진입 서비스의 지연 시간을 쓰고, 사례 전체 구간을 쓴다.
  - 그래서 조건이 다르다. P2 문헌 조사에서 다른 논문의 공표값을 표에 넣을 때 이 차이를 반드시 확인해야 한다.
- **실패 채점 규칙 (확인됨)**: LLM 응답 형식 실패는 후보 전체 동점으로 채점. 실패 1건이 평균을 약 0.025 움직인다.

---

## 5. P0-T5 개발 중 본 데이터의 범위

출처: `configs/task070_testset.json`, `scripts/task070_rcaeval.py:40-45`, TASK_070, `docs/TASK070_DEV_V3.md`, `MATMCD_DATA/task070/head_b` 폴더 목록.

| 분할 | 사례 | 사용 내역 | 구분 |
|---|---|---|---|
| 반복 1 (dev) | 30 | 개발에 사용. v1은 앞 10사례만, v2·v3은 30사례 전체. 출력부 B 개발 실행 폴더 13개 | 확인됨 |
| 반복 2 (test) | 30 | 평가에 사용. **출력부 B 평가를 세 번 실행**: v1(10-19), v2(10-25), v3(10-26). 매번 방법을 다시 개발한 뒤 실행 | 확인됨 |
| 반복 3 (unused) | 30 | 평가·개발 실행 기록 없음. 설정 파일에 "미사용, 결과를 본 뒤 평가 사례를 늘리거나 바꾸지 않는다"고 기록 | 확인됨 (출력부 B 폴더 기준. 출력부 A 폴더는 문서 기록으로만 확인) |

- 주의: 데이터 감사(TASK_070 T1, D-7 수정) 때 90사례 전체의 파일 구조와 열 이름은 확인했다. 반복 3의 사례 내용을 보고 방법을 만든 기록은 없다.
- 반복 2는 v1·v2 평가 결과를 사람과 AI가 본 뒤 v3를 만들었다. 대응책으로 "평가 결과를 모르는 서브에이전트"가 개발했다고 기록돼 있다(TASK_070:214).
- v3 개발 중 반복: 시작 설계 → 반복 1 채택(0.930 → 0.965) → 반복 2 기각. 문서에 "모든 채택 결정이 잡음 범위 안"이라고 적혀 있다 (`TASK070_DEV_V3.md` 198-199행).

---

## 6. P0-T6 "핵심 문서" 정답의 출처

출처: `scripts/task070_direct_run.py:22-31`, 미팅 자료 2.3절.

- **정의 (확인됨)**: 엄격 silver 근거 = 정답 서비스의 근거 단위 중, 이상이 표시된 분이 있고, 종류가 메트릭·KPI·trace 오류인 것.
- **누가 정했나 (확인됨)**: 사람이 라벨링한 것이 아니라 코드의 규칙이다. 2026-10-25에 추가됐다(PR 21). 처음의 느슨한 정의는 정답 서비스의 관측 근거 전부였다.
- **방법 설계와 겹치는 부분 (확인됨)**: 제안 방법 state_fixed는 S4에서 "가설 서비스의 이상 표시 메트릭과 trace 오류를 우선" 고른다(v3 반복 1에서 채택한 변경). 이것은 엄격 silver 근거의 정의(이상 표시 메트릭, trace 오류)와 같은 종류다. 즉 **평가 기준과 방법의 선택 규칙이 같은 신호를 쓴다.** 재현율 0.964에는 이 겹침의 영향이 들어 있을 수 있다.
- flat의 엄격 재현율이 0.000인 이유: flat이 고른 24개 중 81%가 위키 문서였다(위키는 정답 근거가 될 수 없는 종류).

---

## 7. P0-T7 처음 아이디어와 v0의 차이

### 7.1 처음 아이디어 문서 (확인됨, 2026-11-18 추가 확인)
- 읽은 방법: 사용자 승인으로 Poppler 25.07.0을 winget으로 설치하고(저장소 밖의 시스템 변경), 두 PDF를 페이지 이미지로 변환해 전 페이지를 읽었다.
- 문서 A: `E:\연구\Reasoning-State-Aware Evidence Retrieval for Microservice Incident Analysis.pdf` (5쪽, 2026-07-30 생성)
- 문서 B: 같은 이름의 "구현 및 실험 계획.pdf" (6쪽, 2026-07-31 생성). 5.2절 다음이 8.3절이다. 6절, 7절, 8.1절, 8.2절은 PDF에 없다.

#### 문서 A의 내용
- **배경 (1절)**: Wikipedia 기반 multi-hop QA는 같은 성격의 passage를 차례로 잇는다. 장애 분석은 목적이 다른 정보(System Structure, Observation, Diagnosis, Action)를 쓴다. 이들은 추론 과정에서 하는 역할이 다르다.
- **문제 정의 (2절)**: 장애 분석은 증상 이해 → 시스템 구조 파악 → 원인 후보 탐색 → telemetry를 통한 가설 검증 → root cause 판단 → resolution 탐색으로 진행되고, 단계마다 필요한 근거 종류와 탐색 범위가 바뀐다. flat retrieval은 역할이 다른 문서를 같은 공간에 두고 질의-문서 관련도로만 순위를 매겨, 같은 서비스 이름이나 오류 키워드 때문에 지금 단계와 무관한 근거가 상위에 온다.
- **연구 질문 (2절 끝, 원문)**: "마이크로서비스 장애 분석에서 corpus의 evidence role과 reasoning stage를 명시적으로 정렬하고, 각 단계에 필요한 evidence type과 structural scope를 인식하여 선택적으로 탐색한다면 flat retrieval보다 더 정확하고 효율적인 multi-step reasoning이 가능한가?"
- **핵심 아이디어 (3절)**:
  - corpus를 문서 역할에 따라 구분하고, service topology와 evidence 간 관계를 함께 구성한다 (Role-Aware Structured Retrieval Space).
  - 각 evidence에 연결할 정보의 예: 관련 service, evidence type, timestamp, service dependency, 다른 evidence와의 관계, reasoning 과정에서의 역할.
  - 검색 때는 "현재 reasoning state를 기준으로 '현재 해결되지 않은 reasoning goal이 무엇인가?'를 파악한 다음 필요한 evidence role과 탐색 scope를 동적으로 예측하고, 이를 retrieval ranking에 반영"한다.
  - 단계와 근거: 1 증상 이해 = Observation(metric/log), 2 장애 전파 구조 확인 = System Structure(topology/dependency/trace), 3 root cause 후보 생성 = Observation + Diagnosis(telemetry/failure pattern), 4 hypothesis 검증 = Observation(후보 서비스의 metric/log/trace), 5 해결 방법 탐색 = Action.
- **기대 효과 (4절)**: 불필요한 noisy path 감소(검색 횟수, 토큰, 시간), 같은 표현으로 생기는 검색 모호성 감소, root-cause evidence chain의 완성도 향상, 추론 과정의 효율성과 해석 가능성(어느 단계에서 어떤 목적으로 고른 근거인지 명시).
- **관련 연구 (5절)**: MATMCD(Findings of ACL 2025), mABC(Findings of EMNLP 2024), TraceLLM(EMNLP 2025), RepoGenesis(ACL 2026).

#### 문서 B의 내용
- **MATMCD를 고른 이유 (1절)**: 마이크로서비스 RCA를 직접 다룸, metric과 log를 함께 씀, 공식 코드와 데이터 공개, root-cause ranking 결과가 있어 같은 기준으로 평가 가능.
- **MATMCD의 아쉬운 점 (3절)**: 검증할 쌍이 정해지기 전에 evidence를 검색·요약함 / 로그 조회가 서비스 이름 기준이라 무관한 이벤트가 섞임 / 요약 과정에서 필요한 정보(timestamp, 간헐적 오류, 이벤트 순서)가 빠질 수 있음 / 쌍마다 같은 맥락 정보를 씀.
- **제안 방법 (4절)**: "MATMCD의 causal graph 보정 과정을 수정하는 것이 아니라, 동일한 metric과 log를 입력으로 사용하지만 root cause에 도달하는 과정은 다르게 구성". corpus의 이질성을 indexing 단계부터 반영하고, 추론 단계별로 필요한 evidence를 검색하고, **검색된 근거를 바탕으로 root cause를 직접 판단**한다. Action evidence 검색과 복구 방법 생성은 이번 연구에서 제외한다.
- **구현 계획 (5절)**:
  - 5.1 MATMCD 공식 구현으로 재현 (입력 형태, context, 판단 결과, ranking 과정, PR·CC 평가 방법 확인).
  - 5.2 Evidence corpus: MATMCD와 같은 metric과 log를 쓰되 service dependency와 topology 정보를 함께 구성. topology가 제공되지 않으면 trace 호출 관계, service configuration, 공개된 구조로 구성. metric·log를 요약 하나로 저장하지 않고 검색 가능한 단위로 구성(Metric: 특정 service·metric·시간 구간의 변화, Log: 개별 event 또는 template, Trace: 개별 호출 관계·비정상 span·오류 응답, Architecture document: 역할과 dependency를 설명하는 문단, Incident document: 증상과 원인을 설명하는 문장).
- **Reasoning state 구성 (8.3절)**: "초기 구현에서는 reasoning state를 LLM이 자유롭게 생성하지 않고, 다음 단계로 고정": 1 증상 이해, 2 시스템 구조 파악, 3 원인 후보 탐색, 4 Telemetry를 통한 가설 검증, 5 Root cause 판단. 이유: "별도의 복잡한 reasoning planner를 새로 만드는 것보다, 현재 reasoning state에 따라 evidence를 다르게 검색하는 효과를 먼저 확인하기 위해서".
- **Evidence 검색과 판단 (8.4절)**:
  - State 1: 최초 alert나 관찰된 장애 현상에서 incident의 시작점을 구성. 어떤 service에서 어떤 형태의 이상이 언제부터 발생했는지 확인.
  - State 2: 증상 service를 시작점으로 dependency, topology, up/downstream 문서에서 관련 service 탐색. topology상 가까운 service를 모두 원인 후보로 고르지는 않음.
  - State 3: 앞 단계에서 고른 service subgraph 안에서 root-cause hypothesis 생성.
  - State 4: 각 hypothesis마다 별도의 retrieval query와 service·time scope 구성. **evidence가 부족하면 부족한 정보를 새로운 reasoning goal로 변환** (예: Payment에서 timeout은 확인됐지만 Checkout으로 전파됐다는 trace evidence가 부족 → Payment–Checkout trace를 추가 검색).
  - State 5: 각 hypothesis에 연결된 evidence chain을 비교. 최종 출력은 MATMCD와 비교할 수 있도록 root-cause ranking.
- **실험 계획 (9절)**:
  - 9.1 LEMMA-RCA에서 MATMCD와 1대1 비교. 조건을 가능한 한 동일하게: 같은 metric과 log, 같은 root-cause candidate 범위, 같은 LLM, 같거나 유사한 context token budget, 같은 root-cause label, 같은 평가 지표. 주 지표는 MATMCD와 같은 MAP@10, 그리고 MAP@5, MRR, 데이터셋별 rank.
  - 9.2 RCAEval 확장 실험. LEMMA-RCA는 failure case가 적어 일반 성능 판단에 한계. RCAEval(Online Boutique, Sock Shop, Train Ticket, 735 failure case). 지표: AC@1, AC@3, Avg@5, **Indicator Hit@K(검색 결과에 정답 evidence가 포함되는지)**, 토큰 수와 분석 시간.

### 7.2 v0로 오면서 바뀐 것 (확인됨, 출처 표시)

| 항목 | 처음 아이디어 | v0 (v3 최종) | 출처 |
|---|---|---|---|
| 데이터셋 | 주: LEMMA-RCA에서 MATMCD와 1대1 비교. 확장: RCAEval | RCAEval RE2-OB만 (LEMMA-RCA 1대1 비교는 연산량 문제로 포기) | 문서 B 9절, 미팅 자료 1절 |
| 주 지표 | LEMMA-RCA: MAP@10 (MATMCD와 동일). RCAEval: AC@1, AC@3, Avg@5, Indicator Hit@K | Avg@5, AC@k, 규칙으로 만든 엄격 silver 근거 재현율 | 문서 B 9절, TASK_070 |
| 공정 조건 | 같은 입력, 같은 후보 범위, 같은 LLM, 유사한 토큰 예산 | MATMCD는 웹 검색 + 로그 요약, 제안 방법은 고정 근거 풀(텔레메트리 + 위키). 판단 경로도 다름 | 문서 B 9.1절, 미팅 자료 2.1절 |
| State 4의 추가 검색 | 근거가 부족하면 부족한 정보를 새 reasoning goal로 바꿔 추가 검색 | 없음. 가설마다 정해진 개수를 한 번 검색 | 문서 B 8.4절, TASK070_DEV_V3.md 1절 |
| evidence 간 관계, 근거 chain | evidence에 다른 evidence와의 관계를 연결, hypothesis별 evidence chain 비교 | 근거 단위에 서비스·종류·역할 태그만. chain 구성 없음 | 문서 A 3절, 문서 B 8.4절 (v0 쪽은 문서 기록 기준, 코드 전체는 읽지 않음) |
| Action 역할 | 포함 | 제외 | RESEARCH_ROADMAP.md:23 |
| Diagnosis 문서 | 포함 | 없음 (원본 저장소에 장애 패턴·런북이 없어 만들지 않음) | TASK_070:214 |
| System Structure 문서 | 포함 | v1·v2에는 없었고, v3에서 정적 분석 위키로 추가 | TASK_070:184-187 |
| 출력 | 문서 B 4절: 검색된 근거로 root cause를 직접 판단, 출력은 ranking | 2026-10-18 재계획에서 쌍별 판단 → PC → RWR(출력부 A)로 정했다가, 2026-10-19 사례 단위 순위 직접 출력(B)을 주 출력부로 변경. 결과적으로 B가 처음 계획과 같은 방향 | 문서 B 4절, TASK_070:16-26, 115 |
| 제안 방법 | 문서 A는 동적 예측, 문서 B는 "초기 구현에서는 5단계로 고정" | v1·v2는 동적이 제안 방법, v3에서 고정(state_fixed)으로 변경 | 문서 A 3절, 문서 B 8.3절, TASK_070:192 |
| 상태 설계 | 5단계(⑤는 Action) | 5단계: 텔레메트리 → 구조 → 가설 → 가설별 근거 → 판단 | TASK_070:191 |

### 7.3 결과를 보고 바꾼 것 (확인됨)

| 변경 | 계기가 된 결과 | 출처 |
|---|---|---|
| 판단 프롬프트 v1 → v2 | v1에서 Yes가 0~4/156으로 그래프가 빔 (개발 2사례) | TASK_070:105 |
| 상태 검색 v1 → v2 | 개발 10사례에서 제안 방법이 낮음 | TASK_070:112-113 |
| 출력부 B 신설, 주 출력부로 | 출력부 A에서 제안 방법이 flat보다 낮음 | TASK_070:114-116 |
| 출력부 B v1 → v3 (출력 한도, presence_penalty) | 출력 한도 초과 실패 | TASK_070:117 |
| v2 재개발 (서비스 정렬 기준 변경) | v1 평가 우위가 개발 서비스에서만 나타남 | TASK_070:251-257 |
| v3 (위키 추가, 5단계, 제안 방법을 fixed로) | v2 평가에서 flat 대비 유의차 없음, dynamic이 약함 | TASK_070:183-193, 283-288 |
| v3 반복 1 (S4에서 이상 표시 근거 우선) | 개발 30사례 관찰 | TASK070_DEV_V3.md 3절 |

- 각 단계에 개발/평가 분할과 동결 절차는 있었다. 그러나 평가 결과를 본 뒤 새 버전을 만들어 같은 평가 사례로 다시 평가하는 일이 세 번 반복됐다.

---

## 8. P0-T8 진행 중인 실행

- **확인됨**: 실행 중인 프로세스 없음 (`pgrep -af 'task070_|llama-server|matmcd'` 결과 없음, 2026-11-18).
- 인계 문서 기준 모든 평가 실행은 2026-10-27까지 완료. 대기열 없음.
- 따라서 결정 대기 항목 U2(대기 중인 실행을 계속할지)는 해당 없음.

---

## 9. P0-T9 RCA 답 생성 여부

- **확인됨**: v0의 출력부 B는 후보 서비스 12개의 순위를 근거 인용과 함께 출력한다. 공식 지표 형식(순위)과 맞는다. `scripts/task070_direct.py`, `task070_direct_run.py`.
- MASTER_PLAN의 K3("새 방법은 RCA 답을 생성한다")는 새로 추가하는 기능이 아니라 v0에도 있던 것이다.

---

## 10. 환경 제약 (확인됨, 출처: 미팅 자료 1절, MATMCD/AGENTS.md)

- 하드웨어: Ryzen 7 5700X3D, RAM 16GB(WSL 7.7GB), RTX 2080 SUPER 8GB.
- 모델: Qwen3.5-4B Q5_K_M (llama.cpp, 단일 slot), 임베딩 BGE-M3 (CPU).
- 유료 API와 외부 서버는 사용하지 않는다. 웹 검색은 Serper 무료 할당량 안에서만.
- MATMCD를 RE2-OB 1사례에 돌리는 데 약 38분(156쌍 × 2호출 + 검색·요약).

---

## 11. MASTER_PLAN에 영향을 주는 점 (사용자 판단 필요)

AI가 결정하지 않는다. 사실과 선택지만 적는다.

### G1-1. 처음 아이디어 문서의 한글 본문 (해결됨)
2026-11-18 사용자가 도구 설치를 선택했다. Poppler 설치 후 두 문서를 모두 읽었고 7.1절에 내용을 적었다.

### G1-2. MASTER_PLAN의 전제 수정
계획을 세울 때의 전제 두 가지가 사실과 달랐다.
- "지금은 검색 성공만 비교했다" → 실제로는 RCA 점수(Avg@5)도 측정하고 표에 있었다.
- "MATMCD 공식 수치와 0.407을 대조한다" → 같은 데이터셋의 공식 수치가 없다. 대조할 대상이 없다.
이에 따라 K3, K4, P1의 내용을 고쳐야 한다. 고칠 문구는 사용자 확인 후 반영한다.

### G1-3. 교수님의 "공식 기록" 요구를 어떻게 충족할까 (P1·P2·P3에서 결정, 지금은 인지만)
같은 경기장의 공식 기록이 없는 상황이다. 가능한 방향은 다음과 같고, 각각의 조사는 P1·P2에서 한다.
- RCAEval RE2-OB를 쓴 다른 논문의 공표값을 찾는다 (단, 4절의 조건 차이 문제가 있다)
- RCAEval 공식 평가 조건을 그대로 따를지 여부를 다시 정한다 (공식 조건은 정답 정보를 쓴다)
- MATMCD가 공식 수치를 낸 LEMMA-RCA에서 비교한다 (로컬 연산량 문제로 v0에서 포기한 길)
- MATMCD를 "공식 기록이 있는 비교 대상"이 아니라 "이 데이터셋에 직접 돌린 참고 기준선"으로만 둔다

### G1-4. 평가 데이터 (P3 평가 절차에서 결정, 지금은 인지만)
- 반복 2(30사례)는 세 번 평가에 쓰여 "본 데이터"다.
- 반복 3(30사례)은 손대지 않았다.
- 90사례 전체를 쓰는 길도 있다 (다른 논문과 범위를 맞출 때).

### G1-5. MATMCD/AGENTS.md와의 충돌
`MATMCD/AGENTS.md`에 "상태 설계·프롬프트는 개발용 사례로만 다듬고"라는 문장과, 현재 목표를 TASK_070으로 적은 부분이 있다. 2026-11-18에 정한 규칙(개발용 데이터 튜닝도 하지 않음)과 맞지 않는다. 고칠지, 어떻게 고칠지는 사용자가 정한다.

### G1-6. 기존 계획 파일 처리 (U9)
사용자가 "P0 후에 정하자"고 한 항목. 대상 후보와 성격은 다음과 같다.

| 파일 | 성격 | P0 이후에도 참조되는가 |
|---|---|---|
| `docs/EXPERIMENT_PLAN_TASK070.md` | v0 실행 계획 (완료) | 이 보고서의 근거로 인용 |
| `docs/RESEARCH_ROADMAP.md` | v0 연구 방향 | 이 보고서의 근거로 인용 |
| `docs/TASK070_HANDOFF.md` | v0 인계 문서 | 실행 환경 메모(7절)는 계속 유효 |
| `docs/TASK070_DEV_V2.md`, `TASK070_DEV_V3.md` | v0 개발 기록 | 이 보고서의 근거로 인용 |
| `docs/TASK070_INTERIM_REPORT.md`, `TASK070_RESULTS_REPORT.html`, `TASK070_MEETING_BRIEF.html` | v0 보고서, 미팅 자료 | 미팅 자료는 이 보고서의 근거 |
| `tasks/TASK_070_state_aware_retrieval_experiments.md` | v0 전체 기록 (원본) | 이 보고서의 주 근거 |

선택지: 그대로 둠 / `docs/archive_v0/`로 이동 / 삭제(git 이력에만 남음). 이동이나 삭제를 하면 이 보고서의 출처 경로도 함께 고쳐야 한다.

---

## 12. 이번에 읽지 않은 것

- `docs/TASK070_INTERIM_REPORT.md`, `docs/TASK070_RESULTS_REPORT.html`, `docs/TASK070_DEV_V2.md`: TASK_070 본문과 내용이 겹쳐 읽지 않았다.
- `docs/RCA_*.md`, `docs/REPRODUCTION_SPEC.md`, `docs/RCA_ORACLE30_RESULT_REPORT_20260927.md`: LEMMA-RCA 재현의 상세. P1에서 필요한 부분을 읽는다.
- 실행 결과 폴더의 원본 파일(analysis.json, 사례별 출력): 열지 않았다.
- 스크립트 본문: `task070_direct_run.py`의 silver 정의 부분과 `task070_rcaeval.py`의 분할 정의만 읽었다.
