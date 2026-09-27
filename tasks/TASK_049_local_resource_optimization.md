# TASK_049 - 로직 변경 없이 LLM 캐시 설정 적용

## 목적

사용자의 최신 지시에 따라 스크립트 로직 변경을 제외하고, 서버와 요청 양쪽에서 LLM 공통 입력 캐시 설정을 활성화한다. 최초의 PC 자료구조 변경·재개 구현 제안은 이번 범위에서 제외한다.

## 작업 항목

- [x] 로컬 전용 실행 지시 기록
- [x] 무제한 p-value 캐시/중복 간선 목록/꺼진 LLM prompt cache 코드 확인
- [x] 구체적 변경 범위·영향·검증 기준 문서 작성
- [x] 진행 승인 후 캐시 설정만 적용하라는 최신 범위 수정 기록
- [x] 변경 전 클라이언트·서버·검증 스크립트·설정 파일 보존
- [x] 서버 --cache-prompt / 요청 cache_prompt=true 설정
- [x] 별도 RAM cache=0 / 단일 슬롯 / 기존 모델·문맥·sampling 유지
- [x] 기존 오프라인 SDK 검사 17개 PASS
- [x] 설정값 외 스크립트 변경 없음 대조 및 최종 실행 명령 확인
- [x] 현재 설정과 전체 RCA 미완료 상태 구분 기록

## 확인 사항

[최초 구체안과 후속 범위 수정](../docs/LOCAL_COMPLETION_PROPOSAL.md). 사용자는 “진행해” 이후 “일단 스크립트의 로직 변경이 있는건 제외하고 캐시 설정은 모두 셋팅해줘”로 범위를 좁혔다. PC 캐시 상한/LRU·간선 저장·디스크 기록/재개·실행 순서 변경은 미적용이다. LLM 캐시는 같은 seed에서도 응답을 바꿀 수 있다. 실제 캐시 적중·가속률·RAM/VRAM 변화와 전체 실험 완료 시간은 이번 설정 점검에서 측정하지 않았다.

## 결과

2026-09-26: local_llm_client.py의 cache_prompt 상수 False→True, local_llm_runtime.py의 --no-cache-prompt→--cache-prompt만 변경하고 기존 검증의 기대값을 맞췄다. local_llm.json에는 실제 캐시 설정을 식별할 메타데이터(prompt_cache=true, cache_ram_mib=0)를 추가했다. 분기·계산·반복·재개 로직 변경은 없다.

[설정 대조 증거](../docs/evidence/rca_cache_settings_20260926T1309299865715Z.json), [SDK 17개 검사](../docs/evidence/rca_local_transport_20260926T131106690777Z.json). 고정 모델/서버 파일 해시와 최종 실행 명령도 확인했다. 변경 전 파일은 MATMCD_DATA/logs/setup/rca_cache_settings_20260926T1309299865715Z에 보존했다. 공식 소스·Python 패키지 보존 검사를 통과했다.

새 서버·추론·RCA 실험은 시작하지 않았다. TASK_048의 OOM은 해결 완료로 표시하지 않으며 swap 확대/외부 API도 미적용이다. 최초 최적화 제안을 계속 적용하려면 최신 범위 제한을 먼저 고려해야 한다.

## 상태

DONE — 최신 요청의 캐시 설정·전달 검증 완료; 전체 RCA 성공을 뜻하지 않음
