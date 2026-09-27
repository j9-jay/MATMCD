# TASK_033 - 공개 RCA 지표 함수 분리·검증

## 목적
고정 rank 데이터를 실행하는 공개 평가 스크립트에서 지표 함수만 변경 없이 재사용할 수 있도록 준비한다. 실제 예측·정답 대응과 평가 프로토콜은 별도로 확정한다.

## 작업 항목
- [x] 원본 ZIP과 평가 코드의 바이트 일치 확인을 실행 조건으로 구현
- [x] PRK/MAPK/MRR 함수 AST만 원문 그대로 추출해 재사용
- [x] 명시적으로 제공한 양의 1-based rank만 받는 호출 인터페이스 구현
- [x] 공개 예시 수치 및 top-k 경계·잘못된 rank 거부 확인
- [x] 공개 MAPK 정의와 일반 AP의 차이 및 실제 평가의 미확정 부분 기록

## 확인 사항
원본의 rank < k, MAPK 누적 방식, MRR을 바꾸지 않는다. 후보 단위, KPI 포함 여부, root cause 매핑, 동점·반복·사례 선택은 이 도구가 결정하지 않는다. 고정 예시 검증은 새 RCA 실험 결과가 아니다.

## 결과
scripts/rca_metrics.py 구현 및 11개 검사 PASS. [정의와 검증](../docs/RCA_METRIC_ADAPTER.md), [검증 증거](../docs/evidence/rca_metric_adapter_20260925T105908213664Z.json). 실제 결과 평가 TASK_008은 TODO이며 본 Task 완료와 구분한다.

## 상태
DONE
