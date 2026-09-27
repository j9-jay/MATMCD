# TASK_012 - DEP-01 ChromaDB 호환 버전 검증

## 목적

사용자가 승인한 B안에 따라 저자 원본의 고정 패키지를 바꾸지 않는 ChromaDB 후보와 추가 의존성을 조사한다. 설치 승인에 필요한 구체적 변경안을 만든다.

## 작업 항목

- [x] 공식 패키지 메타데이터의 릴리스 시점과 의존성 확인
- [x] 실제 WSL Python 및 기존 141개 설치 버전을 고정한 의존성 해석
- [x] LangChain 연동 코드와 후보 패키지 API 정적 확인
- [x] 추가 패키지·원본 대비 차이·검증 한계 기록
- [x] 설치 승인용 구체적 버전·hash lock·검증 계획 준비

## 확인 사항

사용자 승인 범위는 호환성 검증이다. 실제 환경에 패키지를 추가하거나 원본 코드를 수정하지 않는다. 다운로드·resolver 캐시·원문 로그는 외부 자산 루트에 저장한다. Task 및 작은 검증 문서만 Git 프로젝트에 추가한다. 실험/API 호출은 하지 않는다.

0.5.23, 0.6.3, 1.0.11은 공개 시점으로 선정한 조사 후보다. 저자 사용 버전이라는 근거는 없다. 의존성 해석 성공을 런타임 또는 논문 결과 재현 성공으로 취급하지 않는다.

## 결과

Chroma 0.5.23/0.6.3/1.0.11의 메타데이터 해석은 통과했다. 이후 실제 API 형식과 protobuf 생성 코드를 확인해 단순 resolver 성공만으로 드러나지 않는 두 문제를 확인했다. PostHog 7.59.0은 Chroma의 위치 인자 3개 호출과 맞지 않는다. OpenTelemetry proto 1.11.1의 생성 코드는 기존 protobuf 6.31.1에서 `TypeError: Descriptors cannot be created directly.`로 실패했다.

`chromadb==1.0.11`, `posthog==4.2.0`, OpenTelemetry 1.35.0/0.56b0 계열을 포함한 조합을 제안한다. 기존 141개는 그대로이며 설치 시뮬레이션 결과 58개 추가 예정이다. OpenTelemetry 버전은 제공 논문보다 이후 릴리스인 로컬 선택이다. 저자 버전이라고 주장하지 않는다.

[상세 제안](../docs/CHROMADB_COMPATIBILITY.md), [증거](../docs/evidence/chromadb_compatibility.json), [설치 승인용 lock](../docs/evidence/chromadb_1.0.11.proposed.lock.txt)을 준비했다. 실제 설치·Chroma 전체 런타임·논문 실험은 수행하지 않았다. 환경 freeze와 공식 코드는 검증 전후 동일하다. 설치는 사용자 승인 대기이며 DEP-01과 TASK_004는 BLOCKED를 유지한다.

후속 상태: 위 문단과 사전 검증 JSON은 이 Task 완료 당시 기록이다. 이후 사용자가 잔여 불확실성을 추후 관리하도록 지시했고, [TASK_013](TASK_013_install_chromadb.md)에서 해당 lock으로 설치와 로컬 점검을 완료했다. 현재 설치 상태는 TASK_013을 따른다.

## 상태

DONE
