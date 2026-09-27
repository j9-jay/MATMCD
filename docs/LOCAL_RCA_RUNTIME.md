# 로컬 RCA 실행기 연결 현황

**현재 실물 상태(2026-09-26 21:30 KST 확인):** D07 A안 단일 검증은 PASS. 새 로그 프로필에서 PR 요약44개 완료 후 프로세스 종료를 확인했다. 45번째 요청은 응답 미저장, 종료 원인 UNKNOWN이며 현재 실행 중이 아니다. 기존148개와 별도 보존한다. PC는 D08 OOM으로 중단돼 그래프/순위가 없고 전체 RCA는 미완료다. [전체 Task 대조](TASK_STATUS_20260926.md).

2026-09-26. 실행기 [run_local_rca.py](../scripts/run_local_rca.py)와 [프로필](../configs/local_rca_execution.json)을 구성했다. **현재 상태는 BLOCKED_PENDING_FULL_INTEGRATION이며 실제 실행은 차단된다.** 연결 코드 구성·인공 검사와 실제 end-to-end 실행 성공을 구분한다.

## 구현한 연결

| 경로 | 구성과 보존 범위 |
|---|---|
| 원본 로그 → 프롬프트 | 공식 generate_pod_summary를 별도 CSV worker에서 그대로 실행하고 생성 요청만 포착. 원본 전체 읽기·선택·시스템 문장·temperature 0.5 유지. worker 종료 후 생성 단계로 전달 |
| Qwen 호출 | 실제 Qwen alias와 모델 해시·양자화·모드·sampling·seed·온도를 기록. 실제 GGUF chat tokenizer로 길이 검사. 초과·미완성 응답은 보존하고 실패, 자동 재시도 없음 |
| 로그 요약 → RAG | 고정 BGE-M3 CPU FP32/batch 1과 원본 generate_dataset_summary 함수 연결. 기존 reader·분할·top-k·질의/응답 합성 기본값 유지. LlamaIndex 설치본 기본 temperature 0.1 유지 |
| 인과 판단·제약 | ConstrainNormalAgent와 LLM 클래스 원문 AST를 사용하고 네트워크 client만 명시적으로 주입. Domain 0.5/constraint 0.8 및 모든 방향쌍 순서 유지 |
| RE | 원래 `<Yes>/<No>`를 보존한 채 승인된 G/P 경계 보정만 사용. 기존 OnlyLLMAgent의 소문자 보정은 기본값 그대로. 내용·확률·대소문자를 바꾸지 않음 |
| D01 | 부재/KPI 고정 설명을 구분해 저장하고 최종 노드 설명에도 복원. 정확한 기존 쌍만 읽고 후보를 제거하지 않음 |
| D03/D04 | 초기/초기/보정/보정 RWR 입력, 원본 PC/RWR/지표, 전체 순위·RNG·PR 잠정 점수·CC 두 후보 순위/점수 보류 연결 |
| 결과 | 사례/단계별 그래프·PNG·제약·순위·요약·요청/원문/RE보정·평가를 외부 runs 경로에 보존. 공식 PNG 이름 중복은 별도 출력 경로로만 분리 |

공식 config의 모델 문자열은 원본 생성자의 client 선택 분기를 유지하는 데만 사용한다. 원본 config/API 모듈이나 자격정보를 로드하지 않으며 실제 요청 model 필드는 Qwen alias다. 생성 모델로 원본 GPT를 사용했다고 표시하지 않는다. 저자의 실제 로그/RCA 연결과 동일하다는 근거는 없어 로컬 연결로 명시한다.

## 검증과 한계

[연결 검사 21개 PASS](evidence/local_rca_components_20260926T062351165468Z.json): 원본 두 Agent 경로/온도/방향쌍, D03 프롬프트, RE 대소문자 보존, 설치된 LlamaIndex의 원본 요약 함수/엄격 파서·chat 메시지·기본 분할, D01 부재/KPI, 실제 CC 로그 한 쌍의 원본 요청 일치를 확인했다. 가짜 응답/embedding을 사용한 연결 검사이며 실제 생성·RCA 성능 결과가 아니다.

기존 저장 응답에 대한 RE 오프라인 검사도 22개 PASS했다. [최신 검사](evidence/local_re_format_runtime.json)의 이전 보고서는 해당 외부 로그 디렉터리에 보존했다.

[로컬 호출 보호 검사 17개 PASS](evidence/rca_local_transport_20260926T064526426028Z.json): 실제 설치 OpenAI SDK의 요청 직렬화는 MockTransport로 검사했다. 다중 chat 역할/내용·온도·seed·sampling·모델 식별자 보존, 미완성/뜻밖의 thinking 응답 실패, 입력 초과 시 생성 전 차단·원문 기록을 확인했다. 외부 네트워크/모델 호출은 0회다.

현재 두 사례의 원본 로그 준비는 278쌍 모두를 요구하며 기본 읽기 258 + 승인 D06 20쌍 모두 완료됐다. 이전 3사례 426쌍의 결과도 보존한다. 읽기에 실패한 파일은 그대로 보존하고 실패 목록을 만든다. 다른 파일의 독립 검사를 계속하는 것이며 실패 Pod를 실제 실험에서 제외하는 기능이 아니다. 실행기는 모든 정확한 로그의 프롬프트가 준비되지 않으면 실행하지 않는다.

현재 [D05/TASK_045](RCA_CONTEXT_CAPACITY.md)에서 문맥만 81,920으로 확대해 준비 로그 278/278 수용과 최대 입력 한 건의 실제 응답을 검증했다. GPU all/FP16·전체 Pod를 유지한다. 나머지 로그/RAG/그래프를 포함한 전체 통합 검증과 RCA 실행은 아직 완료하지 않았다. [TASK_043](../tasks/TASK_043_log_encoding_diagnosis.md)은 실물 처리까지 DONE이다. 원본 최종 요약 파서가 요구한 모든 사용 가능한 Pod를 돌려주지 않으면 자동으로 채우거나 파서를 교정하지 않고 실패를 기록한다. 향후 개선 방법의 설계·비교는 기준선 실행의 필수 선행 조건이 아니다.

D06 A안은 사용자 승인을 받았다. `--recover-failed-prompts`는 모든 엄격한 읽기 결과가 존재할 때만 시작한다. UTF-8 오류가 확인된 파일에 한해 승인된 어댑터를 쓰고, 정상 파일은 그대로 재사용한다. 원본 실패는 `lemma_rca_original_prompts_v1`에 유지하고 새 시도는 `lemma_rca_original_prompts_d06_v1`에 저장한다. 선택 필드/최종 프롬프트에 오류가 있으면 차단하며 실패 Pod를 제외하지 않는다. [인공 10개 검사](evidence/rca_log_encoding_tests_20260926T064939884092Z.json)에 이어 [실물 23쌍 처리](evidence/rca_log_recovery_20260926T071852891429Z.json)도 모두 통과했다. 이는 입력 준비 결과이며 모델 생성 검증은 아니다.

## 호출 규모 — 범위 축소 없음

공개 에이전트는 각 방향쌍마다 domain 설명 1회와 제약 판단 1회를 호출하며, 현재 프로필에는 세 LLM 보정 단계가 있다. KPI도 원본처럼 labels에 포함된다.

| 사례 | 전체 노드 | 방향쌍 n(n-1) | 세 단계의 LLM 호출 |
|---|---:|---:|---:|
| PR 20211203 | 219 | 47,742 | 286,452 |
| CC 20231207 | 197 | 38,612 | 231,672 |
| 합계 | — | 86,354 | 518,124 |

로그 요약 278회와 최종 RAG 합성 호출은 별도다. 실제 실행 시간은 아직 측정하지 않았다. 호출당 1초라고 가정해도 방향쌍 호출만 약 6.00일이며 이는 성능 측정이나 예상 완료시간이 아닌 단순 산술 예시다. 실제 속도·문맥 길이·원본 prompt cache의 메모리 사용량은 검증 후 보고해야 한다. TASK_044로 사례 수만 줄였고 사례 내부 노드/방향쌍/단계 축소는 적용하지 않았다.

## 명령과 출력

고정 WSL Python에서 `python -B scripts/run_local_rca.py --prepare-prompts`는 기존 로그를 읽고 프롬프트만 준비한다. 실제 생성/PC/RWR 실행 명령이 아니다. 성공한 기존 포착 결과는 입력/결과 해시를 검사하여 재사용하고 실패 디렉터리는 재시도·덮어쓰지 않는다.

`--run`은 현재 프로필 상태에서 즉시 거부한다. 차단 원인 해결과 통합 검증을 마친 후에만 READY_FOR_LOCAL_RUN으로 전환한다. 실제 출력은 MATMCD_DATA/runs/matmcd_local_rca/<실행시각>/<사례> 아래 역할별로 저장한다. 모델/요약/그래프 결과가 필요해질 때만 해당 디렉터리를 만든다. 원본 프롬프트 준비본은 MATMCD_DATA/processed_data/lemma_rca_original_prompts_v1에 저장한다.

실행 시 OS/Python/공식 소스/설정 snapshot을 전후에 남기며 차이가 있으면 REQUIRES_ENVIRONMENT_REVIEW로 표시한다. 자동 업데이트 중지·OS rollback은 하지 않는다. 현재 기준 기록은 [환경 snapshot](evidence/rca_environment_20260926T061459160665Z.json)이다.
