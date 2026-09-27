# TASK_014 - DEP-02 lxml 설치와 공식 HTML 추출 점검

## 목적

사용자가 승인한 `lxml==5.4.0`을 기존 199개 패키지를 유지하면서 추가하고, 공식 웹 수집기의 HTML 파싱/본문 추출 경로를 확인한다.

## 작업 항목

- [x] 공식 PyPI 메타데이터·호환 wheel·해시 확보
- [x] 기존 199개 유지 조건의 설치 시뮬레이션
- [x] lxml 5.4.0만 추가 설치 및 패키지 일관성 확인
- [x] 네트워크 없이 공식 파싱·추출 함수 점검
- [x] 원본 보존·현재 환경·추후 확인 항목 기록

## 확인 사항

원본은 `BeautifulSoup(html.text, "lxml")`를 사용하지만 requirements에 lxml이 없다. 최초 점검에서 `bs4.exceptions.FeatureNotFound`가 확인됐다. 저자 사용 버전은 미공개이며 5.4.0은 사용자가 승인한 호환 버전이다. 파서 종류/공식 추출 규칙을 교체하지 않는다.

실제 웹 수집·모델 API·논문 실험을 실행하지 않는다. 단순/잘못된 구조의 로컬 HTML 점검은 라이브러리 검사이며 논문 데이터 전처리가 아니다.

## 결과

기존 199개를 유지한 채 lxml 5.4.0만 추가하여 총 200개가 설치됐다. 공식 PyPI wheel의 해시를 확인하고, 해당 로컬 wheel만 대상으로 설치 시뮬레이션과 실제 설치를 진행했다. `uv pip check` 통과 및 기존 패키지 변경 0개를 확인했다. [설치 기록](../docs/evidence/lxml_install.json), [hash lock](../docs/evidence/lxml_5.4.0.lock.txt), [현재 freeze](../docs/evidence/installed_freeze_with_lxml.txt)를 보존했다.

공식 `WebScraper.convert_html_to_soup`와 `extract_main_content`를 변경 없이 호출했다. 기본 제목/문단 추출과 10단어 이하 제외, rule=1의 div 추출, UTF-8 한글, 닫는 태그가 없는 문단의 4개 점검이 통과했다. 실제 parser는 lxml이며 libxml2 2.13.8, libxslt 1.1.43을 관찰했다. [로컬 점검](../docs/evidence/lxml_runtime.json)에 입력 해시와 실제 출력을 기록했다. 외부 웹/API 요청과 논문 실험은 실행하지 않았다.

DEP-02의 패키지 누락은 해결됐다. 저자의 정확한 lxml/native library 버전과 잘못된 HTML 처리의 동일성은 [RISK-002](../docs/FOLLOW_UP_RISKS.md)에 기록했다. 관련 문제가 발생할 때만 재검토한다. 원본 코드·파싱·추출 규칙은 보존했다.

공식 배포 근거: [lxml 5.4.0 PyPI](https://pypi.org/project/lxml/5.4.0/). 원본 메타데이터와 wheel은 자산 루트 `raw_downloads/pypi_lxml_5.4.0/`, 실행 로그는 `logs/lxml_install/` 및 `logs/lxml_runtime/`에서 관리한다.

## 상태

DONE
