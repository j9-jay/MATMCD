# TASK_029 - Qwen non-thinking 전환 및 원본 응답 형식 재검증

## 목적
2026-09-25 사용자의 “non-thinking 으로 변경후 검증 진행” 지시에 따라 같은 모델의 thinking 모드를 끄고 인공 입력·원본 파서 검증을 수행한다. TASK_026의 thinking 예산 4096 제안 대신 선택한 별도 실행 조건이며 저자 모델 재현 완료나 RCA 성능 검증으로 간주하지 않는다.

## 작업 항목
- [x] 사용자 승인과 고정 템플릿/런타임의 non-thinking 지원 확인
- [x] 이전 설정·스크립트 및 실패 이력 보존
- [x] 활성 프로필·서버·클라이언트의 thinking 모드 전환
- [x] 같은 산술·Yes/No·RE 인공 사례 및 원본 파서 검증
- [x] reasoning_content 부재·최종 답변·토큰·처리 시간·GPU 확인
- [x] 요청 조건·원본 소스·기존 패키지 보존과 서버 종료 확인
- [x] 이전 결과와 비교하고 현재 Blocker·문서 갱신

## 확인 사항
- 모델 Qwen3.5-4B Q5_K_M GGUF와 llama.cpp b11146/CUDA 12.8, seed 42, max_tokens 8192, context 16384, sampling 및 두 인공 변수·원본 prompt·parser를 유지한다.
- 서버 `--reasoning off`, 템플릿과 요청 `enable_thinking=false`. reasoning_format=deepseek는 보존하여 별도 reasoning_content가 나타나면 실패 처리한다. thinking 필수 검증을 모드에 맞게 조정하며 최종 응답 누락·한도 도달·태그 혼입·자동 재시도 금지는 유지한다.
- 논문의 RE는 최종 답변에 G/P 형식을 요구하는 별도 경로다. non-thinking 전환을 원본 `use_reasoning=True` 경로 제거로 해석하지 않는다.
- 프로필/alias/로그 이름을 nonthinking으로 변경해 이전 thinking 결과와 구분한다. 기존 모델·런타임 자산을 재사용하고 재다운로드하지 않는다.
- 고정 출처: MATMCD_DATA/raw_downloads/github_ggml_org_llama_cpp_b11146/server_README.md의 `--reasoning` 및 `chat_template_kwargs`, 모델 폴더의 BASE_MODEL_README.md와 upstream_metadata.json에 보관된 chat template.
- 직전 검증 해시와 일치하는 설정·스크립트 4개를 MATMCD_DATA/logs/local_llm/qwen35_4b_q5km_thinking_provisional_v1/20260925T0439333771312Z_before_nonthinking에 보존했다.
- 샘플링을 Qwen 권장 non-thinking 값으로 함께 바꾸지 않는다. 이번 비교는 사용자가 승인한 thinking 모드만 변경한 인공 점검이며 권장값 최적화 실험이 아니다.
- 원문 응답을 정규화하거나 원본 파서를 수정하지 않는다. 실패하면 실제 결과를 보존하고 추가 설정 변경 없이 보고한다.

## 결과
시도 20260925T044215843311Z에서 non-thinking 전환을 확인했다. 전체 인공 검증 결과는 **FAILED**이며 원인은 RE 두 번째 방향의 형식 파싱 실패다. 전환과 검증 작업은 완료했고 남은 형식 문제는 TASK_028에 유지한다.

| 인공 요청 | 입력/생성 토큰 | 생성 구간 | 최종 답변·원본 파서 결과 |
|---|---|---|---|
| 산술 | 43 / 4 | 0.042초 | 323, 통과 |
| Yes/No x→y | 224 / 5 | 0.072초 | ⟨yes⟩, 통과 |
| Yes/No y→x | 224 / 5 | 0.050초 | ⟨no⟩, 통과 |
| RE x→y | 378 / 216 | 2.338초 | G/P 최종 답변 생성, 원본 파서 통과·행렬 [0,1]=1 |
| RE y→x | 378 / 291 | 3.108초 | G/P 최종 답변 생성, 단일 개행·누락된 --- 때문에 IndexError |

다섯 응답 모두 finish_reason=stop, reasoning_content 0문자, 최종 답변에 thinking 태그 없음. 8192 한도에 도달한 요청은 없다. Yes/No 행렬은 [[-1,1],[0,-1]]이며 인공 설정 x→y/y↛x와 일치한다. 이는 2변수 인공 사례의 관찰이며 RCA 정확도 검증은 아니다. RE는 첫 방향만 반영되고 두 번째에서 중단됐다.

이전 thinking 요청 1/2/3과 대응되는 non-thinking 요청 1/2/4를 대조했다. 모델 alias와 enable_thinking 외 요청 전체가 동일하다. 사용자·system 문장, sampling, seed, max_tokens를 유지했으며 렌더링된 입력만 모델의 non-thinking 템플릿에 따라 2토큰 길어졌다.

GPU는 33/33 layers, 전체 사용 peak 4985MiB/8192MiB(다른 프로그램 포함), OOM 없음. startup 26.1초, 산술 전체 요청은 3.7초였다. 표의 시간은 생성 구간만이며 cache/초기화 조건까지 동일한 속도 비교나 RCA 시간 예측으로 사용하지 않는다.

공식 37파일·기존 Python 201패키지·검증 중 OS를 보존했고 직전 OS 감사 대비 추가 차이도 0개다. 서버는 종료했다. 실제 생성 5회, RCA·과금 API·검색·embedding·평가 0회. 재시도·응답 보정·원본 파서 수정은 하지 않았다.

증거: [모드 전환·요청 비교·원인 분석](../docs/evidence/local_llm_nonthinking_verification.json), [해당 실패 시도 이력](../docs/evidence/local_llm_runtime_attempts.json). 외부 로그는 MATMCD_DATA/logs/local_llm/qwen35_4b_q5km_nonthinking_provisional_v1/20260925T044215843311Z_verification이며 변경 전후 스크립트 diff도 보존했다. local_llm_runtime.json은 이후 실행으로 갱신되는 최신 결과다.

현재 프로필은 non-thinking으로 유지한다. LOCAL-01은 현재 승인 경로에서 더 이상 차단하지 않지만 이전 thinking 반복 문제를 교정한 것은 아니다. 이 시점에 남았던 LOCAL-02는 이후 별도 승인 [TASK_028](TASK_028_local_re_response_format.md)의 단회 형식 보정으로 인공 검증을 통과했다. 위 보정 전 실패 이력은 그대로 유지한다.

## 상태
DONE — non-thinking 전환·보정 전 FAILED 기록 보존. 후속 TASK_028에서 단회 형식 보정 후 인공 검증 PASS
