# D01 로그 쌍 미확인의 원인 분석

2026-09-25, TASK_037. **로컬 파일명/경로 파싱이 있는 파일을 놓친 사례는 확인되지 않았다.** 다섯 사례의 410개 pod는 공식 전처리 로그 ZIP에 이름이 일치하는 template/structured 파일이 모두 없다. 그러나 이를 원시 자료 어디에도 해당 pod 정보가 없다는 뜻으로 확대할 수 없다.

현재 확정한 문제는 **공개 metric 후보 목록과 공개 pod 로그의 범위가 일치하지 않으며, 임시 CSV의 모든 후보에 공개 MATMCD 로그 요약 함수를 적용하려 하면 입력 계약이 충족되지 않는 것**이다. 각 pod가 왜 배포 로그에서 빠졌는지, MATMCD 저자가 어떤 최종 후보 목록을 사용했는지는 모두 확정하지 못했다. 로그 재생성·후보 제외·D01 B안은 적용하지 않았다.

## 1. 로컬 파싱/연결 오류를 점검한 결과

| 검사 | 결과 |
|---|---|
| 지정 pod_removed 폴더를 잘못 골랐는가 | ZIP 전체 폴더를 독립 검색해도 추가 정확 쌍 0개 |
| template 또는 structured 중 한쪽만 없는가 | 문제의 410개는 전부 양쪽 파일 부재. 일부 파일만 존재/중복으로 거부된 경우 0개 |
| 대소문자·앞뒤 공백·Unicode 표기 차이인가 | 정규화해서 새로 발견한 대응 0개 |
| namespace/container 접두·접미 때문에 전체 pod 이름을 놓쳤는가 | 전체 pod 이름을 포함한 다른 파일명도 0개 |
| 메트릭 NPY의 Pod_Name을 잘못 변환했는가 | 승인된 6개(PR)/7개(CC) metric NPY를 직접 다시 읽어 이름 합집합과 비교. 활성 후보 1,057개(사례별 합계) 모두 원본에 존재 |
| CSV와 manifest의 이름/순서가 다른가 | 모든 헤더 일치 |
| 저자가 이미 만든 로그 특징 NPY에 해당 pod가 있는가 | 10개 NPY의 Node_Name을 직접 대조했지만 문제의 410개와 교집합 0개 |
| 로컬 Drain 파싱 중 파일을 버렸는가 | 로컬에서는 Drain을 실행하지 않았다. 저자가 배포한 CSV를 바이트 그대로 복사했으며 파일명 판정은 본문 파싱 전에 수행 |

| 사례 | 활성 metric pod | 정확한 로그 쌍 | 두 파일 모두 없음 | 로그 frequency NPY의 pod 수 | golden signal NPY의 pod 수 |
|---|---:|---:|---:|---:|---:|
| PR 20210517 | 208 | 109 | 99 | 95 | 76 |
| PR 20210524 | 207 | 112 | 95 | 95 | 76 |
| PR 20211203 | 218 | 154 | 64 | 132 | 89 |
| PR 20220606 | 228 | 148 | 80 | 124 | 108 |
| CC 20231207 | 196 | 124 | 72 | 98 | 53 |

frequency/golden signal 수는 각 배포 파일의 전체 목록이며 활성 metric과의 교집합 수라는 뜻은 아니다. 이들 특징 파일 자체에도 별도 필터가 있어 원시 로그의 전체 목록과 같다고 간주하지 않는다. 각 특징 파일의 모든 이름에는 대응하는 배포 로그 쌍이 있었다.

실물 근거: [독립 진단 전체 결과](evidence/d01_log_investigation_20260925T114438415224Z.json). 공식 37파일과 configs 전체의 전후 해시도 동일했다. 앞선 TASK_032의 ZIP 전체 SHA256·추출 CRC 검증 이력은 그대로 유지한다.

## 2. 공개 전처리 코드가 보여주는 범위 차이

고정 LEMMA 코드 c560d8cc39c19f04c9ae74fac2404b1e5e8c3b4d 기준:

- IT/data preprocessing/metric_json2npy.py:73~124는 metric JSON의 `result['metric']['pod']`에서 이름을 구성하고 관측 수·공통 시간축 조건을 적용한다. 로그 존재 여부로 목록을 만들지 않는다.
- json2message.py:51~84는 실제 수집된 Elasticsearch hit 중 `_source.kubernetes.pod_name`이 있는 기록만 pod 메시지로 분리한다. systemd 기록은 별도 node 경로로 분리한다. metric에 등장한 pod마다 빈 메시지 파일을 생성하는 구조가 아니다.
- drain3_parse.py는 이미 존재하는 메시지 파일마다 template/structured CSV를 만든다. 정상 처리라면 두 파일을 함께 쓰며, 파일 처리 예외를 warning으로 기록하고 다음 파일로 넘어갈 수 있다. 저자의 당시 실행 로그가 없으므로 **상류 전처리 실패 가능성까지 배제하지는 않는다**.
- log_frequency_extraction.py:158~173은 짧은 structured 자료를 제외한다. 따라서 로그 특징 NPY의 pod 수가 더 적은 것은 별도 단계의 필터와 부합한다. 이것이 CSV 쌍 자체 부재의 원인이라고 주장하지 않는다.
- Baseline/multimodal/RCA_methods_combined.py:91~117 및 Baseline/FastPC/test_FastPC_pod_combine.py:124~137은 metric/log 목록의 교집합을 구성한다. 이는 데이터셋 저자 코드가 모달리티별 목록을 따로 취급한다는 근거다. **MATMCD의 표 4도 같은 교집합을 사용했다는 증거는 아니다.**

[공식 LEMMA 저장소](https://github.com/lemma-rca/rca_baselines), 로컬 고정 원본은 MATMCD_DATA/raw_downloads/github_lemma_rca_preprocessing에 있다. 위 코드는 읽기만 했으며 실행·수정하지 않았다.

## 3. 원시 자료를 추가로 확인한 결과

### Cloud Computing

기존 원자료 ZIP의 장애 전 configuration에는 로그 쌍이 없는 **72개 pod가 모두 존재**했다. 따라서 오타로 만든 가상의 pod가 아니다. 이후 구성에는 이 중 66개가 존재하며, 시점별 pod 교체도 고려해야 한다.

dataplane/host gzip 26개, 134,519행, 비압축 46,390,271바이트를 전부 읽었다. 다음 3개의 정확한 이름은 원시 노드 로그에서 실제로 언급된다.

- aws-node-sp6j9
- productcatalogservice-64b6d7956c-5r244
- rabbitmq-945d8c4f9-fmrmx

각각 dataplane와 host에서 6행씩 확인했다. 같은 사건이 두 수집 경로에 중복됐을 수 있으므로 12개 독립 사건으로 해석하지 않는다. 이들은 kubelet/host 기록의 **대상 언급**이며 해당 pod의 메시지 스트림과 같지 않다. 이를 기존 pod 로그로 조용히 재분류하지 않았다.

원자료의 Log/application 폴더에는 27바이트 aws-logs-write-test 한 개만 있다. 다른 범주에는 ALB·dataplane·host·master-node·performance가 있다. 따라서 공개 원자료의 application 폴더에서 누락 pod의 애플리케이션 메시지를 그대로 복구할 수 있다는 근거도 없다. master-node/performance 본문과 모든 ALB 내용을 전수 분석한 것은 아니다.

### Product Review

[공식 원자료](https://huggingface.co/datasets/Lemma-RCA-NEC/Product_Review_Original/tree/63aa4abe7dd7217d9b0b108894c7d893e2b29aef)의 고정 revision에서 4개 ZIP의 중앙 디렉터리를 HTTP Range로 확인했다. 전체 원자료는 약 53.6GB다. 원격 조회는 HTTP 206·Content-Range·길이를 확인했으며 전체 ZIP SHA256을 검증한 것으로 표시하지 않는다.

- 20210517/20211203은 원시 JSON 엔트리를 직접 읽을 수 있다.
- 20210524/20220606의 로그는 큰 중첩 ZIP으로 들어 있다. 전체 다운로드/압축 해제는 하지 않았다.
- 20210517/20211203에서 사전에 정한 규칙(정렬된 infra JSON의 첫/중간/마지막, app JSON의 중간)으로 8개를 선택해 75,484개 원시 hit를 읽었다. 해당 표본에서는 누락 목록의 pod가 `_source.kubernetes.pod_name`으로 등장하지 않았다.
- **표본 부재는 전체 원시 로그 부재의 증거가 아니다.** 원문 185,957,531바이트와 멤버 CRC·SHA256·선택 규칙을 외부 자산/증거에 보존했다. 이는 원인 조사용 표본이며 RCA 입력을 샘플링/축소한 것이 아니다.

[원격 ZIP 목록과 검증 범위](evidence/d01_pr_original_remote_index.json), [원시 JSON 표본과 pod별 집계](evidence/d01_pr_raw_log_samples.json).

## 4. 다른 이름의 로그가 있는 경우

누락 pod 중 이름의 마지막 5글자만 다르고 앞부분이 동일한 파일 후보는 사례별 17/20/5/11/39개 pod에서 발견됐다. 이것은 복제본·재생성·다른 수집 시점 가능성을 조사할 단서이며 자동 동일성 판정이 아니다.

예: PR 20211203의 metric 이름 `console-7c4d8845b5-5676v`와 배포 로그의 `console-7c4d8845b5-n8d5d`. CC에서도 동일 controller처럼 보이는 접두에 여러 pod suffix가 있다. 단순 suffix 제거는 다른 pod의 로그를 잘못 붙일 수 있다. 재시작/복제 관계와 유효 시간·namespace가 확인되기 전에는 매핑하지 않는다.

## 5. 현재 결론과 이전 설명의 정정

1. **확정:** 로컬 매칭/경로 파싱 오류로 누락된 파일은 발견하지 못했다. 판정된 410개는 배포 pod CSV 쌍 양쪽이 실제로 없다.
2. **확정:** metric과 log의 공개 자료 범위가 다르다. 일부 원시 노드 로그에는 해당 pod의 관련 기록도 있으므로 “해당 pod의 로그 정보가 전혀 없다”는 표현은 부정확하다.
3. **우리 구성의 경계:** 임시 전처리 v1은 메트릭 합집합을 바탕으로 EVT 후보를 유지했고 로그 부재로 제거하지 않았다. 공개 MATMCD 요약 함수는 이 후보마다 파일을 기대한다. 현재 Blocker는 이 둘을 연결할 때 발생하는 입력 범위 불일치다.
   저자의 최종 후보 목록이 없는 상태이므로 저자의 원래 실험에서도 반드시 동일한 Blocker가 존재했다고 판단하지 않는다.
4. **미확정:** 저자가 로그를 수집하지 않았는지, 관측 시점/필터/파싱 실패로 빠졌는지, 별도 파일을 배포하지 않았는지는 pod별로 확인되지 않았다. MATMCD의 최종 CSV 후보 목록도 미공개다.
5. **제안 수정:** D01 B안은 임시 진행을 위한 선택지일 뿐 원인에 대한 확정 해결책이 아니다. 우선 저자 최종 후보 목록·metric/log 대응 명세를 확인하는 것이 원본 충실성 측면에서 중요하다. LEMMA 교집합을 MATMCD에 자동 적용하거나 새 로그를 생성하지 않는다. 이번 조사로 B안이 승인된 것도 아니다.

저자 문의에는 단순 “로그를 달라”에 더해 최종 MATMCD CSV 열 목록, 누락 410개 처리, 다른 pod suffix의 매핑/기간, CC 애플리케이션 원자료와 전처리 실행 기록을 구체적으로 요청하도록 남긴다. 새 실행 조건 선택은 이번 원인 분석과 분리한다.

## 조사 중 오류와 제한

후속 인터넷 조사: [TASK_038 공개 유사 사례 분석](D01_PUBLIC_CASE_RESEARCH.md). 같은 CC 날짜의 제3자 구현과 저자 답변이 있는 관련 이슈를 확인했으나, D01의 직접 해결 지침은 찾지 못했다. 기존 입력과 정책은 유지했다.

초기 탐색에서 CC golden-signal NPY를 중첩 dict로 가정한 진단 오류를 수정했다. 또한 최초 자동 진단의 “CPU 목록에 모든 후보가 있어야 한다”는 가정은 PR 20211203의 다중 metric 합집합과 맞지 않아 실패했다. [실패 기록](evidence/d01_log_investigation_20260925T114320672782Z.json)을 보존했고, 기존 승인 프로필의 metric 목록 전체를 읽는 검사로 바로잡았다. 실험 전처리·원본 데이터는 바꾸지 않았다.
