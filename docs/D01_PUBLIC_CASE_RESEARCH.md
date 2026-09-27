# D01 공개 유사 사례 조사

조사일: 2026-09-25. 사용자 요청은 인터넷에서 같은 문제가 보고됐는지 확인하는 것이다. 실험 조건 변경·누락 정책 적용·제3자 코드 실행은 하지 않았다.

후속 결정: 이 문서는 조사 당시의 기록이다. 이후 사용자가 로그 쌍 불일치를 유지하여 진행하도록 승인했고 TASK_035에서 [부재 표시 정책](RCA_LOG_POLICY.md)을 준비했다. 아래 조사로 원인을 확정한 것은 아니며, 현재 승인은 후속 사용자 결정에 근거한다.

## 결론

**메트릭 pod에 대응하는 template/structured CSV 쌍이 없다는 D01과 동일한 문제를 직접 보고하고 원인을 확정하거나 수정한 공개 이슈는 조사 범위에서 찾지 못했다.** 검색 결과 부재가 다른 사람에게 문제가 없었다는 증거는 아니다.

다만 같은 Cloud Computing 20231207 자료를 사용한 공개 프로젝트를 찾았다. 그 프로젝트의 메트릭 pod 196개 이름은 우리 목록과 대소문자까지 정확히 일치하며, 우리에게 로그 쌍이 없는 72개도 모두 포함한다. 저장된 노트북 출력은 structured CSV 195개 처리를 기록한다. 이 숫자는 우리 배포 ZIP의 전체 로그 쌍 수와 같다. 해당 구현은 pod별 완전한 대응을 요구하지 않고 서비스 이름으로 묶어 처리한다. 이는 비교할 만한 처리 사례이지만 **MATMCD 저자의 처리 방식이나 D01의 확정 해결책은 아니다.**

## 1. 같은 CC 날짜를 사용한 제3자 구현

출처: [dorado-daniel/lemzha-k](https://github.com/dorado-daniel/lemzha-k), 고정 commit `a6e62ef6f29d7112a96a8db7b3c017c3e246fe08` (2026-02-15). LEMMA 데이터를 이용한 별도 멀티모달 RCA 프로젝트이며 MATMCD 공식 구현이 아니다.

- [20231207 manifest](https://github.com/dorado-daniel/lemzha-k/blob/a6e62ef6f29d7112a96a8db7b3c017c3e246fe08/core_multimodal_tmp/20231207/manifest.json): pod 196개, 서비스 그룹 48개, 시간점 91개를 기록한다. pod 이름 전체를 우리 조사 결과와 정확 문자열로 대조하여 집합이 동일함을 확인했다.
- [데이터 변환 노트북](https://github.com/dorado-daniel/lemzha-k/blob/a6e62ef6f29d7112a96a8db7b3c017c3e246fe08/notebooks/02-Transform-Data/Transform-Data-Lemma.ipynb): 저장된 20231207 실행 출력에서 structured 파일 195개 처리를 확인했다. 출력은 제3자가 저장한 기록이며 우리가 재실행한 결과가 아니다.
- 같은 노트북의 `aggregate_logs_to_services`는 실제 존재하는 `*_structured.csv`만 순회한다. `_process_single_log_file`과 `build_pod_to_service_from_pods`는 pod 이름을 `-`로 나눈 첫 부분을 서비스 키로 사용한다. 서비스·시간 bin의 기록이 없으면 빈 문자열을 쓴다.
- 그러므로 metric pod마다 두 파일이 반드시 있는지 검사하는 현재 MATMCD 연결 방식과 다르다. 다른 replica의 로그가 같은 그룹에 들어갈 수 있고, 이름 첫 부분이 같은 별개 구성 요소도 합쳐질 수 있다. 예를 들어 `aws-node`와 `aws-load-balancer-controller`는 모두 `aws` 그룹이다.
- 45분 구간, 30초 bin, 각 bin의 빈도 상위 10개 template 텍스트 등 독자 조건도 사용한다. 이 구현을 그대로 적용하면 입력 단위·시간 범위·로그 표현이 바뀐다. 이번 조사에서는 채택하지 않았다.

수량 해석에 주의한다. **196 - 195 = 누락 1개가 아니다.** 우리 ZIP에서는 메트릭과 로그 이름의 교집합이 124개, 메트릭에만 있는 이름이 72개, 로그에만 있는 이름이 71개다. 제3자가 전체 로그 파일명 목록과 사용 ZIP의 revision/hash를 공개한 것은 확인하지 못했으므로, 그쪽도 정확히 같은 72개가 누락됐다고 독립 검증한 것은 아니다. 동일한 메트릭 이름 집합과 같은 전체 로그 파일 수가 확인된 것이다.

[로컬 대조 결과](evidence/d01_external_comparison_20260925.json), [고정 출처·파일 SHA256](evidence/d01_external_reference_20260925.json).

## 2. 저자 답변이 있는 LEMMA 재현 문의

[KnowledgeDiscovery/rca_baselines issue #1](https://github.com/KnowledgeDiscovery/rca_baselines/issues/1), 2024-06-17 개설, 닫힘.

사용자는 논문 수치 재현이 어렵다며 Hugging Face 데이터 버전, 전처리 결과의 의미, 디렉터리 구조, 실행 및 결과 저장 지침을 요청했다. 이어 NPY의 해석, 전처리 반복 필요 여부, 경로와 import 문제도 질문했다.

- [2024-06-18 저자 답변](https://github.com/KnowledgeDiscovery/rca_baselines/issues/1#issuecomment-2176756987): FastPC 예시를 포함한 README를 보강했다고 안내했다.
- [2024-06-21 저자 답변](https://github.com/KnowledgeDiscovery/rca_baselines/issues/1#issuecomment-2183110072): 공개 전처리 데이터를 사용하면 해당 안내의 2~5단계를 다시 수행할 필요가 없고, 코드를 갱신했다고 답했다.

이 사례는 공개 자료 해석·재현 절차가 다른 사용자에게도 불명확했다는 근거다. **누락 pod 목록, 대응 로그 추가 제공, replica 매핑, MATMCD 후보 제외 방침에 대한 답변은 아니다.** 따라서 전처리를 임의로 다시 돌리는 것이 D01의 공식 해결책이라고 해석하지 않는다.

GitHub 웹 본문에는 댓글이 생략되는 경우가 있어 REST API의 댓글도 확인했다. [댓글 원문 기록](evidence/d01_related_issue_comments_20260925.json).

## 3. 저자가 확인한 CC 시간대 문제 — 다른 종류의 불일치

[Cloud_Computing_Preprocessed discussion #1](https://huggingface.co/datasets/Lemma-RCA-NEC/Cloud_Computing_Preprocessed/discussions/1), 2025-12-07 개설.

사용자는 20231221 시나리오에서 PPTX의 장애 시각과 관측 데이터가 맞지 않는다고 질문했다. 2025-12-12 LEMMA 조직의 KnowledgeDiscovery 계정은 PPT 시각은 JST, metric/log 데이터는 UTC여서 9시간 차이가 정상이라고 답했다.

시간대 변환을 놓치면 장애 구간을 잘못 선택할 수 있다. 그러나 D01은 전체 ZIP의 파일명까지 조사한 뒤 확인한 **파일 쌍의 부재**다. 시간대를 변환해도 존재하지 않는 파일이 생기지 않는다. 이 토론은 D01의 원인이나 해결책으로 분류하지 않는다. 현재 시간축 설정을 바꾸지 않았다.

## 4. 조사 범위와 한계

공개 웹 검색과 각 서비스의 실제 API 목록을 함께 확인했다. GitHub는 `state=all`로 닫힌 항목을 포함했으며 반환 수가 페이지 한도 100보다 적었다. API의 issue 목록에 PR도 포함되므로 분리했다.

| 조사 위치 | 실제 API에서 확인한 항목 | D01 직접 보고 |
|---|---|---|
| D2I-Group/matmcd | issue 1개: Causal DAG 데이터 요청, 댓글 없음 | 미발견 |
| lemma-rca/rca_baselines | issue 0개, PR 1개 | 미발견 |
| KnowledgeDiscovery/rca_baselines | issue 4개, PR 3개; 재현 안내·Nezha 버전·PR 성능·SWaT 관련 | 미발견 |
| Product_Review_Preprocessed / Original | 각각 링크·라이선스 정리 PR 1개 | 미발견 |
| Cloud_Computing_Preprocessed | 시간대 discussion 1개, 메타데이터 PR 1개 | 미발견 |
| Cloud_Computing_Original | 링크·라이선스 정리 PR 1개 | 미발견 |

Hugging Face 네 데이터셋은 목록 수와 상세 조회 수가 일치하고 닫힌 discussion 수는 모두 0이었다. 검색 엔진이 보여주는 과거 Community 수와 실시간 API 수가 달라 API 결과를 기준으로 했다. [조회 URL·원문 응답](evidence/d01_public_issues_20260925.json).

대표 검색어: `"LEMMA-RCA" "missing" logs`, `"MATMCD" "log" "issue"`, `"Lemma-RCA-NEC" "logs" "missing"`, `"rca_baselines" "pod" "missing"`, `"LEMMA-RCA" "logs" "mismatch"`, `"Product_Review_Preprocessed" "missing"`, `"Cloud_Computing_Preprocessed" "missing"`, `"matmcd" "FileNotFoundError"`, `"pod_removed" "missing"`, `"messages_structured.csv" "missing" "LEMMA"`, 누락 pod의 정확한 이름 및 중국어 로그 누락 검색. 검색이 반환한 일반 소개·2차 요약은 원인 근거로 채택하지 않았다.

이 조사는 공개되고 검색/조회 가능한 자료에 한정된다. 비공개 문의·삭제된 게시물·검색에 잡히지 않는 재현 코드를 모두 조사했다는 뜻이 아니다. 일반 Kubernetes 수집 문제만으로 이 데이터셋의 누락 원인을 추정하지 않았다.

## 5. D01에 대한 후속 판단

1. 로컬 매칭 코드를 고치면 빠진 파일이 나타난다는 근거는 이번 인터넷 조사에서도 얻지 못했다.
2. 같은 자료를 사용한 외부 구현의 서비스 집계는 참고 사례다. 이를 원본 MATMCD의 누락 처리로 간주하거나 무단 적용하지 않는다.
3. 저자 확인의 핵심은 최종 MATMCD 후보 pod 목록, metric/log의 대응 단위, replica 교체·수집 기간, 누락 후보 처리와 추가 배포 로그 유무다. [TASK_018](../tasks/TASK_018_author_clarifications.md)에 기존 질문과 연결했다. 메일·이슈는 게시하지 않았다.
4. TASK_038은 조사 완료다. TASK_035의 D01 정책 결정은 BLOCKED로 유지하며 B안이 승인되거나 원인 해결된 것으로 처리하지 않는다.

자료는 외부 자산의 `raw_downloads/github_dorado_lemzha_k_reference/<commit>/`에 읽기용으로 보존했다. 공식 코드·활성 입력·전처리·모델·평가 설정은 이번 조사에서 변경하지 않았다.
