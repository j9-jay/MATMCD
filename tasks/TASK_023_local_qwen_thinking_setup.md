# TASK_023 - 승인된 Qwen 로컬 환경 (thinking 이력·현재 non-thinking)

## 목적
사용자가 선택한 Qwen3.5-4B / Q5_K_M / llama.cpp를 별도 임시 로컬 환경으로 설치하고 검증한다. 최초 thinking에서 TASK_029의 승인된 non-thinking으로 전환한 이력을 보존한다. 논문 모델의 재현 완료로 분류하지 않는다.

## 작업 항목
- [x] 사용자 조합 승인 및 실제 PC/WSL 사양 확인
- [x] 모델 revision·SHA-256과 llama.cpp 고정 배포본 조사
- [x] 모델·서버·CUDA 런타임을 외부 자산에 다운로드하고 해시 확인
- [x] 로컬 전용 서버 실행 설정과 클라이언트 준비
- [x] GPU 로딩·기본 thinking/최종 응답 분리 확인
- [x] 원본 OnlyLLMAgent 메서드의 인공 응답 형식 검증 완료 — TASK_028 승인 보정 포함
- [x] 소스·기존 패키지 보존 검증 및 실제 결과 기록
- [x] 통합·원본 API 후속 작업 분리

## 확인 사항
- 승인: 2026-09-24, `Qwen3.5-4B · Q5_K_M · thinking · llama.cpp`.
- RTX 2080 SUPER 8GiB, RAM 16GB, WSL RAM 약 7.7GiB. 속도·메모리는 실행 후 실측한다.
- 모델은 Qwen 원본의 Unsloth 변환 GGUF이며 원 논문의 GPT 계열/ada-002와 다르다.
- 로컬 추론 점검은 인공 입력에 한정한다. 전체 RCA, 평가, 유료 API, 웹 검색, 임베딩 생성은 실행하지 않는다.
- 임베딩/검색 대체와 공식 파이프라인 통합은 별도 작업이다. 로딩 성공을 end-to-end RCA 준비 완료로 판단하지 않는다.
- 기존 공식 소스 37개와 Python 201개를 유지한다. 원본 설정·입력 연결을 덮어쓰지 않는다.

## 결과
설치·기본 thinking 추론 완료. 모델 revision e87f176479d0855a907a41277aca2f8ee7a09523, Q5_K_M SHA-256 8814232b85594dcd46c50e5b8b29324a7efe9e746edbe8a3d1df3d3fce7aad39. llama.cpp v0.5.0이 가리키는 b11146, commit 7fe450e19305b828c199d602c23a8337aaa1f03b를 설치했다.

첫 검증 20260924T125326303923Z: 서버 health 통과(66.1초), GPU 전체 사용 peak 4,949MiB. 기본 로그 verbosity=3에서 검증 도구가 기대한 `offloaded N/N layers` 줄을 찾지 못해 `Full GPU layer offload not confirmed`로 중단했다. 생성 요청 0회, 서버 종료·원본/패키지 보존 확인. 실제 서버 실패나 메모리 부족으로 판정하지 않는다. 로그 관측만 verbosity=4로 보강하고 동일 모델·문맥·thinking으로 재검증한다. 이전 로그는 외부 실행별 디렉터리와 local_llm_runtime_attempts.json에 보존한다.

두 번째 검증 20260924T125750145164Z: 33/33개 layer GPU offload, CUDA 모델 buffer 2987.56MiB, KV 512MiB, recurrent state 50.25MiB. GPU 전체 peak=5023MiB(다른 프로그램 포함), startup=31.1초. 산술 17×19는 thinking과 최종 답변을 분리해 323 반환. 짧은 인공 요청의 생성 처리량은 약 85~92 tokens/s이며 첫 요청 prefill 지연을 포함한 RCA 속도를 의미하지 않는다.

Yes/No·RE 두 경로 모두 첫 요청이 점검용 2048토큰을 thinking에 소진했고 finish_reason=length, content 빈 값으로 끝났다. 원본 파서는 수정하지 않았고 결과를 성공으로 처리하지 않았다. 생성 요청은 총 3회(정상 산술 1회, 한도 도달 2회)였으며 원본 37개·Python 201개·시스템 패키지 보존과 초과 입력 HTTP 400 거절을 확인했다. 서버는 종료했다.

해결 제안은 [TASK_026](TASK_026_local_thinking_output_budget.md)과 [TASK_028](TASK_028_local_re_response_format.md), 로컬 전체 연결은 [TASK_024](TASK_024_local_rca_integration.md), 추후 원본 API 검증은 [TASK_025](TASK_025_original_api_validation.md)다. 설치 증거는 docs/evidence/local_llm_install.json, 최신 검증 결과는 local_llm_runtime.json(FAILED), 이전 시도는 local_llm_runtime_attempts.json이다.

검증 후 향후 CUDA driver cache 경로만 MATMCD_DATA/caches/nvidia_cuda_llama_cpp_b11146로 명시했다. 첫 두 검증은 기본 driver cache 설정을 사용했다. 모델·수치·문맥·생성 한도는 변경하지 않았으며 최종 launcher 차이는 별도 설치 감사에 기록한다.

최종 감사에서 Graphviz 시점과 OS 175개 패키지 차이가 발견됐다. APT history에 2026-09-24 21:51 KST까지 unattended-upgrade 실행 기록이 있으며 21:53 이후 모델 검증 전에 끝난 최근 이력이다. 위 시스템 보존은 각 검증 시작/종료 사이를 뜻하며 과거 Graphviz 시점부터의 동일성을 뜻하지 않는다. Python 가상환경 201개·공식 37파일은 유지됐다. 설치 manifest의 과거 `system_packages_modified=false`는 설치기가 APT를 호출하지 않는다는 뜻으로 작성했지만 OS 실측처럼 오해될 수 있어 명확한 필드로 정정하고 원래 manifest를 외부 로그에 보존했다. [TASK_027](TASK_027_wsl_system_drift.md)에 버전 차이와 미변경 정책을 기록한다.

2026-09-25 세 번째 검증 20260925T042550544006Z: 사용자 승인으로 생성 한도만 2048→8192로 확대했다. 산술은 성공, Yes/No는 thinking 반복으로 8192토큰을 소진하고 최종 답변 없이 실패했다. RE는 3719토큰에서 최종 답변을 만들었으나 G/P 사이 단일 개행 때문에 원본 파서의 IndexError가 발생했다. 생성 3회, GPU peak 5072MiB, 33/33 layers. 소스·Python·검증 중 OS를 유지하고 서버를 종료했다. 기존 실패 응답은 보존했으며 현재도 전체 검증 FAILED다. [요청 비교·분석](../docs/evidence/local_llm_budget_revalidation.json)을 참고한다.

이후 사용자 승인 non-thinking 전환은 [TASK_029](TASK_029_local_nonthinking_verification.md)에서 완료했다. 시도 20260925T044215843311Z의 다섯 응답은 모두 thinking 없이 stop으로 종료됐다. 산술·Yes/No 양방향·RE 첫 방향은 원본 파서를 통과했으나 RE 두 번째 방향은 빈 줄/구분자 누락으로 IndexError가 발생했다. 전체 결과는 FAILED, 남은 차단은 TASK_028이다. GPU 전체 peak 4985MiB, 원본 37파일·Python 201패키지·검증 중 OS 보존, 서버 종료를 확인했다. thinking 예산 4096안이나 개행 어댑터는 적용하지 않았다.

후속 사용자 승인 TASK_028에서 re_gp_boundary_v1을 적용했다. 시도 20260925T055213980648Z에서 같은 모델 원문 중 RE 두 번째 응답의 경계만 보정해 산술·Yes/No·RE 양방향 모두 PASS를 확인했다. 기존 원문과 실패 기록·공식 파서는 보존했다. 설치와 이 인공 점검은 완료했으며, 실제 RCA 통합이나 다른 에이전트의 형식 호환 검증까지 완료한 것은 아니다.

## 상태
DONE — 설치·GPU·non-thinking·인공 응답 형식 검증 완료. 전체 RCA 통합은 TASK_024 TODO
