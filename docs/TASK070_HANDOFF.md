# TASK_070 인계 문서 (작업 내역·현황)

최종 갱신: 2026-10-19. 컨텍스트 압축 후에도 이 문서와 [TASK_070](../tasks/TASK_070_state_aware_retrieval_experiments.md), [INDEX](../tasks/INDEX.md), [configs/task070_decisions.json](../configs/task070_decisions.json)만 읽으면 이어서 작업할 수 있게 정리한다.

## 1. 연구 목표와 구도

- 목표: **추론 상태 기반 근거 검색(사용자 아이디어)**을 NLP 기여(근거 검색·귀속) 실험으로 검증. 목표 학회 ACL 계열.
- **핵심 비교: 제안 방법(`state_dynamic`) vs flat RAG(`flat`).** ablation: `role_only`, `state_fixed`. 참고 기준선: `none`(검색 없는 LLM), `pc_only`, `matmcd`.
- 카테고리 1(주): RCAEval RE2-OB 장애 분석. 카테고리 2(보조): MATMCD 인과 발견 벤치마크 5종(AutoMPG, DWD, Sachs, Asia, Child).
- **주 출력부 B**: 사례 단위 근거 24개 → LLM이 후보 서비스 12개 전체 순위를 근거 인용과 함께 출력(후보 순서 3가지 반복 평균). **보조 출력부 A**: 쌍별 Yes/No → 제약 PC → RWR. 카테고리 2는 그래프를 내야 하므로 A.
- LEMMA-RCA MATMCD 재현(TASK_050~053, 30 Pod 정답 포함)은 조건부 분석·동기 사례로만 사용. TASK_069(LEMMA 정답 미사용 기준선)는 종료.

## 2. 사용자 결정·승인 (모두 기록됨)

| 항목 | 결정 |
|---|---|
| 데이터셋 | RCAEval RE2-OB만(RE2-SS는 백로그 R14) + 인과 발견 5종 |
| 평가 규모 (G1, B안) | RE2-OB **반복 2의 30사례**(서비스 5 × 장애 6), 모든 방법 동일, 반복 3 미사용. 개발 = 반복 1 |
| 출력부 | 주 B, 보조 A. MATMCD RAG 제목 변형(`Relationships between the nodes:`) 허용 |
| 웹 검색 | Serper 무료 할당량 내(348회 사용, 잔여 약 2,150). 초과 예상 시 생략·Wikipedia API |
| 데이터 | Takayama CSV 다운로드(출처 명시), Asia·Child는 로컬 BIF에서 seed 42로 1,000개 |
| D-1~D-11 | 권장안 전부 승인(`configs/task070_decisions.json`) |
| 작업 방식 | 루틴은 스스로 결정하고 논스톱 진행, 중요한 결정만 승인. **모든 변경은 브랜치 → GitHub PR(origin j9-jay/MATMCD) → 즉시 병합**. upstream(D2I-Group) push 금지 |

## 3. 주요 결과 (지금까지)

- **공통 출력부 검증:** 인과 발견 PC 결과가 MATMCD 표 1 PC 행과 AutoMPG·DWD 일치, Sachs는 소수점 처리 차이(P1).
- **출력부 A, 개발 10사례 (Avg@5):** flat 0.462, role_only 0.431, state_fixed v2 0.255, state_dynamic v2 0.298, pc_only 0.193. MATMCD 개발 1사례 0.05(45분, 323호출). 제안 방법이 낮음 → Yes 증가가 제약 그래프로 증폭되는 구조 문제(가설).
- **출력부 B v3, 개발 10사례:** none 0.49 / flat 0.78 / role_only 0.81(9건) / state_fixed 0.90 / **state_dynamic 0.94** (AC@1 0.90 vs flat 0.55). 근거 정밀도 0.096 vs 0.042, 인용 정밀도 0.35 vs 0.22.
- 상세 경위(판단 프롬프트 v1→v2, 상태 검색 v1→v2, 출력부 B v1→v3)는 TASK_070과 각 PR에 있음.

## 4. 현재 실행 상태 (2026-10-19 기준)

| 순서 | 실행 | 출력 위치 | 상태 |
|---|---|---|---|
| 1 | 출력부 B 평가: `task070_direct_run.py --split test --cases 30` | `MATMCD_DATA/task070/head_b/test_20261019T121820Z` | **완료·분석 완료**(TASK_070 기록). 상태 동적 vs flat 유의차 없음 |
| 2 | 카테고리 2 1차: `task070_causal_run.py` | `causal_run/20261019T153123Z`, 로그 `queue_cat2.log` | **무효**: AutoMPG flat 도중 llama-server `CUDA error: unknown error`(ggml_backend_cuda_synchronize)로 종료. 이후 쌍은 연결 오류로 No 처리, state_dynamic 계획 호출에서 중단. 원인 UNKNOWN. 폴더는 보존 |
| 3 | 출력부 A 1차: `task070_pilot.py --split test --cases 30 --methods pc_only none flat role_only state_fixed state_dynamic matmcd` | `head_a_test/20261019T153640Z`, 로그 `queue_head_a.log` | pc_only·none·flat·role_only 30사례 완료, state_fixed 13사례 완료 후 14번째(인덱스 13) `ob-06a2cff32f`에서 `finish_reason=length`로 중단 |
| 4 | 카테고리 2 재실행(2026-10-21 사용자 승인, 새 폴더) | `causal_run/20261020T153400Z`, 로그 `queue_cat2_rerun.log` | **완료**(실패 쌍 0, 결과는 TASK_070) |
| 5 | 출력부 A state_fixed 이어 실행: `--start 14 --cases 16 --methods state_fixed` | `head_a_test/20261020T172020Z`, 로그 `queue_head_a_state_fixed_from14.log` | **완료**(16사례) |
| 6 | 출력부 A state_dynamic·matmcd: `--start 0 --cases 30 --methods state_dynamic matmcd` | `head_a_test/20261020T190645Z`, 로그 `queue_head_a_dynamic_matmcd.log` | **완료**(MATMCD 실패 4) |

- **모든 평가 실행 완료(2026-10-22).** 출력부 A 합산 분석: `head_a_test/analysis_merged.json`(TASK_070 기록). 남은 일은 5절의 보고서 작성과 해석 검토.

- 첫 대기열은 `pgrep -f task070_direct_run.py`가 대기열 셸 자신의 명령줄과 일치해 끝없이 대기했다. 이후 대기 조건 없이 순차 실행한다.
- 출력부 A 실행기는 사례 실패 시 멈춘다(실패 처리 없음). 동결 실패 규칙(2026-10-21 사용자 확인)대로 state_fixed `ob-06a2cff32f`는 후보 전체 동점으로 채점하고, 15번째 사례부터 이어 실행해 결과를 합친다. 같은 방식으로 다른 사례가 실패하면 다시 멈추므로 그때마다 보고한다.
- 실행 중인지 확인: `wsl.exe -e bash -lc "pgrep -af 'task070_|llama-server'"`.
- llama-server는 단일 slot(포트 18080). 다른 LLM 작업과 동시에 돌리지 않는다.

## 5. 남은 작업

1. ~~출력부 B 분석~~ 완료(#13). ~~카테고리 2 분석~~ 완료(#15). ~~출력부 A 분석~~ 완료(#16).
2. **결과 해석 검토(사용자와):** 세 평가 모두 제안 방법(state_dynamic)이 flat RAG보다 유의하게 낫지 않음. 근거 정밀도·재현율 이득(출력부 B)만 유지. 논문 주장을 어떻게 세울지 결정 필요.
3. MATMCD 카테고리 2 참고 기준선(T7, DA-AGENT 이식) — 미실행.
4. 결과 보고서(T10) 작성 후 PR. 연구계획서 보완점은 [로드맵](RESEARCH_ROADMAP.md) 끝에 있음.
5. 백로그: R11 일반 QA(MuSiQue/HotpotQA), R12 OpenRCA, R14 RE2-SS.

## 6. 동결·검증 장치

- `configs/task070_testset.json`: 평가 30사례와 파일 CRC. `task070_rcaeval.verify_testset()`.
- `configs/task070_frozen.json` (G2, `task070_freeze.py`): 출력부 B v3·A 설정, 방법 구성, 실패 규칙, 스크립트·설정 해시(줄바꿈 정규화). `verify_frozen()`은 `configs/task070_frozen_amendments.json`에 정확히 기록된 변경만 허용(현재 1건: 카테고리 2 corpus 정리).
- `configs/task070_frozen_cat2.json` (`task070_freeze_cat2.py`): 카테고리 2 실행기·공용 모듈.
- **동결 이후 task070 스크립트를 수정하면 평가 실행기가 멈춘다.** 수정이 꼭 필요하면 사유와 이전·이후 해시를 amendments에 기록하고 PR로 남긴다.

## 7. 실행 환경 메모

- Python(WSL): `/mnt/e/연구/MATMCD_DATA/environments/d2i_matmcd_py311/bin/python -B <script>` (scripts 폴더에서 실행).
- GitHub CLI: `"C:\Program Files\GitHub CLI\gh.exe"` (계정 j9-jay 로그인됨). PR 본문은 파일로 넘기고 생성 후 `gh pr merge <n> --merge`, 이어서 `git fetch; git switch main; git merge --ff-only origin/main`.
- Serper 키: `E:\연구\MATMCD_DATA\secrets\serper_api_key.txt`(40자). 출력·기록 금지.
- 주의: Bash heredoc 안의 Python 문자열에 `\b`, `\n`을 넣으면 백스페이스·실제 줄바꿈으로 깨진 적이 있다. 정규식은 Edit 도구나 별도 스크립트 파일로 넣는다.
- 주요 데이터: RCAEval zip `MATMCD_DATA/raw_downloads/zenodo_rcaeval_14590730/`, corpus `MATMCD_DATA/task070/corpus/{re2ob,causal}/`, 임베딩 캐시 `MATMCD_DATA/task070/embeddings/`.

## 8. 병합된 PR 목록

j9-jay/MATMCD#1 재계획 문서 · #2 P0 데이터 준비 · #3 RE2-OB 한정 · #4 P1 corpus·출력부·지표 · #5 P2 파일럿 · #6 평가 30사례 고정 · #7 웹 스냅샷·MATMCD 코드 · #8 상태 검색 v1/v2 결과 · #9 출력부 B·G2 동결 · #10 카테고리 2 실행기 · #11 동결 후 변경 기록
