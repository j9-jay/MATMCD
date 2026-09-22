# TASK_008 - 실험 결과 평가

## 목적
실제 생성된 결과를 저자의 평가 코드와 정의로 평가한다.

## 작업 항목
- [ ] 벤치마크 Precision/F1/FPR/SHD/NHD 평가
- [ ] RCA MAP@5/MAP@10/MRR 및 순위 평가
- [ ] 집계 방식과 원본 평가 코드 문제 검토

## 확인 사항
공식 코드의 고정된 결과 예시를 새 실험 결과로 사용하지 않는다. 평가 입력은 TASK_007이 실제 생성한 그래프와 GT/동일 변수 순서 및 실제 RCA rank다. 벤치마크 평가는 `Utils.metrics.Metrics(...).calc_all_metrics()` 경로를 사용한다. `LEMMA_Metrics.py`는 고정 rank를 집계하므로 현재 새 결과용 평가 명령이 아니다. 자세한 정의/집계 차이/출력 계획은 `docs/REPRODUCTION_SPEC.md`와 `docs/RUNBOOK.md`에 기록했다. 논문 실제 RCA 집계 입력 형식을 확인하기 전 결과 파일을 임의 작성하지 않는다.

## 결과
평가 미실행.

## 상태
TODO
