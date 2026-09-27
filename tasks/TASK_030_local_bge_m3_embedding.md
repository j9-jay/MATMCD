# TASK_030 - 승인된 BGE-M3 로컬 임베딩 구성

## 목적
TASK_024의 첫 결정으로 사용자 승인 BAAI/bge-m3 dense 임베딩을 CPU·FP32·배치 1로 준비하고, 웹 문서 검색 및 LlamaIndex 검색 연결을 인공 자료로 검증한다. 저자 ada-002와 다른 임시 조건이다.

## 작업 항목
- [x] 사용자 승인 범위 및 공식 모델의 pooling/tokenizer 설정 확인
- [x] 모델·tokenizer revision/해시 고정 및 외부 자산 다운로드
- [x] 기존 Python 201개 보존, 별도 경로에 필요한 로더 의존성 구성
- [x] dense 임베딩과 LangChain/LlamaIndex 어댑터 구현
- [x] 입력 길이 초과 거절 및 분할·top-k 보존 검증
- [x] CPU·FP32·배치 1 자원 사용 및 인공 검색·저장/재로드 검증
- [x] 원본·기존 환경 보존 확인, 증거·사용법·상위 Task 갱신

## 확인 사항
- 승인: 2026-09-25 사용자 “너가 권장하는 방법으로 진행”. 직전 제안의 첫 범위인 BGE-M3 dense/CPU 우선 검증이다.
- 기존 Qwen 구성, 웹 검색 서비스, CODE-01, 로그/RWR, 실제 RCA 실행 변경의 승인이 아니다.
- 모델은 BAAI/bge-m3 revision 5617a9f61b028005a4858fdac845db406aefb181. 공식 config의 FP32, CLS pooling 및 Normalize 모듈을 따른다.
- 로더 transformers 4.51.3/safetensors 0.5.3은 기존 tokenizers 0.21.1, huggingface-hub 0.32.2, torch 2.7.0과 호환되는 로컬 구현용 선택이다. 저자 버전 주장이 아니다. 기존 환경 밖의 전용 추가 패키지 경로를 사용한다.
- 문서 분할과 top-k는 변경하지 않는다. BGE tokenizer로 특수 토큰 포함 8192 초과 시 오류 처리하고 자르거나 다른 모델로 바꾸지 않는다.
- 다운로드의 첫 Windows 일반 sandbox 요청은 소켓 권한으로 실패했다. 승인 범위의 공개 다운로드를 escalation으로 조회했으며 모델/조건 변경은 없다.

## 결과
- 설치 완료: 모델·tokenizer 고정 원본 검증, transformers/safetensors만 별도 경로에 설치. 기존 201개와 공식 37개 보존.
- 첫 설치 실패: subprocess의 uv PATH 누락. 기존 /home/goo8412/.local/bin/uv 확인 후 설치 도구의 경로 해석만 수정, 재설치 조건 변경 없음. FAILED 로그 보존.
- 첫 검증 부분 통과: CPU FP32 batch 1, 1024차원 정규화, query/document 동일 입력 일치, 8203토큰 입력 추론 전 거절, 원본 웹 top-10 검색, Chroma 저장/재로드.
- 첫 검증 실패: 외부 tiktoken 캐시 미준비로 LlamaIndex 분할 초기화에서 네트워크 차단 오류. 기존 LlamaIndex wheel에 포함된 cl100k_base 데이터를 원본 해시 확인 후 외부 캐시에 복사. tokenizer/분할/모델을 바꾸지 않았다. FAILED 로그와 당시 코드·설정 사본 보존.
- 최종 인공 검증 PASS: 20260925T094722727219Z_validation. 7개 점검 그룹, 실제 dense forward 26회. 웹 분할 1000자/겹침 0/top-10 및 LlamaIndex 분할 1024토큰/겹침 200/top-2 유지. Chroma/LlamaIndex 저장·재로드와 모델 식별 불일치 거절 통과.
- LlamaIndex 인공 문서의 BGE 토큰 길이는 932/932/302/12이며 최대 932토큰을 실제 추론했다. 8203토큰 입력은 추론 전 거절했다. 모델 한도 8192 전체의 메모리 검증은 아니며 실제 RCA/Qwen 동시 실행은 하지 않았다.
- CPU float32 batch 1, GPU 초기화 없음. 검증 전체 148.87초, 모델 로딩 52.09초, 최대 프로세스 RSS 2355.71MiB. 시간은 이 인공 검증에서의 관측값이며 실제 RCA 예상 시간으로 전용하지 않는다.
- 공식 37개/기존 Python 201개/시스템 패키지/Qwen 설정 보존. 최종 검증에서 Python socket 연결 시도 0, API·웹 검색·생성 LLM·RCA·평가 실행 0.
- [사용법·제한](../docs/LOCAL_EMBEDDING.md), [설치 증거](../docs/evidence/local_embedding_install.json), [검증 증거](../docs/evidence/local_embedding_runtime.json). 실제 RCA 호출 지점 주입과 검색 방식 선택은 TASK_024에 남는다.

## 상태
DONE
