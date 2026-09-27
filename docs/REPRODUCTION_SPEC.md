# RCA 논문·공식 구현 재현 명세

기준 자료는 사용자가 제공한 `E:\연구\MATMCD.pdf`(arXiv:2412.13667v2, 25쪽, 2025-05-31)다. 본문과 부록 A~D를 확인했다. 논문은 RAG를 구성 요소로 사용하는 **인과관계 발견 및 근본 원인 분석** 연구이며, 일반적인 QA/RAG 벤치마크나 LLM 학습 실험이 아니다.

출처: [논문 v2](https://arxiv.org/abs/2412.13667v2), [ACL 출판 페이지](https://aclanthology.org/2025.findings-acl.36/), [공식 코드](https://github.com/D2I-Group/matmcd). 파일 해시와 고정 커밋은 [upstream.json](../configs/upstream.json)에 있다. 아래 코드 경로는 `official/matmcd/` 기준이다.

현재 작업 범위는 **§4.3·표 4의 RCA**다. 일반 인과관계 발견 벤치마크와 그 절제 실험은 사용자 지시로 제외했다. 공통 소스와 전체 논문·공식 ZIP은 출처 확인용으로 보존한다.

## 실험 및 데이터

| 항목 | 논문 근거 | 공개 구현/확인 상태 |
|---|---|---|
| Product Review | §4.3, 8~9쪽: 216 pods × 6 metrics, 길이 131,329 | LEMMA-RCA 원본 배포 ZIP 확보. MATMCD 입력 CSV 미공개 |
| Cloud Computing | §4.3: 168 pods × 7 metrics, 길이 109,351 | LEMMA-RCA 원본 배포 ZIP 확보. MATMCD 입력 CSV 미공개 |
| 데이터 버전 | 논문에 파일 해시/revision 없음 | 현재 배포처의 revision과 SHA256을 고정·기록. 당시 파일과 같다는 보장은 미확인 |
| 전처리: RCA | §4.3: EVT 기반 무관한 pod 제거. 공개 로더는 최종 CSV를 header=0으로 읽음 | MATMCD 저장소에 EVT→최종 CSV 생성 스크립트·설정·선택 pod 목록 없음 |
| Train/Validation/Test | 별도 분할 미기재 | 공개 RCA 로더는 최종 CSV 전체를 읽어 SCD에 투입. 임의 분할하지 않음. HF 웹페이지의 자동 `train` 표시는 논문 split 근거가 아님 |

## 모델·추론·학습

| 항목 | 논문 조건 | 공식 코드 및 미확정 사항 |
|---|---|---|
| 기본 LLM | §4.1: GPT-4o mini | `config.py`: `gpt-4o-mini`. 날짜가 붙은 snapshot 미공개 |
| Temperature | 기본 0.5; 부록 B.1에서 일부 형식 실패 시 0.7 재시도 | Knowledge LLM 0.5, Constraint LLM **0.8**, 웹 중간 요약 **0.0**. LlamaClient는 temperature 인자를 요청에 전달하지 않음 |
| Search LLM | 모든 기본 LLM GPT-4o mini | `collect_web_content`는 모델을 지정하지 않아 `OpenAIClient` 기본값 **gpt-4** 사용 |
| max tokens/top-p/penalty/stop/seed | 정확한 값 미공개 | OpenAIClient 요청에서 명시 안 함. 현재 API 기본값을 당시 설정으로 채우지 않음 |
| Tokenizer | 버전/revision 미공개 | `tiktoken==0.9.0` 설치 목록만 확인. 서버 LLM tokenizer의 정확한 배포본 미확인 |
| Batch size | 학습 batch 미기재 | 변수의 모든 방향쌍 `i != j`를 순차 질의. 서버 batching 미공개 |
| Learning rate/Epoch/Optimizer | MATMCD 자체 LLM 학습/미세조정 단계 없음 | 해당 공개 실행 경로에 적용되지 않음. 0이나 임의 값으로 채우지 않음 |
| Random seed | 전역 seed 미공개 | RWR·API seed 고정 코드 없음 |
| 체크포인트 | MATMCD가 학습한 체크포인트 공개 없음 | API 기반 코드. 임의의 로컬 가중치·양자화 모델로 대체하지 않음 |

## RAG 및 프롬프트

| 항목 | 근거와 확인 값 |
|---|---|
| 전체 흐름 | §3/부록 A: SCD 초기 그래프 → DA-agent 검색·요약 → CC-agent 설명·제약 추론 → 같은 SCD에 제약을 전달하여 그래프 재추정 |
| 검색 서비스 | 부록 B.1: Google/Serper, 정보가 부족하면 Tavily 보충. 코드 Serper 요청은 `page: 2`; 결과 수 `num`은 미지정. `use_tavily=False`라도 검색 실패 시 Tavily 호출 가능 |
| 웹 수집 | `web_utils/web_crawler.py`: HTML BeautifulSoup(`lxml`); h1~h6/p(확장 시 div), 10단어 초과 태그 텍스트; PDF URL 생략, 요청 timeout 8초 |
| 반복 검색 | 논문: `No query needed`까지. 코드: 실행 파일에서 `loop_num=5`; 질문 형식은 `Search Query`를 요구하지만 응답 파서는 `Search Question`을 검사 |
| Embedding | 논문/웹 검색 코드 모두 `text-embedding-ada-002`; 정확한 서버 snapshot 미공개 |
| 웹 내부 retriever | `web_utils/retrieval.py`: LangChain `Chroma` + OpenAIEmbeddings. `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)`, 기본 길이 함수 기준 문자 수. `k=10` |
| 검색 top-k 구분 | 위 **10은 검색된 웹페이지를 쪼갠 chunk의 k**다. Google 검색 페이지 수, 최종 LlamaIndex query k, Top-K Guess의 K와 구분 |
| 최종 요약 RAG | `Web_tools.py`: `SimpleDirectoryReader` → `VectorStoreIndex.from_documents` → `index.as_query_engine()`. Settings/embedding/chunk/top-k/LLM override 없음. 설치된 라이브러리 기본값은 환경 문서에 별도 기록하며 논문 실험값으로 단정하지 않음 |
| Retriever 거리 | 논문 §3.2는 MIPS. 웹 검색 Chroma에 거리 설정 없음·버전 누락. 최종 LlamaIndex 벡터 검색은 라이브러리 기본 경로. 두 단계를 같은 MIPS 구현이라고 단정하지 않음 |
| Reranker | 별도 reranker 모델·단계는 논문 및 공개 코드에서 확인되지 않음 |
| 로그 lookup | §3.2: 변수 이름으로 로그 직접 조회, 템플릿 요약. 부록 B.1: event별 최대 10개 무작위 샘플. 코드는 간격 선택 `iloc[::max(1, occurrence // record_num)].head(10)`; 무작위가 아님 |
| 정보 누출 방지 | §3.2는 정답 그래프 누출 방지 screening 수행을 설명. 공개 코드에서 해당 screening 절차·제외 URL 목록·당시 수집 corpus를 확인하지 못함 |
| CC-agent | Knowledge LLM 설명 후 Constraint LLM이 Yes/No. MATMCD K=1, MATMCD-RE K=2; 공개 K=1 구현은 확률 없이 Yes/No만 요구, RE는 기본 `guess_number=2` 및 확률 내림차순 선택 |
| 프롬프트 원문 | 부록 C.1(17~18쪽), C.2(19쪽), C.3/C.4(20쪽). 코드 `Web_tools.py`, `Log_tools.py`, `ConstrainAgent/LLMs.py`, `web_utils/config/config.yaml`의 원문 보존 |

## 인과 탐색과 RCA

| 항목 | 논문 | 공개 코드 |
|---|---|---|
| 기본 SCD | PC | `causal_discovery_algorithm="pc"` |
| PC 검정 | Fisher's Z | `indep_test="fisherz"`; alpha 등은 호출에 미지정. 설치된 causal-learn 기본값은 환경 점검에 기록 |
| 그래프 제약 | 존재/비존재 제약으로 동일 SCD 재실행 | RCA 기본 PC는 BackgroundKnowledge 사용. 코드별 방향 표기 차이를 이슈 문서에 기록 |
| RCA RWR | §4.3: random walk with restart | `Utils/RCA.py`: 1,000 steps, restart=0.05, max_self=10, 시작 노드 마지막 열; seed 없음 |
| RCA 사례 | 표 4에 PR/CC 각 순위 보고 | 공개 기본 스크립트는 PR 20210517, CC 20231207은 주석 설정. Log_tools에는 PR 4개 날짜도 존재. 최종 표에 사용한 상세 선택 조건 미공개 |

## 평가와 집계

RCA는 부록 B.2의 PR@K, MAP@5, MAP@10, MRR, PR/CC root cause 순위다. `LEMMA_Metrics.py`는 **실험 출력을 읽지 않고 코드 안의 고정 순위를 집계**한다. `rank < K` 조건을 사용한다. 실제 결과 수집·입력 연결은 공개되어 있지 않으며 이 파일 출력물을 재현 결과로 취급하지 않는다.

RCA의 정확한 사례 선택, 반복 횟수, seed, 평균·분산·best 선택 및 실제 결과를 순위 목록에 넣는 절차는 미확정이다. 원 논문의 타 실험 집계 규칙을 RCA에 임의로 옮기지 않는다.

### 이후 비교할 논문 수치 (로컬 실험 결과 아님)

표 4: MATMCD MAP@5=30.0%, MAP@10=55.0%, MRR=0.32, RK(PR)=2, RK(CC)=7. MATMCD-RE는 20.0%, 55.0%, 0.25, 3, 6. 표의 반올림 수치를 역산해서 입력·조건을 조정하지 않는다.
