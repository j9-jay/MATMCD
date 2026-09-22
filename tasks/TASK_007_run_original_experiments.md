# TASK_007 - 원본 실험 실행

## 목적
입력과 환경의 차이점이 해소된 뒤 원본 실험을 수행한다.

## 작업 항목
- [ ] 실행 전 차단 사유 해소 및 별도 실행 지시 확인
- [ ] 벤치마크 실험 수행
- [ ] RCA 및 절제 실험 수행

## 확인 사항
현재 작업 범위에서 실행하지 않는다. `docs/RUNBOOK.md`에 명령/입출력/선행 조건을 기록했다. 기본 벤치마크 `python -B GTdatasets_experiment.py`, RCA `python -B LEMMA_experiment.py`는 **준비 차단 사유 해소 후 외부 작업공간에서만** 사용하는 저자 진입점이다. 현재 완주 가능한 명령으로 검증되지 않았다.

필요 입력: 5개 benchmark data/GT CSV, RCA EVT 처리 CSV와 로그/요약. 필요 모델: 논문의 GPT-4o mini/ada-002 및 표 3 절제 모델. 필요 서비스: Serper/Tavily와 모델 provider. 출력: 외부 작업공간 stdout, image, cache. TASK_003/004/005 및 원본 코드 문제를 먼저 해소해야 한다.

대상은 표 1/2 benchmark 및 baseline, 표 3 절제, 표 4 RCA다. 전체 sweep/일부 baseline의 MATMCD 적용 설정은 미공개이며 임의 구성하지 않는다.

## 결과
실험 미실행.

## 상태
TODO
