# RCA 임시 전처리 v1 — 사용자 승인, 저자 동일성 미확인

이 문서는 저자 답변 전 로컬 준비를 진행하기 위한 구체안이다. 저자의 실제 전처리 복원본이라는 주장이 아니다. TASK_019에서는 미적용 제안서를 작성했고, 2026-09-23 사용자가 후속 TASK_020의 구현·CSV 생성을 승인했다. 공식 코드 변경·RCA 실험·API·메일 발송은 승인 범위에 포함하지 않는다.

선택값은 [승인 설정](../configs/rca_preprocessing_proposal.json)에 모았다. 기존 파일명 proposal은 이력 때문에 유지하며 상태는 APPROVED_FOR_PREPROCESSING이다. 활성 입력 설정 inputs.json은 비어 있는 기존 상태를 유지한다. 원본 동일성 확인은 [TASK_018](../tasks/TASK_018_author_clarifications.md), 구현·입력 생성 결과는 [TASK_020](../tasks/TASK_020_apply_provisional_rca_preprocessing.md)에서 관리한다. 아래의 후보·제안 표현은 승인 당시 근거와 로컬 가정의 구분을 보존한 것이다.

2026-09-24: 다섯 CSV 생성·검증을 완료했다. 실제 유지 pod·상수 채널·로그 누락·시간 정렬 손실과 확인한 수치 차이는 [적용 결과](PROVISIONAL_RCA_PREPROCESSING_RESULT.md)에 있다. 아래 TASK_019 당시 사전 관찰과 구분한다.

## 1. 새로 확인한 실제 입력 구조

고정 revision의 ZIP 10개 중 metric ZIP 5개를 읽고, 이름이 명시된 메트릭 NPY 31개와 별도 스키마 파일 2개를 확인했다. 로그 ZIP은 파일 목록과 구조화 CSV 헤더 예시를 점검했다. 검사 도구는 Windows Python 3.12.14/NumPy 2.3.5이며 재현 환경인 WSL Python 3.11.13/NumPy 2.2.6을 변경하지 않았다.

이 검사는 배열 형태·비유한 값·상수 열·이름·타임스탬프·KPI 일치 여부를 확인한 것이다. 변수 선택이나 학습을 수행하지 않았다. 증거는 [rca_input_inventory.json](evidence/rca_input_inventory.json), 검사기는 [inspect_rca_inputs.py](../scripts/inspect_rca_inputs.py)에 있다.

| 시스템/날짜 | 초안의 KPI key | 메트릭 수 | 전체 메트릭의 공통 타임스탬프 수 | pod 합집합 / 교집합 |
|---|---|---:|---:|---:|
| PR 20210517 | Book_Info_product | 6 | 166,325 | 208 / 207 |
| PR 20210524 | Book_Info_product | 6 | 176,692 | 207 / 206 |
| PR 20211203 | ratings.book-info.svc.cluster.local:9080/* | 6 | 51,529 | 218 / 215 |
| PR 20220606 | reviews-v3 | 6 | 107,789 | 228 / 228 |
| CC 20231207 | book_info | 7 | 79,252 | 196 / 5 |

위 수는 EVT를 적용하기 전의 관찰값이다. 예상 유지 pod 수나 논문 최종 입력 크기로 간주하지 않는다. 5개 날짜는 공개 코드에 등장하는 자료를 모두 준비하려는 범위이며, 표 4가 이들을 모두 집계했다고 단정하지 않는다.

확인 결과:

- 메트릭마다 행 수·pod 목록이 다르다. 행 번호만 맞춰 합치는 방식은 사용할 수 없다.
- 제안한 5개 KPI key에서 공통 타임스탬프로 대조한 KPI 값·특성명은 일치했고, 검사한 정규 메트릭 배열에는 NaN/Inf가 없었다.
- CC의 여섯 메트릭은 196개 pod지만 storage IOPS는 5개다. 그 IOPS 5개 열은 배포 배열 전체에서 상수였다. 교집합 5개만 남기는 방식을 추천하지 않는다.
- PR 20210517/20210524에는 testuser KPI가 별도로 있다. 두 KPI를 합치지 않고, 관련 공식 JMeter/FastPC 코드가 지시하는 Book_Info_product를 초안 기준으로 선택한다.
- PR 20211203의 pod_level_data.npy 및 successful_rate 파일은 KPI_Feature 대신 jaeger_Feature 등을 가진 별도 스키마다. 6개 이름이 명시된 메트릭을 사용하며 이 별도 파일을 중복 입력으로 합치지 않는다.
- 일부 metric pod 이름에 정확히 일치하는 로그 파일이 없다. 예를 들어 필터 전 CPU 목록 기준 PR 20210517의 208개 중 99개, CC의 196개 중 72개가 구조화 로그 이름과 정확히 일치하지 않는다. pod_removed의 basename을 기준으로 확인했으며, 임의 alias 매핑으로 해결하지 않았다. 이는 사전 점검값이며 TASK_020 완료 후 유지 pod의 실제 누락 수는 적용 결과에 기록했다.
- PR 20220606의 배포 CSV 파일명은 Incoming_Success_Rate이지만 헤더·NPY 특성명은 Latency다. 의미를 실제 지연시간이라고 확정하지 않는다. 공개 값·헤더를 보존하고 저자에게 확인한다.
- 배포 README는 시나리오 PPTX는 JST, 메트릭·로그는 UTC라고 설명한다. 장애 시각을 쓰는 후속 평가에서 이 차이를 명시한다.

## 2. 근거와 로컬 선택의 경계

| 분류 | 확인한 내용 |
|---|---|
| 논문에서 명시 | EVT 기반 pod 제거 후 인과 탐색; pod 단위 RCA; PR 6종/CC 7종 메트릭 |
| MATMCD 공개 코드 | 최종 CSV 하나를 header=0으로 읽음. 각 열을 변수로 사용하며 마지막 열에서 RWR 시작. Log_tools는 Latency 열의 로그 요약을 생략 |
| LEMMA-RCA 참고 코드 | 메트릭별 NPY와 KPI/시간 구조, SPOT 파라미터, 메트릭별 100개 관측 합산, 메트릭별 그래프·RWR 후 결과 결합 |
| 새 로컬 선택 | 정확한 시간 교집합, pod 합집합, 시간 집계 없음, SPOT의 pod 유지 규칙, 여러 메트릭을 표준화 평균으로 한 열에 결합 |

FastPC는 메트릭별 그래프의 결과를 합치는 별도 방법이다. 그 전체 실행 코드를 이식하면 MATMCD의 단일 CSV→단일 그래프 경로와 달라진다. 이번 안은 MATMCD 입력 형식을 유지하기 위한 별도 준비 절차다.

MATMCD가 인용한 Wang et al. (2023b), REASON의 §3.2도 EVT 기반 개별 이상 점수를 설명하지만, MATMCD의 최종 CSV나 pod 제거 임계값을 제공하지 않는다. SPOT 파라미터의 구체적인 후보 근거는 아래 LEMMA 코드이며 두 논문의 조건을 동일시하지 않는다.

## 3. 추천 절차와 선택값

### P-01. 사례와 메트릭

위 표의 5개 날짜와 KPI key를 사용한다. PR은 CPU, memory, received/transmitted packets, received/transmit bandwidth 6종을 포함한다. CC는 해당 6종과 storage IOPS를 포함한다. 원래 날짜·KPI·메트릭을 성능을 보고 바꾸지 않는다.

PR 20210517의 KPI 선택은 JMeter_KPI.py와 실제 배포 key를 근거로 한다. 참고 FastPC의 날짜 분기는 20220517이라고 쓰여 있어 그대로 실행하면 MATMCD의 20210517과 일치하지 않는다. 공식 파일을 수정하지 않고 초안에 실제 배포 날짜를 명시했다.

### P-02. 시간 정렬

각 날짜·KPI에서 모든 선택 메트릭의 time 값이 정확히 같은 행만 오름차순으로 정렬한다. KPI 값·특성명도 동일한지 확인한다. 보간·0 채우기·최근값 채우기·장애 중심 구간 자르기를 하지 않는 안이다.

공통 시간축 전체를 사용하며 추가 다운샘플링이나 시간 집계는 하지 않는다. 참고 FastPC의 100개 합산은 별도 방법의 설정이므로 MATMCD 값으로 가져오지 않는다. 예컨대 PR 20211203 CPU 관측 74,511개 중 시간 교집합에 없는 22,982개는 이번 안에서 제외된다. 이 손실은 manifest에 명시해야 하며, '전체 원자료 무손실'로 표현하지 않는다.

시간 간격에 빈 구간이 있더라도 합성 관측을 추가하지 않는다. SPOT의 d와 n_init은 이 공통 시간축의 관측 개수이며 고정 초 단위가 아니다. 시간 정렬에 따른 분포·초기화 구간 변화는 높은 영향의 미확정 사항이다.

### P-03. pod 후보와 상수 채널

메트릭별 pod의 합집합을 후보로 삼는다. 어떤 메트릭이 특정 pod에 없으면 해당 채널이 없는 것으로 표시하고 값을 만들지 않는다. 전체 이름을 유지하며 service prefix로 축약하거나 replica를 합치지 않는다.

정렬한 구간에서 표준편차가 정확히 0인 채널은 SPOT·통합에서 제외하고 이유를 기록한다. 근접 상수 임계값은 새로 넣지 않는다. 유효한 채널이 하나도 없는 pod는 제외 이유를 남긴다. CC의 storage IOPS는 현재 5개 열 모두 상수이므로 이 규칙 아래에서는 유효 신호를 기여하지 못한다. 이를 숨기거나 다른 메트릭으로 대체하지 않는다.

### P-04. EVT/SPOT로 pod 선택

비상수 채널의 원래 수치에 LEMMA 참고 구현의 DSpot과 spot_detection 점수 계산 의미를 사용한다. 권장 후보 값은 다음과 같다.

| 값 | 후보 | 근거 |
|---|---:|---|
| d | 10 | test_FastPC_pod_metric.py의 명시 호출 |
| q | 0.0001 | 같은 호출 |
| n_init | 100개 관측 | 같은 호출 |
| level | 0.95 | 같은 호출. rca.py 함수 default 0.98, DSpot 생성자 default 0.99와 구분 |
| up/down/alert/bounded | 모두 true | 해당 pyspot.DSpot 기본값 |
| max_excess | 200 | 해당 DSpot 기본값 |

초기 100개를 초기화에 쓰되 정상 구간으로 검증됐다고 주장하지 않는다. 참고 FastPC는 100개 관측을 합산한 후 탐지하지만 이 안은 원 해상도의 공통 관측을 사용하므로, 같은 숫자여도 시간 범위가 다르다. 이 차이를 저자 문의와 민감도 검토 대상으로 남긴다.

**pod 유지 규칙은 로컬 가정**이다: 초기화 이후, 보유한 비상수 메트릭 중 하나라도 공식 이상 점수가 0보다 큰 관측이 있으면 해당 pod를 유지한다. 점수 상위 N개만 선택하거나 실행 비용 때문에 후보 수를 제한하지 않는다.

이 규칙은 긴 시계열에서 많은 pod를 남길 수 있으며, 이상 이벤트가 근본 원인이라는 뜻은 아니다. 필터 효과를 보장하지 않는다. 유지 후보가 없거나 native 탐지 오류가 나면 임계값을 자동 완화하지 않는다. 정답 pod가 제외되어도 다시 끼워 넣지 않으며, 이후 평가에서 필터 실패를 숨기거나 해당 사례만 빼지 않는다.

pyspot.py/libspot.so는 보유한 LEMMA 고정 revision을 그대로 사용한다. TASK_020에서 native 합성 입력의 반복 일치를 검증했다. 실제 처리에서도 원본 rca.py의 spot_detection 함수 AST를 수정 없이 실행한다. 문제가 발생하면 정확한 오류·필요한 변경을 기록하고 대체 알고리즘으로 바꾸지 않는다.

### P-05. 여러 메트릭을 pod 한 열로 통합 — 가장 큰 새 가정

살아남은 pod마다 보유한 비상수 메트릭 각각을 공통 시간축 전체에서 z-score로 변환한다. ddof=0을 쓰고, 이 z-score들을 동일 가중 평균한다.

~~~text
z[p,m,t] = (x[p,m,t] - mean_t(x[p,m,t])) / std_t(x[p,m,t], ddof=0)
pod[p,t] = sum_m(z[p,m,t]) / 사용 가능한 비상수 메트릭 수
~~~

이는 단위가 다른 메트릭을 한 pod 변수로 만드는 단순하고 명시적인 임시 규칙이다. MATMCD 저자가 이렇게 했다는 근거는 없다. 원본 RCA 로더에는 이 표준화·평균 단계가 없다.

각 pod의 가중치와 평균·표준편차를 저장한다. 한 채널뿐이면 그 z-score를 사용한다. 결측 채널은 0으로 넣지 않는다. 방향이 다른 메트릭은 평균에서 상쇄될 수 있고, PC의 상관·조건부 독립과 RCA 순위를 바꿀 수 있다. 전체 구간에서 통계량을 구하므로 이 안은 오프라인 입력 구성이며 온라인 탐지 평가로 해석하지 않는다.

비상수 채널들이 합쳐져 상수가 되거나, pod가 2개 미만으로 남거나, KPI가 상수이면 실패로 기록한다. 다른 메트릭만 골라 성공시키는 fallback은 두지 않는다.

### P-06. KPI·로그·출력

검증된 KPI 값은 표준화하지 않고 CSV 마지막 열에 보존한다. 헤더 Latency는 배포 NPY와 MATMCD 공개 로그 코드에 맞추되 PR 20220606의 의미 불확실성을 별도 표시한다. 타임스탬프는 그래프 변수로 넣지 않고 sidecar로 보관한다.

유지 pod는 전체 이름의 코드포인트 오름차순으로 고정한다. 원본의 set 순서에 의존하지 않는 로컬 순서 선택이며, PC의 동률 처리나 RWR 난수 경로에 영향을 줄 가능성도 기록한다.

로그는 log_data/pod_removed에서 이름이 정확히 일치하는 template/structured 쌍을 하나씩 연결한다. 중복·누락은 로그 입력 미준비로 남긴다. 이름을 비슷하게 맞추거나 빈 로그를 만들거나 로그 누락 때문에 metric pod를 제거하지 않는다. metric CSV 생성과 로그 준비 여부를 별도로 보고한다. Log_tools 요약 호출·실제 RCA 파이프라인 연결은 DIFF-09 후속 작업이다.

승인 후 실제 파일이 생길 때만 다음 외부 경로를 만든다.

~~~text
MATMCD_DATA/processed_data/lemma_rca_provisional_v1/<system>/<day>/
  <system>_<day>.csv
  timestamps.csv
  manifest.json
~~~

CSV는 UTF-8, index=False, float_format=%.17g를 제안한다. manifest에는 원본 archive revision/hash, recipe hash, 처리 환경, 시간·채널·pod 제거 내역, EVT 유지 근거, 통합 통계량, 열 순서, 로그 누락, 출력 해시를 담는다. 사용자 PC 절대 경로를 여러 코드에 넣지 않고 기존 paths.json에서 자산 루트를 읽는다.

원본 ZIP·공식 코드·기존 입력을 덮어쓰지 않는다. 승인 설정은 별도 준비 스크립트 prepare_provisional_rca.py에서만 읽는다. 원본 RCA 실행 입력에는 자동 연결하지 않는다.

최종 구현은 채널을 순차 처리하며 native 스레드 설정도 변경하지 않는다. 합성 입력의 반복 처리와 원본 행렬 처리/채널별 처리 결과를 정확히 대조한다. 검토 중 fork 자식 프로세스가 멈추었고, spawn은 합성 입력 일치를 통과했으나 8개 프로세스가 각각 31개 스레드를 사용하며 실제 처리 속도가 크게 저하됐다. 두 병렬 방식은 최종 구현에서 제거했으며 시도·중단 기록은 외부 setup 로그에 보존했다. native 알고리즘·파라미터·관측 순서·표본 수를 바꾸지 않았다.

로그 연결 결과는 ZIP 멤버 경로를 기록한 목록이다. 실제 압축 해제·요약·RCA 통합을 완료했다는 의미가 아니므로 log_input_ready는 false로 유지한다. 누락 로그와 별개로 metric CSV 준비 여부를 기록한다.

## 4. 승인 후 검증 범위

1. 지정된 원본 hash/revision과 사례·KPI·메트릭 일치 확인. 수동 추측한 다른 파일을 대신 선택하지 않는다.
2. 고정 재현 환경에서 SPOT native 호환성 및 동일 입력 처리의 반복 일치 확인. 그래프·RWR·API는 실행하지 않는다.
3. 생성 CSV의 유한 수치·열 이름·행 수·타임스탬프 대응·KPI 마지막 열·manifest/hash·pod/로그 연결을 확인한다.
4. source·패키지 pin 보존을 확인하고 저자 동일성은 UNCONFIRMED로 유지한다.
5. 입력 생성이 완료돼도 API/검색 파서/로그 통합·평가 문제는 각각 남는다. Graphviz는 후속 TASK_021 B안에서 설치·검증했고 저자 버전 확인은 TASK_022에 분리했다. INPUT-02 전체를 단순 DONE으로 바꾸지 않는다.

이 안의 적용 결과는 '임시 입력 준비'이며 논문 표 4를 재현한 결과가 아니다. 실제 비교 때 MATMCD와 제안 방법은 같은 입력·평가 조건에서 실행하고, 주요 가정의 민감도는 별도 실험 계획으로 다룬다.

## 5. 저자 문의에 추가할 질문

- 최종 pod CSV는 6/7개 메트릭을 어떻게 한 열로 표현하는가, 아니면 메트릭별 그래프/결과를 합산했는가?
- 정확한 시간 구간·메트릭별 시간 정렬·집계와 SPOT 초기화 구간, pod 유지 규칙은 무엇인가?
- CC에서 5개 pod에만 존재하며 상수인 IOPS와 다른 메트릭의 196개 pod를 어떻게 처리했는가?
- PR의 product/testuser/ratings/reviews KPI 중 실제 표 4에 사용한 것은 무엇인가?
- PR 20220606의 Latency는 실제로 성공률을 담는가? 이 사례가 표 4에 쓰였는가?
- 필터 후 metric pod에 로그가 없을 때 제외·이름 매핑·별도 원본 로그 중 무엇을 사용했는가?
- 저자 원본은 현재 배포본과 같은가? 논문의 216/168 pod 및 131,329/109,351 길이와 어떤 단계에서 대응하는가?

## 근거

- [MATMCD 논문 §4.3](https://aclanthology.org/2025.findings-acl.36.pdf)
- 공식 MATMCD 고정 커밋의 Utils/data.py, LEMMA_experiment.py, Log_tools.py
- LEMMA-RCA 고정 커밋의 IT/data preprocessing/metric_json2npy.py, JMeter_KPI.py, Baseline/FastPC/test_FastPC_pod_metric.py, rca.py, pyspot.py
- [LEMMA-RCA 공식 저장소](https://github.com/lemma-rca/rca_baselines)
- [Wang et al., 2023b / REASON §3.2](https://nijingchao.github.io/paper/kdd23_reason.pdf)
- 다운로드 manifest와 이번 [입력 점검 증거](evidence/rca_input_inventory.json)
