# TASK_018 - RCA 재현 조건 일괄 저자 확인

## 목적

사용자가 제안한 진행 방식에 따라, 이미 적용한 로컬 환경 선택과 아직 미확정인 RCA 조건을 모아 저자에게 한 번에 확인한다. 임시 구성 준비와 저자 동일성 확인을 구분하여 관리한다.

저자 확인 범위는 현재 대상인 논문 §4.3·표 4 RCA와 공통 환경뿐이다.

2026-09-26: 사용자가 D03 A안의 공개 동작을 유지하고 문제를 추후 일괄 문의하도록 지시했다. [D03/D04 별도 문의 준비 문서](../docs/AUTHOR_QUESTIONS_D03_D04.md)에 코드 근거·영향·질문과 영문 문안을 모았다. D04의 PR 잠정 정답/CC 점수 보류·단일 호출/RNG·집계 방침도 포함한다. 문의는 미발송이며 아래 기존 초안과 함께 한 번에 검토·발송할 자료다.

## 작업 항목

- [x] 적용한 로컬 선택과 미적용·미확정 항목 구분
- [x] 문의 우선순위와 검토용 메일 초안 작성
- [x] 후속 임시 구성안이 승인·적용되면 선택값·근거·영향을 아래 목록에 추가
- [ ] 발송할 문안·수신자·발신자 정보를 확정하고 사용자의 발송 지시 확인
- [ ] 문의 메일 발송 및 발송 내용 기록
- [ ] 저자 답변·첨부 자료·revision·해시 기록
- [ ] 답변과 임시 구성의 차이를 대조하고 필요한 변경안 제시
- [ ] 승인된 변경 적용 후 영향받는 입력·캐시·결과의 재생성 필요 범위 기록

## 확인 사항

2026-09-23: 사용자는 임시 준비와 미확정 사항의 추후 일괄 문의 방식을 제안했고, TASK_019 구체안 검토 후 TASK_020의 전처리 구현·CSV 생성을 승인했다. 이 문서는 저자 문의 TODO다. 과학적 원본 코드 교정·API 사용·메일 발송은 승인받지 않았다.

관련 자료의 기본값은 MATMCD 저자의 실험값이 아니다. 임시 구성안을 만들 때는 각 선택을 논문 명시 / MATMCD 공개 코드 / LEMMA-RCA 참고 코드 / 로컬 선택으로 구분한다. 실행 성공을 저자 동일성 확인으로 처리하지 않는다.

### 이미 적용한 로컬 선택

| 항목 | 현재 적용값·상태 | 저자에게 확인할 내용 |
|---|---|---|
| Python·호스트 | 기존 WSL Ubuntu에서 CPython 3.11.13 사용. 저자 README의 Python 3.11 계열에 맞춘 로컬 선택 | 당시 Python 패치, OS, 환경 export |
| 기본 requirements | 공식 140개 pin 보존. 원본에 pin 없는 setuptools 84.0.0 추가 설치 | 전체 환경 lock/export에 누락된 전이 의존성 |
| Chroma | 사용자 승인 chromadb 1.0.11, PostHog 4.2.0, OpenTelemetry 1.35.0·0.56b0 계열. RISK-001 | 저자의 실제 Chroma/전이 의존성 버전 및 collection 설정 |
| HTML parser | 사용자 승인 lxml 5.4.0, libxml2 2.13.8, libxslt 1.1.43. RISK-002 | 당시 lxml/libxml2/libxslt 버전 |
| Embedding adapter | 사용자 승인 llama-index-embeddings-openai 0.3.1. RISK-003 | 당시 어댑터 버전과 실제 embedding 모델·설정 |
| 임시 로컬 임베딩 | 2026-09-25 승인 BAAI/bge-m3 revision 5617a9f61b028005a4858fdac845db406aefb181, dense/CPU/FP32/batch 1. 로더 transformers 4.51.3/safetensors 0.5.3 분리 설치. 기존 분할·top-k 유지한 인공 검색 검증 PASS, TASK_030 | 원본 ada-002의 정확 설정과 두 검색 단계의 corpus·거리·분할/tokenizer override·캐시 제공 여부. BGE는 저자 모델로 간주하지 않으며 원본 API 재검증 시 새 인덱스 생성 필요 |
| Graphviz B안 | 2026-09-24 Ubuntu graphviz=2.42.2-9ubuntu0.1 및 의존성 8개 설치. dot -V는 2.43.0 (0), Python graphviz 0.20.3/pydot 4.0.0 유지 | 저자의 패키지 버전·dot -V·OS·폰트·렌더링 backend. A안 검토는 TASK_022 TODO |
| 데이터 배포본 | PR revision df25484004e50483de6f6756c3a4d7ab03174b83, CC revision 03f82a2c4b16afe09e9315def9f5d6990427000a에 고정 | 저자가 사용한 배포본·날짜·파일 해시와의 대응 |
| 로컬 RE 형식 보정 | 2026-09-25 사용자 승인 re_gp_boundary_v1. 명확한 G/P 항목의 개행·구분자만 단회 정규화하며 원문·보정본·실패를 보존. 설명문·확률·원본 선택 규칙 유지 | 저자의 형식 위반 응답 처리·재시도/재작성·실패 사례 집계 규칙. 해당 로컬 보정은 저자 구현으로 간주하지 않음 |

위 패키지 버전은 근거 없이 숨겨 채운 실험값이 아니라 이미 기록·승인된 로컬 구성이다. RISK-001~003의 기존 WATCH 정책을 유지하며, 이번에 재설치·재검증을 반복하지 않는다. 저자 문의 항목에 함께 포함한다.

### 저자 원본이 미확인인 사항과 문의 우선순위

| 우선순위 | 관련 항목 | 요청 자료·질문 |
|---|---|---|
| 1 | INPUT-02 | 표 4에 실제 사용한 최종 CSV·열 설명·pod/KPI 매핑·대응 로그. 제공이 어렵다면 정확한 전처리 코드·설정·선택 pod 목록 |
| 1 | INPUT-02 | EVT/SPOT 구현·임계값·초기 구간, 메트릭 선택/결합, 시간 구간/집계/정렬, 결측치/상수 처리. 최종 입력의 마지막 열 의미 |
| 1 | TASK_003/008/009 | PR/CC의 실제 날짜·장애 사례·정답 원인·반복 횟수·seed·집계. 공개 코드의 PR 날짜 목록과 표 4 대응 |
| 2 | DIFF-09/06 | RCA 로그 lookup/요약을 실행하는 실제 진입점·명령·프롬프트·캐시. 웹 경로와의 관계. 이벤트 샘플링은 무작위인지 간격 선택인지 |
| 2 | CODE-01 및 정적 이슈 | Search Query/Search Question 파싱, 첫 제약 반영 이후 RWR의 초기 그래프 재사용, 제약 행렬 방향·첫 쌍 프롬프트 재사용이 실제 실험 코드와 같은지 |
| 2 | TASK_008 | 실제 예측 순위가 평가에 연결되는 코드. rank의 0/1 기준, rank < K, MAP@K/MRR 정의·반복별 집계 규칙 |
| 2 | DIFF-02/03/04 | 단계별 실제 모델 snapshot·temperature·추론 설정. Search gpt-4와 최종 LlamaIndex 기본 LLM 사용 여부 |
| 3 | TASK_022 A안 및 환경 | 전체 환경 export, system Graphviz 패키지와 dot -V, 폰트·렌더링 backend. B안 설치·로컬 검증은 완료했으며 저자 동일성 확인과 분리 |
| 3 | RAG/DIFF-07/08/10 | 당시 검색/로그 corpus·요약·캐시, 반복 종료 규칙, chunk/top-k/거리·screening, K=1/RE 추론 설정. 공개 기본값과 다른 override 여부 |
| 3 | PC/RWR | 공개 PC 호출 기본값·RWR 파라미터 사용 여부와 난수 처리. 실행별 기록·설정 파일 제공 가능 여부 |

RCA 입력 재구성은 승인된 TASK_020 프로필로 진행하며 원본 동일성을 주장하지 않는다. 과학적 원본 코드 교정, API 키·모델 snapshot의 임의 설정·호출은 하지 않았다.

### TASK_019에서 구체화하고 TASK_020에서 승인·적용한 임시 선택

[상세 명세](../docs/PROVISIONAL_RCA_PREPROCESSING.md)와 [승인 설정](../configs/rca_preprocessing_proposal.json)에 선택값을 기록했다. 사용자 후속 승인을 받아 별도 스크립트에서 적용한다. 실제 생성·검증 결과와 실패 내역은 [TASK_020](TASK_020_apply_provisional_rca_preprocessing.md)에서 확인한다. 원본 전처리값으로 승격하지 않는다.

- 시간: 선택 메트릭의 정확한 타임스탬프 교집합 전체, 보간·추가 집계 없음.
- 후보: pod 합집합, 누락 메트릭을 0으로 만들지 않음, 상수 채널 제외.
- EVT: 참고 DSpot d=10, q=0.0001, n_init=100, level=0.95와 공개 wrapper 기본값. 하나 이상의 메트릭에 양의 이상 점수가 있으면 pod 유지하는 규칙은 로컬 가정.
- 통합: pod별 가용 비상수 메트릭을 각각 z-score(ddof=0)로 만든 뒤 동일 가중 평균. MATMCD 저자 사용 근거가 없는 주요 가정.
- KPI: 배포값을 마지막 Latency 열에 보존. PR 20220606의 실제 의미 미확정.
- 로그: 정확한 전체 pod 이름으로만 연결. 누락을 빈 로그나 임의 alias로 대체하지 않음.

새로 확인한 문의 사항:

1. 저자는 메트릭 6/7개를 어떻게 pod 한 열로 바꾸었는가? 아니면 메트릭별 그래프·순위를 합쳤는가?
2. 현재 CC 배포본에서 IOPS는 5개 pod에만 있고 모두 상수인데, 다른 메트릭의 196개 pod와 어떻게 조합했는가?
3. 시간 교집합·원 해상도와 SPOT 초기화 길이가 실제 조건에 맞는가? 관련 FastPC 코드의 100개 합산을 MATMCD에도 적용했는가?
4. PR product/testuser/ratings/reviews 중 실제 KPI와 사례는 무엇인가?
5. PR 20220606 파일명은 Success_Rate이나 배포 헤더는 Latency다. 실제 값의 의미와 해당 사례 사용 여부는 무엇인가?
6. 정확한 이름에 대응하는 로그가 없는 pod를 어떻게 처리했는가? 원본 배포 revision·선택 구간이 현재 자료와 다른가?

이 목록은 적용한 임시 선택과 저자 답변을 대조할 기준이다. 원래 설정이라고 확정하거나 이번에 실험·평가를 수행한 것으로 기록하지 않는다. SPOT은 고정 LEMMA 원본 함수를 순차 사용하며 반복·행렬/채널별 일치를 검증한다. 저자의 전처리와 같다는 주장은 아니다.

2026-09-24 적용 관찰: 다섯 metric CSV가 생성됐다. PR 네 날짜의 (행 수, 유지 pod)는 (166,325, 208), (176,692, 207), (51,529, 218), (107,789, 228), CC는 (79,252, 196)이다. 모든 후보 pod가 유지돼 pod 감소는 0개였다. 상수 채널 제외 수는 순서대로 6/6/23/26/42개이며 CC IOPS 5개는 모두 포함된다. 정확한 로그 쌍 누락은 각각 99/95/64/80/72개다. 로그는 ZIP 멤버 목록만 기록했고 압축 해제·요약·실제 RCA 통합은 하지 않았다.

추가 질문: 저자도 이 정도의 후보를 유지했는지, 별도 이상 구간·유지 임계값·메트릭 결합·시간 집계가 있었는지 확인한다. 현재 규칙이 후보를 줄이지 않았다는 관찰만으로 논문의 EVT 단계나 성능 경향을 재현했다고 판단하지 않는다. 채널별 근거와 시간 정렬 손실은 외부 manifest, 간단한 결과는 [적용 결과](../docs/PROVISIONAL_RCA_PREPROCESSING_RESULT.md)에 보존한다.

### 임시 구성에 대한 제안

1. 원본 코드와 배포 자산은 보존하고, 승인받은 보완 코드·설정만 별도로 관리한다. 필요한 파일이 생길 때 경로를 만든다.
2. 논문과 관련 공식 구현에서 근거를 찾고, 없는 선택은 로컬 가정으로 표시한다. LEMMA-RCA FastPC의 SPOT 설정을 MATMCD 값이라고 단정하지 않는다.
3. 선택값마다 근거, 예상 영향, 생성 입력 해시, 저자 확인 질문을 기록한다. 결과 수치를 보고 전처리 기준을 바꾸지 않는다.
4. 로컬 구성의 실행 준비 상태와 저자 조건 동일성 상태를 별도로 보고한다. 임시 입력의 검증이 끝나기 전에는 INPUT-02를 해결로 처리하지 않는다.
5. 저자 답변으로 조건을 바꾸면 새 설정·입력 버전을 만든다. 기존 자료를 조용히 교체하거나 서로 다른 조건의 결과를 섞지 않는다.
6. 후속 사용자의 조건부 실제 실행 요청은 TASK_007에 기록했다. 준비 완료 후 같은 실행 승인을 반복 요청하지 않는다. TASK_007은 기술적 통합 때문에 BLOCKED이며 평가·비교 TASK_008/009는 결과 생성 전까지 TODO다. 민감도 분석은 현재 단일 호출 방침과 구분한다.

### 문의 메일 초안 — 미발송

수신 후보: cshen9@uh.edu. 공식 저장소 Contact에 공개된 주소이며 발송 시 재확인한다.

Subject: MATMCD RCA reproduction: Table 4 inputs, scripts, and environment

Dear MATMCD authors,

I am preparing to reproduce the microservice RCA experiments in Section 4.3 and Table 4 of your paper. My current scope is Product Review and Cloud Computing.

Our currently selected local cases are PR 20211203, PR 20220606, and CC 20231207. The five-case preparation observations below describe our earlier inventory, not five active experiments. We retain all candidates with an explicit notice for unavailable exact pod logs (216 candidates in the current three-case subset), and preserve the released CSV-reading and event-selection behavior. We also retain the released graph/prompt behavior under our selected profile A. The prepared D03/D04 question supplement provides exact source observations and asks for confirmation of the experiment version, fault labels, and evaluation protocol.

I have preserved the public MATMCD source at commit ef2c3ecad0f5ddb9c3d20a8523c2c1043d213190 and downloaded the referenced LEMMA-RCA metric/log archives. I have not run the full experiments yet.

To proceed with local input preparation while awaiting clarification, we implemented an explicitly provisional profile. It uses the exact shared timestamps across the published metrics, the union of full pod names, and excludes only channels with zero standard deviation on those shared rows. We use the released LEMMA DSpot/spot_detection function with d=10, q=0.0001, n_init=100, level=0.95, both tails and alerts enabled, bounded mode, and max_excess=200. A pod is retained if any nonconstant metric has a strictly positive anomaly score after initialization. There is no temporal aggregation or cap on retained pods.

We then average each pod's available nonconstant metric z-scores (ddof=0, statistics over all shared rows), keeping the published KPI unscaled in the last Latency column. These alignment, retention, and fusion rules are local assumptions, not claimed author settings. They may change the causal graph and RCA ranking. Would you confirm the actual preprocessing and provide the original final inputs so that we can replace this provisional profile? Exact-name log pairs are catalogued separately; missing logs are not replaced by empty or approximate matches.

This profile produced 166325/176692/51529/107789 rows for the four PR dates and 79252 rows for CC. It retained all 208/207/218/228 PR candidate pods and all 196 CC candidate pods. The corresponding numbers without an exact template/structured log pair were 99/95/64/80/72. All five published CC IOPS channels were constant on the shared timestamps and excluded under the stated rule. Did the reported experiments use a different time window, aggregation, or pod retention criterion? These are input-preparation observations; we have not run causal discovery, LLM calls, or RCA evaluation.

Could you please share the following artifacts, or point me to their location?

1. The final RCA input CSVs and corresponding logs actually used for Table 4, including column/pod/KPI mappings and the exact incident dates. If these cannot be shared, the preprocessing scripts and settings would help: EVT filtering, metric selection/combination, time windows/aggregation, alignment, and missing/constant-value handling.

   In particular, how were the 6/7 metrics represented as one column per pod in the final CSV? In the downloaded CC case, storage IOPS covers only 5 pods and is constant, while the other metrics cover 196 pods. Some metric pod names have no exact log-file match. The PR 20220606 KPI filename refers to success rate, although its header says Latency. Clarification of these data mappings would help avoid incorrect reconstruction.
2. The experiment entry point and commands used to integrate log lookup and summaries. The public LEMMA_experiment.py loads a log path but invokes the web collection path; I could not identify how the log summaries were connected for the reported experiments.
3. The actual evaluation inputs and aggregation procedure, including rank indexing, seeds, repetitions, and case selection. LEMMA_Metrics.py contains fixed rank lists and uses rank < K, so I would like to confirm how new predicted rankings should be evaluated.
4. An environment export and stage-specific model identifiers/settings. The public requirements omit Chroma, lxml, and the LlamaIndex OpenAI embedding adapter. Our provisional local versions are chromadb 1.0.11, lxml 5.4.0, and llama-index-embeddings-openai 0.3.1 on Python 3.11.13. We are treating these as local compatibility choices, not verified author settings.

   For PNG output, we installed the Ubuntu graphviz package 2.42.2-9ubuntu0.1 and its dependencies, while retaining the pinned Python graphviz 0.20.3 and pydot 4.0.0. The executable reports “dot - graphviz version 2.43.0 (0)”. A synthetic graph renders successfully using the unmodified public function. Could you provide both your package/build version and dot -V output, together with the OS, fonts and rendering backend if available? We are retaining our local package hashes and test image so that an author-matched environment can be assessed separately later.
5. Whether the released code matches the version used for Table 4. In particular, could you clarify the graph-to-prompt direction/edge-type interpretation, reuse of the first pair's direct-effect sentence, and the initial graph passed to RWR after the first constraint-correction stage without external information? We understand that the graph and the separately generated constraint matrix have different index conventions; that difference itself is not our concern. The prepared D03/D04 supplement includes source details and the unresolved CC replica question. A corresponding experiment commit, cached prompts, and prediction/evaluation files would be especially helpful. The Search Query/Search Question mismatch is a separate question conditional on whether the web path was used in RCA.

We would also appreciate any saved prompts, log summaries, retrieval settings/caches, or notes on differences between the paper and the released implementation. The final RCA inputs and experiment scripts are our highest priority.

Thank you for your time and for releasing the code and resources.

Best regards,
[Sender name / affiliation]

실제 임시 전처리나 추가 교정을 적용하면 발송 전에 그 내용을 정확하게 반영한다. API 비밀정보·사용자 미확정 신원은 넣지 않는다. 상기 메일은 검토용이며 외부 발송·GitHub issue 게시를 하지 않았다.

## 결과
2026-09-26: D03 A안과 D04 권장 방침을 반영했고 상세 문의 자료·영문 문안을 별도 저장했다. TASK_040/041 준비는 완료했지만 저자 실행 동일성·CC 정확 정답은 미확정이다. 메일 초안에 현재 세 사례와 D01/D02 처리, 공개 동작 보존 선택을 반영했다. 발송하지 않았다.

2026-09-25 D03/D04 후속 대조: [TASK_040/041 상세 근거](../docs/RCA_ORIGINAL_PROTOCOL_REVIEW.md). 저자에게 (1) 효과행/원인열 인과 그래프와 프롬프트 방향 불일치·첫 쌍 문장 재사용이 실제 실행에도 있었는지, (2) 외부정보 없는 CC 단계 RWR의 초기 그래프 입력이 실제 실험 동작인지, (3) PR 두 사례의 보조 코드 평가 label과 CC 정확한 replica, (4) RWR seed/반복/집계와 KPI 포함·동점 규칙을 확인한다. 공개 rank로 표 4의 지표가 모두 일치한다는 계산 결과와 저자의 실제 예측/정답 재현 여부를 구분한다. 메일은 발송하지 않았다.


2026-09-23 초안 작성 당시에는 기존 기록을 대조하여 문의 목록과 초안을 마련했고, 전처리·CSV 생성은 아직 수행하지 않았다.

후속 TASK_019에서 구체안을 작성했고, TASK_020에서 사용자 승인에 따라 전처리를 구현하여 2026-09-24 다섯 CSV를 생성했다. 위 초안에 실제 적용 설정·관찰 결과·저자 확인 질문을 반영했다. 과학적 원본 코드 변경·RCA 실험·API 호출·메일 발송은 하지 않았다. 문의 발송과 답변 반영이 남아 TODO를 유지한다.

2026-09-24 TASK_021에서 승인된 Graphviz B안 설치·검증을 완료하여 적용 패키지 버전과 dot 출력, 확인 요청을 추가했다. A안의 자료 대조·전환 검토는 [TASK_022](TASK_022_graphviz_author_version.md) TODO로 분리했다. 이번에도 메일은 발송하지 않았다.

관련 기록: [RCA 입력 준비](TASK_003_dataset_download.md), [미확정 사항](../docs/ORIGINAL_LOCAL_ISSUES.md), [승인된 호환 버전의 잔여 위험](../docs/FOLLOW_UP_RISKS.md).

근거: [MATMCD 공식 저장소와 Contact](https://github.com/D2I-Group/matmcd), [논문](https://aclanthology.org/2025.findings-acl.36.pdf), [LEMMA-RCA 공식 코드](https://github.com/lemma-rca/rca_baselines). 로컬 고정 revision은 configs/upstream.json을 따른다.

## 후속 확인 질문 — 2026-09-25, 미발송

TASK_032~034에서 다음 질문을 구체화했다.

- 정확한 이름의 pod 로그가 없는 사례별 99/95/64/80/72개 후보에 저자는 어떤 정보를 제공했는가? 추가 로그·pod 매핑 또는 누락 처리 지침이 있는가? 현재 후보는 제거하지 않았다.
- 원본 Log_tools의 전체 CSV 읽기에서 6.05GB급 파일은 어떤 메모리/읽기 구현으로 처리했는가? 이벤트 선택은 공개 간격 선택인가 논문 서술의 무작위 표본인가? 부재 정책과 읽기 어댑터는 제안 단계이며 적용하지 않았다.
- CC 20231207에서 장애를 주입한 productpage-v1의 **전체 pod 이름**은 무엇인가? j7t55/vc8ct가 장애 전 존재하고 j7t55가 이후 zvtz8로 바뀌는 설정 자료를 찾았으나 이것만으로 정답을 확정하지 않았다. 주입 기록/정답 파일을 요청한다.
- PR 20220606의 외부 부하·reviews OOM 시나리오와 MATMCD 보조 코드의 istio-ingressgateway 정답은 어떤 평가 정의로 연결되는가? pod/service 평가 단위와 KPI 후보 포함 여부도 요청한다.
- 공개 날짜 5개와 표 4 집계 사례의 대응, 동점 처리·RWR 난수/반복·실제 rank 파일을 요청한다. 공개 MAPK의 rank < K와 내부 K 평균은 의도한 표 4 지표 정의인가? 현재 함수는 그대로 보존했다.

자료 출처·추출 근거는 [공식 시나리오 조사](../docs/RCA_SCENARIO_EVIDENCE.md), 로컬에서 선택해야 할 부분은 [결정 문서](../docs/RCA_DECISIONS.md)에 기록했다. 아래 상태는 저자 문의·답변 반영의 상태이며 조사 준비 완료와 구분한다.

## TASK_037 후속 문의 보강

로컬 파일명 판정 오류는 발견하지 못했다. 저자에게 최종 MATMCD CSV의 전체 열 목록과 로그의 정확한 pod/namespace/기간 대응, 다른 replica suffix의 매핑 여부, 누락 410개 처리 방침, CC application 원자료와 당시 전처리 실패/제외 기록을 요청할 필요가 있다. LEMMA 일부 기준선의 metric/log 교집합 선택을 MATMCD에도 적용했는지 구분해 묻는다. [분석 근거](../docs/D01_LOG_COVERAGE_ANALYSIS.md). 문의는 발송하지 않았다.

TASK_038의 [공개 사례 조사](../docs/D01_PUBLIC_CASE_RESEARCH.md)에서 같은 CC 메트릭 목록을 서비스 단위로 합치는 제3자 구현을 확인했다. 이것을 저자의 처리 방식으로 가정하지 않고, 저자가 pod별 로그와 서비스 공통 로그 중 어떤 단위를 사용했는지 기존 질문에 포함한다. 저자의 과거 공개 답변은 전처리 자료 사용 시 관련 전처리 단계를 반복할 필요가 없다는 안내였으며 누락 대응 지침은 아니었다. 이번에도 문의는 발송하지 않았다.

후속 사용자 결정으로 TASK_035의 후보 유지·부재 명시 정책은 승인·구현·오프라인 검증 완료했다. 사용 가능한 로그만 정확히 연결하고 410개 pod의 부재를 명시한다. 원인은 UNKNOWN으로 유지하며 재시작/종료를 확정하지 않는다. 저자의 실제 처리 방침과 원인 확인은 계속 문의 대상이며, 메일 초안 발송 전 [적용 정책](../docs/RCA_LOG_POLICY.md)을 반영한다. 원본 최종 후보 목록·누락 원인 문의를 임시 실행의 재승인 항목으로 취급하지 않는다.

TASK_039 후속: 현재 실행·평가는 사용자 지정 PR 20211203·PR 20220606·CC 20231207만 포함한다. 이 부분집합에서 로그 부재는 216개다. 앞선 5개/410개 및 6GB 파일 관련 문의는 전체 공개 자료 조사 이력이며, 발송 시 현재 실행 범위와 구분하여 설명한다. 세 사례 선택은 이미 승인됐고 추가 문의/승인 대상이 아니다. 메일은 발송하지 않았다.

## 2026-09-26 추가 문의 자료 — 미발송

- [D06 UTF-8 원본 오류](../docs/RCA_LOG_ENCODING.md): PR 20211203 cluster-version-operator structured.csv의 원본 해시 일치, 첫 오류 위치 8057의 0xc3, 전체 오류 12,944바이트. 저자의 실제 파일 revision/인코딩/오류 처리와 최종 예시·요약을 요청한다. 로컬에서는 사용자 승인 A안으로 오류 바이트를 손실 없이 보존해 읽고 이벤트 선택 필드/최종 프롬프트가 유효한 경우만 허용한다. 원본 삭제·대체는 하지 않는다.
- [D05 문맥 길이](../docs/RCA_CONTEXT_CAPACITY.md): 전체 426개 원본 선택 프롬프트는 현재 로컬 Qwen tokenizer에서 최대 131,003토큰이다. 이는 저자 GPT의 토큰 수가 아니다. 저자의 실제 로그 요약 요청/출력 한도·잘라내기 여부·단계별 모델과 최종 요약을 요청한다. 초기 32,768안은 불충분했고 후속 147,456·GPU 24개 안도 미적용이다. 사용자는 B안으로 현재 16,384/all 유지·실행 보류를 선택했다. 이 로컬 설정을 저자 조건으로 간주하지 않는다.
- [연결 구현·전체 후보 호출 규모](../docs/LOCAL_RCA_RUNTIME.md): 3개 승인 사례의 현재 후보와 공개 전체 방향쌍 루프는 로그/RAG 이외에 831,396회의 생성 호출을 요구한다. 논문 실행 당시 후보 필터·캐시·호출 수·실행 시간과 실제 진입점을 요청한다. 이를 이유로 후보나 쌍을 임의 축소하지 않았다.

## 상태

TODO
