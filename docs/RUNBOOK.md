# RCA 준비와 후속 실행

**현재 실물 상태(2026-09-26 21:30 KST 확인):** D07 A안 단일 검증은 PASS. 새 로그 프로필에서 PR 요약44개 완료 후 프로세스 종료를 확인했다. 45번째 요청은 응답 미저장, 종료 원인 UNKNOWN이며 현재 실행 중이 아니다. 기존148개와 별도 보존한다. PC는 D08 OOM으로 중단돼 그래프/순위가 없고 전체 RCA는 미완료다. [전체 Task 대조](TASK_STATUS_20260926.md).

**TASK_045 최신 상태:** 문맥만 81,920으로 확대한 검증 완료. GPU all/FP16·전체 Pod 유지, 278개 입력 수용 및 최대 입력 실제 생성 1건 PASS. 전체 실행은 미수행이며 현재 BLOCKED_PENDING_FULL_INTEGRATION이다. 이전 16,384 보류·3사례 검증 결과는 각 Task의 이력으로 보존한다. [검증 상세](../tasks/TASK_045_validate_context_81920.md).

현재 범위는 논문 §4.3·표 4다. 사용자가 준비 완료 확인 후 실제 RCA 실행을 요청했다. 실행 승인을 다시 묻지 않지만, 아래 공개 진입점 명령 자체가 준비 완료를 뜻하지는 않는다. 현재 판정은 [RCA_READINESS.md](RCA_READINESS.md), TASK_031을 따른다.

현재 실행·평가 사례는 PR 20211203·CC 20231207이며 [TASK_044](../tasks/TASK_044_select_two_rca_cases.md)의 사용자 선택을 따른다. 제외한 PR 20210517/20210524/20220606의 자료는 보존하지만 실행에 포함하지 않는다. configs/scope.json의 rca_case_selection이 단일 선택 기준이다.

## 환경·경로

WSL Ubuntu에서:

~~~bash
cd /mnt/e/연구/MATMCD
MATMCD_ENV_PY=$(python3 -B -c 'import sys; sys.path.insert(0,"scripts"); from project_paths import asset_path; print(asset_path("environment")/"bin"/"python")')
~~~

기존 설치는 반복하지 않는다. 201개 버전은 docs/evidence/installed_freeze_with_openai_embeddings.txt에 있다. RISK-001~003은 관련 문제가 생길 때만 재확인한다.

RCA 링크·요약 저장 경로 준비와 사전 점검:

~~~bash
"$MATMCD_ENV_PY" -B scripts/prepare_workspace.py
"$MATMCD_ENV_PY" -B scripts/audit_setup.py
~~~

prepare_workspace.py는 RCA 진입점·공통 모듈과 configs/inputs.json의 CSV·로그 디렉터리를 연결한다. TASK_032에서 처음에는 CSV 5개/647쌍을 연결했고, TASK_039의 3개/426쌍에서 TASK_044의 현재 활성 매핑은 CSV 2개/278쌍으로 변경됐다. 보관된 이전 링크를 실행 목록으로 사용하지 않는다. 입력 매핑이 scope.json과 다르면 준비·점검이 오류로 중단된다. 누락 로그나 새 CSV를 만들어 채우지 않는다. audit_setup.py는 원본 ZIP과 configs/scope.json을 대조한다. 제외 목록 밖의 소스 누락·변경·추가는 오류다. RCA 모듈 import·패키지·CUDA·입력을 점검하지만 fitting·RWR·LLM·API는 실행하지 않는다.

차단이 남아 준비 미완료(false, 종료 코드 2)를 보고한다. 실행하면 결과를 docs/evidence/rca_setup_audit.json에 저장하며 최초 setup_audit.json은 과거 이력이다. 이번 범위 정리의 정적·파일 보존 검증은 docs/evidence/rca_scope_verification.json에 기록한다. download_assets.py는 고정 metadata의 LEMMA ZIP·README만 대상으로 한다.

## TASK_020: 승인된 임시 입력 준비

원본 재현 여부는 미확인인 별도 프로필이다. 기존 WSL 환경에서 다음 준비 스크립트가 원본 SPOT 함수·native library를 호출한다. 인과 그래프·RWR·API는 호출하지 않는다.

~~~bash
"$MATMCD_ENV_PY" -B scripts/prepare_provisional_rca.py --check-native
"$MATMCD_ENV_PY" -B scripts/prepare_provisional_rca.py --prepare
"$MATMCD_ENV_PY" -B scripts/verify_provisional_rca.py
~~~

위 prepare 명령은 TASK_020에서 완료한 5개 날짜의 준비 이력이다. 이미 생성된 자료를 재사용하므로 현재 다시 실행하지 않는다. 원본과 비교할 구현 해시를 보존하기 위해 해당 전처리 코드·명세는 바꾸지 않았다. 현재 verify_provisional_rca.py, 연결 및 D01 점검은 사용자 선택 2개만 검사한다. 이미 있는 사례 출력 디렉터리는 덮어쓰지 않는다. 새 전처리 조건은 새 프로필·승인이 필요하다.

결과 경로는 configs/rca_preprocessing_proposal.json의 output_relative_to_asset_root에 명시한다. 사례별 CSV·timestamps.csv·manifest.json과 assets의 logs/setup/provisional_rca_<UTC>/ 로그를 남긴다. 프로젝트에는 docs/evidence/rca_preprocessing_applied.json과 rca_preprocessing_validation.json을 저장한다. 실패한 시도도 보존한다.

최종 구현은 순차 처리다. native 반복·원본 행렬/채널별 점수 일치 검증을 포함한다. fork의 합성 점검 정지와 spawn의 실제 처리 지연을 기록하고 두 병렬 방식은 제거했다. native 스레드 설정은 바꾸지 않았다. 로그는 정확한 ZIP 멤버 목록만 연결하며 압축 해제·요약·RCA 통합 완료로 취급하지 않는다. configs/inputs.json은 자동 변경하지 않는다.

위 문단은 TASK_020의 전처리 범위다. 후속 TASK_032에서 scripts/connect_rca_inputs.py로 정확한 로그 쌍 1,294파일을 추출하고 configs/inputs.json에 CSV·로그 링크를 명시했다. 이미 완료된 44.1GB 추출을 다시 할 필요가 없다. 공식 load_Lemma_data로 CSV 5개가 읽힌 증거는 [입력 연결 기록](RCA_INPUT_CONNECTION.md)에 있다. verify_provisional_rca.py는 현재의 승인된 정확한 링크를 검증할 수 있으며, 전체 재검증을 실행하면 원래 검증 보고서를 보존하고 timestamp 파일을 추가한다.

2026-09-24 현재 다섯 입력의 생성·별도 검증은 완료했다. 위 prepare 명령을 다시 실행할 필요가 없다. [결과·해석상 제한](PROVISIONAL_RCA_PREPROCESSING_RESULT.md)을 확인하고, 이후 무결성 재확인이 필요할 때만 verify 명령을 사용한다. 준비 완료 범위는 이 임시 metric 입력이며 아래 실제 RCA 실행의 선행 조건은 남아 있다.

## TASK_021: Graphviz B안 — 설치·검증 완료

현재 PC는 재설치할 필요가 없다. 승인 버전·시스템 패키지 추가 내역은 [환경 문서](ENVIRONMENT.md), 전체 URL·해시는 [패키지 lock](evidence/graphviz_ubuntu_packages.lock.json)에 있다. setup_graphviz.py --install은 신규 B안 설치용이며 기존 대상 패키지가 있으면 재설치를 거부한다. 정확한 9개 추가 계획만 허용하고 원본·Python·기존 시스템 패키지 보존을 확인한다.

문제 발생 등으로 출력 재확인이 필요할 때, 일반 WSL 사용자와 기존 환경에서:

~~~bash
"$MATMCD_ENV_PY" -B scripts/check_graphviz_runtime.py
~~~

이 명령은 공식 시각화 함수로 인공 PNG만 생성하고 패키지·소스 보존을 확인한다. 실제 RCA를 실행하지 않는다. 저자 버전 확인과 필요 시 전환(A안)은 [TASK_022](../tasks/TASK_022_graphviz_author_version.md) TODO이며 다른 버전을 자동 설치하지 않는다.

## TASK_036: 원본 전체 로그 읽기 검증 — DONE

세 활성 사례의 최대 structured CSV와 정확한 template 쌍을 순차로 읽어 원본 프롬프트 생성까지 검증했다. 결과는 [TASK_036](../tasks/TASK_036_large_log_reading.md)과 [실측 JSON](evidence/rca_log_memory_20260925T131346346807Z.json)에 있다. RSS 최대 2.111GiB, OOM/스왑 0이며 분할 읽기로 바꾸지 않았다.

메모리/환경 문제가 실제로 발생하여 재측정이 필요할 때 기존 WSL 사용자·환경에서:

~~~bash
"$MATMCD_ENV_PY" -B scripts/check_rca_log_memory.py --run
~~~

이 도구는 systemd 사용자 scope의 4GiB/WSL cgroup swap 0 제한으로 한 쌍씩 별도 프로세스에서 검사한다. 제한을 해제하거나 자동으로 분할 읽기/데이터 축소를 적용하지 않는다. 입력 SHA256·원본 함수·패키지/설정 보존과 최대 RSS/시간을 기록하고, 실제 프롬프트와 상세 로그는 MATMCD_DATA의 logs/setup 아래에 저장한다. LLM·임베딩·RCA는 실행하지 않는다. 원본 API import와 main 실행을 피하기 위해 고정 원본에서 두 프롬프트 함수 AST만 그대로 호출한다.

실제 TASK_024 연결도 Pod별 원본 전체 읽기 → 원본 프롬프트 생성 → worker 종료/메모리 반환 → 모델 단계 전달로 구성한다. 나머지 423쌍과 모델 동시 적재, 실제 토큰 길이는 이번 대표 검증에 포함되지 않았다.

## TASK_024/042/043/045: 입력·문맥 검증 완료, 전체 통합 검증 대기

실행기는 [run_local_rca.py](../scripts/run_local_rca.py), 프로필은 [local_rca_execution.json](../configs/local_rca_execution.json)이다. 원본 함수를 유지한 연결 코드와 인공 검사 21개·호출 보호 검사 17개를 구성했다. [구현·현재 제한·호출 규모](LOCAL_RCA_RUNTIME.md)를 따른다. D05는 후속 사용자 승인에 따라 문맥만 81,920으로 확대했고 GPU all/FP16 및 모든 Pod를 유지했다. 이전 147,456·GPU 24개 제안은 적용하지 않았다. D06은 A안 승인·실물 23쌍 검증까지 완료되어 당시 426쌍이 준비됐다. 현재 두 사례는 그중 278쌍이며 모두 준비됐다. 최대 필요 문맥은 73,266이며 현재 81,920에서 278개 모두 수용했다. 최대 입력 65,073토큰의 실제 생성 1건도 807토큰 응답/60.57초로 성공했다. RAG·그래프·전체 실행은 아직 미검증이다.

고정 WSL Python에서 사용하는 준비 명령:

~~~bash
"$MATMCD_ENV_PY" -B scripts/run_local_rca.py --prepare-prompts
"$MATMCD_ENV_PY" -B scripts/run_local_rca.py --recover-failed-prompts
"$MATMCD_ENV_PY" -B scripts/check_rca_context.py --all-prepared
~~~

순서대로 실행하며 동시에 대용량 CSV worker를 띄우지 않는다. 첫 명령은 현재 활성 278쌍의 원본 전체 읽기/프롬프트 요청을 포착한다. 이미 확인한 성공은 재사용하고 실패는 보존한다. 두 번째 명령은 완성된 엄격한 읽기 목록에 대해 승인된 D06 정책만 적용한다. 선택 필드나 최종 프롬프트에 오류 바이트가 남으면 중단하고 해당 파일/Pod를 제외하지 않는다. 세 번째는 모든 준비 프롬프트를 고정 GGUF로 tokenization만 한다. 어느 명령도 LLM 생성·PC fitting·RWR·실제 평가를 수행하지 않는다. 기존 완료 검증을 이유 없이 반복할 필요는 없다.

후속 인공 검사 명령은 `check_rca_local_transport.py`, `check_rca_log_encoding.py`다. 실제 모델 응답 포함 통합 검증은 별도로 남아 있으며 인공 검사의 PASS를 전체 준비 완료로 사용하지 않는다. D01~D04, 모델 선택, 조건부 실제 실행 승인은 반복 요청하지 않는다.

## TASK_007: RCA 실행 — 준비 미완료로 BLOCKED

`"$MATMCD_ENV_PY" -B scripts/run_local_rca.py --run` 명령을 마련했지만 현재 BLOCKED_PENDING_FULL_INTEGRATION 상태에서는 즉시 거부된다. D06과 준비 로그의 D05 용량 검증은 완료했다. 실제 RAG·그래프를 포함한 전체 통합 검증 근거가 확보되기 전에는 READY_FOR_LOCAL_RUN으로 바꾸지 않는다. 이번 사용자 요청은 문맥 재검증 범위이므로 전체 실험을 자동 시작하지 않는다. 원본 LEMMA_experiment.py 직접 실행은 제외 사례 20210517/외부 서비스를 사용하므로 현재 지침이 아니다. 원본 소스는 보존한다.

활성 사례 PR 20211203, CC 20231207만 순차 실행한다. 단계는 PC → 외부 정보 없는 CC-agent → 로그 요약 RAG를 연결한 MATMCD → MATMCD_RE다. D03 A안에 따라 RWR는 초기/초기/보정/보정 그래프를 사용한다. 원본 Agent의 방향쌍·온도·프롬프트·캐시 동작, 원본 PC/RWR/지표, D04 PR 잠정/CC 점수 보류를 유지한다. 공개 진입점의 웹 활용과 로컬 로그 연결의 차이는 저자 미확정 사항으로 표시한다.

출력은 MATMCD_DATA의 runs/matmcd_local_rca/<시각>/<사례> 아래 graphs, rankings, evaluation, summaries, calls, domain_cache 등에 실제 파일이 필요할 때 생성한다. 실험 입력·모델·로그·체크포인트를 Git 저장소 내부에 복사하지 않는다. 순위/NumPy RNG, 원문/RE 보정, 단계별 모델/설정, 실패, 환경 전후 snapshot을 보존한다. 자동 재시도·잘라내기·대체 모델·후보 축소는 하지 않는다. 첫 실제 실패 시 결과를 유지하고 원인과 필요한 변경을 보고한다.

## TASK_008: 평가 — TODO

실제 순위와 정답 원인·사례 대응을 확정한 후 MAP@5/MAP@10/MRR/RK를 계산한다. LEMMA_Metrics.py는 고정 rank 목록을 집계하며 새 결과 평가 도구가 아니다. 순위 0/1 기반, rank < K, 사례·집계·반복 규칙을 원본 정의와 대조한다.

평가에는 선택한 두 사례만 포함한다. 제외한 세 사례를 집계 분모나 성공/실패값으로 채우지 않으며, 전체 표 4와 동일한 집계라고 표시하지 않는다. MATMCD 기준선과 개선안은 동일 두 사례·입력 조건으로 비교한다.

TASK_033의 scripts/rca_metrics.py는 고정 rank 평가 코드를 실행하지 않고 공개 지표 함수만 그대로 사용한다. 함수/경계 검증 11개는 완료됐으므로 반복할 필요가 없다. 명시적으로 검증한 실제 1-based ranks가 생겼을 때만 evaluate_ranks에 전달한다. [정확한 공식과 한계](RCA_METRIC_ADAPTER.md)를 따른다. 함수 준비 완료는 실제 평가 완료가 아니다.

## TASK_009: 표 4 비교 — TODO

데이터·코드 해시, 모델 식별자, 전처리·로그·검색·RWR 조건, 실제 로그, 미확정 차이를 함께 기록한다. 논문 수치에 맞추기 위해 조건을 변경하지 않는다.
