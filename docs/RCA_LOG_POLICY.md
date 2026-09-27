# 승인된 D01 로그 부재 처리

2026-09-25 사용자는 로그 쌍 불일치를 유지한 채 진행하도록 결정했다. 기존 D01 B안의 후보 유지·부재 명시를 적용하며, 서비스 단위 합치기나 다른 replica 로그 대입은 적용하지 않는다. 원 논문과 동일한 조건인지는 UNCONFIRMED다.

## 적용 범위

아래는 TASK_039 이후 현재 활성 세 사례다. 최초 5개 사례(1,057개 pod, 647쌍, 부재 410개)의 검증 기록과 외부 근거 파일은 보존한다. 제외 사례를 현재 요약/평가에 포함하지 않는다.

| 사례 | 유지하는 pod 후보 | 정확한 로그 쌍 | 부재로 명시 |
|---|---:|---:|---:|
| PR 20211203 | 218 | 154 | 64 |
| PR 20220606 | 228 | 148 | 80 |
| CC 20231207 | 196 | 124 | 72 |
| 합계: 사례별 pod 수 | 642 | 426 | 216 |

각 사례의 Latency 열 1개는 pod가 아닌 입력 KPI로 따로 분류한다. KPI 이름만 보고 물리적 의미·역할·장애 사건을 추정하지 않는다.

없는 pod에 제공하는 문장은 [승인 설정](../configs/rca_log_policy.json) 한 곳에서 관리한다.

```text
No matching log evidence is available for this pod in this case.
This does not imply normal operation or absence of causal influence.
```

이는 인위적 로그나 생성형 요약이 아니라 데이터 가용성 표시다. `evidence_available=false`, `reason=exact_log_pair_unavailable`, `underlying_cause=UNKNOWN`으로 기록한다. 후보 수·열 순서·메트릭 값·그래프·정답은 바꾸지 않는다. 부재를 이유로 후보의 방향쌍 판단을 건너뛰거나 정상/비원인으로 고정하지 않는다.

## 재시작·종료와 로그 부재의 관계

이번 결정은 누락 원인을 확정한 것이 아니다. 컨테이너 재시작 시 이전 로그가 남거나 외부 수집 저장소가 pod의 수명과 별개로 보존할 수 있다. 반대로 node의 pod eviction이나 수집 범위·기간·필터 때문에 사용 가능한 자료가 줄어들 수도 있다. [Kubernetes 공식 로그 문서](https://kubernetes.io/docs/concepts/cluster-administration/logging/#how-nodes-handle-container-logs).

따라서 `재시작/종료 때문에 로그 없음`을 사실·라벨·LLM 근거로 넣지 않는다. 현재 확정한 것은 이 공개 자료에 해당 이름의 두 CSV가 없다는 점이다. [TASK_037 분석](D01_LOG_COVERAGE_ANALYSIS.md)에서 원시 노드 로그의 관련 언급과 pod 자체 로그를 구분한 결과도 그대로 유지한다.

## 구현과 출력

- [rca_log_evidence.py](../scripts/rca_log_evidence.py)는 검증된 입력 manifest·TASK_032의 파일 출처와 현 파일 경로/크기를 대조한다. CSV 전체 SHA256과 열 순서도 기존 검증값에 맞는지 확인한다.
- 파일 쌍이 원래 없던 pod만 부재를 허용한다. 알려진 파일이 사라짐, 한쪽만 존재, 모호한 대응, 파일 크기 변경, 새 파일 등장 등은 조용히 부재로 바꾸지 않고 오류로 중단한다.
- `dispatch_summary`는 정확한 로그 쌍이 있는 pod만 요약 콜백에 전달한다. 부재 pod와 KPI는 LLM 호출 없이 고정 문장을 반환한다. 사용 가능한 로그의 프롬프트·이벤트 선택은 이 모듈이 변경하지 않는다.
- `finalize_node_information`은 각 사례에서 사용 가능한 pod에 대한 실제 요약을 받은 뒤, 부재/KPI 표시를 결정적으로 결합한다(현재 세 사례 합계 426개). 부재 pod를 생성형 내용으로 덮거나 노드를 누락한 결과는 거부한다. 입력 열 순서와 이름을 보존한다.
- 시스템 요약에 함께 제공할 `system_coverage_notice`도 각 사례의 전체 후보·로그 가용 수로 생성한다. 내용 요약과 별도 필드로 유지한다.

출력은 `MATMCD_DATA/processed_data/lemma_rca_log_evidence_v1/<system>/<day>.json`이다. 기존 5개 근거 manifest는 보존하며 현재 [inputs.json](../configs/inputs.json)의 `rca_log_evidence_manifests`는 선택한 3개만 참조한다. 사례 선택은 scope.json 한 곳에서 관리한다. 실제 요약·가짜 로그 CSV·RCA 결과 파일은 생성하지 않는다. 자산 루트는 기존 paths.json을 따른다.

## 검증과 실제 통합의 경계

[오프라인 검사](../scripts/check_rca_log_evidence.py)는 실제 사례 목록으로 부재/KPI의 요약 콜백 미호출, 정확한 쌍만 전달, 전체 후보/순서 유지, 생성 내용으로 부재 덮기 거부, 파일 소실·부분 쌍·새 파일·읽기 실패 처리 등을 검사한다. 인공 콜백 문자열은 검사용이며 실제 요약으로 저장하지 않는다. 공식 소스는 고정 ZIP과 바이트 비교한다. [TASK_035](../tasks/TASK_035_missing_log_policy.md)에 실제 검사 결과를 남긴다.

원본 로그 44.1GB의 전체 바이트는 TASK_032에서 검증했다. 이번 정책 검사는 기록된 SHA256을 출처로 보존하고 현재 경로·크기를 확인하며, 로그 본문 전체 재해시·파싱을 반복하지 않는다. CSV 5개와 전처리 manifest는 이번에도 기존 해시와 비교한다.

WSL의 기존 Python 환경에서 실행하는 준비 명령:

```bash
cd /mnt/e/연구/MATMCD
../MATMCD_DATA/environments/d2i_matmcd_py311/bin/python -B scripts/check_rca_log_evidence.py --prepare
```

이 명령은 모델·RCA를 실행하지 않는다. 같은 근거 manifest는 재사용하지만 내용이 다르면 덮어쓰지 않는다.

**TASK_024의 실제 로그 요약·RAG·로컬 LLM 연결은 아직 미완료다.** 해당 경로를 구현할 때 이 모듈의 고정 부재 정보와 전체 후보 검사를 반드시 호출해야 한다. 공통 readiness 도구는 승인된 부재와 손상/소실을 구분하지만 전체 실행 READY를 자동으로 선언하지 않는다. D02의 대용량 읽기·D03/D04의 과학적 동작/평가 결정은 이번 승인에 포함되지 않는다.
