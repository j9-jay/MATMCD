# MATMCD RCA 로컬 기준선

**현재 목표(2026-10-18):** 추론 상태 기반 근거 검색을 NLP 기여 실험으로 검증한다. 카테고리 1은 장애 분석(RCAEval RE2-OB/SS), 카테고리 2는 인과 발견(MATMCD 벤치마크 5종)이다. 작업은 [TASK_070](tasks/TASK_070_state_aware_retrieval_experiments.md), 방향은 [연구 로드맵](docs/RESEARCH_ROADMAP.md), 전체 현황은 [작업 현황](tasks/INDEX.md)을 따른다.

이 저장소는 MATMCD(ACL Findings 2025) 논문 §4.3·표 4의 마이크로서비스 RCA를 로컬에서 재구현한 기록과, 이를 참고 기준선으로 쓰는 후속 연구를 담는다. 원 논문 수치 일치는 목표가 아니며, 원 논문과 다른 조건을 모두 명시한다. LEMMA-RCA 기준선(TASK_069)은 후보 선정 문제로 종료했다.

## 지금까지의 결과

- **정답 포함 30 Pod 개발 실험 (PR 20211203):** 끝까지 실행했다. 잠정 정답 Pod 순위는 PC 4위, MATMCD 5위다. 정답을 후보에 강제로 넣었으므로 주 실험에서 제외하고 조건부 분석으로만 쓴다. [결과 보고서](docs/RCA_ORACLE30_RESULT_REPORT_20260927.md), [실행 조건](docs/RCA_ORACLE30_DEVELOPMENT.md).
- **전체 후보 실행:** 미완료. PC 메모리 부족(D08)과 LLM 호출 규모 때문에 보류했다.

## 원 논문과 다른 주요 조건

| 항목 | 논문 | 로컬 |
|---|---|---|
| 생성 LLM | GPT-4o mini | Qwen3.5-4B Q5_K_M, non-thinking, llama.cpp |
| 임베딩 | text-embedding-ada-002 | BGE-M3 dense, CPU/FP32/batch 1 |
| 입력 전처리 | 최종 CSV 미공개 | 승인된 임시 전처리 `lemma_rca_provisional_v1` (저자 동일성 UNCONFIRMED) |
| 근거 경로 | 로그(본문 서술), 공개 진입점은 웹 | 로그만 사용, 웹 미사용 |
| 그래프 설명 | — | 공개 코드의 방향 반전·첫 쌍 재사용 유지 (D03 A) |

전체 차이와 확인된 공개 코드 문제는 [원본·로컬 차이](docs/ORIGINAL_LOCAL_ISSUES.md), [결정 기록](docs/RCA_DECISIONS.md), [재현 명세](docs/REPRODUCTION_SPEC.md)에 있다.

## 문서

- [실행 절차](docs/RUNBOOK.md)
- [환경](docs/ENVIRONMENT.md), [외부 자산](docs/ASSETS.md), [로컬 LLM](docs/LOCAL_LLM.md), [로컬 임베딩](docs/LOCAL_EMBEDDING.md), [로컬 실행기](docs/LOCAL_RCA_RUNTIME.md)
- [임시 전처리 명세](docs/PROVISIONAL_RCA_PREPROCESSING.md), [적용 결과](docs/PROVISIONAL_RCA_PREPROCESSING_RESULT.md)
- [평가 함수](docs/RCA_METRIC_ADAPTER.md), [공식 시나리오 조사](docs/RCA_SCENARIO_EVIDENCE.md)
- [저자 문의 최종 문안](docs/AUTHOR_INQUIRY_RCA_SHORT.md), [23개 문의 목록](docs/AUTHOR_QUESTIONS_RCA.md)

## 경로

| 위치 | 역할 |
|---|---|
| official/matmcd/ | 공식 소스 부분집합 (`D2I-Group/matmcd` 커밋 `ef2c3ecad0f5ddb9c3d20a8523c2c1043d213190`). 승인된 6개 파일 제외, 남은 37개 파일 원본 보존 |
| configs/ | 외부 경로, 입력, 실행 프로필 |
| scripts/ | 환경 설치, 입력 준비, 로컬 실행기 |
| docs/ | 명세, 차이, 결정, 검증 근거(`docs/evidence`) |
| tasks/ | 작업 기록 |

외부 자산(데이터, 모델, 실행 환경, 실행 결과)은 `E:/연구/MATMCD_DATA`에 있으며 `configs/paths.json`에서 관리한다. 유료 API는 사용하지 않았다. origin은 https://github.com/j9-jay/MATMCD.git 이다.
