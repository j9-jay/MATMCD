# RCA 저자 문의 — 최종 메일 본문

> **2026-10-18 상태:** 메일은 발송했으나 답신이 없어 사용자 결정으로 문의 Task를 종료했다. 이 문서는 미확정 조건의 기록으로 보존한다.

2026-09-27. 사용자 지정 순서인 기존 질문 **1 → 6 → 4 → 3 → 2**만 남겼다. 메일에서는1~5로 번호를 다시 붙였으며, 각 문항을 「배경 / 확인이 필요한 부분 / 제가 임시로 적용한 방법 / 질문」으로 구성했다. 배경에는 논문 절·표·그림 또는 공개 함수명을 단서로 넣었다. 국문·영문은 같은 내용을 담는다. **미발송**이며 이름은 발송 전 기입한다.

## 국문 메일

제목: MATMCD의 RCA 실험을 공부하며 몇 가지 여쭙고 싶습니다

안녕하세요, MATMCD 논문의 저자님들께.

로그와 메트릭을 LLM 에이전트로 연결해 근본 원인을 분석하신 접근을 인상 깊게 읽었습니다. 이런 연구를 수행하시고 논문과 코드까지 공개해 주신 점에 존경과 감사의 말씀을 드리고 싶습니다.

저는 석사과정 진학을 준비하고 있는 학생 [이름]입니다. 마이크로서비스의 근본 원인 분석에 관심이 있어, MATMCD를 제 PC에서 구현하고 실행해 보며 공부하고 있습니다.

바쁘실 텐데 갑작스럽게 메일을 드려 죄송합니다. 논문과 코드를 함께 살펴보았지만 제 이해가 부족하거나 실제 실험 조건을 확인하기 어려운 부분이 있어 조심스럽게 여쭙습니다. 시간 괜찮으실 때 답변 가능한 부분만 짧게 알려주셔도 공부와 연구 준비에 큰 도움이 될 것 같습니다. 답변을 주신다면 정말 감사하겠습니다.

문의는 논문4.3절과 표4의 RCA 실험에 관한 것이며, 공개 저장소의 `ef2c3ec` 커밋을 기준으로 확인했습니다. 어느 부분에 관한 질문인지 바로 보실 수 있도록 각 항목에 논문이나 코드의 해당 단계를 짧게 적고, 제가 확인한 내용과 임시로 적용한 방법을 덧붙였습니다. 임시 방법이 논문에서 사용하신 조건과 같다고 가정하지는 않았습니다.

### 1. 입력 전처리와 EVT 필터링

**배경**  
논문4.3절에서는 PR의 각 Pod에6개, CC에는7개의 메트릭이 있고, 인과 탐색 전에 EVT로 무관한 Pod를 제거한다고 설명하셨습니다. 이 질문은 그 원자료를 공개 `Utils/data.py`의 `load_Lemma_data()`가 읽는 최종 CSV로 만드는 단계에 관한 것입니다.

**확인이 필요한 부분**  
여러 메트릭을 Pod별 변수로 합치는 방법과 EVT로 Pod를 제거하는 구체적인 기준을 찾지 못했습니다. 시간 정렬과 정상 초기화 구간도 확인하고 싶습니다.

**제가 임시로 적용한 방법**  
메트릭의 공통 타임스탬프를 사용하고, Pod별 비상수 메트릭을 z-score로 정규화한 뒤 동일 가중 평균했습니다. EVT는 LEMMA 참고값 `d=10, q=0.0001, n_init=100, level=0.95`를 사용하고, 초기화 이후 어느 메트릭에서든 양수 이상 점수가 있으면 Pod를 유지했습니다. 누락 채널은0으로 채우지 않고 상수 채널은 제외했으며, KPI는 원래 값을 마지막 열에 두었습니다.

**질문**  
실제 실험에서는 시간 구간·정렬, 메트릭 통합, 정상 초기화 구간과 Pod 제거 기준을 어떻게 설정하셨나요? 누락·상수 채널과 KPI도 위와 같이 처리하셨는지 궁금합니다.

### 2. 실제 정답과 순위·평가 기준

**배경**  
논문4.3절에서는 정답 인과 그래프 대신 알려진 장애 원인을 기준으로 평가하고, RWR로 얻은 원인 순위를 표4의 RK·MAP@5/10·MRR로 보고하셨습니다. 공개 `LEMMA_Metrics.py`의 계산을 실제 사례의 정답과 예측 순위에 연결하는 과정에 대해 여쭙고자 합니다.

**확인이 필요한 부분**  
PR 20211203의 장애 시나리오는 외부 NFS 장애인데, 보조 코드의 정답 라벨은 MongoDB입니다. CC 20231207은 두 productpage-v1 replica 중 어느 것이 실제 장애 대상인지 확정하지 못했습니다. 표4의 순위에 KPI가 포함되는지도 궁금합니다.

**제가 임시로 적용한 방법**  
PR은 MongoDB Pod를 잠정 정답으로 사용하고, CC의 단일 정답 점수는 보류했습니다. KPI 포함 순위에 공개 평가 함수를 적용하고 Pod만의 순위는 따로 표시했습니다. 동점은 원래 열 순서로 처리했으며 방법별로 한 번 실행했습니다. RWR에는 별도 seed를 지정하지 않고 RNG 상태를 기록·복원했습니다.

**질문**  
표4에 사용한 장애 날짜와 정답 노드, 평가 단위가 Pod인지 서비스인지 알려주실 수 있을까요? 순위에 KPI를 포함하고 공개 코드의 `rank < K`와 MAP 계산을 그대로 사용하셨는지, 동점·복수 정답·seed·반복 횟수·결과 집계는 어떻게 처리하셨는지도 확인하고 싶습니다.

### 3. 그래프 프롬프트의 방향과 첫 질문 문장 재사용

**배경**  
논문3.3절의 CC-agent는 초기 인과 그래프와 노드 정보를 바탕으로 변수 쌍의 관계를 설명한 뒤 제약을 생성하는 것으로 이해했습니다. 아래 질문은 이때 PC 그래프를 Knowledge LLM의 입력 문장으로 바꾸는 `ConstrainAgent/LLMs.py`의 `DomainKnowledgeLLM.generate_graph_prompt()`에 관한 것입니다.

**확인이 필요한 부분**  
`cg2matrix`에서 `A[i,j]=1`은 `j→i`를 뜻하지만, `DomainKnowledgeLLM`에서는 이를 `i→j`로 설명하는 것으로 읽었습니다. 무향·양방향 표식도 원인 문장으로 표현되며, 첫 노드 쌍의 직접 영향 판정 문장이 이후 다른 쌍의 질문에도 남아 있습니다. 그래프와 제약 행렬의 서로 다른 규약 자체보다, LLM에 전달되는 그래프 설명에 관해 여쭙고 싶습니다.

**제가 임시로 적용한 방법**  
제가 의도를 잘못 이해했을 가능성이 있어 공개 동작을 그대로 유지했습니다. 그래프를 전치하거나 쌍마다 해당 문장을 다시 생성하도록 바꾸지는 않았습니다.

**질문**  
표4를 얻은 실행에서도 이 동작을 그대로 사용하셨나요? 아니면 방향·간선 종류를 변환하거나 쌍별 문장을 갱신하는 다른 구현을 사용하셨는지 궁금합니다.

### 4. 로그 요약과 RAG 연결 방식

**배경**  
논문3.2절과 그림5에서는 DA-agent가 Pod 로그를 조회하고 Summary LLM으로 해석·요약하는 과정을 설명하셨습니다. 요약한 정보를 CC-agent가 사용할 노드 정보로 전달하는 부분을 따라가며, 공개 `Web_tools.py`의 `generate_dataset_summary()`가 LlamaIndex 인덱스를 질의하는 경로를 확인했습니다.

**확인이 필요한 부분**  
공개 RCA 진입점은 `log_dir`를 읽지만 웹 수집을 호출하고 있어, 실제 로그 요약이 어떻게 연결되는지 확인하지 못했습니다. 각 Pod의 요약이 모두 전달되는지, 검색된 일부만 전달되는지도 궁금합니다.

**제가 임시로 적용한 방법**  
별도 실행기에서 로그 요약을 RAG에 연결했고 웹 검색은 사용하지 않았습니다. 최종 요약 검색은 설치된 버전의 `as_query_engine()` 기본 top-k=2를 유지했습니다.

**질문**  
실제 RCA에서는 로그만 사용하셨나요, 웹 정보도 함께 사용하셨나요? Pod별 요약을 모두 직접 전달했는지, 검색된 일부만 사용했는지와 실제 chunk·top-k·embedding·거리 설정을 알려주실 수 있을까요?

### 5. 로그가 없는 Pod와 로그 선택·읽기 처리

**배경**  
이 질문은 부록B.1의 log lookup 구현과 공개 `Log_tools.py`에서 요약 프롬프트를 준비하는 단계에 관한 것입니다. 코드에서는 Pod별 `*_messages_templates.csv`와 `*_messages_structured.csv`를 읽고, `generate_log_text()`에서 `EventId`가 같은 기록을 모아 이벤트 예시를 선택합니다.

**확인이 필요한 부분**  
일부 메트릭 Pod에는 정확히 대응하는 로그 쌍이 없고, 일부 원본 CSV는 기본 UTF-8 읽기에 실패했습니다. 논문에서는 이벤트 예시를 최대10개 무작위로 추출한다고 설명하지만, 공개 코드는 일정 간격으로 선택하는 것으로 확인했습니다.

**제가 임시로 적용한 방법**  
전체 Pod 이름이 정확히 일치하는 로그 쌍만 연결하고, 없는 경우에도 후보를 유지하면서 로그 부재를 표시했습니다. UTF-8 실패 파일만 `surrogateescape`로 읽되 선택 필드와 최종 프롬프트가 유효할 때만 사용했습니다. 예시 선택과 템플릿 수 제한은 공개 함수의 동작을 유지했습니다.

**질문**  
실제 실험에서는 로그 연결, 로그가 없는 Pod와 인코딩 오류를 어떻게 처리하셨나요? 이벤트 예시는 무작위 추출과 간격 선택 중 어느 방식을 사용했고, 템플릿 수 제한도 공개 코드와 같았는지 궁금합니다.

질문을 정리하다 보니 메일이 길어졌습니다. 모든 항목에 답해 주시지 않아도 괜찮습니다. 관련 코드나 설정 파일의 위치만 알려주셔도 제가 직접 확인해 보겠습니다.

바쁘신 중에 읽어주셔서 감사합니다. 연구를 배워가는 학생으로서 도움을 주신다면 감사한 마음으로 공부하겠습니다.

[이름] 드림

## English email

Subject: Questions about the RCA experiments in MATMCD

Dear MATMCD authors,

I found your approach to combining logs and metrics with LLM agents for root cause analysis particularly interesting. I have great respect for this work, and I appreciate your making both the paper and code available.

My name is [Name], and I am a student preparing to pursue a master's degree. I am interested in microservice root cause analysis and have been studying MATMCD by implementing and running it on my own PC.

I am sorry to contact you out of the blue when you are likely busy. I have read the paper alongside the code, but there are a few points I may have misunderstood or could not resolve on my own. If you have time, even a brief reply to any of the questions below would help me a great deal as I prepare for graduate study. I would be very grateful for your guidance.

These questions concern Section 4.3 and Table 4, based on public commit `ef2c3ec`. For each question, I have added a short reference to the relevant step in the paper or code, followed by what I found and the provisional choice I made. I do not assume these choices match your experimental conditions.

### 1. Input preprocessing and EVT filtering

**Background**  
Section 4.3 describes six metrics per pod in PR and seven in CC, with EVT used to filter irrelevant pods before causal discovery. My question concerns turning those observations into the final CSV read by `load_Lemma_data()` in `Utils/data.py`.

**What I could not confirm**  
I could not find the exact method for combining metrics into one variable per pod or the rule for removing pods using EVT. The time alignment and normal calibration interval are also unclear to me.

**My provisional approach**  
I aligned metrics on shared timestamps and averaged each pod's nonconstant metric z-scores. I used the LEMMA reference values `d=10, q=0.0001, n_init=100, level=0.95`, retaining a pod if any metric had a positive anomaly score after initialization. Missing channels were not filled with zeros, constant channels were excluded, and the original KPI values were kept in the last column.

**My question**  
What time window/alignment, metric fusion, normal calibration interval and pod filtering rule did you use? Were missing/constant channels and the KPI handled in the same way?

### 2. Ground truth, rankings and evaluation

**Background**  
Section 4.3 evaluates the graphs against known incident causes rather than ground-truth causal graphs, using RWR rankings to report RK, MAP@5/10 and MRR in Table 4. I am trying to connect the calculations in `LEMMA_Metrics.py` to the actual incident labels and predicted rankings.

**What I could not confirm**  
The PR 20211203 scenario describes an external NFS failure, while the helper code gives MongoDB as the label. For CC 20231207, I could not determine which of the two productpage-v1 replicas was the faulty one. I am also unsure whether Table 4's rankings include the KPI node.

**My provisional approach**  
I used the MongoDB pod as a provisional PR label and withheld a single CC score. I applied the released metrics to KPI-inclusive rankings and reported pod-only ranks separately. Ties followed input column order, with one run per method. I recorded/restored the RNG state without assigning a separate RWR seed.

**My question**  
Could you confirm the incident dates, ground-truth nodes and whether evaluation was at pod or service level? Did the reported rankings include the KPI and use the released `rank < K` and MAP calculations? How did you handle ties, multiple labels, seeds, repetitions and aggregation?

### 3. Graph direction and reuse of the first pair's statement

**Background**  
My understanding of the CC-agent in Section 3.3 is that it uses the initial causal graph and node information to explain each variable pair before generating constraints. This question concerns `DomainKnowledgeLLM.generate_graph_prompt()` in `ConstrainAgent/LLMs.py`, where the PC graph is turned into text for the Knowledge LLM.

**What I could not confirm**  
My reading is that `A[i,j]=1` in `cg2matrix` denotes `j→i`, whereas `DomainKnowledgeLLM` describes `i→j`. Undirected/bidirected markers are also described as causal links, and the first pair's direct-effect statement remains in prompts for later pairs. My question concerns the graph description passed to the LLM; I understand that the graph and constraint matrices themselves use different conventions.

**My provisional approach**  
I kept the released behavior in case I had misunderstood its intent. I did not transpose the graph or change the code to regenerate that statement for each pair.

**My question**  
Were these behaviors used in the runs that produced Table 4, or did those runs use another version that converted directions/edge types or refreshed the pair-specific statement?

### 4. Log summaries and RAG integration

**Background**  
Section 3.2 and Figure 5 describe the DA-agent's log lookup and the Summary LLM's interpretation of pod logs. While tracing how that information reaches the CC-agent as node information, I followed `generate_dataset_summary()` in `Web_tools.py`, which queries a LlamaIndex index.

**What I could not confirm**  
The released RCA entry point loads `log_dir` but calls web collection, so I could not trace how log summaries were connected in the actual experiments. I am also unsure whether all pod summaries reach the agent or only the retrieved ones do.

**My provisional approach**  
I connected log summaries to RAG through a separate runner without web search, keeping the installed `as_query_engine()` default top-k of 2 for the final summary query.

**My question**  
Did the RCA experiments use only logs, or web information as well? Were all pod summaries passed directly to the agent, or only retrieved context? Could you confirm the chunking, top-k, embedding and similarity settings used?

### 5. Missing logs, event selection and file reading

**Background**  
This concerns the log lookup implementation in Appendix B.1 and the preparation of summary prompts in `Log_tools.py`. The code reads each pod's `*_messages_templates.csv` and `*_messages_structured.csv`, then `generate_log_text()` groups records by `EventId` to select event examples.

**What I could not confirm**  
Some metric pods have no exact matching log pair, and some original CSVs fail strict UTF-8 decoding. The paper describes randomly selecting up to 10 event examples, while the released code appears to select them at intervals.

**My provisional approach**  
I matched exact full pod names and retained pods without logs with an explicit notice that log evidence was unavailable. Only files failing UTF-8 decoding were read with `surrogateescape`, and I accepted them only when the selected fields and final prompts were valid. I kept the released event-selection and template-limit behavior.

**My question**  
How did you handle log matching, pods without logs and encoding errors? Were event examples sampled randomly or selected at intervals, and was the template limit the same as in the released code?

I realize this has become a long email, so please do not feel you need to answer every point. A link to the relevant code or configuration would also be very helpful, and I would be happy to work through it myself.

Thank you for taking the time to read this. I would appreciate any advice you are able to offer as I learn more about this area.

Best regards,
[Name]

## 내부 기록 — 발송 본문에 포함하지 않음

| 최종 번호 | 기존7개 문항 번호 |23개 기록 중 관련 항목 |
|---|---|---|
| 1 | 1 | Q01~Q05: 입력·전처리·EVT |
| 2 | 6 | Q06·Q18~Q19: 정답·난수/반복·평가 |
| 3 | 4 | Q14~Q15: 그래프 프롬프트·첫 쌍 재사용 |
| 4 | 3 | Q09~Q11: 로그/RAG 연결·검색 설정 |
| 5 | 2 | Q07~Q08: 로그 부재·선택·읽기 |

사용자 지시로 기존5번 PC/RWR 별도 처리와7번 모델/실패/환경 질문은 이번 메일에서 제외했다. 기존6번에 속했던 RWR seed·반복 평가는 최종2번에 유지한다. 제외된 항목을 해결 완료로 처리하지 않으며 [전체 기록](AUTHOR_QUESTIONS_RCA.md)에 남긴다. 웹/RE 세부 후속 질문도 자동으로 추가하지 않는다.

서론은 연구에 대한 존경과 감사, 석사과정 진학을 준비하는 학생이라는 소개, 바쁜 중 문의드리는 송구함, 답변에 대한 감사를 유지했다. 현재 석사과정에 재학 중이라는 표현이나 이름/소속을 만들어 넣지 않았다. 개인의 문의에 맞춰 일인칭을 사용했다. 후속 요청으로 각 질문 앞에 논문·코드의 해당 단계와 연결점을 설명하는 두 문장의 배경을 추가했으며, 기존 확인 사항·임시 처리·질문 내용과 순서는 유지했다.

발송할 때는 위 국문 또는 영문 중 하나의 제목·인사부터 서명까지를 사용한다. 문서 안내와 이 내부 기록은 메일 본문에 포함하지 않는다. 실제 발송은 TASK_018의 TODO이며, 이번 작업에서는 문안만 작성했다.
