# TASK_034 - 공식 장애 시나리오 확인

## 목적
기존 공식 데이터 ZIP에 들어 있는 시나리오 자료를 확보하고 RCA 정답·장애 시각의 근거와 미확정 부분을 구분한다.

## 작업 항목
- [x] 메트릭 ZIP 5개에 포함된 PPTX 원문 확보·해시 기록
- [x] 슬라이드·표 텍스트 추출 및 CC 핵심 구성도 확인
- [x] CC 단일 replica 장애와 두 후보 pod의 평가 모호성 확인
- [x] PR 20220606 파일 날짜·실제 장애 시각·외부 원인과 정답 노드의 차이 기록
- [x] 시나리오 자료를 모델 입력과 분리
- [x] CC 원자료 ZIP의 고정 revision·SHA256 확보, 장애 전후 pod 설정과 시나리오 중복 확인

## 확인 사항
슬라이드를 편집하지 않았고 정답 정보를 RAG에 넣지 않았다. 전체 슬라이드의 시각적 검토가 아니라 텍스트 추출과 CC 핵심 이미지 확인이다. 전체 pod 정답과 논문 표 4 사례 대응은 아직 미확정이다.

## 결과
[공식 시나리오 확인 결과](../docs/RCA_SCENARIO_EVIDENCE.md), [추출 증거](../docs/evidence/rca_scenario_slides.json)에 기록했다. 스크립트는 scripts/inspect_rca_scenarios.py다. 이 Task 완료는 TASK_008의 정답·집계 확정을 의미하지 않는다.

추가 원자료 1,397,313,780바이트의 다운로드는 전송 중단 후 동일 파일을 재개하여 공식 해시 검증까지 완료했다. scripts/inspect_cc_original.py로 2,085개 엔트리와 전후 pod 목록을 확인했다. j7t55가 이후 목록에서 zvtz8로 바뀌지만 주입 정답의 명시적 증거로 단정하지 않았다. [원자료 조사 증거](../docs/evidence/rca_cc_original_inspection.json)에 근거와 한계를 남겼다. 정답 미확정은 D04에서 관리한다.

## 상태
DONE
