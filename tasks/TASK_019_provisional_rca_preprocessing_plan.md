# TASK_019 - 근거를 명시한 임시 RCA 전처리안

## 목적

저자 답변을 기다리면서 검토할 수 있도록, 확보한 LEMMA-RCA 입력과 공식 코드를 대조하여 구체적인 임시 전처리안을 작성한다.

## 작업 항목

- [x] MATMCD 입력 규약과 LEMMA-RCA 참고 구현 대조
- [x] 보유 ZIP의 NPY·시간축·pod·KPI·로그 연결 구조 점검
- [x] 임시 선택값·근거·영향·실패 조건 명세
- [x] 원본 조건 확인 항목을 TASK_018에 연결
- [x] 문서·설정 일관성과 원본 보존 확인

## 확인 사항

2026-09-23 사용자 "그래 진행해줘"는 직전 제안인 구체적인 임시 전처리안 작성에 대한 진행 지시로 해석한다. 초안의 임시 선택은 저자 값으로 주장하지 않는다. 이번 Task는 데이터 점검과 검토 가능한 명세 작성이며, 실제 전처리 적용·과학적 코드 수정·실험·API 호출·메일 발송을 포함하지 않는다.

보유한 공식 ZIP을 풀어 실험 입력을 생성하지 않고 읽어서 구조를 확인한다. 검사 도구의 Python/NumPy 버전은 별도로 기록하며 논문 실행 환경을 바꾸지 않는다.

## 결과

구체안 작성 완료. [상세 명세](../docs/PROVISIONAL_RCA_PREPROCESSING.md)와 [설정 초안](../configs/rca_preprocessing_proposal.json)에 값·근거·영향·실패 조건을 기록했다. 초안은 PROPOSED_NOT_APPLIED이고 원본 입력 연결은 비어 있다.

5개 날짜에서 이름이 명시된 메트릭 NPY 31개와 별도 스키마 2개를 검사했다. 원본 ZIP을 읽어 배열·시간축·KPI·pod를 확인했으며 로그 ZIP에서는 pod_removed 목록과 각 날짜의 structured/template 헤더 예시를 읽었다. 실제 로그 본문 전체를 점검했다는 뜻은 아니다.

첫 검사에서는 PR 20211203의 합본 파일에 KPI_Feature가 없어서 KeyError가 났다. 확인 결과 jaeger_Feature 등을 사용하는 별도 스키마였다. 검사기가 스키마 차이를 기록하고 명명된 메트릭을 독립적으로 조사하도록 보완했으며 원본은 변경하지 않았다. 최초 오류와 최종 errors=[]를 [inventory](../docs/evidence/rca_input_inventory.json)에 함께 보존했다.

권장 후보는 시간 교집합 전체·pod 합집합·공개 참고 SPOT 설정·양의 이상 점수 pod 유지·pod별 z-score 동일 가중 평균·KPI 마지막 열 보존이다. 시간 정렬·보유 메트릭 차이·EVT 유지 기준·통합 방식은 저자 동일성이 확인되지 않은 로컬 선택으로 명시했다. CC IOPS의 5개 상수 pod, 정확한 로그 이름 누락, PR 20220606 KPI 의미 불일치를 TASK_018 메일 초안에도 추가했다.

정적 검증에서 5개 사례와 설정의 관찰값이 일치했고, 공식 37개 파일의 원본 ZIP 대비 SHA256 일치·검사기 문법·문서 링크·후속 TODO 유지를 확인했다. [검증 결과](../docs/evidence/rca_preprocessing_proposal_check.json)는 all_pass=true다. native SPOT 호환성과 과학적 타당성·저자 동일성을 검증한 것은 아니다.

입력 부재 INPUT-02와 저자 동일성 미확정 상태는 유지한다. 실제 전처리 구현·입력 생성은 [TASK_020](TASK_020_apply_provisional_rca_preprocessing.md) TODO다. 출력 폴더·CSV·실험 결과·메일 발송은 생성하거나 실행하지 않았다.

## 상태

DONE
