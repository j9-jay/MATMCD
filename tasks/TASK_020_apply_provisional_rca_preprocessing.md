# TASK_020 - 승인된 임시 RCA 전처리 구현·입력 준비

## 목적

검토용 전처리안의 선택값과 영향을 승인받은 뒤, 실제 입력을 준비하고 저자 동일성 확인과 분리해 관리한다.

## 작업 항목

- [x] TASK_019의 구체안과 적용 범위에 대한 사용자 승인 확인
- [x] 승인된 recipe와 보완 스크립트 구현, 고정 재현 환경 유지
- [x] 보유 SPOT native 라이브러리 호환성 점검
- [x] 5개 공개 날짜의 입력 생성·원본과 분리 보관
- [x] CSV·KPI·시간·pod·로그·해시·결정 manifest 검증
- [x] 임시 입력 준비 상태와 저자 동일성 상태를 각각 보고
- [x] 실제 적용 내용을 TASK_018 문의 초안에 반영

## 확인 사항

[승인 설정](../configs/rca_preprocessing_proposal.json)은 APPROVED_FOR_PREPROCESSING이며 별도 준비 스크립트만 사용한다. 원본 RCA 실행 경로에는 연결하지 않는다. [상세 명세](../docs/PROVISIONAL_RCA_PREPROCESSING.md)의 시간 정렬, EVT 유지 규칙, pod별 z-score 평균은 주요 로컬 가정이다.

이번 Task는 준비 작업이다. PC fitting·LLM·RWR·RCA 평가를 실행하지 않는다. 원본 코드·ZIP을 보존하며, 실제 산출물이 생길 때만 외부 processed_data/lemma_rca_provisional_v1 경로를 만든다.

KPI·로그 불일치나 native 오류가 발생하면 실패를 기록한다. 실행 성공을 위해 기본값·metric·pod·사례를 자동 교체하거나 원인 정답을 이용해 필터를 조정하지 않는다.

## 결과

2026-09-23: 사용자가 구체안의 구현·CSV 생성을 승인했다. 기존 WSL Python 3.11.13 / NumPy 2.2.6에서 전처리와 입력 검증을 진행한다. 실제 실험 TASK_007/008/009 및 저자 문의 TASK_018은 TODO로 유지한다.

구현: [prepare_provisional_rca.py](../scripts/prepare_provisional_rca.py), 독립 산출물 검증: [verify_provisional_rca.py](../scripts/verify_provisional_rca.py). 실행 명령은 [RUNBOOK](../docs/RUNBOOK.md)에 있다. 원본 spot_detection AST와 pyspot/libspot를 수정 없이 호출한다. 원본 환경의 201개 패키지 freeze와 일치를 확인하며 새 라이브러리를 설치하지 않았다.

합성 입력에서 반복 점수와 원본 행렬/채널별 점수가 정확히 일치했다. 실행 방식 검토 중 fork 정지, spawn 8개 프로세스의 스레드 경합 의심 지연을 확인했다. 최종 구현은 순차 처리로 돌아왔으며 native 스레드 설정도 변경하지 않았다. 전체 관측·메트릭·사례·SPOT 값·통합 규칙을 줄이거나 바꾸지 않았다.

시도 로그는 외부 자산 루트 기준 다음 경로에 보존한다.

- logs/setup/provisional_rca_20260923T101158896993Z: 최초 순차 native 검증 PASS.
- logs/setup/provisional_rca_20260923T102618164138Z: 실행 방식 검토를 위해 중단한 순차 처리; interruption.json.
- logs/setup/provisional_rca_20260923T111727470598Z: fork 합성 점검 정지; execution_failure.json. 정확한 내부 정지 원인은 미확정이다.
- logs/setup/provisional_rca_20260923T112144930947Z: spawn 합성 일치 PASS, 실제 입력에서 각 프로세스 31개 스레드와 처리 지연 관찰; interruption.json. 내부 스레드 경합은 추정이다.
- logs/setup/provisional_rca_20260923T112815216854Z: 최종 순차 처리 PASS 기록.

중단 시도에서는 CSV를 생성하지 않았다. 데이터·원본 코드·native binary·환경 버전은 보존했다.

### 입력 생성 진행 결과

| 사례 | 상태 | 공통 행 수 | 유지 pod | 정확한 로그 쌍 / 누락 |
|---|---|---:|---:|---:|
| PR 20210517 | PREPARED_PROVISIONAL — CSV·타임스탬프 roundtrip 통과 | 166,325 | 208 / 후보 208 | 109 / 99 |
| PR 20210524 | PREPARED_PROVISIONAL — CSV·타임스탬프 roundtrip 통과 | 176,692 | 207 / 후보 207 | 112 / 95 |
| PR 20211203 | PREPARED_PROVISIONAL — CSV·타임스탬프 roundtrip 통과 | 51,529 | 218 / 후보 218 | 154 / 64 |
| PR 20220606 | PREPARED_PROVISIONAL — CSV·타임스탬프 roundtrip 통과 | 107,789 | 228 / 후보 228 | 148 / 80 |
| CC 20231207 | PREPARED_PROVISIONAL — CSV·타임스탬프 roundtrip 통과 | 79,252 | 196 / 후보 196 | 124 / 72 |

2026-09-24: 다섯 CSV는 외부 자산의 processed_data/lemma_rca_provisional_v1/<system>/<day>에 생성했다. 각각 timestamps.csv와 manifest.json을 동반한다. 생성 실행은 PASS이며 공식 소스·201개 패키지·승인 설정 보존을 확인했다. 저자 입력 동일성은 미확인이고, 로그는 ZIP 멤버 연결 목록이며 미추출 상태다. 공식 입력 설정은 자동 변경하지 않았다. [생성 증거](../docs/evidence/rca_preprocessing_applied.json), [적용 결과](../docs/PROVISIONAL_RCA_PREPROCESSING_RESULT.md).

독립 검증 첫 시도는 공식 ZIP에 공통 최상위 폴더가 있다고 잘못 가정한 로컬 검증기 때문에 FileNotFoundError(LlamaClient.py)가 발생했다. 실제 ZIP·로컬 경로는 Client/LlamaClient.py다. 검증기의 경로 해석만 기존 audit_setup.py와 동일하게 고쳤으며 원본·CSV·전처리·환경은 바꾸거나 다시 생성하지 않았다. [실패와 수정 기록](../docs/evidence/rca_preprocessing_validation_attempts.json). 수정 후 다섯 사례 모두 재검증을 통과했다.

검증 결과: [rca_preprocessing_validation.json](../docs/evidence/rca_preprocessing_validation.json)의 all_checks_pass와 all_five_metric_inputs_ready는 true다. 원본 KPI·시간축·CSV 해시·열·EVT 결정 기록·로그 목록, 공식 소스 37개와 LEMMA 원본, 승인 환경 201개 패키지 보존을 확인했다. 공식 pandas 읽기 방식의 최대 절대 수치 차이는 약 3.64e-12로 별도 기록했고 파서를 변경하지 않았다. 실제 RCA 영향은 미평가다.

이 Task의 임시 metric 입력 준비는 완료했다. 모든 후보 pod가 유지됐다는 관찰, 상수 채널·로그 누락을 TASK_018의 미발송 초안에도 반영했다. 저자 동일성·원본 실행 입력 연결·로그 통합은 미해결이며 TASK_003은 BLOCKED를 유지한다. Graphviz·API·검색 파서 등 다른 Blocker는 변경하지 않았다. 실험 TASK_007/008/009와 저자 문의 TASK_018은 TODO다. commit/push는 수행하지 않았다.

## 상태

DONE
