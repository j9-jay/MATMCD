# 연구 로드맵 — 추론 상태 기반 근거 검색 (NLP/RAG)

2026-10-18 작성. **현재 미착수 백로그다.** 현재 진행 작업은 MATMCD 기준선([TASK_069](../tasks/TASK_069_blind_baseline.md))뿐이다.

근거 자료: 연구 아이디어와 구현·실험 계획 PDF(`E:/연구/Reasoning-State-Aware Evidence Retrieval for Microservice Incident Analysis*.pdf`), [30 Pod 결과 보고서](RCA_ORACLE30_RESULT_REPORT_20260927.md).

## 방향

- 연구 분야는 **NLP/RAG**다. 목표 학회는 ACL, EMNLP, NAACL, EACL, COLING이다.
- 마이크로서비스 RCA는 방법을 검증하는 응용 과제로 사용한다. 연구가 RCA 시스템이나 엔지니어링 쪽으로 이동하지 않게 한다.
- 핵심 주장(초안): 역할이 서로 다른 근거로 이뤄진 corpus에서 추론 상태에 따라 검색 대상과 범위를 바꾸면 다음을 기대할 수 있다.
  - flat retrieval보다 필요한 근거를 더 잘 찾는다.
  - 최종 판단이 더 정확해진다.
  - 비용이 줄어든다.

## 백로그

| ID | 작업 | 내용 | 결정·확인 필요 |
|---|---|---|---|
| R1 | 연구 질문 확정 | RQ1 근거 recall·사슬 완결성 / RQ2 최종 RCA 정확도 / RQ3 검색 횟수·토큰 비용 / RQ4 여러 LLM에서의 일반성 | 지도교수 합의. 기여 유형(방법만 / 방법+주석 데이터) |
| R2 | 벤치마크 재선정 | LEMMA-RCA는 사례가 적음. RCAEval, OpenRCA 등 사례가 많고 metric·log·trace가 있는 데이터 조사 | 데이터 구성·사례 수·라이선스·오염 위험은 **미확인** |
| R3 | corpus 설계 | 근거 단위 분할, 역할 태그(System Structure / Observation / Diagnosis / Action), 서비스·시간 메타데이터 | 정답 누출 자료(장애 시나리오 문서 등) 분리 |
| R4 | 평가 설계 | 근거 recall·precision·사슬 완결성, 최종 과제 지표(Hit@k, MRR 등), 후보 recall, 토큰·지연, 사례 단위 paired bootstrap/permutation 검정 | 실험 전 고정 |
| R5 | 정답 근거 주석 | 일부 사례에 필요한 근거를 gold로 주석하거나 공식 문서로 silver label 생성. 평가에만 쓰고 모델 입력에는 넣지 않음 | 주석 규모·방식 |
| R6 | NLP 기준선 | 검색 없는 LLM, flat RAG(단일·노드별 질의), 반복 검색(ReAct·IRCoT 계열), 질의 분해(Self-Ask 계열), 그래프 RAG, **역할 태그만 쓰는 RAG**, MATMCD(TASK_069) | 모든 방법에 같은 LLM·corpus·토큰 예산 |
| R7 | 제안 방법·ablation | 추론 상태 5단계(증상 이해 → 구조 파악 → 원인 후보 → telemetry 가설 검증 → root cause). ablation: 상태 제거, 역할 태그 제거, 구조 범위 제거, 고정 순서와 동적 순서 비교 | 최종 순위 생성 방식(LLM 직접 vs 그래프·RWR), 동점 처리 |
| R8 | 여러 LLM·오염 분석 | 로컬 Qwen 외 오픈 모델 1~2개. 검색 없는 LLM 성능과 정답 문자열 검사로 공개 벤치마크 암기 여부 확인 | 8GB GPU에 맞는 모델, 서버·API 사용 여부 |
| R9 | 오류 분석·정성 사례 | flat RAG가 MongoDB 디스크 부족 근거를 놓친 30 Pod 사례를 동기 예시로 사용 | — |
| R10 | 논문 작성 | ACL Rolling Review 형식, Limitations 절, Responsible NLP 체크리스트(연산 자원, 데이터 라이선스, 주석 정보, 재현성) | 투고 주기와 마감은 **미확인** |

## 비교 설계 원칙

- 제안 방법이 MATMCD에 없는 근거(topology, trace 등)를 쓰면 개선의 원인이 검색 방식인지 자료 증가인지 구분할 수 없다. 그래서 **같은 확장 corpus를 쓰는 flat RAG**를 주 비교 대상으로 둔다.
- 기준선의 코드 문제(D03 방향 반전, 첫 쌍 재사용)를 피한 효과와 제안 방법의 효과를 분리한다. 필요하면 교정판 기준선을 함께 둔다.
- 후보 선정은 정답을 모르는 상태의 규칙으로 하고 후보 recall을 함께 보고한다. 정답 포함 조건은 조건부 상한 분석으로만 쓴다.
- 결과를 보기 전에 조건을 고정하고, 원 논문 보고값과 재현값을 구분한다.

## 연구계획서에서 보완할 점

- 제안 방법의 최종 순위 생성 방식(LLM 직접 판단과 RWR 중 무엇인지, 전체 순위 길이, 동점 처리)
- "동일 context token budget"의 정의(입력 토큰, 총 토큰, 호출 수 중 무엇을 맞출지)
- RCAEval 735건 실행 가능성과 자원 계획
- 3.3절의 이벤트 샘플링 서술: 논문은 무작위, 공개 코드는 간격 선택
- 절 번호 5.2 → 8.3 누락
- 반복 횟수와 통계 검정 계획
