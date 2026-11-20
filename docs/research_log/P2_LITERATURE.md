# P2 보고서 — 문헌 조사 (LEMMA-RCA 중심)

- 작성일: 2026-11-18
- 검색 방법: 사용자 결정 후보 C (2026-11-18). 주 방법은 LEMMA-RCA 데이터셋 논문을 인용한 논문의 전수 확인. 보조로 MATMCD 인용 논문 확인과 학회별 키워드 검색.
- 실행: 서브에이전트 3개가 병렬로 조사했다. 핵심 수치는 작업자가 arXiv HTML 원문을 직접 열어 대조했다(2절 표시).
- 표기: **원문 대조 완료** = 작업자가 원문에서 직접 확인. **서브에이전트 보고** = 서브에이전트가 원문에서 읽었다고 보고했으나 작업자가 대조하지 않음. **초록만** = 초록이나 메타데이터만 확인됨.
- 검색어에는 논문 제목, 데이터셋 이름, 기술 용어만 썼다.
- 상태: 사용자 검토 대기 (P2-G2: 논문별 포함/제외 결정)

---

## 0. 요약

1. **같은 데이터셋·같은 지표로 비교할 수 있는 공표값은 두 출처뿐이다.** LEMMA-RCA 데이터셋 논문 자체의 기준선 표(통계·인과 방법 6종)와 OCEAN(Product Review만, 딥러닝)이다. 둘 다 LLM 방법이 아니다.
2. **LEMMA-RCA 논문과 MATMCD는 지표 계산 방식이 다르다.** LEMMA-RCA 논문의 표는 "순위 K 이하"로 계산됐고, MATMCD 표 4는 "순위 K 미만"으로 계산됐다(2.2절에서 수치로 검증). 같은 순위라도 두 논문의 MAP@K 값이 다르게 나온다. 그대로 한 표에 놓으면 안 된다.
3. **LEMMA-RCA 논문은 사례 수와 날짜를 밝히지 않는다.** 수치가 0.25 단위로만 나와 Product Review와 Cloud Computing 모두 4사례로 보인다(추정). MATMCD는 데이터셋당 1사례다. 사례 구성이 다르다.
4. **LEMMA-RCA에서 LLM 방법의 결과를 낸 논문은 두 편뿐이고, 둘 다 프로토콜이 다르다.** "Free to Look, Free to Reason"(5사례, PR@1만)과 TimeRAG(객관식 정답률, 순위 과제 아님).
5. LLM·RAG 기반 RCA 연구 약 25편은 모두 다른 데이터셋(RCAEval, OpenRCA, AIOps 챌린지, 회사 내부 데이터)을 썼다.
6. LEMMA-RCA 논문은 버전마다 결과표가 다르다(v1·v2와 v3·v4의 기준선이 다름). 인용할 때 버전을 고정해야 한다.

---

## 1. 검색 범위와 확인 수

| 경로 | 확인 수 | 방법 | 접근하지 못한 것 |
|---|---|---|---|
| LEMMA-RCA 인용 논문 | 서로 다른 논문 32편 (+ 인용하지 않은 관련 RCA 논문 11편) | Semantic Scholar 17건, OpenAlex 28건을 합쳐 중복 제거, 웹 검색 1편 추가 | Google Scholar 인용 목록, CAVIAR(KDD 2026, ACM 403), UIUC 학위논문(403), BIANCA(Springer 로그인 필요) |
| MATMCD 인용 논문 | 서로 다른 논문 29편 (전문 4편, 나머지 초록·메타데이터) | OpenAlex 30건, Semantic Scholar 20건 | Google Scholar 인용 목록, OpenReview, 초록 없는 3편은 제목으로만 판단 |
| 학회별 키워드 검색 | 관련 논문 약 25편 + 서베이 4편 | 웹 검색과 arXiv HTML | ISSRE, KDD, NAACL·ACL 본회의, NeurIPS, AAAI의 논문집을 직접 훑지 않음. 결과가 대부분 arXiv로 나옴 |

- 조사 중 두 웹 페이지에 AI에게 지시하는 문장이 숨어 있었고 서브에이전트는 따르지 않았다(arXiv 2606.08590 HTML, OpenAlex API 응답). 결과에는 영향이 없다.

---

## 2. LEMMA-RCA 데이터셋 논문 (가장 중요한 비교 대상)

- 논문: Zheng et al., "LEMMA-RCA: A Large Multi-modal Multi-domain Dataset for Root Cause Analysis", arXiv 2406.05375. v4(2026-08-25)에 "Accepted by CIKM 2026".
- 버전: v1 2024-06-08, v2 2024-09-26, v3 2025-05-16, v4 2026-08-25. **원문 대조 완료** (arXiv abs 페이지).
- v3와 v4의 결과표는 같다고 서브에이전트가 보고했다. 작업자는 v4만 대조했다.
- v1·v2는 기준선이 다르다(Dynotears, PC, C-LSTM, GOLEM, REASON, Nezha, MULAN 등). 서브에이전트 보고.

### 2.1 실험 조건 (v4, 원문 대조 완료)

| 항목 | 내용 |
|---|---|
| Product Review | 장애 4종(메모리 부족, CPU 과다, 외부 저장소 가득 참, DDoS)을 "4개의 다른 날짜"에 수집. 각 49시간 이상. Pod 216개 |
| Cloud Computing | 장애 유형 6종 |
| 평가 사례 수, 날짜 | **본문에 없음** |
| 후보 필터 | 정상성(stationarity)이 없는 Pod를 제외. 로그가 부족한 개체도 제외 |
| 기준선 | PC, RCD, ε-Diagnosis, CIRCA, BARO, Nezha. LLM 없음 |
| 반복, 시드 | 없음 |
| 라이선스 | 데이터셋은 CC BY-ND 4.0 |

### 2.2 지표 정의와 계산 방식 (원문 대조 완료, 작업자 검증)

논문의 수식(alttext 원문):
- `PR@K = 1/|A| Σ_a ( Σ_{i<k} R_a(i) ∈ V_a ) / min(K, |v_a|)`
- `MAP@K = 1/(K|A|) Σ_a Σ_{i≤j≤K} PR@j`
- `MRR@K = 1/|A| Σ_a 1/rank_{R_a}`

수식 표기는 MATMCD 부록과 거의 같지만, **실제 표의 숫자는 "순위 K 이하" 방식으로 계산돼 있다.** 검증:
- Product Review, Multi-Modality, BARO 행: PR@1 0.750, PR@5 0.750, PR@10 1.000, MRR 0.775, MAP@10 0.775.
- 4사례 중 3사례가 1위이고 1사례가 r위라면 MRR = (3 + 1/r)/4 = 0.775 → r = 10.
- "이하" 방식: MAP@10 = (3×1.0 + 1×(1/10))/4 = 0.775. 표와 일치. PR@1 = 3/4 = 0.75. 표와 일치.
- "미만" 방식(MATMCD 코드)이라면 PR@1은 항상 0이고 MAP@10은 (3×0.9 + 0)/4 = 0.675가 된다. 표와 맞지 않는다.

**MATMCD 표 4를 "이하" 방식으로 다시 계산하면** (공표된 순위 2위, 7위 사용):

| 지표 | MATMCD 표 4 (미만 방식) | 같은 순위를 이하 방식으로 계산 |
|---|---:|---:|
| MAP@5 | 30.0% | (4/5 + 0)/2 = 40.0% |
| MAP@10 | 55.0% | (9/10 + 4/10)/2 = 65.0% |
| MRR | 0.32 | 0.32 (같음) |

- MRR은 두 방식에서 같다. MAP@K만 다르다.
- 이 재계산은 공표된 순위로 한 산술이며, 논문에 실린 값은 아니다.

### 2.3 결과표 (v4, 원문 대조 완료)

**표 3. Product Review (오프라인)**

| 데이터 | 방법 | PR@1 | PR@5 | PR@10 | MRR | MAP@3 | MAP@5 | MAP@10 |
|---|---|---|---|---|---|---|---|---|
| 메트릭만 | PC | 0 | 0 | 0.250 | 0.053 | 0 | 0 | 0.050 |
| | RCD | 0 | 0.250 | 0.750 | 0.185 | 0.167 | 0.200 | 0.350 |
| | ε-Diagnosis | 0 | 0 | 0.250 | 0.038 | 0 | 0 | 0.050 |
| | CIRCA | 0 | 0.750 | 0.750 | 0.283 | 0.250 | 0.450 | 0.600 |
| | BARO | 0.250 | 0.250 | 0.250 | 0.286 | 0.250 | 0.250 | 0.250 |
| 로그만 | PC | 0 | 0 | 0.250 | 0.069 | 0 | 0 | 0.125 |
| | RCD | 0 | 0 | 0.250 | 0.056 | 0 | 0 | 0.025 |
| | ε-Diagnosis | 0 | 0 | 0.250 | 0.038 | 0 | 0 | 0.050 |
| | CIRCA | 0 | 0 | 0.500 | 0.080 | 0 | 0 | 0.125 |
| | BARO | 0 | 0.250 | 0.250 | 0.139 | 0.167 | 0.200 | 0.225 |
| 멀티모달 | PC | 0 | 0 | 0.250 | 0.064 | 0 | 0 | 0.125 |
| | RCD | 0 | 0.500 | 0.750 | 0.231 | 0.167 | 0.300 | 0.525 |
| | ε-Diagnosis | 0 | 0 | 0.250 | 0.041 | 0 | 0 | 0.075 |
| | CIRCA | 0 | 0.750 | 1.000 | 0.299 | 0.250 | 0.450 | 0.650 |
| | BARO | 0.750 | 0.750 | 1.000 | 0.775 | 0.750 | 0.750 | 0.775 |
| | Nezha | 0 | 0.500 | 0.750 | 0.193 | 0.083 | 0.250 | 0.475 |

**표 7. Cloud Computing (오프라인, 부록 E)**

| 데이터 | 방법 | PR@1 | PR@5 | PR@10 | MRR | MAP@3 | MAP@5 | MAP@10 |
|---|---|---|---|---|---|---|---|---|
| 메트릭만 | PC | 0 | 0 | 0 | 0.029 | 0 | 0 | 0 |
| | RCD | 0 | 0.250 | 0.250 | 0.126 | 0.083 | 0.150 | 0.200 |
| | ε-Diagnosis | 0 | 0 | 0.250 | 0.067 | 0 | 0 | 0.025 |
| | CIRCA | 0 | 0 | 0.500 | 0.105 | 0 | 0 | 0.150 |
| | BARO | 0 | 0.250 | 0.250 | 0.105 | 0 | 0.100 | 0.175 |
| 로그만 | PC | 0 | 0 | 0 | 0.032 | 0 | 0 | 0 |
| | RCD | 0 | 0 | 0 | 0.059 | 0 | 0 | 0 |
| | ε-Diagnosis | 0 | 0 | 0 | 0.059 | 0 | 0 | 0 |
| | CIRCA | 0 | 0.250 | 0.250 | 0.110 | 0 | 0.100 | 0.175 |
| | BARO | 0 | 0.250 | 0.250 | 0.105 | 0 | 0.100 | 0.175 |
| 멀티모달 | PC | 0 | 0 | 0.250 | 0.064 | 0 | 0 | 0.125 |
| | RCD | 0 | 0.250 | 0.250 | 0.092 | 0 | 0.050 | 0.150 |
| | ε-Diagnosis | 0 | 0 | 0.250 | 0.067 | 0 | 0 | 0.025 |
| | CIRCA | 0 | 0.250 | 0.500 | 0.147 | 0.083 | 0.150 | 0.225 |
| | BARO | 0 | 0.250 | 0.250 | 0.126 | 0.083 | 0.150 | 0.200 |
| | Nezha | 0 | 0.250 | 0.250 | 0.105 | 0 | 0.100 | 0.175 |

- 온라인 설정 결과(표 6, 표 8)도 있다. 원문 대조 완료(표 8), 표 6은 서브에이전트 보고. 온라인은 PC, CIRCA, Nezha가 사례당 24시간을 넘어 빠졌다.
- Cloud Computing은 장애 유형이 6종인데 수치는 0.25 단위다. 평가에 쓴 사례 수가 장애 유형 수와 다를 수 있다(추정, 논문에 없음).

---

## 3. LEMMA-RCA로 실험한 다른 논문

| 논문 | 학회 | 데이터 | 과제와 지표 | 방법 | 확인 상태 |
|---|---|---|---|---|---|
| **OCEAN** (Zheng et al., "Online Multi-modal Root Cause Identification in Microservice Systems") | IEEE BigData 2025, arXiv 2410.10021 | Product Review만 ("2021년 5월~12월의 장애 4개"). 그 외 Online Boutique, Train Ticket | 순위. PR@K, MAP@K, MRR. 1회 실행 | 딥러닝 온라인 인과 학습. LLM 없음 | 원문 대조 완료 (표 II) |
| **Free to Look, Free to Reason** (Bi et al.) | arXiv 2610.35767 (2026-10, 사전 공개) | LEMMA 10사례 중 5사례 선택. Product Review/Cloud Computing 구분 없음, 사례 목록 미공개. 후보 거르기 여부 미기재 (표 1의 347은 무작위 적중률의 역수로 계산한 유효 후보 수이며 실제 Pod 수가 아님. 2026-11-19 정정, 9절) | PR@1만 | LLM 하네스, LLM 에이전트, 비LLM 방법 비교 | 원문 대조 완료 (표 7) |
| **TimeRAG** (Park) | arXiv 2601.04709 (2026) | LemmaRCA Prod, Cloud | **순위 과제가 아님.** 4지선다 정답률과 GPT-4o 판정 승률 | RAG + LLM + 시계열 인코더 | 서브에이전트 보고 |
| MiCCD (Cai et al.) | Neural Networks 2025 | "전처리된 IT 시스템 데이터" | 원인을 다중 분류로 보고 F1 | 인과·반사실 | 서브에이전트 보고 |
| Kodela et al. | ICCDS 2025 | LEMMA-RCA | 분류 정확도 등 ">92%" | 딥러닝 + 랜덤 포레스트 | 초록만 |
| RIO-CPD | CIKM 2025 | Product Review | 변화점 탐지 (RCA 아님) | 기하학적 방법 | 서브에이전트 보고 |
| Tree-of-Evidence | Findings of ACL 2026 | LEMMA | 장애 탐지 이진 분류 AUROC (RCA 아님) | 다중모달 근거 탐색 | 서브에이전트 보고 |
| MARLIN | AAAI 2026 | SWaT만 (OT) | 그림만, 숫자 없음 | 강화학습 인과 탐색 | 서브에이전트 보고 |

### 3.1 OCEAN 표 II (Product Review, 원문 대조 완료) 중 멀티모달 행

| 방법 | PR@1 | PR@5 | PR@10 | MRR | MAP@3 | MAP@5 | MAP@10 |
|---|---|---|---|---|---|---|---|
| PC | 0 | 0 | 0.25 | 0.054 | 0 | 0 | 0.075 |
| Dynotears | 0 | 0.25 | 0.5 | 0.114 | 0 | 0.05 | 0.225 |
| C-LSTM | 0.25 | 0.5 | 0.5 | 0.341 | 0.250 | 0.35 | 0.425 |
| REASON | 0.5 | 1.00 | 1.00 | 0.687 | 0.667 | 0.80 | 0.900 |
| MULAN | 0.75 | 1.00 | 1.00 | 0.833 | 0.833 | 0.90 | 0.950 |
| CORAL | 0.75 | 1.00 | 1.00 | 0.875 | 0.917 | 0.95 | 0.975 |
| BARO | 0.50 | 0.75 | 1.00 | 0.587 | 0.500 | 0.60 | 0.700 |
| ε-Diagnosis | 0 | 0 | 0.25 | 0.042 | 0 | 0 | 0.075 |
| OCEAN | 1.00 | 1.00 | 1.00 | 1.000 | 1.000 | 1.00 | 1.000 |

- 같은 Product Review인데 BARO의 값이 LEMMA-RCA 논문(MRR 0.775)과 다르다(0.587). OCEAN은 온라인 설정이라 조건이 다르다.
- 같은 연구 그룹(NEC/UIUC)의 논문이다. LEMMA-RCA와 같은 사례 묶음인지는 확인되지 않았다.

### 3.2 Free to Look 표 7 중 LEMMA 열 (원문 대조 완료, PR@1 %, 5사례)

| 방법 | PR@1 | 방법 | PR@1 |
|---|---:|---|---:|
| Codex (LLM 하네스) | 96.7 | NSigma (비LLM) | 60.0 |
| SQL agent (LLM 하네스) | 95.6 | TORAI (비LLM) | 20.0 |
| One-shot (LLM) | 64.4 | FaultInsight (비LLM) | 6.7 |
| FoA (LLM 에이전트) | 46.7 | SimpleRCA, BARO, CIRCA, RCD | 0.0 |
| RCA-Agent | 46.7 | Random | 1.1 |
| RCAgent | 33.3 | | |
| DecompRCA | 13.3 | | |
| mABC | 0.0 | | |

- LLM 행은 여러 모델(GPT-6 Luna, DeepSeek V4.1 Flash, Claude Haiku 5.5)의 평균이다.
- 논문 스스로 LEMMA 결과는 5사례라 잡음이 크다고 적었다(서브에이전트 보고).
- 사례가 MATMCD와 같은지 알 수 없다. 지표도 다르다.

---

## 4. MATMCD 인용 논문

- 29편 중 마이크로서비스 RCA 실험을 한 논문은 없다. LEMMA-RCA를 쓴 논문도 없다. MATMCD와 수치를 비교한 논문도 없다.
- RCA 수치를 낸 유일한 인용 논문은 CausalPulse(arXiv 2603.29755, 2026)이며 제조 데이터다.
- 대부분은 인과 발견, 시계열, 의료, 에이전트 일반 연구다. 목록은 서브에이전트 보고에 있고 이 보고서에는 옮기지 않았다.

---

## 5. LLM·RAG 기반 RCA 연구 (LEMMA-RCA 미사용, 참고용)

모두 서브에이전트 보고이며 작업자가 수치를 대조하지 않았다. 관련 연구 서술과 RCAEval 백로그(B1)에 쓸 수 있다.

| 논문 | 학회 | 방법 | 데이터 |
|---|---|---|---|
| OpenRCA (Xu et al.) | ICLR 2025 | 벤치마크 + RCA 에이전트 | 기업 시스템 3종, 335건 |
| RCAEval (Pham et al.) | WWW Companion 2025 | 벤치마크, 비LLM 기준선 15종 | Online Boutique, Sock Shop, Train Ticket |
| mABC (Zhang et al.) | Findings of EMNLP 2024 | 다중 에이전트 LLM 투표 | Train-Ticket, AIOps 2020 |
| Flow-of-Action (Pei et al.) | WWW Companion 2025 | 표준 운영 절차(SOP) 검색 + 다중 에이전트 | Online Boutique 90건 |
| RCAgent (Wang et al.) | CIKM 2024 | 도구 사용 LLM 에이전트 | 알리바바 내부 |
| RCACopilot (Chen et al.) | EuroSys 2024 | 근거 수집 + 과거 사고 검색 | 마이크로소프트 내부 |
| Zhang et al. (GPT-4 문맥 학습) | FSE 2024 Industry | 과거 사고 검색 기반 문맥 학습 | 마이크로소프트 내부 |
| TAMO, TopoEvo | arXiv 2025, 2026 | 도구 보조 LLM 에이전트 | AIOps 챌린지 |
| GALA (Tian et al.) | arXiv 2025 | 인과 추론 + 다중 에이전트 LLM | RCAEval RE2-OB 90건 |
| RCLAgent, AMER-RCL, ThinkFL (Zhang et al.) | ICSE-SEIP 2026 등 | 다중 에이전트, 기억 검색, 강화학습 소형 LLM | AIOps 2022, Train-Ticket |
| MetaRCA, EvoCause | FSE 2026, arXiv 2026 | LLM 지식 + 인과 그래프 | 공개·내부 장애, 통신 알람 |
| 그 외 약 10편 | 2025~2026 | 에이전트 실패 분석, 벤치마크 | OpenRCA, AIOps 2025 등 |

서베이: "A Survey of AIOps in the Era of Large Language Models"(arXiv 2507.12472, 읽은 부분에 LEMMA-RCA 언급 없음), "What a Pooled Leaderboard Does Not Say"(arXiv 2606.29159, LEMMA-RCA는 문헌 표의 한 행으로만 등장).

---

## 6. 비교 가능성 정리

| 비교 대상 | 데이터 | 사례 | 지표 계산 | 후보 | 방법 유형 | MATMCD 표 4와 한 표에 놓을 수 있나 |
|---|---|---|---|---|---|---|
| MATMCD 표 4 | PR, CC | 데이터셋당 1 (날짜 불명) | 순위 K 미만 | EVT 필터 후 (규칙 미공개) | LLM 에이전트 + 인과 발견 | — |
| LEMMA-RCA 표 3, 7 | PR, CC | 4사례로 보임 (날짜 불명) | 순위 K 이하 | 정상성 없는 Pod 제외 | 통계·인과 | 사례와 지표 계산이 다름. MRR은 계산 방식이 같으나 사례가 다름 |
| OCEAN 표 II | PR만 | 4사례로 보임 | 이하 방식으로 보임 (PR@1이 0이 아님) | 미기재 | 딥러닝 | 위와 같음, CC 없음 |
| Free to Look 표 7 | LEMMA 5사례 | 5 (목록 미공개) | PR@1만 | 미기재 (2026-11-19 정정) | LLM, 비LLM | 지표가 다름 |

- **새 방법이 따를 사례와 지표는 K14로 정해졌다(MATMCD 논문의 사례와 지표).** 그런데 이 표에서 보듯 같은 데이터셋의 다른 공표값들은 사례 수와 지표 계산 방식이 서로 다르다. 어느 값을 어떤 형태로 최종 표에 넣을지는 사용자가 정한다(7절).

---

## 7. 사용자 판단이 필요한 항목 (P2-G2)

| 번호 | 항목 |
|---|---|
| G2-A | **결정됨(K21, 2026-11-20): 주 비교 MATMCD 표 4 + LEMMA-RCA 표 3·7 멀티모달 행 + OCEAN 행, 보조 비교 Free to Look PR@1, TimeRAG 제외.** 원래 항목: 최종 표에 넣을 논문: LEMMA-RCA 표 3·7, OCEAN 표 II, Free to Look 표 7, TimeRAG 중 무엇을 넣고 무엇을 뺄지 |
| G2-B | **결정됨(K19, 2026-11-18): `rank <= K`로 통일, MATMCD는 공개 순위로 다시 계산하고 표 4 원래 값은 각주.** 원래 항목: 지표 계산 방식이 다른 값을 어떻게 다룰지: 그대로 각 출처의 방식으로 표기 / 공표 순위가 있는 MATMCD만 두 방식 모두 표기 / 별도 표로 분리 등 (P1의 G1-E와 연결) |
| G2-C | LEMMA-RCA 논문의 인용 버전 (v4 권장 여부) — **결정됨(K22, 2026-11-20): v4 인용, CIKM 2026 채택본으로 표기** |
| G2-D | 사례 구성이 다른 결과(4사례 vs 1사례)를 같은 표에 놓을지 — **결정됨(K23, 2026-11-20): 한 표, 사례 수 열과 구분선, 다른 사례 구성은 "참고"** |
| G2-E | 접근하지 못한 출처(Google Scholar 인용 목록, CAVIAR, UIUC 학위논문, 학회 논문집 직접 검색)를 추가로 확인할지 — **결정됨(K24, 2026-11-20): 확인 완료, 비교 대상 추가 없음** |

---

## 8. 원문 대조 기록

| 항목 | 출처 | 대조 결과 |
|---|---|---|
| LEMMA-RCA 버전 이력 | arxiv.org/abs/2406.05375 | 일치 |
| LEMMA-RCA 지표 수식 | arxiv.org/html/2406.05375v4 수식 alttext | 일치. 계산 방식은 BARO 행으로 작업자가 검증 |
| LEMMA-RCA 표 3, 표 7, 표 8 | 같은 HTML 본문 | 서브에이전트 보고와 모든 값 일치 |
| Free to Look 표 7 LEMMA 열 | arxiv.org/html/2610.35767 | 일치 |
| OCEAN 표 II, "one trial" | arxiv.org/html/2410.10021 | 일치 |
| 그 외 (TimeRAG, MiCCD, 5절 논문들) | — | 대조하지 않음 |

---

## 9. 순위 대상에 KPI가 들어가는가 (2026-11-19 추가 조사, G1-F)

사용자 지적("MATMCD만이 아니라 다른 논문도 같이 봐야 한다")으로 서브에이전트가 조사했다. 작업자가 LEMMA-RCA 공식 코드의 핵심 줄을 직접 대조했다(스크래치 클론, 프로젝트 파일 변경 없음).

| 출처 | KPI 처리 | 근거 수준 |
|---|---|---|
| LEMMA-RCA 논문 v4 | 2절 과제 정의: RCA는 "KPI와 가장 관련 있는 상위 K개 개체(entity)"를 찾는다. KPI는 기준이며 후보로 정의되지 않음. PR의 KPI는 지연시간, CC는 지연시간·오류율·사용률 | 원문 확인. "KPI를 뺀다"는 명시 문장은 없음 |
| LEMMA-RCA 공식 코드 `github.com/lemma-rca/rca_baselines` | `Baseline/FastPC/test_FastPC_pod_metric.py` 222행 `count[:-1]`로 KPI 점수를 버리고 Pod만 출력. 저장소의 유일한 지표 계산 스크립트 `Baseline/FastPC/baseline_evaluation.py`는 `Pod_level_combine_ranking.csv`의 `pod` 열만 읽음. 정답은 Pod 이름 | 작업자 대조 |
| 같은 저장소 RCD, CIRCA, ε-Diagnosis (`metric_only/RCA_methods_metric.py` 144행), BARO (`baro_main_metric.py` 140행) | KPI 열을 입력에 넣고, 출력에서 KPI를 거르는 줄이 없음. 이 방법들의 지표 계산 스크립트는 공개되지 않아 논문 수치에서 KPI를 뺐는지는 알 수 없음 | 코드 확인, 논문 수치와의 관계 미확인 |
| OCEAN (arXiv 2410.10021) | KPI는 인과 그래프의 노드이자 랜덤 워크 재시작 노드. 순위 대상은 "시스템 개체". Cloud Computing 미사용. 코드 미공개 | 원문 확인(서브에이전트). 명시적 제외 문장 없음 |
| Free to Look (arXiv 2610.35767) | 후보는 인벤토리 개체. 메트릭 열은 그 열을 가진 개체로 바꿔 채점. KPI 언급 없음. 표 1의 347은 유효 후보 수 | 원문 확인(서브에이전트) |
| MATMCD 공개 코드 `official/matmcd/LEMMA_experiment.py` 31-42행 | 모든 열(KPI `Latency` 포함)을 순위 목록에 남김 | 작업자 대조 |

- 결론: KPI를 순위에 넣는 것은 MATMCD 공개 코드뿐이고, 나머지는 문장이나 코드로 개체(Pod)만을 후보로 둔다. 결정은 MASTER_PLAN K20.
- 부수 확인: LEMMA-RCA 공식 평가 스크립트의 PR@k는 `min(k, 정답 수)`로 나누고, MRR은 첫 정답의 순위로 계산한다.
