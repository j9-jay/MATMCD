# 원본 공개 자료의 문제 및 미확정 사항

원본 소스와 requirements를 수정하지 않았다. 아래는 이번에 직접 확인한 파일/설정 차이 또는 실행 전 점검 결과다. 실험 실행 결과가 아니다. 모든 경로는 `official/matmcd/` 기준이며 고정 커밋은 `ef2c3ecad0f5ddb9c3d20a8523c2c1043d213190`이다.

## 실행을 막는 항목

| ID | 확인 근거/실제 상태 | 영향 및 필요한 자료·결정 |
|---|---|---|
| INPUT-01 | Asia/Child BIF만 공개; `model.simulate(n_samples=1000)`에 seed 없음 | 저자의 실제 관측 CSV 또는 정확 sampling 상태 필요. 임의 seed로 생성 안 함 |
| INPUT-02 | LEMMA ZIP 10개에 MATMCD 형식 CSV 없음; `Utils/data.py:39`는 해당 CSV를 읽음 | EVT 필터 후 CSV 또는 정확 전처리/열/pod/기간/metric 설정 필요 |
| DEP-01 | requirements 140개 모두 설치됐으나 `chromadb` 없음. 점검: `ModuleNotFoundError: No module named 'chromadb'` | `web_utils/retrieval.py:34` Chroma 생성 경로 실패. 저자 사용 버전 미공개; 임의 설치 안 함 |
| DEP-02 | `lxml` 없음. BeautifulSoup 점검: `bs4.exceptions.FeatureNotFound` | `web_utils/web_crawler.py` HTML parser 생성 실패. 저자 버전 필요 |
| DEP-03 | `llama_index.embeddings.openai` 없음. 점검: `ModuleNotFoundError: No module named 'llama_index.embeddings'` | 기본 LlamaIndex embedding resolver의 import 경로 실패. 정확 추가 패키지 버전 필요 |
| DEP-04 | WSL `dot` 실행 파일 없음 | Python `graphviz==0.20.3`은 Graphviz OS 실행 파일이 아님. pydot PNG 출력 전 system Graphviz 필요; 저자 binary 버전 미공개 |
| ACCESS-01 | API 키는 원본에서 모두 빈 값. 기본 모델·embedding·검색은 외부 서비스 | 별도 과금 API 금지 조건에서 원본 end-to-end 실행 불가. 임의 로컬 모델 대체 안 함 |
| CODE-01 | `Web_tools.py:75` 프롬프트는 `Search Query`, `:89` 응답 검사는 `Search Question` | 지시대로 응답하면 검색이 종료되어 RAG 자료가 생성되지 않을 수 있음. 파서 수정 안 함 |
| CODE-02 | `GTdatasets_experiment.py` MATMCD/MATMCD-RE 단계가 `use_cache=True`; `ConstrainNormalAgent.generate_domain_knowledge`는 존재 확인/재생성 없이 np.load | 새 환경에는 `_with_info`/`_reasoning` 캐시가 없어 첫 실행이 완주하지 못함. 캐시 조작이나 옵션 변경 안 함 |
| CODE-03 | `generate_dataset_summary`는 `output_dir` 생성 없이 파일을 씀 | 공개 실행이 요구하는 `cache/Summarized_info`가 없으면 저장 실패. 이번에는 실행을 성공시키기 위한 빈 폴더/우회 생성 안 함 |
| CODE-04 | BIF 생성 파일에 `_1000`이 붙고 loader 기대 파일에는 없음 | 파일명 대응 절차가 README에 명확히 없음. 정확 표본 확보 전 임의 이름 변경 안 함 |

## 논문과 코드의 과학적 조건 차이

| ID | 논문 | 공개 코드/관찰 |
|---|---|---|
| DIFF-01 | 부록 B.1 ES k=2, max parents=2 | `Utils/CausalDiscovery.py:99,104`는 k=1/max_parents=1 |
| DIFF-02 | 기본 temperature=0.5, 특정 모델 형식 실패 시 0.7 | `ConstrainAgent/ConstrainAgent.py:226`은 Constraint LLM에 0.8; `web_utils/llm_answer.py`는 0.0 |
| DIFF-03 | 기본 LLM 모두 GPT-4o mini | Search LLM은 생성자 default gpt-4; 최종 LlamaIndex summary는 코드에서 LLM 미지정 |
| DIFF-04 | 기본 model의 exact snapshot 불명 | 날짜 없는 API 별칭만 있음. 현재 provider 동작/출력을 당시와 같다고 보장할 수 없음 |
| DIFF-05 | DWDClimate 350개 | 공식 지정 CSV 349개 관측. 행 추가/제거 안 함 |
| DIFF-06 | log event 최대 10개 무작위 표본 | `Log_tools.generate_log_text`는 간격을 두고 앞에서 최대 10개 선택 |
| DIFF-07 | 부록 A는 종료 응답까지 반복 | 실행 코드는 최대 5회; 종료 문구도 `No question needed` |
| DIFF-08 | retrieved memory MIPS 및 정보 누출 screening | 코드의 2단계 검색 설정과 filtering 재현 근거 부족; 당시 corpus/URL/필터 목록 없음 |
| DIFF-09 | RCA에서 log modality 활용 | `LEMMA_experiment.py`는 `log_dir`를 로드하지만 Log_tools 호출 없이 웹 검색 수행. 별도 로그 요약 스크립트와 파이프라인 연결 명령 미제공 |
| DIFF-10 | MATMCD K=1과 RE K=2 Top-K Guess 설명 | K=1 코드 경로는 단순 Yes/No. RE만 확률을 파싱 |

## 추가 정적 코드 확인

- `DomainKnowledgeLLM.generate_graph_prompt`는 행렬 [i,j]의 비영 값을 i→j라고 서술하지만 `cg2matrix`, `matrix_to_text`, `visualize_graph`는 값 1을 j→i로 해석한다. -1/2도 방향 문장으로 포함될 수 있다. 방향 해석을 임의 통일하지 않았다.
- `DomainKnowledgeLLM.generate_prompt`는 `graph_prompt`를 첫 방향쌍에서 한 번 만들고 재사용한다. 그 안에는 첫 쌍에 대한 직접 영향 설명이 포함된다. 이후 쌍의 설명과 불일치할 가능성이 있다. 이 부분도 수정하지 않았다.
- `LEMMA_experiment.py`의 첫 제약 반영 후 RWR는 새 그래프 대신 초기 `adjacency_matrix`를 다시 사용한다. 뒤의 웹/RE 단계는 refined graph를 사용한다.
- RCA 마지막 두 시각화는 동일한 `PC_graph_Optimized_web.png` 경로를 사용하여 나중 출력이 앞 출력을 덮어쓸 수 있다.
- README는 존재하지 않는 `RCA_experiment.py`와 `results/` 출력을 안내한다. 실제 RCA 파일은 `LEMMA_experiment.py`, 실험 출력은 주로 stdout, `image/`, `cache/`다.
- `LEMMA_Metrics.py`는 고정 rank 목록을 평가한다. 실제 새 예측을 자동 수집하는 평가·집계 도구가 아니므로 실행하지 않았다.
- `Metrics.calc_NHD`를 단독 최초 호출하면 `self.SHD`가 아직 없을 수 있다. 공식 전체 평가 경로는 SHD 선계산으로 이 문제를 피한다.
- LlamaClient는 temperature 인자를 전송하지 않고 실패 시 무한 재시도한다. ReactClient도 inquiry의 temperature를 모델에 전달하지 않는다.
- `ConstrainReasoningLLM`은 파싱된 guess가 없으면 첫 항목 접근에 실패할 수 있다. 저자의 재시도 횟수/선택 규칙은 미공개다.

## 공개 자료에서 찾지 못한 사항

저자 사용 OS/CPU/GPU/RAM, Python 패치·빌드, system Graphviz 버전, 누락 패키지 버전, API snapshot, 서버 tokenizer/정밀도/추론 기본값, RNG 상태, 실제 Asia/Child 샘플, RCA 최종 입력·사례 선택·EVT 설정, 당시 웹 검색 결과 및 누출 screening, 캐시, full sweep/ablation 실행 스크립트, 대부분 방법의 반복·집계 규칙이 미확인이다.

GitHub API로 확인한 공식 브랜치는 main 한 개, tag/release/PR 목록은 비어 있었다. 닫힌 issue #1은 causal DAG 데이터 요청이며 조회 당시 댓글은 0개였다. 프로젝트 페이지와 ACL 페이지에서 별도 재현 bundle/컨테이너/모델 체크포인트를 확인하지 못했다. 이를 전 세계 어디에도 자료가 없다는 의미로 확대하지 않는다.

## 변경 승인·결정이 필요한 범위

현재 요청은 원본 보존을 요구하므로 위 코드 오류나 논문/코드 불일치는 고치지 않았다. 후속으로 수정한다면 (1) 논문 명세를 따르는 교정 구현인지, (2) 공개 코드를 그대로 실행하는 감사인지 구분하고 변경 승인이 필요하다. 누락 의존성 버전 결정, Graphviz 추가 설치, 새로운 BIF 표본 생성, RCA 전처리 재구성, API 접근 또는 모델 대체도 원본 재현과의 차이를 먼저 명시해야 한다. 이번 작업에서는 이런 대체안을 선택하지 않았다.
