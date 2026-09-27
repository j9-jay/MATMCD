# 문제 발생 시 재확인할 항목

이 문서는 사용자가 현재 진행을 허용한 잔여 불확실성을 기록한다. 문제가 없으면 반복 조사하거나 버전을 임의 변경하지 않는다. 원본 환경과 동일하다고 확정한 목록은 아니다.

## RISK-001 — Chroma 호환 버전과 검색 결과의 동일성

- 관련 항목: DEP-01, [TASK_012](../tasks/TASK_012_chromadb_compatibility.md), [TASK_013](../tasks/TASK_013_install_chromadb.md)
- 사용자 판단(2026-09-23 KST): 나중에 문제가 생길 여지가 있는 항목으로 별도 표시하고, 문제 발생 시에만 다시 확인한다.
- 적용 기준: 제안한 Chroma 1.0.11 / PostHog 4.2.0 / OpenTelemetry 1.35.0·0.56b0 조합을 사용하며 기존 141개 패키지는 유지한다.
- 남은 불확실성: 저자의 Chroma와 전이 의존성 버전은 미확인. OpenTelemetry는 제공 논문보다 이후 릴리스다. 검색 엔진/기본 설정/근사 검색 동작 차이가 검색 문서와 이후 LLM 출력에 영향을 줄 수 있다. 영향 크기는 측정하지 않았다.
- 현재 예상: OpenTelemetry/PostHog는 실행 추적·이벤트 기록에 쓰여 검색 계산에 대한 직접 영향은 낮을 것으로 판단한다. Chroma의 실제 검색 결과 동일성은 확인하지 못했다.
- 적용 후 확인: 58개 추가 설치, 기존 141개 보존, 패키지 일관성 검사와 Chroma/LangChain의 작은 로컬 저장·검색 점검 통과. 시험 collection의 관찰값은 L2, ef_construction=100, ef_search=100, max_neighbors=16이었다. 저자가 이 값을 사용했다는 근거는 아니다. [설치 기록](evidence/chromadb_install.json), [로컬 점검](evidence/chromadb_runtime.json).
- 재확인 조건:
  - Chroma/LangChain/protobuf 관련 import·실행 오류, native crash 또는 비정상적인 리소스 사용
  - 같은 문서·벡터·질의로 검색했는데 결과가 예상과 다르거나, 저장/재사용 시 문서 혼입·누락·순위 문제가 관찰됨
  - 향후 실험 결과 불일치를 분석하면서 검색 단계가 원인 후보로 좁혀짐
- 재확인 시 보존할 자료: 승인된 lock과 설치 freeze, 오류 원문, 검색 입력 문서 ID/해시, 벡터·질의·반환 ID/순위/거리, collection 설정, 관련 실행 로그. 모델/API 비밀정보는 기록하지 않는다.
- 대응 원칙: 문제가 난 상태와 결과를 보존하고 원인을 확인한다. 저자 버전 확보 또는 대체 버전 비교가 필요하면 먼저 구체적 변경안을 제시하고 승인받는다. 논문 결과에 맞추려고 검색 설정을 바꾸지 않는다.
- 상태: WATCH — 문제 발생 시 재검토. 당장의 진행 차단 사유로 반복 취급하지 않는다.

## RISK-002 — lxml 버전과 HTML 본문 추출의 동일성

- 관련 항목: DEP-02, [TASK_014](../tasks/TASK_014_install_lxml.md)
- 사용자 승인(2026-09-23 KST): lxml 5.4.0 추가, 원본 파서/추출 코드 유지, 로컬 HTML 점검 및 버전 차이 별도 기록.
- 적용값: lxml 5.4.0, wheel 내 libxml2 2.13.8 / libxslt 1.1.43. 기존 BeautifulSoup 4.13.4 및 requests 2.32.3 유지.
- 남은 불확실성: 저자의 lxml/libxml2/libxslt 버전은 미공개다. 특히 잘못된 구조의 HTML을 복구하는 방식 차이가 추출 문장과 이후 검색/요약에 영향을 줄 수 있다. 전체 웹 문서에서의 동일성은 확인하지 않았다.
- 확인한 범위: 기존 199개 패키지 보존, lxml 1개 추가, pip check 통과. 공식 함수의 기본 제목/문단·단어 수 필터·div·한글·엔티티·닫히지 않은 문단 처리를 포함한 로컬 4개 사례 통과. [설치 기록](evidence/lxml_install.json), [점검 결과](evidence/lxml_runtime.json).
- 재확인 조건: HTML parser 예외, 원문 대비 비정상적인 본문 누락/중복/문자 깨짐, 또는 향후 결과 차이의 원인이 HTML 추출 단계로 좁혀진 경우.
- 재확인 시 보존할 자료: 해당 HTML 원문과 출처/수집 시각/해시, 추출 텍스트, rule 값, 실제 parser 및 lxml/libxml2/libxslt 버전, 오류 로그. 실제 페이지 내용이 바뀐 경우와 parser 차이를 구분한다.
- 대응 원칙: 먼저 같은 저장 HTML로 원인을 확인한다. parser나 라이브러리 버전 변경이 필요하면 해결안을 제시하고 승인받는다. 추출량이나 논문 수치를 맞추려고 필터 조건을 바꾸지 않는다.
- 상태: WATCH — 문제가 관찰될 때 재검토하며 현재 실행을 막는 항목으로 취급하지 않는다.

## RISK-003 — OpenAI embedding 어댑터 버전과 출력의 동일성

- 관련 항목: DEP-03, [TASK_015](../tasks/TASK_015_install_openai_embeddings.md). 실제 서비스 접근은 별도 ACCESS-01이다.
- 사용자 승인(2026-09-23 KST): `llama-index-embeddings-openai==0.3.1`만 추가하고 기존 200개를 보존하며 API 요청 없이 기본 설정/SDK 구성을 검증한다. 저자 버전 미확정 사항은 별도 기록한다.
- 적용값: 어댑터 0.3.1, 기존 core 0.12.37 및 OpenAI SDK 1.82.0 유지. 원본 MATMCD의 embedding 지정 방식은 변경하지 않았다.
- 관찰한 기본값: `text-embedding-ada-002`, mode=`text_search`, 질의·문서 모두 동일 모델, 배치 100, dimensions 미지정, 재시도 10, timeout 60초, client 재사용. 설치 버전에서 관찰했으며 저자의 실제 설정이라고 확정하지 않는다.
- 남은 불확실성: 저자 어댑터 버전, 실제 embedding 서비스 snapshot/서버 tokenizer/정밀도와 출력 벡터 동일성. 버전 차이가 요청 구성·배치/실패 처리 또는 벡터에 영향을 주면 검색 순위와 이후 요약/그래프 결과도 달라질 수 있다. 영향 크기는 측정하지 않았다.
- 확인한 범위: 기존 200개 유지/1개 추가, pip check, import와 실제 기본 resolver, 동기/비동기 SDK 객체 생성·재사용 통과. 네트워크 차단하에 점검용 가짜 키로 객체만 구성했다. 실제 인증·요청·embedding 생성은 수행하지 않았다. [설치 기록](evidence/openai_embeddings_install.json), [로컬 검증](evidence/openai_embeddings_runtime.json).
- 재확인 조건: 어댑터/SDK import 또는 요청 형식 오류, embedding 차원·개수 이상, 동일 입력의 예상하지 못한 검색 변화, 또는 결과 차이의 원인이 embedding 단계로 좁혀진 경우.
- 재확인 시 보존할 자료: 패키지 freeze/배포 wheel 해시, 입력 문서·질의 해시, 요청 모델명/비밀정보 없는 파라미터, 벡터 차원·해시·검색 순위, 서비스가 반환한 모델 식별자와 오류 로그. API 키는 기록하지 않는다.
- 대응 원칙: 당시 입력·출력과 오류를 보존하고 원인을 확인한다. 어댑터·모델·배치 등 변경이 필요하면 구체적 방안을 설명하고 승인받는다.
- 상태: WATCH — 버전 동일성은 관련 문제 발생 시 재검토한다. 인증·서비스 접근 미해결을 승인된 것으로 간주하지 않는다.
