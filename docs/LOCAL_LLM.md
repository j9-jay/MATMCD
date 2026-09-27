# 승인된 임시 Qwen 로컬 환경

**2026-09-26 TASK_049 최신 캐시 설정:** 사용자 후속 지시에 따라 서버 `--cache-prompt`와 요청 `cache_prompt=true`를 설정했다. 별도 RAM 캐시는 `--cache-ram 0`, parallel=1, K/V=f16, 문맥81920을 유지한다. 현재 실행은 설정 변경·요청 전달 확인 범위이며 실제 캐시 적중/가속률/전체 RCA 성공을 확인한 것이 아니다. 모델·프롬프트·sampling·PC/재개 로직은 변경하지 않았다. 캐시의 수치 계산 경로 차이로 같은 seed에서도 생성 내용이 달라질 수 있으며, 이전 캐시 꺼짐 실행과 같은 조건으로 섞지 않는다. 변경 전 파일은 외부 `logs/setup/rca_cache_settings_20260926T1309299865715Z`에 보존했다.

2026-09-24 사용자가 Qwen3.5-4B / Q5_K_M / thinking / llama.cpp를 선택했고, 2026-09-25 thinking 검증 이후 **non-thinking 전환**을 승인했다. 현재 활성 모드는 non-thinking이다. 목적은 로컬에서 방법을 개발·검토한 뒤 원본 API 조건으로 후속 검증하는 것이다. 원 논문과 동일한 모델을 재현한 결과로 분류하지 않는다.

## 고정 자산과 출처

| 항목 | 선택값 |
|---|---|
| 원 모델 | [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B), Apache-2.0 |
| 양자화 배포자 | [unsloth/Qwen3.5-4B-GGUF](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF), Qwen 직접 배포 GGUF와 구분 |
| GGUF revision | e87f176479d0855a907a41277aca2f8ee7a09523 |
| 파일 | Qwen3.5-4B-Q5_K_M.gguf, 3,143,656,608 bytes |
| SHA-256 | 8814232b85594dcd46c50e5b8b29324a7efe9e746edbe8a3d1df3d3fce7aad39 |
| tokenizer·chat template | 해당 GGUF에 포함된 모델 tokenizer와 template 사용. GPT tokenizer로 대체하지 않음 |
| llama.cpp | [v0.5.0](https://github.com/ggml-org/llama.cpp/releases/tag/v0.5.0)의 nightly-tag.txt → [b11146](https://github.com/ggml-org/llama.cpp/releases/tag/b11146) |
| runtime commit | 7fe450e19305b828c199d602c23a8337aaa1f03b |
| 배포 형식 | Ubuntu x64 CUDA 12.8 실행 파일 + 별도 cudart 배포본 |
| 실행 위치 | 기존 WSL2 Ubuntu, 일반 사용자 |

모델 카드 참고용 Qwen 원본 revision은 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a다. 이것을 Unsloth가 양자화할 때 실제 사용한 commit이라고 단정하지 않는다. 실행 자산의 확정 식별자는 GGUF revision과 파일 해시다. 원본 모델/양자화 설명·config·상위 배포 metadata를 모델 옆에 보관한다.

모든 경로는 configs/paths.json의 asset_root에서 해석한다. 세부 선택값은 [configs/local_llm.json](../configs/local_llm.json)에 있다.

| MATMCD_DATA 아래 경로 | 역할 |
|---|---|
| models/huggingface_unsloth_Qwen3.5-4B_Q5_K_M | 모델·출처 metadata |
| raw_downloads/github_ggml_org_llama_cpp_b11146 | 원본 서버/CUDA 압축파일·배포 metadata·고정 서버 문서 |
| tools/github_ggml_org_llama_cpp_b11146_cuda12.8 | 분리 설치한 실행 파일과 CUDA 라이브러리 |
| logs/local_llm/qwen35_4b_q5km_nonthinking_provisional_v1 | 현재 non-thinking 실행별 명령·서버 로그·인공 요청/응답·검증 결과 |
| logs/local_llm/qwen35_4b_q5km_thinking_provisional_v1 | 이전 thinking 결과와 전환 전 설정/스크립트 보존 |
| caches/nvidia_cuda_llama_cpp_b11146 | 이후 실행에서 사용할 NVIDIA CUDA driver cache |

## 실행 설정의 의미

서버는 127.0.0.1:18080에만 바인딩하며 offline, GPU layers=all, fit=off, parallel=1로 시작한다. 모델·문맥 크기를 자동 변경하거나 CPU fallback을 성공으로 인정하지 않는다. 기존 WSL Python 201개·시스템 패키지·공식 소스 37개를 바꾸지 않는다. CUDA 12.8 런타임은 이 서버 자식 프로세스의 라이브러리 경로에만 적용하며 PyTorch의 CUDA 12.6 설치를 교체하지 않는다.

문맥 16,384토큰, logical batch=512, microbatch=128, KV=f16은 로딩 확인을 위한 로컬 용량 선택이다. 원 논문 batch나 확정된 RCA 설정이 아니다. 문맥 초과를 임의 자르지 않고 오류로 처리한다. 실제 프롬프트의 tokenizer 기준 길이는 TASK_024에서 확인해야 한다. Qwen이 지원하는 최대 문맥 전체를 이 PC에서 검증했다는 뜻이 아니다.

현재 서버는 `--reasoning off`, 템플릿과 요청은 `enable_thinking=false`를 명시한다. reasoning_format=deepseek는 유지해 reasoning_content가 별도로 출력되는지도 점검한다. non-thinking에서는 비어 있지 않은 reasoning_content를 실패로 처리하고, 로컬 클라이언트 LocalLLMClient는 최종 content만 기존 inquire_LLMs와 같은 문자열 인터페이스로 반환한다. 한도 소진·최종 답변 누락·thinking 태그 혼입은 오류로 남긴다. 숨겨진 재시도나 LLM 재작성은 없다. 이후 사용자 승인 TASK_028에 따라 명시적 RE 호출만 REFormatClient로 감싸 경계 형식을 한 번 정규화하고 감사 기록을 남긴다. 이전 thinking 모드의 제한 없는 reasoning_budget=-1은 명령에 남아 있지만 thinking 비활성화와 구분한다. 제안했던 4096 제한은 적용하지 않았다.

모델의 thinking 비활성화와 논문의 RE 프롬프트는 별개다. 원본 `use_reasoning=True`의 G/P 요청·파서 검증을 계속 수행한다. 모델의 최종 답변에 요구되는 설명을 제거하지 않는다.

설치 점검의 seed=42·max_tokens=8192·temperature=0.6·top_p=0.95·top_k=20·min_p=0·presence_penalty=0은 명시적인 인공 테스트 값이다. max_tokens는 최초 2048에서 2026-09-25 사용자 승인으로 8192로 늘렸다. 원본 OnlyLLMAgent 메서드의 호출에는 로컬 클라이언트의 기존 temperature=0.5가 적용된다. 이 값들을 저자 설정이나 추후 RCA 최종 조건으로 간주하지 않는다.

## 명령

WSL Ubuntu의 프로젝트 디렉터리에서 기존 환경 Python을 선택한다.

```bash
cd /mnt/e/연구/MATMCD
MATMCD_ENV_PY=$(python3 -B -c 'import sys; sys.path.insert(0,"scripts"); from project_paths import asset_path; print(asset_path("environment")/"bin"/"python")')
```

설치 최초 1회 또는 다른 PC에서 승인된 동일 자산을 준비할 때:

```bash
"$MATMCD_ENV_PY" -B scripts/setup_local_llm.py --install
```

설치 완료 후 서버 실행(포그라운드, Ctrl+C로 종료):

```bash
"$MATMCD_ENV_PY" -B scripts/local_llm_runtime.py --serve
```

서버는 자동 시작 서비스로 등록하지 않는다. 위 명령만으로 실험이나 웹 검색을 실행하지 않는다. 원본 공식 클라이언트가 자동으로 이 서버에 연결되는 것도 아니다.

인공 입력 재검증이 필요한 경우에만, 위 서버를 종료한 상태에서:

```bash
"$MATMCD_ENV_PY" -B scripts/check_local_llm_runtime.py
```

검증 스크립트는 전용 서버를 시작·종료한다. 모델·라이브러리 해시, GPU offload, 산술 1회, 원본 OnlyLLMAgent 메서드의 가상 2노드 Yes/No 최대 2회·RE 최대 2회를 확인한다. 각 경로에서 오류가 나면 해당 메서드는 중단한다. 원본 메서드를 AST로 그대로 추출해 인공 객체에 실행하고 원본 프롬프트·파서를 수정하지 않는다. 실제 통계 인과 발견·RWR·웹·embedding·RCA 평가는 없다. 산술이나 형식 점검이 통과해도 RCA 정확도를 입증하지 않는다.

## 2048토큰 검증 이력 (2026-09-24)

설치 증거: [local_llm_install.json](evidence/local_llm_install.json). 아래 thinking 검증의 FAILED 결과는 [이전 시도 이력](evidence/local_llm_runtime_attempts.json)과 해당 외부 실행 디렉터리에 보존했다. 최신 결과는 아래 non-thinking 검증과 [local_llm_runtime.json](evidence/local_llm_runtime.json)이다.

| 점검 | 결과 |
|---|---|
| 고정 파일 해시·분리 설치 | 완료 |
| GPU 배치 | 33/33 layers, RTX 2080 SUPER |
| GPU 주요 buffer | 모델 2987.56MiB, KV 512MiB, recurrent state 50.25MiB |
| 전체 GPU 사용 최고값 | 5023MiB/8192MiB, 다른 프로그램 포함. OOM 없음 |
| 두 번째 시도 startup | 약 31.1초 |
| 기본 thinking | 17×19 요청: reasoning_content 분리, 최종 content=323, stop |
| 원본 Yes/No 인공 요청 | prompt 222, completion 2048 tokens; length, 최종 content 없음 |
| 원본 RE 인공 요청 | prompt 376, completion 2048 tokens; length, 최종 content 없음 |
| 문맥 초과 요청 | HTTP 400 거절. 입력을 잘라서 생성하지 않음 |
| 보존·종료 | 공식 37파일·Python 201패키지 보존. 각 검증 시작/종료 사이 시스템 동일, 서버 종료. 과거 OS와는 아래 차이 존재 |

실제 모델 생성 요청은 3회다. 파서 두 경로는 각각 첫 요청에서 멈춰 두 번째 방향 질의를 실행하지 않았다. 이 시도의 디코딩 처리량은 약 85~92 tokens/s지만 첫 산술 요청에는 prompt 처리 약 38.1초, 전체 약 45.4초가 걸렸다. 짧은 인공 사례이며 전체 RCA 시간 예측·정확도 수치로 사용하지 않는다.

첫 시도는 기본 로그에서 GPU offload 문구가 보이지 않아 생성 요청 전에 중단됐다. 로그 verbosity만 3→4로 높여 배치를 확인했다. [이전 시도 이력](evidence/local_llm_runtime_attempts.json)과 모든 외부 로그를 보존했다. 모델·수치·thinking·문맥은 이때 변경하지 않았다.

이 시점에는 생성 한도를 자동 확대하거나 thinking을 끄지 않았다. 이후 2026-09-25 사용자가 **2048→8192 인공 검증**을 승인해 아래 재검증을 수행했다. 원본 파서는 그대로 유지했다.

마지막 정리에서 이후 실행의 CUDA cache를 외부 자산 경로로 지정했다. 첫 두 시도는 기본 driver cache 설정이었으며 원래 캐시를 탐색·삭제하지 않았다. 추가 추론 없이 버전·파일·패키지·서버 종료만 확인한 [최종 설치 감사](evidence/local_llm_post_setup_audit.json)를 별도로 둔다. 추론 당시 launcher와 마지막 cache 위치 명시의 차이를 이 감사에서 구분한다.

과거 Graphviz 시점의 OS와 최종 상태를 대조하자 175개 패키지 차이가 발견됐다. APT history에서 모델 검증 전에 끝난 unattended-upgrade 기록을 확인했다. 설치 스크립트는 APT를 호출하지 않았으나 백그라운드 OS 갱신까지 없었다고 주장하지 않는다. [전체 버전 차이](evidence/local_llm_system_drift.json)와 [TASK_027](../tasks/TASK_027_wsl_system_drift.md)을 따른다. 최종 감사는 이 차이를 포함해 PASS_WITH_HISTORICAL_OS_DRIFT로 구분한다. 기존 모델 추론은 업데이트 후 환경의 결과다. 자동 업데이트 설정 변경·OS rollback은 하지 않았다.

## 8192토큰 재검증 (2026-09-25)

시도 20260925T042550544006Z의 전체 결과는 **FAILED**다. 이전 세 요청과 비교해 max_tokens 외 요청 payload가 동일하고, 네 개 설치/실행/클라이언트/점검 스크립트도 직전 감사와 해시가 같다. 고정 파일 해시 검증을 다시 통과했다. [요청 대조·분석 증거](evidence/local_llm_budget_revalidation.json)에 근거를 남겼다.

| 점검 | 결과 |
|---|---|
| 산술 | 350토큰, stop, 최종 323·thinking 분리 성공 |
| Yes/No 첫 방향 | 입력 222 + 생성 8192, length, 최종 content 빈 값. thinking 28603문자에 출력 형식 관련 문장 반복 |
| RE 첫 방향 | 입력 376 + 생성 3719, stop, 최종 content 348문자. G/P 사이 단일 개행으로 원본 파서 IndexError |
| 문맥 여유 | 입력 + 생성 한도: 8233 / 8414 / 8568, 모두 16384 이내 |
| GPU·startup | 33/33 layers, 전체 GPU peak 5072MiB/8192MiB, OOM 없음. startup 약 63.1초 |
| 보존·종료 | 공식 37파일·Python 201패키지·검증 중 OS 동일. 이전 감사 이후 OS 차이 0개. 서버 종료 |
| 초과 입력 | HTTP 400 거절, 잘라서 생성하지 않음 |

인공 생성은 3회뿐이며 두 파서 경로는 각 첫 방향에서 중단했다. 실제 RCA·유료 API·embedding·검색은 실행하지 않았다. 생성 구간은 산술 3.83초, Yes/No 90.94초, RE 40.58초다. 이번부터 외부 CUDA cache 경로를 사용하므로 이전과 같은 cache 상태의 속도 비교가 아니다.

Yes/No의 반복은 동일 줄이 최대 100회 나타난 실제 관찰이며 근본 원인을 양자화·모델 크기 등 하나로 확정하지 않는다. RE는 답변 생성에 성공했으나 원본 파서가 두 개행을 요구하고 응답은 단일 개행을 사용해 추론 후보 목록이 비었다. 답변을 고쳐서 파서를 통과시키지 않았다.

[TASK_026](../tasks/TASK_026_local_thinking_output_budget.md)에 총 8192를 유지한 채 thinking budget만 4096으로 제한하는 후속 제안을, [TASK_028](../tasks/TASK_028_local_re_response_format.md)에 개행 호환 선택지를 기록했다. 두 변경 모두 적용하지 않았다. 이후 사용자가 non-thinking 전환을 선택해 [TASK_029](../tasks/TASK_029_local_nonthinking_verification.md)에서 별도 검증한다.

## non-thinking 보정 전 검증 이력 (2026-09-25)

사용자 승인으로 thinking을 끄고 같은 모델·8192 생성 한도·원본 프롬프트·파서·seed·sampling·문맥으로 검증했다. 시도는 20260925T044215843311Z, 프로필은 qwen35_4b_q5km_nonthinking_provisional_v1이다. 이 보정 전 시도는 **FAILED**였으며 당시 RE 두 번째 방향이 남았다. 이후 승인된 형식 보정 검증은 다음 절과 구분한다.

| 인공 요청 | 생성 토큰 | 최종 답변·원본 파서 |
|---|---|---|
| 산술 | 4 | 323, 통과 |
| Yes/No x→y | 5 | ⟨yes⟩, 통과 |
| Yes/No y→x | 5 | ⟨no⟩, 통과 |
| RE x→y | 216 | G/P 답변, 원본 파서 통과 |
| RE y→x | 291 | G/P 답변은 완료했으나 빈 줄·--- 누락으로 IndexError |

다섯 응답 모두 stop, reasoning_content 0문자, 최종 답변에 thinking 태그 없음. 문맥 초과 입력은 HTTP 400으로 거절했다. Yes/No 행렬은 [[-1,1],[0,-1]]로 인공 설정과 일치한다. RE는 첫 방향만 반영됐다. 원문 보정·재시도·원본 파서 교정은 하지 않았다.

이전과 공통인 세 요청을 대조해 model alias와 enable_thinking 외 동일함을 확인했다. 사용자/system 문자열은 그대로이며 모델 템플릿의 non-thinking 처리로 입력 토큰만 2개 증가했다. 서버 환경 경로·모델·런타임 자산도 유지했다. 이전 설정과 변경 스크립트 원본은 thinking 로그 폴더의 20260925T0439333771312Z_before_nonthinking에 보존하고, 현재 실행 로그에 diff를 남겼다.

GPU 전체 peak 4985MiB/8192MiB(다른 프로그램 포함), 33/33 layers, OOM 없음. startup 26.1초, 생성 구간은 Yes/No 약 0.05~0.07초·RE 약 2.34~3.11초다. 이는 짧은 인공 사례이며 실제 RCA 속도·정확도 평가가 아니다. cache/초기화까지 통제한 속도 비교로 사용하지 않는다.

공식 37파일·Python 201패키지·검증 중 OS를 보존했고 이전 OS 감사 이후 차이는 0개다. 서버는 종료했다. 실제 RCA·과금 API·검색·embedding·평가는 실행하지 않았다. [해당 실패 이력](evidence/local_llm_runtime_attempts.json), [요청 대조·분석](evidence/local_llm_nonthinking_verification.json), [TASK_029](../tasks/TASK_029_local_nonthinking_verification.md)에 기록했다. 이후 사용자가 TASK_028의 형식 보정을 별도로 승인했다.

## 승인된 RE 단회 형식 정규화

2026-09-25 사용자가 “그냥 llm 응답 결과를 한 번 보정하자”를 승인했다. [local_re_response.py](../scripts/local_re_response.py)의 re_gp_boundary_v1은 추가 LLM 호출 없이 G/P 항목 경계의 빈 줄·구분자만 한 번 처리한다. 원본 메서드·프롬프트·모델·sampling은 유지한다. 이미 원본 파서로 완전히 읽히는 유효 응답은 바이트 그대로 통과한다.

G1/P1 … Gn/Pn의 순서·개수·대응 번호, 소수 형태의 0~1 확률, 후보 끝의 <yes>/<no>를 확인한다. 추론 문장 내부 공백/개행과 확률 표기는 보존하고 합계 정규화나 후보 정렬을 하지 않는다. 원본이 수행하는 후보 정렬·yes/no 해석은 그대로다. 누락·중복·불명확한 레코드, 후보 내부의 원본 파서 구분자, 확률 설명/지수 표기/잘못된 범위 등 지원하지 않는 형식은 REFormatError로 기록한다. 유효 정보가 부족한 응답을 추측해 복구하지 않는다.

이 정책은 엄격한 원본과 허용 형식이 다르며, 원본이 일부 후보만 읽거나 잘못된 확률 표기를 수용하던 경우보다 더 엄격히 거절할 수도 있다. 저자 실행 조건으로 간주하지 않는다. 기준선과 개선안 양쪽에 같은 정책을 적용하고 UNCHANGED/NORMALIZED/REJECTED 건수를 기록해야 한다.

실행별 response_NN.json은 모델 원문 그대로 보존한다. RE 응답별 response_NN_re_format.json에 원문·보정본·후보 필드·정책 버전·상태를 별도로 저장한다. 실패 시 보정본은 null이며 원문과 원인을 남긴다. 모델 재생성·응답 선택·복수 보정 시도는 하지 않는다.

오프라인 검증은 다음 명령을 사용한다. 저장된 응답과 인공 실패 사례를 그대로 원본 파서에 대입하며 서버를 실행하지 않는다.

```bash
"$MATMCD_ENV_PY" -B scripts/check_local_re_format.py
```

현재 연결 범위는 check_local_llm_runtime.py의 OnlyLLMAgent RE 인공 점검뿐이다. Yes/No는 보정기를 거치지 않는다. ConstrainNormalAgent·다른 파서·전체 RCA의 실제 연결은 TASK_024에서 별도로 구성한다.

오프라인 22개 점검은 모두 PASS다. 이전 정상 응답 무변경, 실패 응답의 원본 파싱, 설명문 내부·확률 표기·동률 선택 보존, 잘못된 응답 거절·원문 감사·재시도 없음 등을 확인했다. [오프라인 증거](evidence/local_re_format_runtime.json)에 기록했다.

실제 인공 추론 시도 20260925T055213980648Z도 **PASS**다. 산술·Yes/No 양방향·RE 양방향을 모두 처리했다. RE 첫 응답은 원문 그대로, 두 번째는 경계만 한 번 정규화했다. 직전 실행과 5개 요청 및 모델 응답 메시지가 모두 동일하므로 성공한 새 응답을 선택한 결과가 아니다. [최신 실행 결과](evidence/local_llm_runtime.json), [전후 비교](evidence/local_re_format_comparison.json), [TASK_028](../tasks/TASK_028_local_re_response_format.md)을 참고한다.

생성 5회, 보정용 추가 LLM 호출 0회, GPU 33/33 layers·전체 peak 4980MiB, 원본 37파일·Python 201패키지·검증 중 OS 보존과 서버 종료를 확인했다. 실제 RCA는 실행하지 않았다.

## 남은 작업

- TASK_028의 현재 인공 형식 검증은 완료했다. 새로운 모호한 응답은 보정 범위를 자동 확대하지 않고 실패로 기록한다. thinking 반복 이력 TASK_026은 현재 non-thinking 경로의 선행 차단으로 두지 않는다.
- [TASK_024](../tasks/TASK_024_local_rca_integration.md): 임베딩·검색의 로컬 대체안, 실제 프롬프트 길이, ConstrainNormalAgent/웹/최종 요약 연결, 입력·코드 차단 항목.
- [TASK_025](../tasks/TASK_025_original_api_validation.md): 로컬 성과 이후 저자 모델·API 조건 구성 및 기준선/개선안 양쪽의 후속 검증.
- 원본 TASK_007/008/009는 실제 실험·평가·비교 TODO로 유지한다.

로컬 환경의 기준선과 개선안에는 같은 모델·양자화·tokenizer·thinking·생성 한도·sampling·응답 보정 정책·자료·평가 조건을 적용해야 한다. 모델이나 응답 허용 범위를 바꿔서 생긴 차이를 RCA 방법의 효과로 해석하지 않는다.
