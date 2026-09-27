# 원본 공개 자료의 문제 및 미확정 사항

**TASK_045 최신 판정:** 현재 81,920/all/FP16에서 278/278 로그 입력 수용 및 최대 입력 실제 생성 1건 PASS. Pod 축소 없음. D05의 준비 로그 용량 문제는 해결됐으며 RAG/그래프/전체 통합 검증은 남아 있다. 아래 16,384/미적용/124개 초과는 변경 전 이력이다. [실측·한계](../tasks/TASK_045_validate_context_81920.md).

**TASK_044 최신 범위:** PR 20211203·CC 20231207의 278쌍만 실행·평가 대상으로 사용한다. 준비된 입력을 보존해 재사용했고, 최대 필요 문맥은 73,266이다. 후속 TASK_045에서 문맥만 81,920으로 확대해 준비 로그 문맥 차단을 해결했다. 아래 426개/139,196 및 147,456/24는 이전 3사례 이력이다. [현재 범위](../tasks/TASK_044_select_two_rca_cases.md).

**TASK_045 이전 진행 이력:** TASK_024의 원본 함수/로컬 Qwen·BGE/RWR·평가 연결 코드를 구성하고 인공 검증했다. 전체 입력 준비와 [D06 로그 UTF-8 처리](RCA_LOG_ENCODING.md)는 완료했다. 실제 생성 검증과 실행은 [D05 문맥 용량 및 사용자 보류 결정](RCA_CONTEXT_CAPACITY.md)에 따라 차단돼 있다. D01~D04는 확정됐고 재승인 대상이 아니다. 전체 측정 후 사용자는 D05 B안(현재 16,384/all 유지·실행 보류)을 선택했다. 147,456·GPU 24개 제안은 미적용이다. D06 A안은 23쌍 실물 처리까지 완료했다. 이 문단은 당시 이력이며 현재 문맥 판정은 위 TASK_045 결과를 따른다. 아래 저자 원조건 이슈와 로컬 실행 준비를 구분한다.

현재 RCA 작업용 공식 소스는 원본 43개 중 사용자 승인 제외 6개를 뺀 37개 파일이다. 제외 목록은 configs/scope.json에 있으며 남은 파일과 requirements의 내용은 수정하지 않았다. 아래는 이번에 직접 확인한 파일/설정 차이 또는 실행 전 점검 결과다. 실험 실행 결과가 아니다. 모든 경로는 `official/matmcd/` 기준이며 고정 커밋은 `ef2c3ecad0f5ddb9c3d20a8523c2c1043d213190`이다.

## 실행을 막는 항목

현재 준비 판정은 [RCA_READINESS.md](RCA_READINESS.md), TASK_031의 실물 점검을 따른다. 사용자의 준비 완료 후 실행 요청은 확인했다. 아래 INPUT-02/ACCESS-01 중 저자 원본 조건 확인은 후속으로 구분하며, CODE-01은 웹 수집 경로를 사용할 때의 조건부 문제다. 로컬 실행은 실제 입력·로그·모델 연결 및 과학적 코드·평가 선행 사항으로 차단돼 있다.

| ID | 확인 근거/실제 상태 | 영향 및 필요한 자료·결정 |
|---|---|---|
| INPUT-02 | LEMMA ZIP 10개에 MATMCD 형식 CSV 없음; `Utils/data.py:39`는 해당 CSV를 읽음 | EVT 필터 후 CSV 또는 정확 전처리/열/pod/기간/metric 설정 필요 |
| ACCESS-01 | API 키는 원본에서 모두 빈 값. 사용자 승인 Qwen 생성은 TASK_023/028/029, BGE-M3 임베딩은 TASK_030 준비 완료 | 원본 API는 TASK_025 후속 검증. 실제 로컬 모델·로그 파이프라인 연결은 TASK_024 미완료 |
| CODE-01 (조건부) | `Web_tools.py:75` 프롬프트는 `Search Query`, `:89` 응답 검사는 `Search Question` | 웹 수집 경로 사용 시 검색이 종료돼 자료가 생성되지 않을 수 있음. RCA 공통 필수 항목이 아니며 파서 수정 안 함 |

INPUT-02 후속: TASK_019에서 공개 NPY 5개 날짜의 실제 시간축·pod·KPI를 점검하고 [임시 전처리안](PROVISIONAL_RCA_PREPROCESSING.md)을 작성했다. CC IOPS는 5개 pod에만 존재하며 상수, 다른 6개 메트릭은 196개 pod다. 일부 pod의 정확한 이름에 대응하는 로그가 없고, PR 20220606은 파일명 Success_Rate와 컬럼 Latency의 의미 차이가 있다. 상세 증거는 [입력 inventory](evidence/rca_input_inventory.json)에 있다. 사용자 승인에 따라 TASK_020에서 임시 규칙을 구현·적용하며, 원본 CSV 확보·저자 동일성은 TASK_018에 남는다. 임시 입력 생성만으로 INPUT-02 전체를 해결 처리하지 않는다.

2026-09-24: TASK_020의 임시 metric CSV 5개 생성·별도 검증을 완료했다. 모든 후보 pod가 유지됐고 정확한 로그 쌍 누락은 PR 99/95/64/80개, CC 72개다. 당시 입력 설정·압축 해제·실행 연결은 미완료였다. [실제 적용 결과](PROVISIONAL_RCA_PREPROCESSING_RESULT.md)에 시간 정렬 손실, 상수 채널, pandas 읽기의 미세한 수치 차이도 기록했다.

2026-09-25 후속: TASK_032에서 CSV 5개 및 정확한 로그 647쌍을 연결하고 공식 로더 5개를 통과했다. TASK_039에서 현재 실행·평가를 PR 20211203·PR 20220606·CC 20231207로 제한하여 활성 CSV 3개/로그 426쌍이 됐다. 나머지 두 사례의 준비 자료는 보존한다. CSV 파일/링크 부재는 해결됐다. INPUT-02의 저자 동일성 확인과 누락 pod의 로그 처리 정책은 구분해 남긴다. D01은 후보 유지·부재 명시로 승인됐고 [별도 어댑터](RCA_LOG_POLICY.md)를 구성했다. 누락 원인은 UNKNOWN이다. 후속 [D02](RCA_DECISIONS.md)는 원본 전체 읽기를 유지하는 것으로 정리했고, 사례별 최대 파일 3개 모두 프롬프트 생성까지 PASS했다(최대 RSS 2.111GiB). 나머지 파일의 메모리 감시와 실제 요약·모델 연결은 TASK_024다.

TASK_033에서 공개 지표 함수를 그대로 분리·검증했다. 표준 AP로 수정하지 않았다. TASK_034의 공식 시나리오 및 CC 원자료 조사에서 productpage 단일 replica 장애를 확인했으나 정확한 전체 pod 정답은 확정하지 못했다. 전후 pod 교체를 정답으로 단정하지 않는다. 과학적 코드 처리 D03 및 실제 평가 D04는 [결정 문서](RCA_DECISIONS.md)에 정리했다.

## 해결한 항목

LOCAL-01은 원본 thinking 경로를 교정한 항목이 아니라 **사용자 승인 모드 전환으로 현재 경로의 차단을 해소한 항목**이다. 8192 thinking 실패는 TASK_026과 이전 실행 이력에 보존한다. TASK_029에서 non-thinking의 다섯 응답은 모두 stop·reasoning_content 없음으로 완료됐고 Yes/No 양방향이 통과했다. thinking 복귀 시 이 문제가 해소됐다고 가정하지 않는다.

| ID | 원인 | 처리 및 검증 |
|---|---|---|
| LOCAL-02 | RE 응답의 G/P 사이 빈 줄 누락으로 후보 추출 실패·IndexError. --- 누락만으로 항상 실패하는 것은 아님 | 2026-09-25 사용자 승인 re_gp_boundary_v1로 명확한 항목 경계만 단회 정규화. 원문·공식 파서·설명문/확률/선택 규칙 유지. 오프라인 22개와 인공 Yes/No·RE 양방향 검증 PASS. 정상 RE 1개 무변경, 실패 RE 1개 경계 보정. [TASK_028](../tasks/TASK_028_local_re_response_format.md), [비교 증거](evidence/local_re_format_comparison.json). 다른 에이전트·실제 RCA 연결은 TASK_024 |
| CODE-03 | `generate_dataset_summary`가 부모 폴더 생성 없이 요약 파일을 저장함 | 2026-09-22: 당시 공식 진입점들에 명시된 `cache/Summarized_info`를 외부 작업공간에 준비. `scripts/prepare_workspace.py`에도 반영. WSL 임시 파일 쓰기/정리 확인, 당시 공식 파일 43개 보존 확인(현재 범위 변경 이전 기록). 요약·캐시 내용과 실험 결과는 생성하지 않음. [TASK_011](../tasks/TASK_011_summary_output_directory.md), [검증 기록](evidence/code03_directory_check.json) |
| DEP-01 | 원본 requirements에 chromadb가 없어 import/Chroma 생성 경로가 막힘 | 2026-09-23: 사용자 수용 조합 Chroma 1.0.11과 전이 의존성 57개 설치. 기존 141개 보존, pip check 및 로컬 Chroma/LangChain 저장·검색 통과. [TASK_013](../tasks/TASK_013_install_chromadb.md). 원본 버전 동일성은 [RISK-001](FOLLOW_UP_RISKS.md)로 별도 관리하며 문제 발생 시에만 재검토 |
| DEP-02 | lxml 누락으로 BeautifulSoup parser 생성 시 FeatureNotFound 발생 | 2026-09-23: 승인된 lxml 5.4.0만 추가. 기존 199개 보존, pip check 및 공식 HTML 파싱/추출 함수의 로컬 4개 사례 통과. [TASK_014](../tasks/TASK_014_install_lxml.md). 버전 동일성과 HTML 복구 차이는 [RISK-002](FOLLOW_UP_RISKS.md)로 관리 |
| DEP-03 | `llama_index.embeddings.openai` 누락으로 기본 resolver import 실패 | 2026-09-23: 승인된 어댑터 0.3.1만 추가, 기존 200개 유지, pip check와 기본 resolver/SDK 객체 구성 점검 통과. [TASK_015](../tasks/TASK_015_install_openai_embeddings.md). 실제 API 호출은 없으며 접근은 ACCESS-01에 남음. 버전/출력 동일성은 [RISK-003](FOLLOW_UP_RISKS.md)로 관리 |
| DEP-04 | system Graphviz dot이 없어 공식 visualize_graph의 PNG 출력 불가 | 2026-09-24: 사용자 승인 B안으로 Ubuntu graphviz=2.42.2-9ubuntu0.1 및 의존성 8개 설치. 기존 시스템 변경·삭제 0개, Python 201개·공식 37개 파일 유지, 일반 사용자 인공 PNG 검증 통과. dot -V는 2.43.0 (0). [TASK_021](../tasks/TASK_021_install_system_graphviz.md), [검증](evidence/graphviz_runtime.json). 저자 버전 확인·전환 검토인 A안은 [TASK_022](../tasks/TASK_022_graphviz_author_version.md) TODO |

CODE-03의 해결은 저장 경로에 한정된다. 요약 생성에 필요한 입력·패키지·API와 나머지 코드 문제는 여전히 미해결이다.

## 논문과 코드의 과학적 조건 차이

| ID | 논문 | 공개 코드/관찰 |
|---|---|---|
| DIFF-02 | 기본 temperature=0.5, 특정 모델 형식 실패 시 0.7 | `ConstrainAgent/ConstrainAgent.py:226`은 Constraint LLM에 0.8; `web_utils/llm_answer.py`는 0.0 |
| DIFF-03 | 기본 LLM 모두 GPT-4o mini | Search LLM은 생성자 default gpt-4; 최종 LlamaIndex summary는 코드에서 LLM 미지정 |
| DIFF-04 | 기본 model의 exact snapshot 불명 | 날짜 없는 API 별칭만 있음. 현재 provider 동작/출력을 당시와 같다고 보장할 수 없음 |
| DIFF-06 | log event 최대 10개 무작위 표본 | `Log_tools.generate_log_text`는 간격을 두고 앞에서 최대 10개 선택 |
| DIFF-07 | 부록 A는 종료 응답까지 반복 | 실행 코드는 최대 5회; 종료 문구도 `No question needed` |
| DIFF-08 | retrieved memory MIPS 및 정보 누출 screening | 코드의 2단계 검색 설정과 filtering 재현 근거 부족; 당시 corpus/URL/필터 목록 없음 |
| DIFF-09 | RCA에서 log modality 활용 | `LEMMA_experiment.py`는 `log_dir`를 로드하지만 Log_tools 호출 없이 웹 검색 수행. 별도 로그 요약 스크립트와 파이프라인 연결 명령 미제공 |
| DIFF-10 | MATMCD K=1과 RE K=2 Top-K Guess 설명 | K=1 코드 경로는 단순 Yes/No. RE만 확률을 파싱 |

## 추가 정적 코드 확인

- `DomainKnowledgeLLM.generate_graph_prompt`는 행렬 [i,j]의 비영 값을 i→j라고 서술하지만 `cg2matrix`, `matrix_to_text`, `visualize_graph`는 값 1을 j→i로 해석한다. -1/2도 방향 문장으로 포함될 수 있다. 방향 해석을 임의 통일하지 않았다.
- `DomainKnowledgeLLM.generate_prompt`는 `graph_prompt`를 첫 방향쌍에서 한 번 만들고 재사용한다. 그 안에는 첫 쌍에 대한 직접 영향 설명이 포함된다. 이후 쌍의 설명과 불일치할 가능성이 있다. 이 부분도 수정하지 않았다.
- `LEMMA_experiment.py`의 첫 외부정보 없는 CC 제약 반영 후 RWR는 새 그래프 대신 초기 `adjacency_matrix`를 다시 사용한다. 뒤의 추가정보/RE 단계는 refined graph를 사용한다. 모든 MATMCD 단계에 같은 문제가 있다고 해석하지 않는다.
- RCA 마지막 두 시각화는 동일한 `PC_graph_Optimized_web.png` 경로를 사용하여 나중 출력이 앞 출력을 덮어쓸 수 있다.
- README는 존재하지 않는 `RCA_experiment.py`와 `results/` 출력을 안내한다. 실제 RCA 파일은 `LEMMA_experiment.py`, 실험 출력은 주로 stdout, `image/`, `cache/`다.
- `LEMMA_Metrics.py`는 고정 rank 목록을 평가한다. 해당 전체 스크립트는 새 실험 결과로 실행하지 않았다. TASK_033은 원문 함수만 추출해 명시적 rank를 받는 도구와 11개 기능 검사를 구성했으며, 실제 새 예측 수집·정답/집계 선택은 수행하지 않았다.
- LlamaClient는 temperature 인자를 전송하지 않고 실패 시 무한 재시도한다. ReactClient도 inquiry의 temperature를 모델에 전달하지 않는다.
- `ConstrainReasoningLLM`은 파싱된 guess가 없으면 첫 항목 접근에 실패할 수 있다. 저자의 재시도 횟수/선택 규칙은 미공개다.

## 공개 자료에서 찾지 못한 사항

저자 사용 OS/CPU/GPU/RAM, Python 패치·빌드, system Graphviz 버전, 누락 패키지 버전, API snapshot, 서버 tokenizer/정밀도/추론 기본값, RNG 상태, RCA 최종 입력·사례 선택·EVT 설정, 당시 웹 검색 결과 및 누출 screening, 캐시, RCA 전체 사례 실행 스크립트와 반복·집계 규칙이 미확인이다.

GitHub API로 확인한 공식 브랜치는 main 한 개, tag/release/PR 목록은 비어 있었다. 닫힌 issue #1은 causal DAG 데이터 요청이며 조회 당시 댓글은 0개였다. 프로젝트 페이지와 ACL 페이지에서 별도 재현 bundle/컨테이너/모델 체크포인트를 확인하지 못했다. 이를 전 세계 어디에도 자료가 없다는 의미로 확대하지 않는다.

## 변경 승인·결정이 필요한 범위

RCA 범위 전환 이후 사용자가 TASK_020의 임시 전처리 구체안 적용을 별도로 승인했다. 위 원본 코드 오류나 논문·코드 불일치는 고치지 않았다. 후속 변경은 논문 명세를 따르는 교정인지 공개 코드 그대로의 실행인지 구분하고, 영향과 해결안을 설명하여 승인받는다.

DEP-01~03은 사용자 승인 버전을 추가했으며 저자 버전 미확정 사항을 RISK-001~003으로 관리한다. DEP-04는 TASK_021 B안 설치를 완료했고 A안은 TASK_022에 분리했다. TASK_020 v1 이외의 전처리 변경, Graphviz의 다른 버전으로 전환, API 접근 또는 모델 대체는 별도 결정이 필요하다.

제외한 실험의 전용 Blocker·차이는 현재 목록에서 제거했으며 해결한 것으로 재분류하지 않았다. 삭제 내역은 [TASK_017](../tasks/TASK_017_scope_rca_only.md)에 남겼다.
