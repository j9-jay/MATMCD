# TASK_026 - LOCAL-01 thinking 생성 한도와 원본 응답 형식

## 목적
로컬 모델이 원본 MATMCD 프롬프트에 대해 최종 답변까지 완성하고 원본 파서가 이를 처리하는지 확인한다. 변경은 구체안을 승인받은 뒤 적용한다.

## 작업 항목
- [x] 최초 실패 요청·응답·원인·GPU 상태 보존
- [x] 다른 조건을 보존하는 생성 한도 변경안 작성
- [x] 인공 검증의 max_tokens 2048→8192 변경 승인 (2026-09-25)
- [x] 승인 후 실패한 Yes/No·RE 형식을 동일 입력·모델·thinking·sampling·seed로 재검증
- [x] 최종 content 생성·원본 파서 처리·처리 시간·메모리 확인
- [x] 8192에서도 실패하면 추가 자동 변경 없이 원인과 선택지 보고
- [x] 실제 RCA 생성 한도 확정을 TASK_024로 분리 — 아직 확정하지 않음
- [x] 후속안 채택 여부 기록 — 사용자가 non-thinking을 선택, 4096 제한안 미적용·TASK_029로 분리

## 확인 사항
- 2048은 저자 설정이 아니라 TASK_023에서 선택한 **인공 설치 점검용** 생성 한도다. 원본 OpenAIClient는 max_tokens를 명시하지 않는다.
- 20260924T125750145164Z의 원본 OnlyLLMAgent 메서드를 사용하는 인공 두 경로에서 첫 요청이 각각 한도에 도달했다. Yes/No prompt=222 tokens, RE prompt=376 tokens, completion=2048 tokens, finish_reason=length, content는 모두 빈 문자열이다.
- thinking 내용은 각각 8297/8171문자다. 서버 응답 원문은 외부 로그에 보존했다. 추론 문장을 잘라 답변으로 사용하거나 yes/no를 대신 만들어 넣지 않았다.
- 원본 파서 자체가 잘못됐다고 확정한 것이 아니다. 최종 답변 생성 전 중단돼 파서의 정상 완료를 확인할 수 없었다.
- GPU peak total used=5023MiB/8192MiB, 33/33 layers GPU. 해당 시도에서 OOM은 관찰되지 않았다.
- 2026-09-25 재검증 전 확인: 이전 응답의 실제 prompt token 수에 8192를 더하면 산술 8233, Yes/No 8414, RE 8568로 모두 문맥 16384 이내다. 이전 설치 감사 이후 OS 패키지 차이는 0개다.
- 이전 실행 이후 CUDA driver cache 위치를 MATMCD_DATA 아래로 명시한 변경이 이미 반영돼 있다. 모델·프롬프트·sampling 조건과 구분하며, 초기화/처리 시간은 같은 cache 상태의 속도 비교로 해석하지 않는다.

## 해결 제안
A(2026-09-25 승인·실행): 생성 한도만 8192로 늘려 같은 인공 사례를 확인한다. 서버 문맥 16384·모델·양자화·thinking·프롬프트·원본 파서·seed·sampling은 유지한다. 입력+8192가 문맥 안에 들어가는지 먼저 확인한다. 추론 시간이 늘 수 있으며 이것만으로 성공을 보장하지 않는다.

B: 2048을 유지하고 이번 로컬 모델은 단순 질의 검증에만 사용한다. MATMCD 인과 판단 연결은 미완료로 둔다.

thinking을 끄거나 모델·프롬프트·temperature를 바꾸는 방법은 이번 선택을 임의 변경하므로 적용하지 않는다. 반복 생성으로 원하는 응답만 고르지 않는다. 새로운 실패/성공 결과를 모두 보존한다.

## 결과
2026-09-25 사용자가 “토큰한도를 높여 재검증 진행”을 지시했다. configs/local_llm.json의 인공 검증 max_tokens만 8192로 변경해 기존 검증 스크립트를 1회 실행했다. 시도 ID는 20260925T042550544006Z이며 결과는 **FAILED**다.

| 인공 요청 | 입력/생성 토큰 | 실제 결과 | 생성 시간 |
|---|---|---|---|
| 산술 | 41 / 350 | stop, 최종 323, thinking 분리 성공 | 3.83초 |
| Yes/No 첫 방향 | 222 / 8192 | length, 최종 content 빈 값. thinking 내 출력 괄호·종료 관련 문장 반복 | 90.94초 |
| RE 첫 방향 | 376 / 3719 | stop, 최종 답변 생성. G/P 사이 단일 개행으로 원본 파서 IndexError | 40.58초 |

시간은 서버의 생성 구간만이며 로딩·prompt 처리를 포함하지 않는다. startup은 63.1초, 산술 전체 요청은 43.9초다. CUDA cache 조건이 이전과 같지 않아 속도 개선/저하의 근거로 사용하지 않는다.

Yes/No의 thinking에는 동일한 비어 있지 않은 줄이 최대 100회 반복됐다. 단순히 2048토큰이 짧았던 문제로만 설명할 수 없다. 반복의 근본 원인이 모델·양자화·prompt·sampling 중 무엇인지는 이 1회 검증으로 확정하지 않는다. RE의 최종 답변 부재는 해소됐지만 새로 드러난 개행/파서 호환 문제는 별도 [TASK_028](TASK_028_local_re_response_format.md), LOCAL-02로 분리했다. 두 경로 모두 첫 방향에서 실패해 반대 방향은 실행되지 않았다.

이전 3개 요청과 현재 요청을 대조하여 **max_tokens 외 payload 완전 동일**을 확인했다. 이전 thinking 문자열도 세 요청 모두 새 응답의 정확한 prefix였다. 기존 검증·클라이언트·launcher·설치 스크립트 4개는 직전 감사와 해시가 같다. 공식 37파일·Python 201패키지·검증 중 OS 패키지를 보존했고 이전 감사 이후 OS 변화도 0개다.

GPU 33/33 layers, 전체 GPU 사용 peak 5072MiB/8192MiB(다른 프로그램 포함), OOM 없음. 입력 초과 요청은 HTTP 400으로 거절됐으며 잘라서 생성하지 않았다. 서버는 종료했다. 실제 생성 3회, 유료 API·embedding·검색·RCA 실험 0회다.

증거: [thinking 실행 이력](../docs/evidence/local_llm_runtime_attempts.json), [요청 비교·원인 분석](../docs/evidence/local_llm_budget_revalidation.json). 원문 요청·응답·서버 로그는 MATMCD_DATA/logs/local_llm/qwen35_4b_q5km_thinking_provisional_v1/20260925T042550544006Z_verification에 있다. local_llm_runtime.json은 이후 실행으로 갱신되는 최신 결과이므로 이 시도의 고정 증거와 구분한다.

## 후속 제안 — 미적용
총 생성 한도 8192는 유지하고 서버의 `--reasoning-budget -1`만 `4096`으로 제한하는 인공 검증을 제안한다. 고정 배포본의 server_README.md에 양수 thinking budget 및 예산 소진 시 end-of-thinking 처리가 명시돼 있다. 모델·thinking 활성화·원본 프롬프트·파서·seed·sampling·문맥은 유지한다. 4096은 이번 RE 전체 생성 3719보다 큰 임시 점검값이며 저자 조건이 아니다. Yes/No가 thinking에서 계속 반복해도 최종 출력으로 전환할 여지를 남기는지 확인하는 목적이다.

이는 thinking을 자연 종료 전에 끊을 수 있어 추론 내용과 답변 정확도에 영향을 주는 **새 추론 조건 변경**이다. 성공을 보장하지 않으며 별도 사용자 승인 전 적용·재실행하지 않는다. RE 형식 문제를 해결하는 조치도 아니므로 TASK_028은 별도로 남는다. 한도를 더 늘리는 반복 실행, thinking 비활성화, sampler/모델/프롬프트/파서 교정은 하지 않았다.

이후 사용자 결정(2026-09-25): thinking budget 4096안 대신 **non-thinking 전환 후 검증**을 승인했다. 이 후속 작업은 [TASK_029](TASK_029_local_nonthinking_verification.md)에 분리한다. 위 실패 기록은 thinking 모드의 과거 결과이며, 모드 전환을 thinking 경로 자체의 교정으로 간주하지 않는다.

## 상태
DONE — 승인된 8192 검증·실패 분석 완료, 후속 non-thinking은 TASK_029에서 완료. thinking 문제 자체는 미교정이며 재개 시 별도 검토
