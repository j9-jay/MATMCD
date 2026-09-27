# DEP-01 호환 버전 검증과 설치 승인안

2026-09-23 KST. 사전 검증 이후 사용자가 잔여 불확실성을 추후 문제 발생 시 확인할 항목으로 수용했다. **제안한 조합 설치와 로컬 저장·검색 점검을 TASK_013에서 완료했다. DEP-01의 패키지 누락은 해결됐으며 원본 버전 동일성은 [RISK-001](FOLLOW_UP_RISKS.md)로 관리한다.**

## 제안

`chromadb==1.0.11`을 다음 전이 의존성과 함께 설치하는 안을 제안한다. 원본 requirements 140개와 기존 로컬 setuptools 84.0.0을 모두 유지하며 총 58개 패키지를 추가한다. 전체 설치 목록은 199개다.

| 핵심 패키지 | 제안 버전 | 선택 근거 |
|---|---|---|
| chromadb | 1.0.11 | 2025-05-28 공개. 공식 requirements 커밋(2025-05-29 00:03:08 UTC) 직전 릴리스이며, 기존 LangChain에서 사용하는 API 서명을 확인함 |
| posthog | 4.2.0 | 당시 공개된 버전. Chroma의 `capture(distinct_id, event, properties)` 호출 형식과 일치 |
| opentelemetry-api/sdk/proto 및 exporter 2종 | 1.35.0 | 원본 protobuf 6.31.1을 지원하는 메타데이터 및 생성 코드 확인. 2025년 7월 릴리스이므로 논문 제공본보다 이후 버전이라는 차이를 수용해야 함 |
| opentelemetry-instrumentation/asgi/fastapi, semantic-conventions, util-http | 0.56b0 | 위 1.35.0 계열에 맞춘 동반 버전 |
| fastapi | 0.115.9 | Chroma 1.0.11의 정확한 의존성 pin |
| pypika | 0.48.9 | 당시 공개된 버전. wheel이 없어 설치 시 해시로 확인한 소스 배포본의 빌드가 필요 |

전체 버전·배포 파일 해시가 포함된 [승인된 lock](evidence/chromadb_1.0.11.proposed.lock.txt)으로 설치했다. 파일명은 사전 제안 당시 이름을 보존한다. `scripts/setup_chromadb.py`는 이 lock의 승인된 해시를 확인한 후 설치한다. 추가 58개 전체 목록은 [설치 기록](evidence/chromadb_install.json)의 `added`에 있다.

이 조합은 **저자가 실제 사용한 환경이라고 확인된 조합이 아니다.** 버전 선택 이유는 공개 시점, 기존 pin 보존, 확인된 API 충돌 회피다. 검색 결과 및 수치의 동일성은 주장하지 않는다. 특히 Chroma 1.0.11의 기본 클라이언트 구현은 RustBindingsAPI이며, 저자가 이 구현을 사용했는지는 모른다.

## 수행한 검증

1. 실제 WSL Ubuntu의 Python 3.11.13을 대상으로 의존성을 해석했다. 기존 설치 141개를 모두 정확히 고정했다.
2. Chroma 0.5.23, 0.6.3, 1.0.11을 현재 PyPI 기준으로 각각 조사했다. 세 후보 모두 메타데이터 해석은 통과했지만 이것만으로 실행 가능하다고 판정하지 않았다.
3. 1.0.11의 추가 의존성을 공식 requirements 커밋 시점 이전으로 제한했다. 기존 로컬 setuptools 84.0.0만 날짜 제한 예외로 유지했다.
4. 이때 발견된 PostHog/OpenTelemetry 문제를 아래와 같이 확인하고, 구체적 호환성 제안 조합을 다시 해석했다.
5. 최종 hash lock으로 실제 환경에 `uv pip install --dry-run --require-hashes`를 실행했다. **58개 추가, 기존 패키지 교체·삭제 0개**를 확인했다.
6. 검증 전후 freeze가 동일했다. 공식 소스도 변경하지 않았다.

| 확인 범위 | 결과 |
|---|---|
| 기존 140개 공식 pin + 로컬 setuptools 보존 | 통과 |
| 전체 의존성 해석 | 통과, 199개 |
| 실제 환경 대상 설치 시뮬레이션 | 통과, 58개 추가 예정 |
| LangChain 0.3.24 → Chroma API 정적 대조 | Client, get_or_create_collection, get_max_batch_size, create_batches, upsert, query의 호출에 필요한 인자 확인 |
| PostHog 함수 인자 검사 | 4.2.0은 Chroma의 위치 인자 3개 지원; 7.59.0은 미지원 |
| OpenTelemetry protobuf 코드 부분 검사 | 1.11.1 실패, 1.35.0 성공 |
| Chroma import·네이티브 라이브러리·로컬 저장/검색·LangChain 연결 | 후속 TASK_013에서 작은 시험용 벡터로 통과. 논문 데이터/전체 RAG 결과 동일성 검사는 아님 |
| 원래 모델/API/웹 검색/논문 데이터 실험 | 미실행 |

## 발견한 실제 오류와 처리

### PyPika 배포 형식

처음 `--no-build`로 조사하면 `pypika>=0.48.9 has no usable wheels` 때문에 날짜 제한 해석이 실패했다. 이는 논문의 과학적 조건 충돌이 아니라 검사 도구가 소스 배포본을 배제한 결과다. `uv pip compile`에서 임시 빌드 환경을 통한 메타데이터 확인을 허용한 뒤 해석이 통과했다. 대상 실험 환경에 PyPika나 다른 후보 패키지를 설치하지 않았다.

### PostHog 호출 형식

Chroma 1.0.11의 `chromadb/telemetry/product/posthog.py`는 위치 인자 3개를 전달한다. 현재 resolver가 선택한 PostHog 7.59.0의 함수는 위치 인자를 1개만 받는다. Chroma는 이 오류를 잡아 로깅하므로 이것만으로 검색 전체 실패를 주장하지 않는다. 확인된 호출 불일치를 피하기 위해 당시 릴리스인 4.2.0을 제안한다. 텔레메트리 전송은 수행하지 않았다.

### OpenTelemetry와 protobuf

당시 날짜로 제한하면 resolver는 `opentelemetry-proto==1.11.1`을 선택했다. 메타데이터에는 `protobuf>=3.13.0`만 적혀 있어 원본 6.31.1과 충돌하지 않는 것처럼 보인다. 그러나 공식 wheel의 `common_pb2.py`를 기존 protobuf 환경의 별도 네트워크 차단 프로세스에서 실행하니 다음 오류가 발생했다.

```text
TypeError: Descriptors cannot be created directly.
```

1.33.1과 1.34.x는 `protobuf<6.0,>=5.0`을 요구해 원본 pin과 맞지 않는다. 1.35.0은 `protobuf<7.0,>=5.0`을 선언하고 동일한 부분 검사도 통과했다. protobuf를 낮추거나 pure-Python 구현으로 바꾸는 우회는 하지 않았다. 해당 검사에서 패키지를 설치하거나 후보 Chroma 전체를 import하지 않았다.

## 승인 후 적용한 내용

1. 위 lock을 그대로 사용해 기존 외부 실험 환경에 58개 패키지를 추가한다. 다른 버전 선택이나 원본 pin 교체가 필요해지면 중단하고 보고한다.
2. 설치 후 패키지 일관성, 기존 pin, Chroma import를 확인한다.
3. 네트워크를 차단하고 작은 시험용 벡터로 Chroma 생성·저장·검색 및 LangChain 연결만 점검한다. 시험용 벡터는 패키지 동작 확인용이며, 논문의 모델·임베딩·데이터를 대체하지 않는다.
4. 실제 논문 실험이나 API 호출은 하지 않는다. 성공한 검증 범위와 원본 버전 미확정 상태를 따로 기록한다.

위 범위의 설치·점검을 완료했다. [설치 기록](evidence/chromadb_install.json), [현재 freeze](evidence/installed_freeze_with_chromadb.txt), [로컬 점검 결과](evidence/chromadb_runtime.json)를 보존한다. 원본과의 동일성에 관한 추가 비교는 RISK-001의 문제 발생 조건에 해당할 때 수행한다.

## 증거 위치와 한계

- [Task 012](../tasks/TASK_012_chromadb_compatibility.md)
- [검증 JSON](evidence/chromadb_compatibility.json): resolver 명령/결과, 추가 버전, 다운로드 해시, 부분 검사 오류, 설치 시뮬레이션 원문
- 자산 루트 `raw_downloads/pypi_chromadb_compatibility/`: PyPI 메타데이터와 검사한 공식 wheel
- 자산 루트 `logs/chromadb_compatibility/20260922T150452Z/`: UTC 기준 원문 로그와 각 후보 lock
- `scripts/check_chromadb_compatibility.py`는 초기 후보/날짜 제한 검사를 재현한다. 이후 원인 확인과 최종 조합 명령은 JSON에 기록했다. 스크립트의 재실행 출력은 `chromadb_compatibility_initial.json`으로 분리하여 현재 종합 보고서를 덮어쓰지 않도록 했다. 승인 검토 시에는 현재 종합 기록과 lock의 해시를 기준으로 한다.

사전 설치 시뮬레이션 이후 실제 PyPika 빌드와 Chroma 로딩·로컬 검색도 통과했다. lock은 런타임 패키지 및 배포본 해시를 고정하며, 소스 빌드 도구 전체 환경을 저자의 환경으로 고정한 것은 아니다. 실제 논문 검색 순위나 결과의 동일성은 별도의 문제다. 사전 검증 JSON의 설치 미승인/미실행 표시는 당시 snapshot이며, 후속 설치 상태는 별도의 설치·로컬 점검 JSON을 따른다.

공식 근거: [Chroma 1.0.11](https://pypi.org/project/chromadb/1.0.11/), [PostHog 4.2.0](https://pypi.org/project/posthog/4.2.0/), [OpenTelemetry proto 1.35.0 metadata](https://pypi.org/pypi/opentelemetry-proto/1.35.0/json), [저자 requirements](https://github.com/D2I-Group/matmcd/blob/ef2c3ecad0f5ddb9c3d20a8523c2c1043d213190/requirements.txt).
