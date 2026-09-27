# TASK_005 - RCA 모델 및 외부 서비스

## 목적
공식 LLM·embedding·검색 조건과 접근을 준비한다.

## 작업 항목
- [x] 모델 별칭·embedding·검색 서비스 조사
- [x] snapshot·tokenizer·서빙 조건 미확정 기록
- [x] API 요청 없는 패키지·객체 구성 점검
- [ ] 승인된 서비스 접근 및 사용 모델 조건 확정

## 확인 사항
별도 과금 API 호출·자격정보 탐색·임의 로컬 모델 대체를 하지 않는다.

2026-09-24 사용자는 Qwen3.5-4B / Q5_K_M / thinking / llama.cpp에 한해 임시 로컬 대체를 승인했고, 2026-09-25 non-thinking 전환 및 단회 RE 형식 보정을 승인했다. 설치·인공 점검은 TASK_023/028/029에서 완료했다. 이후 승인된 BGE-M3 dense CPU 임베딩은 TASK_030에서 설치·두 검색 경로 인공 검증을 완료했다. 실제 연결·검색은 TASK_024, 원본 API 후속 검증은 TASK_025로 분리한다. 원본 모델·API 접근 문제는 해결 처리하지 않는다.

## 결과
기본 gpt-4o-mini와 ada-002 등을 기록했다. Search·최종 요약 모델 차이, snapshot 미공개, 키·접근 미구성 ACCESS-01이 남는다.

## 상태
BLOCKED
