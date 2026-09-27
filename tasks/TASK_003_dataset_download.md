# TASK_003 - RCA 공식 입력 준비

## 목적
LEMMA-RCA를 공식 MATMCD 입력과 연결한다.

## 작업 항목
- [x] ZIP 10개·revision·URL·해시 확보
- [x] 내부 구조와 최종 CSV 부재 조사
- [x] 공식 전처리 자료 조사
- [ ] 최종 CSV와 EVT·pod·metric·기간·열 순서 확보

## 확인 사항
배포명 Preprocessed와 MATMCD 최종 입력은 다르다. 기본값으로 재구성하지 않는다.

저자에게 최종 입력·전처리 설정을 확인하는 일은 [TASK_018](TASK_018_author_clarifications.md)에 모았다. [TASK_019](TASK_019_provisional_rca_preprocessing_plan.md)의 구체안을 사용자가 승인하여 [TASK_020](TASK_020_apply_provisional_rca_preprocessing.md)에서 임시 입력을 준비한다. 실제 생성 결과는 해당 Task에 기록하며, 이 Task의 저자 원본 확보·동일성 확인과 구분한다.

## 결과
공개 코드의 5개 날짜에 해당하는 배포 원본 ZIP은 확보했으나 저자의 최종 CSV와 정확 전처리는 미확보다. 표 4 사례 선택·집계 대응도 확인해야 한다.

2026-09-24: 별도 TASK_020의 승인 프로필로 임시 metric CSV 5개 생성·검증을 마쳤다. [실제 결과](../docs/PROVISIONAL_RCA_PREPROCESSING_RESULT.md)에 크기·pod 유지·로그 누락을 기록했다. 이 Task는 저자 원본 확보를 다루므로 BLOCKED를 유지하며, 임시 준비 완료와 구분한다. 원본 실행 입력에 자동 연결하지 않았다.

## 상태
BLOCKED
