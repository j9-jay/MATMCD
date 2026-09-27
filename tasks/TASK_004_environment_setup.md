# TASK_004 - RCA 공통 의존성 환경 구성

## 목적
공식 Python·requirements를 유지한 RCA 실행 환경을 준비한다.

## 작업 항목
- [x] WSL·GPU 확인 및 Python 3.11.13 구성
- [x] 공식 140개 pin 설치
- [x] 승인된 Chroma·lxml·embedding 어댑터 추가·점검
- [x] system Graphviz 설치안 승인·설치·검증

## 확인 사항
저자 OS·Python 패치·Graphviz 버전은 미공개다. RISK-001~003은 현재 설치 Blocker로 재분류하지 않는다. Graphviz B안 설치는 TASK_021, A안의 저자 버전 확인·전환 검토는 TASK_022로 분리한다.

## 결과
2026-09-24: Python 패키지 201개를 유지하면서 [TASK_021](TASK_021_install_system_graphviz.md)의 Graphviz B안 설치·PNG 검증을 완료했다. 시스템 패키지 9개 추가, 기존 시스템 패키지 변경·삭제 0개, 공식 소스 37개 보존을 확인했다. 이 Task의 의존성 구성은 DONE이며 저자 환경 동일성은 [TASK_022](TASK_022_graphviz_author_version.md)와 TASK_018에서 계속 확인한다. 전체 RCA 실행 준비 완료를 의미하지 않는다.

## 상태
DONE
