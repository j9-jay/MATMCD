# RCA 공통 환경과 원본 환경의 차이

2026-09-26 TASK_027 후속: [현재 환경 snapshot](evidence/rca_environment_20260926T061459160665Z.json)을 기록했다. OS 패키지 805개, Python 201개, 공식 파일 37개다. 현 OS 설정을 유지하고 실제 실행 전후 목록/해시가 달라지면 결과에 환경 검토 필요를 표시한다. 자동 업데이트 중지·OS rollback·저자 환경 동일성 확정은 하지 않는다.

현재 활성 범위는 RCA다. TASK_017에서 전용 파일만 제거했으며 환경은 유지한다. 최초 설치·검사 수치는 당시 이력이다. 이번 정적·파일 보존 검증은 evidence/rca_scope_verification.json이다. 후속 audit_setup.py 실행 시 evidence/rca_setup_audit.json을 생성한다.

## 실제 설치 결과

2026-09-24 사용자 승인으로 추가한 로컬 생성 모델은 [Qwen 로컬 환경](LOCAL_LLM.md)에서 별도로 관리한다. 2026-09-25 승인된 non-thinking 전환에서도 같은 모델·런타임 자산을 재사용했다. llama.cpp b11146의 CUDA 12.8 런타임을 외부 자산에 분리 설치하며 이 서버 프로세스에만 적용한다. 아래 원본 재현용 Python/PyTorch/CUDA 패키지는 교체하지 않는다. 로컬 모델 설치·인공 추론 검증과 전체 RCA 실행 준비 완료는 구분한다.

같은 작업의 최종 감사에서 WSL의 unattended-upgrade 이력과 과거 Graphviz snapshot 대비 OS 패키지 175개 차이를 확인했다. Python 가상환경 201개는 그대로이며, 아래 초기 환경 기록을 현재 OS 전체가 불변이라는 뜻으로 해석하지 않는다. [버전 차이](evidence/local_llm_system_drift.json), [TASK_027](../tasks/TASK_027_wsl_system_drift.md)에 변경 이력과 이후 환경 고정 결정 사항을 분리했다. OS를 임의로 되돌리거나 업데이트 서비스를 끄지 않았다.

기존 WSL2 Ubuntu에 별도 Python 환경을 만들었다. 환경 폴더는 자산 루트 아래 `environments/d2i_matmcd_py311`이며, Python 배포본은 `environments/uv_cpython`, 다운로드 캐시는 `caches/uv_packages`에 있다. 사용자 전역 Python/패키지를 교체하지 않았다.

| 항목 | 실제 확인값 | 원본과의 관계 |
|---|---|---|
| 호스트 | Windows 11 Pro 10.0.26200, 64bit | 저자 OS 미공개 |
| Linux | WSL2 Ubuntu 24.04.3 LTS, kernel 6.18.33.2-microsoft-standard-WSL2 | 기존 설치본 사용. 저자 OS와 동일성 미확인 |
| RAM | 17,083,305,984 bytes | 저자 RAM 미공개 |
| GPU | NVIDIA GeForce RTX 2080 SUPER, 8,192 MiB | 저자 GPU 미공개 |
| 호스트 GPU 드라이버 | 591.86 | 저자 driver 미공개 |
| Python | CPython 3.11.13, Clang 20.1.4 빌드 | README의 3.11 major/minor 충족. 저자 패치/빌드 미공개; 이 패치를 저자 값으로 확정한 것은 아님 |
| 환경 도구 | 기존 WSL `uv 0.8.15` | 패키지 설치용 로컬 도구; 저자 도구 버전 아님 |
| PyTorch | distribution 2.7.0, runtime 2.7.0+cu126 | 공식 pin 일치 |
| CUDA | torch build 12.6, `cuda_available=True` | 원본 requirements의 cu12 12.6 계열 사용. 별도 nvcc toolkit 설치는 하지 않음 |
| cuDNN | nvidia-cudnn-cu12 9.5.1.17 | 공식 pin 일치 |
| causal-learn | 0.1.4.1 | 공식 pin 일치 |
| NumPy/Pandas/SciPy/sklearn | 2.2.6 / 2.2.3 / 1.15.3 / 1.6.1 | 공식 pin 일치 |
| LlamaIndex core/OpenAI LLM | 0.12.37 / 0.3.44 | 공식 pin 일치 |
| LangChain/community/core/OpenAI | 0.3.25 / 0.3.24 / 0.3.62 / 0.3.18 | 공식 pin 일치 |
| OpenAI SDK/pgmpy/tiktoken | 1.82.0 / 1.0.0 / 0.9.0 | 공식 pin 일치 |
| setuptools | 84.0.0 | 전이 의존성으로 resolver가 선택. 원본 목록에는 pin이 없어 당시 버전 미확인 |

최초 설치에서 원본 `requirements.txt`의 **140개 고정 패키지가 전부 정확히 일치**했다. 전이 의존성 setuptools 포함 총 141개가 설치되었고 `uv pip check`가 통과했다. Linux용 NVIDIA/Triton 패키지를 제외하거나 Windows용 대체 requirements를 만들지 않았다.

초기 점검에서 빠져 있던 `chromadb`, `lxml`, `llama-index-embeddings-openai`는 2026-09-23 TASK_013~015에서 사용자 승인 조합으로 설치했다. Python 패키지는 현재 총 201개다. system Graphviz는 2026-09-24 TASK_021의 B안으로 추가·검증했다. 입력·API·코드 차단 사유가 남아 **전체 RCA 실행 준비는 미완료**다. 상세 상태는 [ORIGINAL_LOCAL_ISSUES.md](ORIGINAL_LOCAL_ISSUES.md)에 있다.

## 승인된 Chroma 호환 조합 추가

Chroma 1.0.11 / PostHog 4.2.0 / OpenTelemetry 1.35.0·0.56b0 계열을 포함한 58개 패키지를 추가했다. 기존 141개 변경은 0개이며 총 199개가 [승인된 hash lock](evidence/chromadb_1.0.11.proposed.lock.txt)과 일치한다. `uv pip check`, Chroma import/native 저장·검색, 기존 LangChain 경로의 저장·검색이 통과했다. 원본 코드 및 패키지 pin은 보존했다.

[설치 기록](evidence/chromadb_install.json), [당시 freeze](evidence/installed_freeze_with_chromadb.txt), [로컬 점검](evidence/chromadb_runtime.json)에 증거를 저장했다. `installed_freeze.txt`와 `setup_audit.json`은 최초 환경의 snapshot으로 보존한다. Chroma 조합은 저자 버전이라고 확정된 값이 아니며, 사용자의 지시에 따라 [RISK-001](FOLLOW_UP_RISKS.md)을 문제 발생 시에만 재검토한다.

로컬 점검은 3개 인공 벡터의 in-memory collection을 생성·검색한 후 정리했다. 공식 실험 데이터·모델·Top-k 설정은 변경하지 않았다. 실제 RAG/API/논문 결과 평가도 수행하지 않았다.

## 승인된 lxml 추가

[TASK_014](../tasks/TASK_014_install_lxml.md)에서 `lxml==5.4.0` 하나를 추가했다. 기존 199개 변경 없이 당시 총 200개였으며 pip check가 통과했다. 당시 freeze는 [installed_freeze_with_lxml.txt](evidence/installed_freeze_with_lxml.txt), 설치 증거는 [lxml_install.json](evidence/lxml_install.json)에 있다. 이전 freeze와 audit은 각 단계의 snapshot으로 보존한다.

공식 WebScraper의 parser/본문 추출 함수로 기본 필터, div 옵션, 한글/엔티티, 닫는 태그 없는 문단 등 로컬 4개 사례를 확인했다. lxml 5.4.0의 실제 libxml2 및 libxslt 버전은 각각 2.13.8과 1.1.43이다. [lxml_runtime.json](evidence/lxml_runtime.json)에 실제 결과를 보존했다. 저자의 정확한 버전 및 모든 HTML 처리의 동일성은 [RISK-002](FOLLOW_UP_RISKS.md)로 관리한다.

## 승인된 OpenAI embedding 어댑터 추가

[TASK_015](../tasks/TASK_015_install_openai_embeddings.md)에서 `llama-index-embeddings-openai==0.3.1`만 추가했다. 기존 200개 버전 변경 없이 총 201개이고 pip check가 통과했다. [현재 freeze](evidence/installed_freeze_with_openai_embeddings.txt), [설치 증거](evidence/openai_embeddings_install.json), [추가 패키지 hash lock](evidence/llama_index_embeddings_openai_0.3.1.lock.txt)을 보존했다. 설치 스크립트는 기존 Chroma/lxml hash lock도 함께 입력하여 모든 전이 의존성을 고정한다.

공식 PyPI 메타데이터의 의존성은 `openai>=1.1.0`, `llama-index-core>=0.12.0,<0.13.0`이며 기존 1.82.0/0.12.37로 충족한다. 원본 MATMCD는 `VectorStoreIndex.from_documents`에서 embedding을 지정하지 않아 core의 기본 resolver를 사용한다. 이 경로와 `Settings.embed_model`, 동기/비동기 SDK 객체 생성을 네트워크 차단 상태에서 확인했다. [로컬 검증](evidence/openai_embeddings_runtime.json)에 기본값과 적용 버전을 기록했다.

기본 모델/질의·문서 엔진은 `text-embedding-ada-002`, mode=`text_search`, 배치 크기 100, dimensions 미지정, 재시도 10, timeout 60초, client 재사용이었다. 이는 **설치한 어댑터의 관찰값**이며 저자 설정으로 확정하지 않는다. 모델/배치를 직접 지정하거나 공식 코드를 변경하지 않았다. 버전/출력 동일성은 [RISK-003](FOLLOW_UP_RISKS.md)으로 관리한다.

키가 없는 상태에서는 패키지 import를 통과한 뒤 `No API key found for OpenAI` 오류가 난다. SDK 객체 검사에는 별도 프로세스에만 가짜 키 문자열을 넣었고 실제 API 요청·인증·embedding 생성은 수행하지 않았다. 서비스 접근과 모델 snapshot은 ACCESS-01에 남는다.

## Graphviz B안 설치와 A안 후속 확인

2026-09-24 사용자가 B안을 승인하여 WSL Ubuntu 24.04의 시스템 Graphviz를 설치했다. A안인 저자 버전 확인·필요 시 전환은 [TASK_022](../tasks/TASK_022_graphviz_author_version.md) TODO로 따로 관리한다. 현재 버전을 저자 버전으로 확정하지 않는다.

| 식별자 | 실제 확인값 |
|---|---|
| Ubuntu 배포 패키지 | graphviz=2.42.2-9ubuntu0.1, amd64 |
| 실행 파일 | /usr/bin/dot |
| dot -V 출력 | dot - graphviz version 2.43.0 (0) |
| 기존 Python 패키지 | graphviz=0.20.3, pydot=4.0.0 유지 |
| 추가 시스템 패키지 | graphviz와 의존성 8개, 총 9개 |
| 기존 패키지 변경 | 시스템 변경·삭제 0개, Python 201개 모두 보존 |
| 원본 보존 | 공식 파일 37개가 고정 ZIP과 일치 |

배포 패키지 버전과 실행 파일의 버전 출력은 구분해 보존한다. 7개 Graphviz 계열 패키지는 2.42.2-9ubuntu0.1, libann0는 1.1.2+doc-9build1, libgts-0.7-5t64는 0.7.6+darcs121130-5.2build1이다. 정확한 목록은 [승인 설정](../configs/graphviz_packages.json), URL·크기·SHA256/SHA512는 [패키지 lock](evidence/graphviz_ubuntu_packages.lock.json)에 있다. 출처는 구성된 Ubuntu noble/noble-updates universe 저장소다. apt update/upgrade나 Python 패키지 재설치는 하지 않았다.

공식 visualize_graph 함수로 3개 인공 노드의 PNG 출력을 확인했다. 설치 사용자와 일반 WSL 사용자(uid 1000)에서 각각 405×131 PNG가 생성됐고 해시가 일치했다. 입력 행렬은 보존됐고 세 노드·B→A 화살표·B—C 점선의 표시를 확인했다. 이는 렌더링 점검이며 실제 PC·RWR·RCA·LLM·API 실행이 아니다. [설치 증거](evidence/graphviz_install.json), [일반 사용자 검증](evidence/graphviz_runtime.json).

원본 코드에서 Graphviz는 계산된 행렬을 PNG로 저장하는 데 사용한다. 저자와 버전·폰트·렌더링 backend가 다르면 그림 배치나 표현이 달라질 수 있다. 같은 행렬에서 RCA 수치로 다시 입력되는 경로는 확인되지 않아 직접적인 수치 영향은 낮을 것으로 판단하지만, 저자 환경/출력 동일성은 미확인이다. A안에서는 저자 환경 자료를 확보한 뒤 B안과 대조하고, 전환이 필요하면 현재 DEB·해시·로그·이미지를 보존한 상태로 구체적인 변경안을 승인받는다.

설치의 첫 모의 실행은 --no-download와 외부 로컬 DEB 경로의 조합으로 실패했다. 설치 도구의 이 옵션만 교정했고 패키지 버전·해시·실험 조건은 유지했다. 상세 실패·수정 기록은 [TASK_021](../tasks/TASK_021_install_system_graphviz.md)에 있다.

## API 호출 없는 검증

[setup_audit.json](evidence/setup_audit.json)에 최초 구성 시의 실제 출력과 오류를 저장했다. 아래는 최초 snapshot이며 Chroma/lxml/embedding 어댑터 후속 결과는 위 절을 따른다.

- 공식 export의 모든 파일을 원본 ZIP과 SHA256 비교: 일치.
- 공식 Python 파일 AST 문법 검사: 통과. 실행 파일 자체를 import하여 실험을 시작하지 않았다.
- 핵심 라이브러리, causal 도구, agent/Web_tools 모듈 import: 통과. 최초 두 import는 45초 제한에 걸려 해당 두 항목만 180초 제한으로 재확인했다.
- GPU 인식: PyTorch에서 RTX 2080 SUPER 및 CUDA 12.6 사용 가능 확인. 모델 추론/학습/벤치마크 계산은 안 함.
- chromadb, lxml parser, LlamaIndex OpenAI embedding import: 실패. system Graphviz dot 없음.

최초 audit의 점검 subprocess는 네트워크를 차단했고, API client를 생성하거나 요청하지 않았다. 설치 성공과 실험 실행 준비 성공은 다른 판정이다. 최초 audit의 `ready_for_original_experiments`는 false이며 현재도 입력/API/코드 등 남은 차단 사유로 전체 실행 준비는 미완료다.

## 설치된 라이브러리의 기본값 조사

아래 값은 **고정 라이브러리 코드를 읽어 확인한 로컬 기본 동작**이다. 논문 저자가 직접 설정했다고 주장하는 값이 아니다. 공식 MATMCD가 해당 값을 override하지 않는다는 점에서 공개 구현 분석에 필요하다.

| 경로/항목 | 확인값 |
|---|---|
| causal-learn `pc` signature | alpha=0.05, fisherz, stable=True, uc_rule=0, uc_priority=2, mvpc=False |
| LlamaIndex `Settings.node_parser` | `SentenceSplitter()` |
| SentenceSplitter | chunk_size=1024 tokens, chunk_overlap=200 tokens; 일반 constants의 DEFAULT_CHUNK_OVERLAP=20과 실제 클래스 default=200을 구분 |
| LlamaIndex VectorIndexRetriever | similarity_top_k=2 |
| SimpleVectorStore 기본 query | `get_top_k_embeddings` → default similarity=cosine; 논문의 MIPS 표기와 차이 검토 필요 |
| LlamaIndex OpenAI 기본 model/temperature | `gpt-3.5-turbo` / 0.1 |
| LlamaIndex tokenizer 선택 | `get_tokenizer(model_name="gpt-3.5-turbo")`에서 tiktoken `encoding_for_model` 호출 |
| LlamaIndex 기본 embedding | 원본 목록에서 누락된 `OpenAIEmbedding()` 어댑터를 TASK_015에서 추가; 설치한 0.3.1의 기본 모델은 text-embedding-ada-002, 배치 100 |

OpenAI embedding의 실제 server tokenizer나 snapshot, Chroma의 버전/거리 기본값은 이 자료만으로 확정하지 않았다. tokenizer 캐시를 임의의 다른 모델로 교체하지 않았다.

## 설치/검증 기록

2026-09-25 TASK_030의 임시 BGE-M3 로더는 기존 가상환경 밖의 environments/pypi_bge_m3_loader_tf4.51.3에 transformers 4.51.3/safetensors 0.5.3만 설치했다. 기존 Python 201개와 시스템 패키지는 보존했으며 해당 로컬 어댑터 프로세스만 추가 경로를 읽는다. 공식 BGE config에 기록된 transformers_version=4.33.0 및 MATMCD 원본 조건과 구분한다. 원래 LlamaIndex 분할용 cl100k_base는 기존 wheel의 동일 파일을 SHA-256 검증 후 외부 caches/tiktoken으로 복사했다. 분할 tokenizer나 chunk/top-k는 변경하지 않았다. [구성·제한](LOCAL_EMBEDDING.md), [별도 설치 증거](evidence/local_embedding_install.json), [CPU 인공 검증 PASS](evidence/local_embedding_runtime.json).

자산 루트 `logs/setup/`에 설치 원문 로그, `environment_status.json`, `installed_freeze.txt`가 있다. Git에는 작은 설치 manifest와 감사 결과만 보관한다. 감사 과정에서 생성되는 라이브러리 캐시도 자산 루트로 지정했다. 과거에 폐기한 실행 환경이나 결과는 사용하지 않았다.
