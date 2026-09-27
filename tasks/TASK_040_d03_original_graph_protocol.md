# TASK_040 - D03 원본 그래프·RWR 동작 근거 확인

## 목적
논문 알고리즘과 고정 공식 코드의 그래프 방향·프롬프트 재사용·단계별 RWR 입력을 대조하고, 근거로 확정할 사항과 승인할 변경을 분리한다.

## 작업 항목
- [x] 논문 §3/§4.3·Algorithm 1 및 공식 소스 대조
- [x] 원본 함수의 작은 인공 그래프/프롬프트 검사
- [x] 공개 코드 보존안과 논문 설명에 따른 교정안의 영향 기록
- [x] A안 사용자 승인 확인 및 configs/rca_protocol.json에 공개 동작 보존 반영
- [x] 발견한 문제와 근거·질문을 별도 문서 및 TASK_018 메일 초안에 보존
- [x] 로컬 RWR 단계 선택 함수에 초기/초기/보정/보정 규칙 반영·검증

## 확인 사항
원본 소스·프롬프트를 수정하지 않는다. 인공 입력 검증은 실제 RCA 실험이 아니다. 교정이 저자의 실제 실행 코드와 같다고 추정하지 않는다.

## 결과
인과 그래프 A[결과,원인]과 제약 C[원인,결과]를 구분했고 일괄 전치를 하지 않았다. 방향/edge type 프롬프트 불일치, 첫 질문 문장 재사용, 외부정보 없는 첫 CC 단계만 초기 그래프로 RWR를 하는 동작을 확인했다. 최종 MATMCD/RE는 이미 보정 그래프를 사용한다.

[상세 근거·A/B안](../docs/RCA_ORIGINAL_PROTOCOL_REVIEW.md), [D03/D04 총 40개 검사 PASS](../docs/evidence/rca_original_protocol_20260925T133730423769Z.json). 2026-09-26 사용자가 A안을 명시적으로 선택했다. [승인 프로필](../configs/rca_protocol.json)과 scripts/rca_ranking.py의 rank_stage_with_original_rwr에 원본 단계별 입력을 반영했다. 프롬프트·공식 소스는 수정하지 않았다. B 교정은 미적용이며 저자의 실제 실행 동일성은 UNCONFIRMED다.

[별도 저자 문의 준비 자료](../docs/AUTHOR_QUESTIONS_D03_D04.md)에 그래프 문장 방향/edge type, 첫 쌍 문장 재사용, 첫 외부정보 없는 제약 보정 단계의 RWR 입력을 근거와 함께 기록했다. 행렬 규약 차이 자체를 오류라고 문의하지 않는다. TASK_018에 연결했으며 미발송이다. 실제 전체 파이프라인 연결은 TASK_024에 남는다.

검증: [승인 방침 23개 PASS](../docs/evidence/rca_approved_protocol_20260926T055338403913Z.json), [적용 후 원본 동작 40개 PASS](../docs/evidence/rca_original_protocol_20260926T060140494272Z.json). 실제 실험은 미실행.

## 상태
DONE
