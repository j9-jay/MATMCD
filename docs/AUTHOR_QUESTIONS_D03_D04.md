# RCA D03/D04 저자 일괄 문의 준비

2026-09-26 KST. **문의 준비 자료이며 미발송**. 기존 환경·전처리·모델·로그 질문과 함께 [TASK_018](../tasks/TASK_018_author_clarifications.md)의 메일에 포함한다. 현재 활성 실험은 PR 20211203, PR 20220606, CC 20231207뿐이다.

기준 공식 커밋: `ef2c3ecad0f5ddb9c3d20a8523c2c1043d213190`. [공식 저장소](https://github.com/D2I-Group/matmcd), [인공 검증 근거 40개](evidence/rca_original_protocol_20260925T133730423769Z.json). 공개 소스 관찰과 논문 수치를 만든 실제 실행에 대한 확인을 구분한다.

사용자는 D03 **A안(공개 동작 보존)**을 선택했다. 아래 사항을 교정하지 않고 기록한다. D04는 [승인 프로필](../configs/rca_protocol.json)대로 잠정 PR 평가와 CC 점수 보류를 준비했다. 저자 답변을 받으면 기존 입력·캐시·결과를 보존하면서 차이와 변경 필요 범위를 검토한다.

## D03-01: 그래프를 LLM 문장으로 변환하는 방향과 edge type

근거: [cg2matrix·matrix_to_text](../official/matmcd/Utils/CausalDiscovery.py), [DomainKnowledgeLLM.generate_graph_prompt](../official/matmcd/ConstrainAgent/LLMs.py), [RCA 호출부](../official/matmcd/LEMMA_experiment.py).

- 그래프 A[결과,원인]=1과 제약 C[원인,결과]=1은 서로 다른 규약이다. **이 차이 자체는 오류가 아니다.** C는 LLM 판단으로 새로 만들며 matrix2backgroundknowledge와 일치한다. 일괄 전치를 제안하지 않는다.
- 공개 PC 그래프 A[Y,X]=1은 X→Y다. 이 그래프를 전치 없이 넘기는 DomainKnowledgeLLM은 `Y is the cause of X.`라고 설명한다. 특정 방향의 직접 영향 확인도 A[cause,result]를 조회한다.
- -1(무방향)/2(양방향 표시)도 비영 원소라는 이유로 각각 두 개의 원인 문장으로 표현한다.

저자 질문: 표 4를 만든 실행에서도 이 프롬프트 변환이 사용됐는가? 다른 전치/변환 단계 또는 수정된 prompt 구현이 있었다면 실제 커밋·코드·저장 프롬프트를 제공할 수 있는가? 무방향/양방향 edge는 어떻게 설명했는가?

가능한 영향: 통계 그래프에 대한 LLM의 해석과 이후 제약이 달라질 수 있다. 영향 크기·성능 방향은 미측정이다. 현재 조치: **공개 구현 유지**, 그래프/제약 방향 모두 원본 그대로.

## D03-02: 첫 질문의 직접 영향 문장 재사용

근거: `LLMs.py`의 generate_prompt는 graph_prompt가 빈 경우에만 생성한다. graph_prompt 안에는 전체 그래프뿐 아니라 첫 (cause,result)의 직접 영향 문장도 들어 있다. 이후 다른 쌍의 질문에도 그 문장이 남는다.

저자 질문: 실제 표 4 실험에서는 쌍마다 이 문장을 재생성했는가, 공개 코드처럼 첫 문장을 재사용했는가? 실행 당시 prompt cache 또는 대표적인 연속 두 쌍의 프롬프트를 제공할 수 있는가?

가능한 영향: 현재 질문과 다른 노드 쌍의 판단이 문맥에 섞일 수 있다. 현재 조치: **공개 캐시 동작 유지**, 임의 쌍별 재작성 없음.

## D03-03: 외부정보 없는 첫 제약 보정 단계의 RWR 입력

근거: `LEMMA_experiment.py`의 RWR 네 호출 입력은 순서대로 초기/초기/보정/보정 그래프다. 첫 외부정보 없는 제약 보정(CC) 단계는 보정 그래프를 계산한 뒤에도 초기 그래프를 사용한다. 여기서 CC는 제약 보정 단계이며 Cloud Computing 사례를 뜻하지 않는다. 이후 MATMCD와 MATMCD-RE 단계는 이미 보정 그래프를 사용한다.

저자 질문: 해당 초기 그래프 재사용이 실제 비교 실험에서도 의도된 동작인가? 실제 방법별 RWR 입력 그래프·실행 스크립트와 표 4의 방법 대응을 제공할 수 있는가?

가능한 영향: 그 단계에서 생성한 제약의 효과가 RWR 입력에 반영되지 않는다. 동일 초기 그래프라도 난수 상태가 달라 순위까지 동일하다는 뜻은 아니다. 현재 조치: **초기/초기/보정/보정 유지**, 네 단계 모두를 교정하지 않음.

## D04-01: 실제 정답과 표 4의 사례 대응

근거: [공식 시나리오 대조](RCA_SCENARIO_EVIDENCE.md), `Log_tools.py`의 dataset_info.Ground_Truth, 현재 CSV 열 목록.

| 사례 | 현재 잠정 처리 | 저자에게 필요한 확인 |
|---|---|---|
| PR 20211203 | mongodb-v1-64c6b69879-p4wfp를 공개 보조 코드 기준 잠정 평가 노드로 사용 | 외부 NFS disk-full 시나리오와 MongoDB 평가 노드의 관계, 실제 정답 파일 |
| PR 20220606 | istio-ingressgateway-c5c48c9f4-997nl를 같은 기준으로 잠정 사용 | 외부 접근 부하·reviews OOM 시나리오에서 ingress를 정답으로 평가하는 정의 |
| CC 20231207 | productpage-v1-94d68db49-j7t55 / productpage-v1-94d68db49-vc8ct의 순위를 모두 보존, 단일 점수 보류 | 정확한 장애 주입 pod의 전체 이름과 주입 기록/정답 파일 |

저자 질문: 공개 다섯 날짜와 표 4의 PR/CC 두 rank는 어떻게 대응하는가? 서비스 단위인가 pod 단위인가? 물리적 외부 장애원인과 그래프 안의 평가 노드를 어떻게 구분하는가? j7t55의 교체 이력만으로 주입 pod를 확정하지 않았다.

## D04-02: 순위·난수·반복·집계

현재 공개 동작: RWR steps=1000/rp=0.05/max_self=10, 마지막 열 시작, KPI 포함, 방문 횟수 내림차순·동점 입력 열 순서. 공개 MAPK/MRR를 그대로 사용하면 표 4의 9개 방법 표시값이 일치하며 `rank < K` 경계를 유지한다. 이는 공개 숫자의 산술 대조이고 실험 재현 결과가 아니다.

저자 질문: 실제 실행에도 이 기본값과 KPI/동점 규칙을 사용했는가? NumPy seed 또는 RNG 상태, 방법별 반복 횟수, 평균/최고값 선택, 사례별 집계는 무엇이었는가? 공개 rank를 생성한 예측 파일과 평가 연결 코드를 제공할 수 있는가? Efficient-CDLMs의 best-of-10을 MATMCD에도 적용했는지는 확인되지 않았다.

현재 임시 조치: 방법·사례별 단일 실행 구조, 새 RWR seed를 지정하지 않고 실행 전후 RNG 상태 기록. PR은 잠정 개별 점수, CC는 후보 순위만 보존. CC 정답 확인 전 전체 3사례 집계와 PR만의 부분 집계는 생성하지 않는다. 추후 세 사례가 모두 평가 가능해지면 동일 비중 집계하되 **사용자 선택 부분집합의 로컬 프로토콜**로 표시한다. 저자 원실험의 집계와 같다고 주장하지 않는다.

## 기존 메일에 포함할 영문 문안 — 미발송

We have retained the released graph/prompt behavior for our local RCA baseline, rather than changing it without knowing which implementation produced Table 4. Could you clarify the following points or provide the corresponding experiment commit and cached prompts?

1. We understand that the graph uses effect-row/cause-column entries, while the separately generated constraint matrix uses cause-row/effect-column entries; these different conventions are not themselves an inconsistency. However, LEMMA_experiment.py passes the PC graph unchanged to DomainKnowledgeLLM, where a nonzero entry at [i,j] is described as i causing j. The target check also uses [cause,result], and -1/2 entries are described as causal edges. Was this the prompt construction used for Table 4, or was another conversion used?
2. The graph prompt includes the first queried pair's direct-effect statement and is cached across subsequent pairs. Was that statement regenerated for each pair in the reported experiments?
3. The first constraint-correction stage without external information computes a refined graph but passes the initial graph to RWR. The later MATMCD/RE stages already use refined graphs. Which graph was used for each reported method?
4. For PR 20211203 and 20220606, we provisionally use the unique pod matching the helper labels mongodb-v1 and istio-ingressgateway, respectively. Could you confirm the actual evaluation labels and their relation to the incident scenarios? For CC 20231207, which exact productpage-v1 replica was injected: productpage-v1-94d68db49-j7t55 or productpage-v1-94d68db49-vc8ct? We retain both ranks and withhold a single CC score until this is known.
5. Could you share the actual case/date mapping, NumPy seed or RNG state, repetitions, aggregation procedure, and prediction-to-evaluation script? We preserve the released RWR defaults, KPI inclusion, stable tie order, and rank < K metric boundary, but cannot confirm these were the settings used for the reported runs.

모델·프롬프트에 정답 문의 자료를 넣지 않는다. 수신자·발신자 확정과 외부 발송은 TASK_018에 남으며 이번 요청은 메일 발송 승인이 아니다.
