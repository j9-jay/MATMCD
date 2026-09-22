# 구성한 환경과 원본 환경의 차이

## 실제 설치 결과

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

원본 `requirements.txt`의 **140개 고정 패키지가 전부 정확히 일치**했다. 전이 의존성 setuptools 포함 총 141개가 설치되었고 `uv pip check`가 통과했다. Linux용 NVIDIA/Triton 패키지를 제외하거나 Windows용 대체 requirements를 만들지 않았다.

하지만 설치 목록 자체에 빠진 `chromadb`, `lxml`, `llama-index-embeddings-openai` 및 system Graphviz `dot` 때문에 **완전한 실행 환경은 아직 아니다**. 버전을 추측하여 추가 설치하지 않았다. 상세 오류는 [ORIGINAL_LOCAL_ISSUES.md](ORIGINAL_LOCAL_ISSUES.md)에 있다.

## API 호출 없는 검증

[setup_audit.json](evidence/setup_audit.json)에 실제 출력과 오류를 저장했다.

- 공식 export의 모든 파일을 원본 ZIP과 SHA256 비교: 일치.
- 공식 Python 파일 AST 문법 검사: 통과. 실행 파일 자체를 import하여 실험을 시작하지 않았다.
- 핵심 라이브러리, causal 도구, agent/Web_tools 모듈 import: 통과. 최초 두 import는 45초 제한에 걸려 해당 두 항목만 180초 제한으로 재확인했다.
- GPU 인식: PyTorch에서 RTX 2080 SUPER 및 CUDA 12.6 사용 가능 확인. 모델 추론/학습/벤치마크 계산은 안 함.
- 벤치마크 CSV 수치/직사각형 여부와 크기 검사: 통과. DWDClimate 샘플 수 불일치는 별도 보존.
- chromadb, lxml parser, LlamaIndex OpenAI embedding import: 실패. system Graphviz dot 없음.
- 실제 필요한 입력 9개 누락 확인(Asia/Child data+GT 4개, LEMMA 5개 CSV). 로그/캐시 등 추가 차단 사유는 별도 목록에 있다.

점검 subprocess는 네트워크를 차단했고, API client를 생성하거나 요청하지 않았다. 설치 성공과 실험 실행 준비 성공은 다른 판정이다. 현재 audit의 `ready_for_original_experiments`는 false다.

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
| LlamaIndex 기본 embedding | `llama_index.embeddings.openai.OpenAIEmbedding()` import 시도; 이 패키지가 원본 목록에 없음 |

OpenAI embedding의 실제 server tokenizer나 snapshot, Chroma의 버전/거리 기본값은 이 자료만으로 확정하지 않았다. tokenizer 캐시를 임의의 다른 모델로 교체하지 않았다.

## 설치/검증 기록

자산 루트 `logs/setup/`에 설치 원문 로그, `environment_status.json`, `installed_freeze.txt`가 있다. Git에는 작은 설치 manifest와 감사 결과만 보관한다. 감사 과정에서 생성되는 라이브러리 캐시도 자산 루트로 지정했다. 과거에 폐기한 실행 환경이나 결과는 사용하지 않았다.
