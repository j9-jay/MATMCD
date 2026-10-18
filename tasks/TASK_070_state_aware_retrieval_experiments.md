# TASK_070 - 추론 상태 기반 근거 검색 실험 설계와 기준선

## 목적

추론 상태 기반 근거 검색(사용자 방법)이 flat retrieval보다 필요한 근거를 더 잘 찾고, 그 결과 최종 판단이 더 정확해지는지 검증한다. 연구는 NLP 기여(근거 검색·귀속)로 읽히도록 구성한다. 상세 방향은 [연구 로드맵](../docs/RESEARCH_ROADMAP.md).

## 확정된 설계 (2026-10-18 사용자 결정)

### 실험 카테고리

| 카테고리 | 데이터 | 역할 |
|---|---|---|
| 1. 장애 분석 | RCAEval RE2-OB | 주 응용. 90사례. RE2-SS는 백로그(아래 범위 변경 참고) |
| 2. 인과 발견 | MATMCD 벤치마크 5종: AutoMPG(5 변수), DWDClimate(6), SachsProtein(11), Asia(8), Child(20) | 도메인 독립성, MATMCD와 같은 조건 비교 |

### 공통 출력부 (A안)

모든 방법이 같은 출력부를 쓴다. 방법 간 차이는 근거 수집과 그 근거를 판단 프롬프트에 넣는 부분뿐이다.

```text
근거 수집(방법마다 다름) → 쌍별 1단계 Yes/No 판단 → 제약 PC → 인과 그래프
                                                              └→ (카테고리 1) KPI에서 RWR → 서비스 순위
```

- 판단 프롬프트는 단순한 1단계 Yes/No로 하고 모든 방법이 공유한다. MATMCD의 2단계 설명→판단 구조와 Top-K Guess는 쓰지 않는다.
- 제약 PC, RWR, 그래프·순위 지표는 이 분야의 공통 틀이며 MATMCD 고유 아이디어가 아니다.

### 비교 방법

| 방법 | 근거 | 위치 |
|---|---|---|
| PC만 | 없음 | 하한 |
| 검색 없는 LLM | 없음 (LLM 내부 지식) | 검색 효과 확인 |
| flat RAG | 같은 corpus, 단일 질의 유사도 검색 | **핵심 비교 대상** |
| 사용자 방법 | 같은 corpus, 상태별 역할 근거 검색 | 제안 |
| MATMCD | DA-AGENT + CC-AGENT | 외부 참고 기준선 (출력 경로가 달라 차이 원인 특정 불가) |

### 지표

| 층 | 카테고리 1 | 카테고리 2 |
|---|---|---|
| 검색 | 근거 recall/precision (silver label) | 근거 관련성 (LLM 판정 + 일부 사람 검토) |
| 답 | AC@k, Avg@k, MAP@K, MRR | Prc, F1, FPR, SHD, NHD |
| 귀속 | 인용 precision/recall | 인용 precision/recall |
| 효율 | 검색 횟수, LLM 호출, 토큰, 시간 | 같음 |

### corpus 원칙

- 근거 내용은 모든 방법이 공유한다. 역할·상태 태그 같은 색인 구조만 방법 고유다.
- corpus·질의 구성에 정답 정보를 쓰지 않는다. RCAEval의 `fault_description`, 정확한 주입 시각, 원인 서비스는 평가에만 쓴다. 장애 구간은 정답 없이 정한다.
- 상태 설계와 프롬프트는 개발용 사례로만 다듬는다. 카테고리 2는 사례 분할이 어려우므로 설계를 먼저 고정하고 한 번에 평가한다.

### 웹 근거

- Serper·Tavily는 **무료 할당량 안에서만** 사용한다. 넘으면 웹 근거를 빼고 웹 외 경로로 다시 실험한다.
- 웹은 corpus를 만들 때 한 번만 검색해 스냅샷으로 고정하고 모든 방법이 공유한다. 사용량을 기록한다.
- 검색 경로는 설정 조건이다: `serper_tavily` / `wikipedia_api` / `offline_snapshot`. 브라우저 자동화 검색은 쓰지 않는다(약관·CAPTCHA·재현성).
- 누출 검사: 데이터셋·논문·저장소 식별자와 정답 그래프·정답 목록이 담긴 문서를 사전 고정 규칙으로 제외하고 기록한다. Asia·Child·Sachs는 정답 그래프가 웹에 공개돼 있어 특히 주의한다.

## 결정 대기

| ID | 항목 |
|---|---|
| D-1 | RCAEval 서비스당 여러 메트릭을 한 열로 묶는 규칙 |
| D-2 | RE2-SS KPI 열 확인 (공식 코드는 `frontend_latency`, SS 존재 미확인) |
| D-3 | 정답 없이 장애 구간을 정하는 방법 |
| D-4 | 동적 상태 설계: 상태 유형 분류 + 근거 공백 결합안 (로드맵 참고) |
| D-5 | 공유 1단계 판단 프롬프트 문안 |
| D-6 | RCAEval 개발·평가 사례 분할 |
| D-7 | MATMCD 참고 기준선용 RCAEval 로그 변환 방식 (공개 코드는 LEMMA 로그 형식 전제) |
| D-8 | 웹 할당량 초과 시 대체 경로 |
| D-9 | 판단 결과의 양방향 Yes 처리 (제약 PC에 그대로 전달할지) |
| D-10 | 새 프롬프트의 샘플링 설정 |
| D-11 | RWR·LLM 반복 실행 규칙 |

단계 순서, 관문, 결정 권장안, 비용 추정은 [실행 계획](../docs/EXPERIMENT_PLAN_TASK070.md)에 있다.

**2026-10-18 범위 변경(사용자 결정):** 카테고리 1은 RCAEval RE2-OB로만 진행한다. RE2-SS는 로그에 템플릿 열이 없어(템플릿 번호별 개수 `logts.csv`만 있음) MATMCD 참고 기준선을 원래 입력 형식에 맞추기 어려우므로 백로그(로드맵 R14)로 옮긴다. 받은 RE2-SS 자료와 감사 기록은 보존한다. D-7은 OB의 `log_template` 열을 MATMCD 로그 템플릿 입력으로 쓰는 것으로 정한다(원본 LEMMA 형식과 다른 조건으로 기록).

**2026-10-18 사용자 승인:** D-1~D-11 권장안 전부와 E-1(RCAEval RE2-OB·SS 다운로드), E-2(인과 발견 공식 파일 3개 복원), E-3(실행 계획 커밋)을 승인했다. 웹 검색은 무료 할당량을 크게 넘을 것으로 예상되면 **생략하고 대체 경로(D-8: Wikipedia API)로 진행**한다. D-2·D-7은 데이터 확인 후 결정하는 항목이고, D-5 판단 프롬프트 문안은 P1에서 다시 승인받는다.

## 작업 항목

- [x] T1 RCAEval RE2-OB/SS 다운로드와 데이터 감사 — 2026-10-18 Zenodo record 14590730(CC BY 4.0)에서 `RE2-OB.zip`(1,191,025,569 B, md5 `b9e23f88…de4`)과 `RE2-SS.zip`(245,629,018 B, md5 `bd747a8f…225`)을 받아 `MATMCD_DATA/raw_downloads/zenodo_rcaeval_14590730/`에 두었다. 둘 다 Zenodo md5와 일치. 압축은 풀지 않고 zip 안에서 읽기 전용으로 감사했다.
  - 사례: 각 90개(`{서비스}_{장애}/{반복}`). 사례 파일은 `simple_metrics.csv`, `metrics.csv`, `logs.csv`, `logts.csv`, `inject_time.txt`, `cluster_info.json`, `pod-node-*.csv`. OB는 `traces.csv`, `tracets_lat.csv`, `tracets_err.csv`가 더 있다.
  - OB zip에는 사례가 아닌 `RE2-OB/checkoutservice_cpu/multi-source-data`(중첩 zip 포함)와 `.DS_Store`가 있다. 평가 사례에서 제외한다.
  - 길이: SS는 모두 1,441행. OB는 88사례 1,441행, 1사례 1,186행, 1사례 1,262행.
  - 컨테이너: OB는 서비스 11개 + redis, 그리고 workload·error만 있는 `frontend-external`. SS는 15개(DB, rabbitmq 포함).
  - KPI: OB `frontend_latency-90`, SS `front-end_latency-90`이 90/90 사례에 존재. D-2 확정.
  - 로그: OB `logs.csv`에는 `cluster_id`, `log_template` 열이 있다. SS에는 템플릿 열이 없고 템플릿별 개수 시계열 `logts.csv`만 있다. D-7은 이 차이를 반영해 결정한다.
  - **RCAEval 공식 평가 코드(`main.py`)는 원인 서비스(정답)의 latency가 있으면 그것을 SLI로 고르고, `inject_time` 기준으로 정상·이상 구간을 자른다.** 우리는 정답 미사용 원칙에 따라 진입 서비스 지연을 KPI로, 사례 전체 구간을 쓴다(D-2, D-3). 따라서 RCAEval 논문의 기존 기준선 수치와 직접 비교할 수 없다.
- [x] T2 카테고리 2 공식 파일 복원 — 2026-10-18 원본 ZIP(sha256 `3cf8a201…2647`)에서 3개를 바이트 동일하게 복원하고 `configs/scope.json`을 갱신했다(공식 파일 40개).
  - **데이터는 공식 저장소에 없다.** `Utils/data.py`는 `./data/{name}_data.csv`와 `{name}_GTmatrix.csv`를 읽지만 ZIP에 해당 파일이 없다. Asia·Child는 `SampleFromBIF.py`가 BIF에서 seed 없이 1,000개를 생성하는 구조이며 BIF 파일도 없다.
  - 후보 출처(미다운로드): AutoMPG·DWDClimate·Sachs는 MATMCD가 따랐다고 밝힌 Takayama et al.의 저장소 `mas-takayama/LLM-and-SCD`(`benchmark datasets/`, `ground truth matrix/`, 라이선스 표기 없음). Asia·Child BIF는 로컬 Efficient-CDLMs 저장소(`raw_downloads/github_superkaiba_causal_llm_bfs/data/`)에 있다.
  - **해결(2026-10-18 사용자 승인):** Takayama 저장소(커밋 `5aaeaea89e71e2cff443289e473c06d2f79172c5`)의 CSV를 출처 명시 조건으로 받았다. Asia·Child는 로컬 BIF에서 공식 생성 절차에 seed 42를 넣어 1,000개를 만들었고 모든 방법이 같은 표본을 쓴다. [준비 스크립트](../scripts/prepare_causal_benchmarks.py), 출력 `MATMCD_DATA/datasets/causal_benchmarks_task070_v1`(manifest에 출처·해시·pgmpy 1.0.0 기록).
  - 확인: AutoMPG 392행(논문 392), Sachs 7,466행(논문 7,466), **DWD 349행(논문 350)**. 차이는 기록만 하고 고치지 않는다. Asia 노드 8·간선 8, Child 노드 20·간선 25. seed 42 표본은 두 번 생성해 동일함을 확인했다.
  - 37개 고정 검사를 쓰는 과거 감사 스크립트 4개는 재실행 시 실패한다(`configs/scope.json` 기록).
- [ ] T3 웹 스냅샷 수집과 누출 검사 (무료 할당량 내)
- [ ] T4 corpus 구성기 (근거 단위, 역할·상태 태그)
- [ ] T5 공통 출력부와 지표 연결 (제약 PC, RWR, AC@k·MAP·MRR, 그래프 지표)
- [ ] T6 기준선: PC만, 검색 없는 LLM, flat RAG
- [ ] T7 MATMCD 참고 기준선 (두 카테고리)
- [ ] T8 사용자 방법과 ablation (상태 유무, 역할 태그 유무, 고정 vs 동적 상태)
- [ ] T9 평가와 통계 검정 (사례 단위 paired bootstrap/permutation)
- [ ] T10 결과 보고서

## 비용 추정 (30 Pod 설명 호출 실측 18.67초/호출을 적용한 대략치. 1단계 판단은 출력이 짧아 더 빠를 수 있고, 근거 검색 비용은 제외)

| 대상 | 쌍 | 판단 1회 전체 |
|---|---:|---:|
| RCAEval OB 1사례 (12개 서비스 + KPI) | 156 | 약 49분 |
| RCAEval SS 1사례 (15개 + KPI) | 240 | 약 1.2시간 |
| 인과 발견 5종 합계 | 596 | 약 3시간 |

## 상태

TODO — 설계 확정, 실행 계획 작성, 결정 대기(D-1~D-11)
