# TASK_015 - DEP-03 OpenAI embedding 어댑터 설치와 로컬 점검

## 목적

승인된 `llama-index-embeddings-openai==0.3.1`만 추가하여 LlamaIndex 기본 embedding resolver의 패키지 누락을 해결한다. 기존 200개 패키지와 공식 코드를 유지한다.

## 작업 항목

- [x] 공식 PyPI 메타데이터·wheel·해시 및 현재 의존성 충족 여부 확인
- [x] 기존 200개 유지 조건의 설치 시뮬레이션 및 추가 설치
- [x] 패키지 일관성, import, 실제 기본 설정 및 SDK 객체 구성 점검
- [x] API 요청 없이 확인한 범위와 버전 미확정 위험 기록

## 확인 사항

사용자가 제안된 0.3.1 추가와 실제 API 호출 없는 검증을 승인했다. 저자 사용 버전은 미공개이므로 이 버전을 저자의 실험값으로 간주하지 않는다. 공식 `VectorStoreIndex.from_documents`의 모델 선택이나 설정을 변경하지 않는다. 실제 embedding 생성·검색·LLM 호출·논문 실험은 실행하지 않는다. API 접근과 모델 snapshot은 별도 ACCESS-01이다.

## 결과

기존 200개 버전 변경 없이 어댑터 1개만 추가하여 총 201개가 됐다. 공식 PyPI wheel SHA256을 확인했고 로컬 wheel로 설치 시뮬레이션·설치를 완료했다. 기존 `openai==1.82.0`, `llama-index-core==0.12.37`이 어댑터의 의존 조건을 충족하며 `uv pip check`가 통과했다. [설치 기록](../docs/evidence/openai_embeddings_install.json), [추가 패키지 hash lock](../docs/evidence/llama_index_embeddings_openai_0.3.1.lock.txt), [201개 freeze](../docs/evidence/installed_freeze_with_openai_embeddings.txt)를 보존했다.

첫 설치 시뮬레이션은 `In --require-hashes mode, all requirements must be pinned upfront with ==, but found: llama-index-core` 오류로 종료됐다. constraints만으로는 uv의 모든 전이 의존성 hash lock 요구를 충족하지 못했다. 이때 실제 설치는 진행되지 않았으며 기존 200개와 공식 코드가 그대로였다. 설치 스크립트에서 기존 Chroma 199개 lock과 lxml lock도 입력하도록 보완한 뒤 통과했다. 패키지 버전·원본 requirements·해시 검사 조건은 변경하지 않았다. 실패 원문은 자산 루트 `logs/openai_embeddings_install/20260922T155837Z/`, 성공 기록은 `logs/openai_embeddings_install/20260922T160116Z/`에 있다.

네트워크를 차단한 별도 프로세스에서 import, `resolve_embed_model("default")`, `Settings.embed_model`, 동기/비동기 OpenAI SDK 객체 생성과 재사용을 확인했다. 키 없는 상태의 `No API key found for OpenAI` 오류도 확인했다. 이후 객체 구성에만 임시 가짜 키 문자열을 사용했으며 자격정보를 조회하거나 실제 인증·embedding API를 호출하지 않았다. 기본 모델/질의·문서 엔진은 `text-embedding-ada-002`, mode는 `text_search`, 배치 크기 100, dimensions 미지정, 재시도 10, timeout 60초였다. 이 값은 설치한 라이브러리의 관찰값이며 저자 실험값 확정이 아니다. [로컬 검증 기록](../docs/evidence/openai_embeddings_runtime.json)에 저장했다.

공식 파일 43개를 보존했고 실제 실험·embedding 생성·외부 HTTP 요청은 실행하지 않았다. DEP-03 패키지 누락은 해결했다. 저자 어댑터 버전과 출력 동일성의 미확정 사항은 [RISK-003](../docs/FOLLOW_UP_RISKS.md)으로 관리한다. API 접근·모델 snapshot은 ACCESS-01에 남으며 전체 재현 준비 완료를 뜻하지 않는다.

배포 근거: [공식 PyPI 0.3.1 메타데이터](https://pypi.org/pypi/llama-index-embeddings-openai/0.3.1/json). 메타데이터와 wheel은 자산 루트 `raw_downloads/pypi_llama_index_embeddings_openai_0.3.1/`, 로컬 검증 로그는 `logs/openai_embeddings_runtime/`에서 관리한다.

## 현재 범위

위 파일 수와 점검은 당시 전체 범위의 이력이다. 현재 RCA 부분집합과 삭제 내역은 [TASK_017](TASK_017_scope_rca_only.md)을 따른다.

## 상태

DONE
