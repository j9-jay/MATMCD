# 승인된 임시 RCA 전처리 v1 적용 결과

2026-09-24 KST: 승인 프로필 lemma_rca_provisional_v1의 다섯 metric CSV 생성과 별도 산출물 검증을 완료했다. 상태는 PREPARED_PROVISIONAL이다. 저자 전처리와의 동일성은 UNCONFIRMED이며 논문의 RCA 결과를 재현한 것이 아니다.

## 입력별 상태

| 시스템 / 날짜 | 상태 | 행 수 | 유지 pod / 후보 | 정확한 로그 쌍 | 로그 쌍 누락 |
|---|---|---:|---:|---:|---:|
| Product Review / 20210517 | 생성·검증 통과 | 166,325 | 208 / 208 | 109 | 99 |
| Product Review / 20210524 | 생성·검증 통과 | 176,692 | 207 / 207 | 112 | 95 |
| Product Review / 20211203 | 생성·검증 통과 | 51,529 | 218 / 218 | 154 | 64 |
| Product Review / 20220606 | 생성·검증 통과 | 107,789 | 228 / 228 | 148 | 80 |
| Cloud Computing / 20231207 | 생성·검증 통과 | 79,252 | 196 / 196 | 124 | 72 |

각 CSV는 pod 열 뒤에 배포 KPI를 보존한 Latency 열 1개를 둔다. 행 수는 선택 메트릭의 정확한 공통 시간축이다. 원자료의 모든 관측이 보존됐다는 의미는 아니다. 시간 교집합 밖으로 제외된 행은 manifest에 기록한다.

## 저장 위치와 추적 정보

자산 루트는 configs/paths.json 한 곳에서 관리한다. 이 PC의 생성 경로는 E:/연구/MATMCD_DATA/processed_data/lemma_rca_provisional_v1이다.

~~~text
<자산 루트>/processed_data/lemma_rca_provisional_v1/<system>/<day>/
  <system>_<day>.csv
  timestamps.csv
  manifest.json
~~~

manifest는 출처 revision·원본 ZIP 해시, 적용 설정, 런타임, 정렬 전후 크기, 채널 평균·표준편차와 이상 점수 근거, pod 유지 결정, 로그 연결 목록, 출력 SHA256을 담는다. Git 관리용 [생성 요약](evidence/rca_preprocessing_applied.json)과 [산출물 검증·출력 해시](evidence/rca_preprocessing_validation.json)를 남겼다. 전체 manifest와 데이터는 외부 자산에 보관한다. CSV 5개의 합계 크기는 2,523,657,083바이트다.

최종 순차 실행 기록: 자산 루트 아래 logs/setup/provisional_rca_20260923T112815216854Z. 이전 실행 방식 검토·중단 기록은 [TASK_020](../tasks/TASK_020_apply_provisional_rca_preprocessing.md)에 있다.

## 확인된 해석상 제한

- 다섯 사례 모두 후보 pod가 전부 유지돼 pod 감소는 0개다. 승인한 규칙은 긴 시계열의 비상수 메트릭 중 하나라도 양의 이상 점수가 있으면 유지한다. 유지됐다는 사실은 근본 원인이라는 의미가 아니며, pod 필터가 논문과 같거나 효과적이었다고 주장하지 않는다. 후보 수를 줄이기 위해 설정을 변경하지 않았다.
- 여러 메트릭을 pod 하나의 z-score 평균으로 결합하는 방식, 시간 교집합, pod 유지 기준은 로컬 가정이다. 인과 그래프와 RCA 순위에 영향을 줄 수 있다.
- 로그는 ZIP 내부에서 전체 pod 이름이 정확하게 대응하는 template/structured 쌍을 기록한 상태다. 압축 해제·요약·RCA 연결은 미완료이며 모든 사례의 log_input_ready는 false다. 누락을 임의 이름 매핑이나 빈 로그로 채우지 않았다.
- PR 20220606의 Latency 의미와 공개 날짜 5개의 논문 표 4 대응은 저자 확인이 필요하다.

이 임시 입력에서 후속 방법의 성능이 개선되더라도 저자 원본 입력에서도 같은 개선 방향이 나온다고 보장할 근거는 없다. 같은 입력·평가 조건에서 방법을 비교하고, 저자 답변에 따른 전처리 차이와 민감도를 별도로 검토해야 한다.

### 시간 정렬과 상수 채널

| 사례 | 상수라 제외한 채널 / 전체 채널 | 시간 교집합 밖 제외 행 |
|---|---:|---|
| PR 20210517 | 6 / 1,244 | CPU 0, memory 66, 네트워크 각 30 |
| PR 20210524 | 6 / 1,238 | 모든 메트릭 0 |
| PR 20211203 | 23 / 1,302 | CPU 22,982, memory 69, 네트워크 각 6 |
| PR 20220606 | 26 / 1,368 | CPU 0, memory 73, 수신 packet/bandwidth 각 25, 송신 packet/bandwidth 각 6 |
| CC 20231207 | 42 / 1,181 | CPU 36, memory 47, 네트워크 각 257, IOPS 42,936 |

상수 채널 제외와 pod 제거는 다르다. 다른 메트릭에 양의 이상 점수가 있는 pod는 유지됐다. CC IOPS의 5개 채널은 정렬 구간에서도 모두 표준편차 0이어서 탐지·통합에서 제외됐다. 나머지 pod의 IOPS는 없는 채널이며 0으로 채우지 않았다.

## 검증과 후속 상태

각 사례의 float64 CSV·타임스탬프 저장 후 정확 재읽기와 모든 선택 메트릭 간 KPI 일치를 확인했다. [별도 검증기](../scripts/verify_provisional_rca.py)에서도 다섯 사례의 출력 해시·크기·열 순서·유한 수치·비상수성, 원본 CPU NPY의 KPI/타임스탬프와 정확 일치, 기록된 EVT 결정·로그 목록 일관성을 확인했다. 실제 PC·RWR·LLM·검색·RCA 평가를 실행하지 않았다.

공식 소스 37개는 고정 ZIP과 바이트 동일하다. LEMMA 함수·wrapper·native binary도 보존됐고, Python 3.11.13 / NumPy 2.2.6 / pandas 2.2.3 및 승인 환경의 201개 패키지 버전이 유지됐다. [native 시스템 라이브러리 기록](evidence/rca_native_system_runtime.json)도 남겼으며 저자 시스템과의 동일성은 미확인이다.

검증기 첫 실행은 ZIP 경로의 첫 요소를 잘못 제거하여 FileNotFoundError가 발생했다. 로컬 검증기의 경로 처리만 교정하고 다시 실행하여 통과했다. [실패·수정 이력](evidence/rca_preprocessing_validation_attempts.json)을 보존했고 CSV·과학적 코드·전처리 조건은 바꾸거나 재생성하지 않았다.

### 공식 pandas 읽기 방식에서 관찰한 수치 차이

공식 load_Lemma_data와 같은 pd.read_csv(..., header=0)로 형식·열·유한 수치 호환성을 확인했다. CSV 자체의 float64 정확 재읽기는 통과했지만 pandas 기본 파서는 NumPy 재읽기와 비트 단위로 같지 않았다.

| 사례 | 전체 값 최대 절대 차이 | KPI 최대 절대 차이 |
|---|---:|---:|
| PR 20210517 | 3.637978807091713e-12 | 3.637978807091713e-12 |
| PR 20210524 | 3.637978807091713e-12 | 3.637978807091713e-12 |
| PR 20211203 | 1.7763568394002505e-15 | 0 |
| PR 20220606 | 3.552713678800501e-15 | 1.1102230246251565e-16 |
| CC 20231207 | 2.842170943040401e-14 | 2.842170943040401e-14 |

파서 옵션이나 CSV 값을 교체하지 않았다. 위는 읽기 차이의 관찰값이며 인과 그래프·RCA 순위에 대한 영향은 실험하지 않았다. 전체 함수 실행이나 원본 실행 경로 연결을 완료했다는 의미도 아니다.

RCA 전체 실행 준비는 아직 미완료다. 원본 실행 입력 설정 configs/inputs.json은 자동 변경하지 않았으며, 저자 원본 입력·API·검색 파서·로그 통합·실제 순위의 평가 연결 등은 [남은 항목](ORIGINAL_LOCAL_ISSUES.md)에서 관리한다. Graphviz 설치는 후속 TASK_021 B안에서 완료했고 저자 버전 확인은 TASK_022 A안 TODO로 분리했다. 실제 RCA·평가·표 4 비교 TASK_007/008/009와 저자 문의 TASK_018은 TODO로 유지한다.

관련 문서: [승인 명세](PROVISIONAL_RCA_PREPROCESSING.md), [적용 설정](../configs/rca_preprocessing_proposal.json), [TASK_020](../tasks/TASK_020_apply_provisional_rca_preprocessing.md), [저자 문의 초안](../tasks/TASK_018_author_clarifications.md).
