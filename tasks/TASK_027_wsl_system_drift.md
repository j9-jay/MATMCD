# TASK_027 - WSL 자동 업데이트와 시스템 버전 차이

## 목적
과거 시스템 snapshot과 현재 WSL 사이의 차이를 기록하고, 현재 설정을 유지하면서 실제 실행 전후 환경 변화가 드러나도록 한다.

## 작업 항목
- [x] Graphviz 설치 직후 snapshot과 현재 dpkg 상태 대조
- [x] 차이 175개와 최근 unattended-upgrade 이력 보존
- [x] 로컬 검증 중의 보존과 과거 환경 동일성을 구분
- [x] 시스템 설정은 유지하고 실행 전후 snapshot·변경 감지 방침을 실행기에 연결
- [x] 현재 OS baseline 기록 — 실제 실행 시 다시 포착하여 실행 결과와 연결
- [x] 영향이 확인될 때만 해당 기능 재검증하고 변경 사실을 숨기지 않는 방침 명시

## 확인 사항
- TASK_023 설치 스크립트는 curl 다운로드·tar 분리 추출만 수행하며 apt/dpkg 설치 명령을 호출하지 않았다.
- 2026-09-24 21:51 KST까지의 APT history에 unattended-upgrade 실행이 있다. 이는 21:53 이후 두 모델 검증 전에 끝난 최근 이력이다.
- 과거 Graphviz snapshot 대비 패키지 차이 175개. 예: libc6 2.39-0ubuntu8.6→2.39-0ubuntu8.9. 전체 차이는 docs/evidence/local_llm_system_drift.json.
- 모델 검증은 당시 시작/종료 사이 시스템 패키지가 같은지 확인했고 두 번 모두 같았다. 이것이 Graphviz 설치 직후부터 전혀 바뀌지 않았다는 뜻은 아니다.
- 공식 소스 37개와 재현용 Python 가상환경 201개는 보존됐다. 시스템 Python 3.12 업데이트와 별도 재현용 Python 3.11 환경을 구분한다.
- 실제 RCA나 원본 시스템 의존 기능에 대한 영향은 아직 측정하지 않았다. 최신 상태가 저자 환경과 일치한다는 근거도 없다.

## 결과
2026-09-26 읽기 전용 [현재 baseline](../docs/evidence/rca_environment_20260926T061459160665Z.json)을 기록했다. Ubuntu 24.04.3, WSL kernel 6.18.33.2, 시스템 패키지 805개, Python 3.11.13/201개, 공식 파일 37개다. 자동 업데이트 서비스는 포착 시 inactive였으며 timer는 기존대로 유지했다. 시스템 설정·패키지 변경은 하지 않았다.

run_local_rca.py는 실제 실행 전후 패키지/소스/설정 snapshot을 저장하고 차이가 있으면 결과를 REQUIRES_ENVIRONMENT_REVIEW로 표시한다. 현재 baseline은 저자 원본 환경 동일성을 입증하지 않는다. 향후 자동 업데이트 중지/OS rollback을 하려면 구체적 변경안과 승인이 필요하지만 현재 보존·기록 방침의 선행 조건으로 요구하지 않는다.

현재 패키지 snapshot과 최근 APT history 요약을 MATMCD_DATA/logs/local_llm/qwen35_4b_q5km_thinking_provisional_v1에 보관했다. 초기 최종 감사의 과거 baseline 동일성 assertion 실패를 정상으로 숨기지 않고 차이로 기록했다. OS rollback·서비스 중지·자동 업데이트 설정 변경은 하지 않았다.

## 상태
DONE
