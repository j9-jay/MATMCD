# 승인된 임시 BGE-M3 임베딩

2026-09-25 사용자 승인으로 BAAI/bge-m3의 dense 임베딩을 CPU·FP32·배치 1로 구성한다. 원본 text-embedding-ada-002를 재현한 것이 아니라 로컬 개발·비교용 별도 조건이다. 실제 RCA 실행과 검색 서비스 선택은 TASK_024에 남는다.

## 고정 구성과 출처

| 항목 | 값 |
|---|---|
| 공식 배포 | https://huggingface.co/BAAI/bge-m3 |
| revision | 5617a9f61b028005a4858fdac845db406aefb181 |
| 가중치 | pytorch_model.bin, 2,271,145,830 bytes |
| 가중치 SHA-256 | b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38 |
| tokenizer | 같은 revision의 tokenizer.json 및 설정, fast XLM-RoBERTa tokenizer |
| 토큰 한도 | 특수 토큰 포함 8192, 초과 시 오류, truncation=False |
| dense 계산 | 마지막 hidden state의 CLS → L2 정규화 → 1024차원 |
| 입력 가공 | query/document prefix 없음, 원문 변경 없음 |
| 실행 | CPU / float32 / batch 1 / eval / inference_mode |
| 로컬 실행 세부 | torch threads 8, transformers SDPA attention. MATMCD 저자 설정이 아닌 로컬 실행값 |
| 추가 로더 | transformers 4.51.3, safetensors 0.5.3. 기존 Python 환경과 분리 |

pooling은 공식 1_Pooling/config.json, 정규화는 modules.json의 Normalize 모듈, 길이는 sentence_bert_config.json/tokenizer_config.json에 근거한다. sparse·ColBERT head는 사용하지 않으므로 다운로드 대상에서 제외했다. 공식 README와 모델 설정도 원본 그대로 저장한다. BGE 모델 config의 transformers_version=4.33.0은 배포 파일 기록이며 이번 로더 4.51.3과 구분한다. 로더 선택은 기존 tokenizers 0.21.1 / huggingface-hub 0.32.2 / torch 2.7.0을 보존하기 위한 호환 선택이다.

설정 위치는 [local_embedding.json](../configs/local_embedding.json), 모든 외부 경로의 기준은 [paths.json](../configs/paths.json)이다. 다운로드 URL·파일별 SHA-256·non-LFS Git blob 해시·의존성 검사는 [설치 증거](evidence/local_embedding_install.json)에 남긴다.

## 자산 배치

MATMCD_DATA 아래 상대 경로다. 실제 파일이 필요한 경로만 생성한다.

| 경로 | 내용 |
|---|---|
| models/huggingface_BAAI_bge-m3 | 고정 원본 모델·tokenizer·설정·README·배포 metadata |
| raw_downloads/pypi_bge_m3_loader_tf4.51.3 | 로더 wheel 2개와 PyPI metadata |
| environments/pypi_bge_m3_loader_tf4.51.3 | 명시적 로컬 어댑터에서만 읽는 추가 패키지 경로 |
| logs/local_embedding/bge_m3_dense_cpu_fp32_v1 | 시도별 설치/검증 기록, 인공 벡터·길이·시간 |
| caches/retrieval_bge_m3_dense_cpu_fp32_v1 | 생성된 인공 Chroma/LlamaIndex 인덱스와 모델 식별 manifest |
| caches/tiktoken | 기존 LlamaIndex wheel의 동일 cl100k_base 데이터를 복사한 분할 tokenizer 캐시 |

기존 environments/d2i_matmcd_py311의 201개 패키지는 변경하지 않는다. 새 프로세스에서 local_embedding을 사용하지 않으면 추가 로더 경로는 활성화되지 않는다. 모델·벡터·wheel은 Git 저장소에 넣지 않는다.

## 두 검색 경로 연결 방식

scripts/local_embedding.py가 한 DenseBGE 인스턴스를 공유하는 langchain_embedding(engine), llamaindex_embedding(engine)을 제공한다. 공식 파일·전역 Settings를 수정하지 않으며 실제 RCA 진입점에 자동 주입하지 않는다.

- 웹 검색: 원본 EmbeddingRetriever 클래스의 코드를 그대로 추출해 실행하고 OpenAIEmbeddings 생성자만 인공 검증에서 로컬 어댑터로 치환한다. 기존 1000자/겹침 0/Chroma/top-k 10을 검증한다.
- 요약 자료 검색: LlamaIndex VectorStoreIndex에 embed_model을 명시한다. 기존 SentenceSplitter의 1024토큰/겹침 200과 기존 tokenizer, 기본 top-k 2를 유지한다. 생성 LLM 호출 없이 retriever까지 점검한다.
- LlamaIndex의 분할용 tokenizer와 BGE의 임베딩용 tokenizer는 구분한다. 분할 tokenizer를 BGE로 바꾸지 않으며, 실제 임베딩 입력의 토큰 수는 BGE tokenizer로 별도 검사한다.
- 캐시 경로는 profile별로 분리하고 index_directory(name)가 모델/revision/가중치/설정 식별자를 검사한다. manifest가 없거나 다르면 기존 인덱스 사용을 거절한다. 다른 모델로 전환할 때는 새 인덱스가 필요하다.

실제 RCA 통합에서 위 어댑터와 인덱스 식별 검사를 명시적으로 연결해야 한다. 단순히 모델을 설치하거나 이 모듈을 import해도 원본 ada-002 호출이 자동 변경되지 않는다.

## 명령

WSL Ubuntu에서:

```bash
cd /mnt/e/연구/MATMCD
MATMCD_ENV_PY=$(python3 -B -c 'import sys; sys.path.insert(0,"scripts"); from project_paths import asset_path; print(asset_path("environment")/"bin"/"python")')
```

승인된 동일 자산을 다시 준비할 때:

```bash
"$MATMCD_ENV_PY" -B scripts/setup_local_embedding.py --install
```

필요 시 인공 검증만 다시 수행할 때:

```bash
"$MATMCD_ENV_PY" -B scripts/check_local_embedding.py
```

검증은 인공 문서와 기존 라이브러리 분할/검색 경로만 사용한다. 웹 검색·유료 API·Qwen 생성·실제 RCA·평가를 실행하지 않는다. 각 시도에 새 로그와 인공 인덱스를 만들고 이전 결과를 보존한다. 임베딩 호출은 CPU만 사용한다. offline/local_files_only와 Python socket guard를 적용한다.

## 영향과 한계

임베딩 변경은 문서 순위→요약 근거→인과 제약→RCA 순위에 영향을 줄 수 있다. 원본 ada-002 결과와 수치나 개선 방향이 같다고 보장할 수 없다. 이후 기준 방법/개선 방법에는 같은 임베딩·문서 모음·검색 조건을 사용하도록 실험을 설계해야 한다.

인공 검색 통과는 실제 자료의 검색 품질이나 RCA 정확도 검증이 아니다. 8192는 모델의 지원 한도이며 현재 PC에서 모든 길이의 입력, Qwen 동시 실행 또는 실제 pod 전체 요약의 메모리 여유를 보장하지 않는다. 검증에서 측정한 길이·메모리·시간은 [런타임 증거](evidence/local_embedding_runtime.json)에 기록한다. 범위를 넘는 실제 검증은 TASK_024에서 별도 결정한다.

## 진행 기록

- 첫 설치는 모델/파일 검증 이후 subprocess에서 uv를 찾지 못해 실패했다. 기존 uv의 실제 위치를 확인해 설치 도구의 경로 해석만 수정했다. 조건 변경·재다운로드·원본 수정은 없으며 첫 FAILED 보고서를 보존했다.
- 첫 인공 검증에서는 CPU 벡터 생성·8192 초과 거절·원본 웹 top-10 검색·Chroma 저장/재로드가 통과했다. LlamaIndex 분할 생성 시 외부 TIKTOKEN_CACHE_DIR에 cl100k_base가 없어 네트워크 차단 오류가 발생했다. 해당 데이터는 기존 llama-index-core wheel 안에 있었으므로 원본 SHA-256(223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7)을 검증해 동일 bytes를 외부 캐시에 복사했다. 별도 tokenizer 선택·재학습·분할 변경·추가 API 호출은 없었다. FAILED 보고서·스크립트·설정 사본을 시도별 로그에 보존했다.
- 최종 인공 검증 PASS: 20260925T094722727219Z_validation. 모델/벡터/길이 초과/원본 웹 검색/Chroma 재로드/LlamaIndex 분할·검색·재로드/다른 모델 인덱스 거절 등 7개 점검 그룹 통과. 최종 시도의 dense forward 26회, 네트워크 연결 시도 0, CUDA 초기화 없음.
- LlamaIndex 인공 입력은 BGE 기준 932/932/302/12토큰이다. 실제 인코딩한 최대 길이는 932토큰이며, 8203토큰 입력은 forward 전에 거절했다. 8192토큰의 메모리 실측이나 실제 서비스 자료의 검색 품질 검증은 아니다.
- 최종 검증 전체 148.87초, 모델 로딩 52.09초, 최대 프로세스 RSS 2355.71MiB(약 2.30GiB). Qwen 동시 실행은 검증하지 않았다.
- 공식 파일 37개, 기존 Python 패키지 201개, 시스템 패키지 목록, Qwen 설정을 보존했다. TASK_030 DONE, 실제 RCA 통합 TASK_024 IN_PROGRESS, TASK_007/008/009 TODO.
