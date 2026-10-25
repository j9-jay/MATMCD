# TASK_070 출력부 B 제안 방법 재개발 (STATE_DEV_V2, 개발 30사례)

작성: 2026-10-25. 평가 결과를 보지 않은 에이전트가 수행했다(블라인딩 준수, 아래 "블라인딩" 참고).

## 범위와 조건

- 목적: 기존 개발(개발 10사례 = 고장 대상 2개 서비스)에 맞춰졌을 수 있는 제안 방법의 근거 선택을 개발 분할 전체 30사례(RCAEval RE2-OB 반복 1, 5개 서비스 × 6개 고장)로 다시 개발한다.
- 변경한 것: `scripts/task070_direct.py`의 `DirectSelector.select` 중 `state_fixed`/`state_dynamic` 분기와 `PLANNER_TEMPLATE`, 보조 함수(`deviation_strength`, `strength_order`, `case_overview`)만. `state_fixed`는 `state_dynamic`에서 planner 호출만 뺀 같은 설계로 유지했다.
- 고정한 것: `task070_corpus.py`, `K_DIRECT=24`, `ORDER_REPEATS=3`, `SAMPLING`, `SYSTEM`, `TEMPLATE`, `FLAT_QUERY`, `STATE_BUDGET`(role_only가 STRUCTURE 예산을 공유하므로 미변경), `none`/`flat`/`role_only`, `judge`, `parse_ranking`, `task070_metrics.py`, Qwen3.5-4B(고정 llama-server), BGE-M3. 새 다운로드 없음.
- 실행: 모든 실행은 `--split dev --start 0 --cases 30`, 각 실행의 `summary.json`이 30사례 전부를 포함함을 확인했다. `--split test`, 출력부 A, 카테고리 2는 실행하지 않았다.
- 채택 규칙: 30사례 평균 Avg@5가 오르고 어떤 서비스 평균도 0.10 넘게 떨어지지 않을 때만 채택. 판정은 제안 방법의 주 변형인 `state_dynamic`(분석 스크립트의 `PROPOSED`) 기준으로 했다. `state_fixed` 수치는 함께 기록했다.
- 최대 4회 반복(시작 실행 제외) 중 4회를 사용했다.

## 집계 방법

- 전체 Avg@5: `analyze_task070_head_b.py`와 같은 실패 규칙(실패 = 모든 후보 동률, 12후보에서 Avg@5 = 0.25)으로 30사례 평균.
- 서비스별 Avg@5: 사례의 서비스는 `task070_rcaeval.evaluation_label(path)["root_cause_service"]`(개발 분할에만 사용).
- 문제: 같은 실행에서 두 방법이 같은 사례에서 모두 실패하면 `analyze_task070_head_b.py`가 후보 수를 얻지 못해 `RuntimeError: No completed run gives the candidate count`로 중단된다(반복 1·2 실행). 분석 스크립트는 고정 대상이라 고치지 않았고, 같은 규칙을 적용한 임시 집계(후보 수는 `node_table`, 모든 개발 사례 12개)로 계산했다. 시작 실행에서 두 집계 결과가 일치함을 확인했다.

## 실행 폴더 (`MATMCD_DATA/task070/head_b/`)

| 단계 | 폴더 | 방법 |
|---|---|---|
| 시작 | `dev_20261025T094345Z` | none, flat, role_only, state_fixed, state_dynamic (v1 설계) |
| 반복 1 | `dev_20261025T104753Z` | state_fixed, state_dynamic |
| 반복 2 | `dev_20261025T111427Z` | state_fixed, state_dynamic |
| 반복 3 | `dev_20261025T114130Z` | state_fixed, state_dynamic |
| 반복 4 | `dev_20261025T120633Z` | state_fixed, state_dynamic |
| 최종 확인 | `dev_20261025T123210Z` | state_fixed, state_dynamic (최종 코드 = 반복 1 설계) |

## 시작 실행 (v1 설계)

| method | 전체 | checkout | currency | email | productcatalog | recommendation | AC@1 | 실패 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 0.227 | 0.467 | 0.350 | 0.033 | 0.283 | 0.000 | 0.017 | 0 |
| flat | 0.810 | 0.633 | 0.900 | 0.800 | 0.800 | 0.917 | 0.400 | 0 |
| role_only | 0.837 | 0.592 | 0.808 | 0.850 | 0.967 | 0.967 | 0.672 | 2 |
| state_fixed | 0.787 | 0.775 | 1.000 | 0.775 | 0.742 | 0.642 | 0.578 | 4 |
| state_dynamic | 0.887 | 0.900 | 1.000 | 0.817 | 0.867 | 0.850 | 0.650 | 0 |

관찰
- planner가 30사례 중 25사례에서 VERIFY를 정확히 frontend, checkoutservice, currencyservice로 골랐다(사례와 무관한 고정 선택). VERIFY에 정답 서비스가 들어간 사례는 13/30이고, checkout·currency(기존 개발 10사례의 두 서비스)에서만 점수가 높았다(1.000, 0.900).
- `state_fixed`의 "가장 이른 첫 이탈" 규칙은 완료 26사례 중 10사례에서만 정답 서비스를 VERIFY에 넣었다. 기준 구간(처음 5분) 직후 5~9분의 짧은 잡음 이탈이 고장 이후 지속되는 이탈보다 앞선다.
- 개발 사례 특징 조사(정답은 개발 분할에서만 사용, 근거 단위 메타데이터만 계산): 서비스별 "가장 이른 이탈" 순위로 정답이 1위인 사례 1/30(3위 이내 12/30), "이탈 표시된 metric 단위 수" 1위 15/30(3위 이내 26/30), "이탈 표시된 metric-분 합계" 1위 25/30(3위 이내 30/30).
- 실패(전부 판정 응답 형식 문제, 고정 부분): role_only 2(길이 초과 1, RANKING 줄 없음 1), state_fixed 4(RANKING 줄 없음: `**checkoutservice > ...**`처럼 접두어 없이 쓰거나 번호 목록으로 순위를 씀).

## 반복 1 — 이탈 강도 순서 (채택)

- 변경: 서비스 순서를 label-free "이탈 강도"(그 서비스 metric 단위들의 이탈 표시 분 수 합, 동률은 첫 이탈 시각·이름)로 바꿨다. `state_fixed` VERIFY = 강도 상위 3개 서비스(이탈 0인 서비스 제외), CANDIDATES = 강도 순으로 서비스마다 이탈 분이 가장 많은 metric 1개. planner 개요는 같은 순서로 서비스마다 "N flagged metric-minutes over M metrics, first deviation at minute X"를 보여 주고, CANDIDATES 설명을 "strong, sustained deviations"로, VERIFY 설명을 "detailed metrics/logs/traces"로 고쳤다.
- 이유: 위 관찰. 이른 이탈은 잡음에 약하고 지속 이탈 합계가 정답 서비스를 가장 잘 앞세운다(25/30). planner의 고정 선택은 개요가 이른 이탈만 보여 줘 사례 간 차이를 거의 주지 못한 결과로 봤다.

| method | 전체 | checkout | currency | email | productcatalog | recommendation | AC@1 | 실패 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| state_fixed | 0.892 | 0.750 | 0.967 | 0.967 | 0.842 | 0.933 | 0.775 | 3 |
| state_dynamic | 0.925 | 0.875 | 0.967 | 0.967 | 0.850 | 0.967 | 0.803 | 1 |

- 판정: state_dynamic 0.887 → 0.925, 최대 서비스 하락 −0.033(currency), −0.025(checkout), −0.017(productcatalog). **채택**. (state_fixed 0.787 → 0.892, 최대 하락 −0.033.)
- 실패: state_fixed 3(0ed36a9ed3·77586d7c84 RANKING 줄 없음, 23063f7a6f 길이 초과), state_dynamic 1(23063f7a6f, `**RANKING:** ...`처럼 줄 앞에 `**`가 붙어 파싱 실패).

## 반복 2 — 증상 서비스(frontend)를 VERIFY에서 제외 (기각)

- 관찰: 반복 1에서도 planner가 완료 29사례 중 16사례에서 frontend를 VERIFY에 넣었다. frontend의 증상 근거는 SYMPTOM 상태가 이미 가져온다. 880fd5269a·d400057411은 VERIFY가 frontend/checkout/currency여서 정답 서비스 근거가 빠졌다.
- 변경: 두 방법 모두 VERIFY 후보에서 frontend 제외, planner 지시에 같은 내용 추가.

| method | 전체 | checkout | currency | email | productcatalog | recommendation | AC@1 | 실패 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| state_fixed | 0.910 | 0.750 | 0.967 | 0.967 | 0.933 | 0.933 | 0.772 | 2 |
| state_dynamic | 0.883 | 0.750 | 0.967 | 0.933 | 0.867 | 0.900 | 0.706 | 2 |

- 판정: state_dynamic 0.925 → 0.883. **기각, 되돌림**. 사례별로 개선 2(880fd5269a, d400057411), 악화 3(74b7f07db3, 77586d7c84, cd8184b114), 새 형식 실패 1(0ed36a9ed3). state_fixed 변화는 반복 1에서 실패했던 77586d7c84가 완료된 것뿐이다(형식 실패 변동).
- 실패: 두 방법 모두 0ed36a9ed3(RANKING 줄 없음), 23063f7a6f(길이 초과).

## 반복 3 — 상태 간 중복 제거 + 남는 예산을 VERIFY로 채우기 (기각)

- 관찰: VERIFY의 후보 pool이 CANDIDATES가 이미 고른 단위를 빼지 않아, 중복 제거 뒤 VERIFY 단위가 줄었다(예: 1bc72e3881에서 VERIFY 8개 중 3개만 남음). 남는 예산은 flat 질의로 채워졌고 대부분 frontend 로그·metric이었다(1bc72e3881에서 판정이 cartservice를 1위로 둠).
- 변경(반복 1 기준): 각 상태 pool에서 앞 상태가 고른 단위를 제외, 남는 예산은 선택된 VERIFY 서비스의 다음 VERIFY 단위를 서비스별로 번갈아 채운 뒤에도 부족하면 flat 질의로 채움.

| method | 전체 | checkout | currency | email | productcatalog | recommendation | AC@1 | 실패 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| state_fixed | 0.962 | 1.000 | 0.967 | 1.000 | 0.967 | 0.875 | 0.903 | 1 |
| state_dynamic | 0.898 | 0.875 | 1.000 | 0.833 | 0.817 | 0.967 | 0.803 | 1 |

- 판정: state_dynamic 0.925 → 0.898, emailservice −0.133. **기각, 되돌림**. state_fixed는 0.892 → 0.962로 올랐다. state_dynamic의 손실은 planner가 정답 서비스를 VERIFY에서 뺀 사례에 몰렸다(3ae525f8f8 1.0 → 0.0, VERIFY = checkout/ad/recommendation; 880fd5269a 0.5 → 0.3). 채우기가 예산을 planner가 고른 서비스에 더 몰아 주기 때문으로 본다.
- 실패: state_fixed cca1ac0113(RANKING 줄에 후보 이름 없음), state_dynamic 23063f7a6f(길이 초과).

## 반복 4 — 반복 3 + 강도 1위 서비스 항상 VERIFY (기각)

- 관찰: 반복 3의 state_dynamic 손실은 planner가 정답 서비스를 빼는 데서 왔고, 강도 1위가 정답인 사례가 25/30이다.
- 변경: 반복 3의 방식에 더해 강도 1위 서비스를 항상 VERIFY에 넣고, planner는 나머지 최대 2개를 고름(planner 지시에 "<서비스> is always verified" 추가). state_fixed는 강도 상위 3개 그대로(반복 3과 같은 설계).

| method | 전체 | checkout | currency | email | productcatalog | recommendation | AC@1 | 실패 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| state_fixed | 0.962 | 1.000 | 0.967 | 1.000 | 0.967 | 0.875 | 0.903 | 1 |
| state_dynamic | 0.920 | 0.875 | 0.875 | 1.000 | 0.850 | 1.000 | 0.856 | 2 |

- 판정: state_dynamic 0.920 < 0.925(반복 1). **기각, 되돌림**. 하락분 대부분은 판정 길이 초과 실패 2건(500db6905b, f16c5adcad; 실패 1건당 −0.025)이다. state_fixed는 반복 3과 사례별로 완전히 같아 실행의 결정성을 확인했다.
- 실패: state_dynamic 500db6905b·f16c5adcad(길이 초과), state_fixed cca1ac0113(RANKING 줄에 후보 이름 없음).

## 최종 설계 (= 반복 1)

- 상태: SYMPTOM(4) → STRUCTURE(4) → CANDIDATES(8) → VERIFY(8), 예산 변경 없음. 남는 예산은 v1과 같이 flat 질의로 채움.
- 서비스 순서: label-free 이탈 강도 = 그 서비스 metric 단위들의 이탈 표시 분(|z| ≥ 3, 처음 5분 기준) 수의 합. 동률은 첫 이탈 시각, 이름 순.
- CANDIDATES: 강도 순으로 서비스마다 이탈 분이 가장 많은 metric 단위 1개(최대 8개).
- VERIFY: `state_fixed`는 강도 상위 3개 서비스(강도 0 제외). `state_dynamic`은 planner가 강도·첫 이탈·호출 관계 개요를 보고 최대 3개 서비스와 상태 순서를 고르며, 응답이 비거나 파싱되지 않으면 `state_fixed`의 기본값을 쓴다. 서비스마다 log_template/trace_perf/metric 중 "errors, failures or abnormal behaviour of {s}" 질의로 상위 단위를 고름(v1과 같음).

## 최종 확인 실행

되돌린 최종 코드로 다시 실행한 결과가 반복 1과 사례별로 완전히 같았다(실패 사례 포함). 최종 코드가 반복 1 설계와 같고 실행이 결정적임을 확인했다.

| method | 전체 | checkout | currency | email | productcatalog | recommendation | AC@1 | 실패 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| state_fixed | 0.892 | 0.750 | 0.967 | 0.967 | 0.842 | 0.933 | 0.775 | 3 |
| state_dynamic | 0.925 | 0.875 | 0.967 | 0.967 | 0.850 | 0.967 | 0.803 | 1 |

## 요약 표 (시작 vs 최종, 개발 30사례 Avg@5)

기준선(none/flat/role_only)은 시작 실행 한 번의 값이다.

| method | 단계 | 전체 | checkout | currency | email | productcatalog | recommendation | 실패 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| none | 기준선 | 0.227 | 0.467 | 0.350 | 0.033 | 0.283 | 0.000 | 0 |
| flat | 기준선 | 0.810 | 0.633 | 0.900 | 0.800 | 0.800 | 0.917 | 0 |
| role_only | 기준선 | 0.837 | 0.592 | 0.808 | 0.850 | 0.967 | 0.967 | 2 |
| state_fixed | 시작(v1) | 0.787 | 0.775 | 1.000 | 0.775 | 0.742 | 0.642 | 4 |
| state_fixed | 최종 | 0.892 | 0.750 | 0.967 | 0.967 | 0.842 | 0.933 | 3 |
| state_dynamic | 시작(v1) | 0.887 | 0.900 | 1.000 | 0.817 | 0.867 | 0.850 | 0 |
| state_dynamic | 최종 | 0.925 | 0.875 | 0.967 | 0.967 | 0.850 | 0.967 | 1 |

## 실패와 재현 불가 부분

- 모든 실패는 판정 LLM 응답 형식 문제(`RANKING:` 접두어 누락, `**RANKING:**` 굵게 표기, 번호 목록, 4096 토큰 길이 초과)이며, `judge`·`parse_ranking`·`SAMPLING`은 고정 대상이라 고치지 않았다. 실패는 분석 규칙대로 동률(0.25)로 계산했다. 실행마다 1~4건의 실패가 생겨 방법 평균이 ±0.025~0.1 흔들리므로, 반복 간 작은 차이(예: 반복 4의 −0.005)는 이 변동 범위 안이다.
- `analyze_task070_head_b.py`는 한 실행 안의 모든 방법이 같은 사례에서 실패하면 중단된다(반복 1·2 실행). 고정 대상이라 고치지 않았다. 최종 동결 뒤 평가에서 같은 일이 생기면 후보 수를 얻는 방법을 정해야 한다.
- 판정 기준을 state_dynamic에 둔 결과, state_fixed가 더 높았던 반복 3·4 방식(0.962)은 채택하지 않았다. 이 판정 해석은 주 세션이 확인할 사항이다.

## 블라인딩

- 지시된 금지 파일·폴더를 열지 않았다. 새 실행 폴더 이름을 확인하려고 `head_b/`를 `ls`했을 때 기존 폴더 이름(`test_20261019T121820Z`, `dev_20261019T115801Z`)만 보였고, 내용은 열지 않았다.
- `analyze_task070_head_b.py`는 내 개발 실행 폴더 안에만 `analysis.json`을 썼고, 다른 실행의 `analysis*.json`은 열지 않았다.
