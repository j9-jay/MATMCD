# TASK_013 - 승인된 Chroma 호환 환경 설치와 로컬 점검

## 목적

사용자가 잔여 불확실성을 추후 확인 항목으로 관리하도록 지시한 제안 조합을 설치하고 DEP-01의 패키지 누락을 해소한다.

## 작업 항목

- [x] 버전 차이와 검색 동작 불확실성을 별도 위험 기록에 등록
- [x] 승인안 lock 해시와 기존 141개 패키지 보존 조건 확인
- [x] 기존 외부 실험 환경에 고정 조합 설치
- [x] 패키지 일관성·기존 pin·원본 코드 보존 확인
- [x] 네트워크 없는 Chroma 저장·검색 및 LangChain 연결 점검
- [x] 실제 상태에 맞춰 blocker와 환경 문서 갱신

## 확인 사항

설치 범위는 TASK_012에서 제안한 58개 추가 패키지다. 다른 버전으로 바꾸거나 원본 requirements/코드를 수정하지 않는다. 실제 논문 실험·모델 API 호출은 하지 않는다. 시험용 벡터는 라이브러리 점검에만 쓰며 실험에 투입하지 않는다.

이전의 승인 대기 상태는 2026-09-23 사용자의 잔여 위험 수용 및 문제 발생 시 재확인 지시에 따라 진행 상태로 바뀐다. [RISK-001](../docs/FOLLOW_UP_RISKS.md)로 불확실성을 보존한다.

## 결과

제안한 lock으로 58개 패키지를 추가하여 총 199개가 설치되었다. 기존 141개 버전 변경은 0개이고 공식 소스도 보존되었다. PyPika 0.48.9 빌드와 `uv pip check`가 통과했다. [설치 기록](../docs/evidence/chromadb_install.json)과 [현재 freeze](../docs/evidence/installed_freeze_with_chromadb.txt)를 보존했다.

Chroma native client의 3개 시험 벡터 저장·상위 2개 검색, LangChain의 `from_documents → as_retriever → get_relevant_documents` 경로가 통과했다. 문서·메타데이터·순위와 거리(0, 약 0.02)를 확인했고 시험 collection을 정리했다. [로컬 점검 기록](../docs/evidence/chromadb_runtime.json)을 보존했다.

실험용 Top-k=10을 바꾼 것이 아니다. k=2와 인공 벡터는 독립된 3개 문서 점검 fixture에만 사용했다. 점검 프로세스에서 telemetry를 끄고 Python socket 연결을 차단했으며 연결 시도는 없었다. 공식 실험 설정을 변경하거나 모델/API/실제 데이터 실험을 실행하지 않았다.

LangChain의 기존 import 및 get_relevant_documents에 deprecation warning은 나왔지만 호출은 정상 동작했다. 공식 코드를 최신 API로 교체하지 않았다. DEP-01의 설치 차단은 해결됐고 버전 동일성은 RISK-001로 관리한다. 다른 blocker는 변경하지 않는다.

## 상태

DONE
