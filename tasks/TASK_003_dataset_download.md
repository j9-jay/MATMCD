# TASK_003 - 공식 데이터 출처 및 자산 확보

## 목적
저자가 안내한 원본 자료를 MATMCD_DATA에 출처별로 보관하고 입력 완전성을 확인한다.

## 작업 항목
- [x] 연속형 3개 벤치마크 CSV 및 정답 그래프 확보
- [x] Asia/Child BIF 및 실제 샘플 공개 여부 확인
- [x] LEMMA-RCA 원본 및 MATMCD 전처리 입력 확인
- [x] 버전·URL·해시·예상 경로 기록
- [ ] 저자 실제 Asia/Child CSV 및 MATMCD RCA 최종 입력 확보

## 확인 사항
논문 실험 샘플과 원본 자료를 구분하며 누락 CSV를 임의 생성하지 않는다.

## 결과
CSV/GT 6개, Asia/Child BIF, LEMMA 공식 코드에 등장하는 5개 사례의 로그/메트릭 ZIP 10개 확보. 공개 LFS SHA256 검증 완료. `docs/ASSETS.md`, `docs/evidence/downloads.json` 참고. DWDClimate는 349행으로 논문 350행과 다르다. BIF 표본 seed와 RCA EVT→CSV 절차가 없어 원본 실행 입력 준비는 BLOCKED다. 샘플링·전처리를 임의로 수행하지 않았다.

## 상태
BLOCKED
