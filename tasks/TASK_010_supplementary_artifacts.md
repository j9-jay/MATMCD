# TASK_010 - 추가 발견된 전처리 및 비교 방법 자료 조사

## 목적
공식 MATMCD에 포함되지 않은 LEMMA-RCA 전처리 및 Efficient-CDLMs 공식 자료의 적용 가능 범위를 확인한다.

## 작업 항목
- [x] LEMMA-RCA 공식 전처리 저장소 확보
- [x] Efficient-CDLMs 공식 저장소 확보
- [x] MATMCD 적용 설정/누락 연결 과정 기록
- [x] 원본 자료 revision과 후속 필요 사항 기록

## 확인 사항
MATMCD 저자가 이들 코드를 어떤 설정과 수정으로 실행했는지는 별도 확인이 필요하다. 다른 논문의 기본값을 MATMCD 조건으로 간주하지 않는다.

## 결과
LEMMA-RCA 전처리/EVT 코드와 Efficient-CDLMs 원본 환경을 확인했다. MATMCD용 전처리 연결/수정본/전체 설정은 없으며 다른 논문의 기본값을 그대로 이식하지 않았다. revision과 차이는 `docs/ASSETS.md`에 기록했다. 저자 MATMCD의 branch/tag/release/PR/issue 및 프로젝트/ACL 페이지에서 추가 재현 bundle을 찾지 못했다. 공식 issue #1은 닫힌 데이터 요청이며 댓글은 없었다.

## 상태
DONE
