# TASK_005 - 모델 및 외부 서비스 명세

## 목적
실제로 사용한 모델·임베딩·검색 서비스를 식별하고 접근 제한을 기록한다.

## 작업 항목
- [x] 모델 별칭 및 정확한 revision 공개 여부 조사
- [x] tokenizer·embedding·검색 서비스 대조
- [x] 로컬 체크포인트 배포 여부 확인
- [x] 서비스 호출 없이 준비 상태 기록
- [ ] 저자 사용 모델 snapshot 및 원본 서비스 접근 조건 해소

## 확인 사항
유료 API 사용과 임의 로컬 모델 대체를 하지 않는다.

## 결과
기본 gpt-4o-mini, embedding text-embedding-ada-002, 절제 모델 및 provider를 기록했다. Search LLM의 gpt-4, 최종 summary의 라이브러리 기본 gpt-3.5-turbo와 논문 차이를 확인했다. API snapshot/서빙 설정/정확 tokenizer는 미공개이며 별도 과금 API를 사용할 수 없어 BLOCKED다. 로컬 가중치로 대체하지 않았고 모델 폴더/임의 checkpoint도 만들지 않았다.

## 상태
BLOCKED
