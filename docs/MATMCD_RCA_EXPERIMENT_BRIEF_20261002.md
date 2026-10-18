# MATMCD 로컬 RCA 실험

환경 · 단계별 산출물 · 결과 · 확인 사항

작성 2026-10-02 / 완료 실행 2026-09-27 / PR 20211203 · 정답 포함30 Pod

## 1. Scope — 실험 범위

| 항목 | 구성 |
| --- | --- |
| 목적 | 로컬 MATMCD 완주 · 후속 중간 로직 교체 실험의 기준선 확보 |
| 대상 | LEMMA-RCA · Product Review · 20211203 |
| 비교 | PC 기준선 → 로그/RAG·LLM 제약 추가 → MATMCD |
| 범위 | 일반 모드 · 1개 사례 · 1회 최종 실행 · 학습/미세조정 없음 |
| 후보 | 잠정 정답 MongoDB 포함 30 Pod + Latency |
| 완료 | 2026-09-27 04:43 KST |
| 해석 | 정답 포함 개발 평가. 원논문 동일 조건 재현·전체 후보 탐색 성능은 미검증 |

- **Pod:** 프로그램 실행 단위
- **Latency:** 서비스 응답 지연 지표
- **RCA:** 장애 원인 후보의 순위 산출

## 2. Environment — 로컬 구성

| 구분 | 실제 설정 |
| --- | --- |
| CPU / RAM / GPU | Ryzen 7 5700X3D / 약16GB / RTX 2080 SUPER 8GB |
| OS / Python | Windows 11 · WSL2 Ubuntu / Python 3.11.13 |
| 공식 코드 | D2I-Group/matmcd · commit `ef2c3ec` 고정 |
| 통계 분석 | causal-learn 0.1.4.1 · PC · Fisher-Z |
| 생성 모델 | Qwen3.5-4B · Q5_K_M · non-thinking |
| 추론 서버 | llama.cpp b11146 · GPU 전체 레이어 · 요청 순차 처리 |
| 임베딩 | BGE-M3 · CPU · FP32 · batch 1 |
| RAG | chunk 1,024 · overlap 200 · top-k 2 · 별도 reranker 없음 |
| 문맥 / 최대 답변 | 81,920 / 요청당 8,192토큰 |
| 캐시 | prompt cache ON · KV FP16 |
| 반복 억제 | 로그·관계 설명 1.5 / RAG 합성·Yes/No 판단 0 |
| 파일 분리 | `MATMCD`: 코드·설정·문서 / `MATMCD_DATA`: 데이터·모델·산출물 |

**실제 설명 요청 설정 — 필요한 필드만 발췌**


```json
{
  "model": "qwen35-4b-q5km-nonthinking",
  "temperature": 0.5,
  "max_tokens": 8192,
  "seed": 42,
  "top_p": 0.95,
  "presence_penalty": 1.5
}
```

[원본 요청 call_0000480.json](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/calls/call_0000480.json)

- 논문 대비 차이: 생성·임베딩 모델 대체, 승인된 임시 전처리, 후보 축소.
- 원본 RCA 코드 보존 + 별도 실행기로 로컬 모델·경로 연결.

## 3. Input — 데이터와 후보

| 항목 | 실제 입력 |
| --- | --- |
| 원자료 | CPU·메모리·수신/송신 패킷·대역폭 + Pod 이벤트 로그 |
| 전처리 | 공통 시각 정렬 → 비상수 채널 z-score → Pod별 동일 가중 평균 |
| 수치 배열 | 51,529행 × 31열 |
| 후보 선정 | 준비된218 Pod → 잠정 정답1 + 이상 점수 상위29 |
| 잠정 정답 | `mongodb-v1-64c6b69879-p4wfp` |
| 로그 | 정확히 대응하는20 Pod / 근거 부재10 Pod |
| 행 보존 범위 | 전처리된 입력의 전체51,529행. 원자료 전체 시각과는 다름 |

**실제 배열 — 첫 3행, 3열 발췌 / 소수 6자리 표시**


```text
MongoDB         ratings         Latency
 0.662825       -0.386389       3514.0
 0.662825       -0.386389       22150.0
 0.662825       -0.386389       2140.0
```

[metrics.npy](E:/연구/MATMCD_DATA/processed_data/lemma_rca_oracle30_pr20211203_v1/metrics.npy)

- MongoDB·ratings: 정규화된 Pod 메트릭 통합값 / Latency: KPI 값.
- 정답은 후보 선정·평가에만 사용. LLM에 정답 라벨 전달 없음.
- 후보 포함 여부 자체의 성능은 평가하지 않음.

**추가 입력 예시 — 서로 다른 시각·Pod의 실제 값**

| 행 번호(0부터) | 시각(UTC) | amq-streams | MongoDB | ratings | web | Latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 2021-12-02 21:41:26 | 0.218999 | 0.662825 | -0.386389 | -0.067812 | 3514.000000 |
| 25764 | 2021-12-03 10:08:50 | 0.101947 | -1.044114 | -0.939204 | -1.014750 | 5985.000000 |
| 51528 | 2021-12-03 22:35:13 | -0.626232 | -0.917585 | 0.128028 | -0.228076 | 11952.000000 |

- 원본 입력의 첫·중간·마지막 행 발췌. 추가 샘플링·재전처리 없음.
- Pod 열: 여러 메트릭을 표준화·통합한 값. 음수는 평균보다 낮다는 뜻이며 오류 코드가 아님.
- Latency: 공개 KPI 값 유지. 표만 소수6자리 표시; 단위는 이 예시에서 임의 지정하지 않음.
- 표시명은 축약. 열 순서는 실제 후보 목록과 대조.

[실제 입력 배열](E:/연구/MATMCD_DATA/processed_data/lemma_rca_oracle30_pr20211203_v1/metrics.npy) · [대응 시각](E:/연구/MATMCD_DATA/processed_data/lemma_rca_provisional_v1/Product_Review/20211203/timestamps.csv) · [열 이름](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/selection.json)

## 4. Pipeline — 단계별 입력·산출물

```text
Metrics → PC → 초기 그래프 G0 ───────────────→ RWR → PC 순위
                  │
Logs → 요약 → RAG ─┤
                  ↓
          관계 설명 930개
                  ↓
          Yes/No 제약 930개
                  ↓
Metrics + 제약 → PC 재실행 → 최종 그래프 G1 → RWR → MATMCD 순위
```


| 단계 | 입력 → 처리 | 산출물 | 실행 판정 |
| --- | --- | --- | --- |
| ① 입력 준비 | 메트릭·로그 → 정렬·후보 고정 | `metrics.npy`, `selection.json` | Pass |
| ② Initial Graph | 수치 배열 → PC·RWR | `graphs/PC.npy`, `rankings/PC.json` | Pass · 30 Pod |
| ③ Log / RAG | 로그 → 요약·검색·합성 | `summaries/*.txt`, `node_information.json` | Pass |
| ④ Knowledge LLM | 초기 그래프·노드 정보 → 관계 설명 | `calls/1~930`, 설명 캐시 | Pass · 930개 |
| ⑤ Constraint LLM | 설명 → Yes/No | `calls/931~1860`, 제약 행렬 | Pass · 930개 |
| ⑥ Graph Refiner | 수치 배열·제약 → PC 재실행 | `graphs/MATMCD.npy`, `.png` | Pass |
| ⑦ Ranking / Evaluation | 최종 그래프 → RWR·정답 대조 | `rankings/`, `evaluation/` | Pass |

- 방향쌍: **31 × 30 = 930**. A→B와 B→A 각각 평가.
- Pass: 단계 실행·산출물 저장 기준. 내용 정확성·성능 개선과 별개.
- 초기 PC·로그20개·RAG: 부모 실행에서 해시 검증 후 계승.
- 관계 설명930개·제약930개: 최종 실행에서 새 생성.

## 5. Initial Graph — 수치 기반 기준선

- 입력: 51,529 × 31 메트릭 배열
- 처리: PC 조건부 독립성 검사 → 초기 인과 그래프
- 평가: 초기 그래프에서 RWR → 잠정 정답 Pod **4위**
- 소요: 초기 PC·그림·RWR·평가 **691.12초**

**실제 초기 그래프 — 행/열 순서: MongoDB, ratings, Latency**


```text
[[0 1 1]
 [0 0 0]
 [0 0 0]]
```


- 그래프 규약: `G[결과, 원인] = 1`과 역방향0이면 확정 방향 간선.
- 발췌 해석: `ratings → MongoDB`, `Latency → MongoDB`.
- 통계적으로 추정한 관계. 실제 시스템의 정답 관계로 확정한 것은 아님.

[PC.npy](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/graphs/PC.npy) · [PC 전체 그래프](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/graphs/PC.png)

## 6. Log / RAG — 근거 수집과 전달

- 로그20개: 원본 코드의 이벤트 예시 선택 → LLM 요약
- 요약 자료: 분할·BGE-M3 임베딩 → 의미 검색 top-k2 → 종합 설명
- 로그 부재10개: 고정된 ‘근거 없음’ 표시
- 실행 경로: 로컬 로그 검색. 웹 검색 없음.

**요약 전 실제 로그 입력 — 유형별 발췌**

- 저장된 LLM 요청의 로그 예시에서 시각·내용을 그대로 추출. LLM이 생성한 요약문이 아님.
- 아래 4건은 형식을 보여주는 발췌이며 전체 로그의 분포·장애 빈도를 대표하지 않음.

**① MongoDB · 저장 공간 부족**

```text
2021-12-03T09:35:04.962504+00:00
E STORAGE  [WTCheckpointThread] WiredTiger error (28) [1638524104:952400][1:0x7f3165064700], file:WiredTiger.wt, WT_SESSION.checkpoint: __posix_open_file, 672: /data/db/WiredTiger.turtle.set: handle-open: open: No space left on device Raw: [1638524104:952400][1:0x7f3165064700], file:WiredTiger.wt, WT_SESSION.checkpoint: __posix_open_file, 672: /data/db/WiredTiger.turtle.set: handle-open: open: No space left on device
```

- 파일 열기·체크포인트 중 디스크 부족 오류.
- 템플릿 ID 1698 / 요청에 기재된 발생 횟수 4. 아래 한 줄의 반복 횟수가 아닌 해당 이벤트 유형의 집계.

[실제 로그 입력 call_0000007.json](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T132900237241Z/calls/call_0000007.json)

**② ratings · DB 연결 상태 확인**

```text
2021-12-02T08:30:02.170374+00:00
app.INFO: Health-Check {"pdo_connectivity":true} []
```

- 해당 시점의 연결 검사 true. 전체 서비스 무장애를 뜻하지 않음.
- 템플릿 ID 1691 / 요청에 기재된 발생 횟수 35400. 아래 한 줄의 반복 횟수가 아닌 해당 이벤트 유형의 집계.

[실제 로그 입력 call_0000011.json](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T132900237241Z/calls/call_0000011.json)

**③ ratings · 사용 중단 예정 API 경고**

```text
2021-12-02T08:30:02.151402+00:00
php.INFO: User Deprecated: Since symfony/http-kernel 5.3: "Symfony\Component\HttpKernel\Event\KernelEvent::isMasterRequest()" is deprecated, use "isMainRequest()" instead. {"exception":"[object] (ErrorException(code: 0): User Deprecated: Since symfony/http-kernel 5.3: \"Symfony\\Component\\HttpKernel\\Event\\KernelEvent::isMasterRequest()\" is deprecated, use \"isMainRequest()\" instead. at /var/www/html/vendor/symfony/http-kernel/Event/KernelEvent.php:88)"} []
```

- 프레임워크 API 교체 안내. 이 문장만으로 서비스 중단을 확정하지 않음.
- 템플릿 ID 1689 / 요청에 기재된 발생 횟수 35400. 아래 한 줄의 반복 횟수가 아닌 해당 이벤트 유형의 집계.

[실제 로그 입력 call_0000011.json](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T132900237241Z/calls/call_0000011.json)

**④ amq-streams · 주기적 운영 이벤트**

```text
2021-12-02T08:30:51.113184+00:00
INFO  ClusterOperator:125 - Triggering periodic reconciliation for namespace quarkus...
```

- 운영자의 주기적 상태 조정 작업 기록.
- 템플릿 ID 1891 / 요청에 기재된 발생 횟수 1475. 아래 한 줄의 반복 횟수가 아닌 해당 이벤트 유형의 집계.

[실제 로그 입력 call_0000001.json](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T132900237241Z/calls/call_0000001.json)

**MongoDB 개별 요약 — 실제 응답 발췌**


```text
- Disk Space Exhaustion: Explicit error messages indicate "No space left on device" during file operations and checkpointing, which directly correlates with the storage engine panics.
```

[MongoDB 개별 요약](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T132900237241Z/summaries/Product_Review_20211203/mongodb-v1-64c6b69879-p4wfp_summary.txt)

**RAG에 실제 전달된 문맥 — 원본 요청에서 파일명만 추출**

```text
amq-streams-cluster-operator-v1.7.3-5f6b9df578-kbgtc_summary.txt
ratings-755c5794c9-m8fxz_summary.txt
```

[RAG 요청 call_0000021.json](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T132900237241Z/calls/call_0000021.json)

**최종 MongoDB 설명 — 첫 두 문장 발췌**

```text
This entity serves as a database for storing product rating data and user profiles. The Kafka Streams cluster processes data destined for MongoDB, meaning network issues in the operator could delay data availability here.
```

[node_information.json](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/node_information.json)

- 관측: 개별 요약의 디스크 부족 근거가 최종 설명에는 없음.

## 7. CC-Agent — 설명 → Yes/No

| 역할 | 입력 | 출력 |
| --- | --- | --- |
| Knowledge LLM | 초기 그래프 + 노드 정보 + 현재 방향쌍 | 관계 설명930개 |
| Constraint LLM | 해당 방향쌍의 설명 | Yes/No 930개 |

**MongoDB → Latency — 실제 설명 요청**


```text
Please provide an explanation that leverages your expert knowledge on the causal relationship between mongodb-v1-64c6b69879-p4wfp and Latency, and assess the correctness of this causal discovery result.
```

[설명 요청·응답 call_0000480.json](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/calls/call_0000480.json)

**같은 쌍의 실제 제약 응답**

```text
<Yes>
```

[제약 응답 call_0001410.json](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/calls/call_0001410.json)

- 실제 제약값: `C[MongoDB, Latency] = 1`
- 제약 규약: `C[원인, 결과]` / Yes=1, No=0, 대각선=-1.
- 전체 판단: **Yes109 / No821**
- 설명과 제약 각각930개, 모두 정상 종료.

## 8. Graph Refiner / RWR — 최종 산출물

**실제로 실행된 연결 코드 — 연속 구간 발췌**


```python
refined = official_pc()(data, labels, method="pc", constraint_matrix=constraints)
np.save(directory / "graphs/MATMCD.npy", refined)
official_visualize()(refined, labels, str(directory / "graphs/MATMCD.png"))
ranking = rank_stage_with_original_rwr("MATMCD", initial, refined, labels)
write(directory / "rankings/MATMCD.json", ranking)
write(directory / "evaluation/MATMCD.json", evaluate(ranking, selection))
```

[continue_rca_oracle30.py](E:/연구/MATMCD/scripts/continue_rca_oracle30.py)

**실제 최종 그래프 — 행/열 순서: MongoDB, ratings, Latency**

```text
[[0 1 0]
 [0 0 0]
 [1 0 0]]
```


- 발췌 해석: `ratings → MongoDB → Latency`.
- 초기/최종 그래프: **161개 방향 간선 + 무향3쌍 → 방향 간선69개**.
- Yes109개가 그대로 최종 간선109개가 되는 것은 아님. 같은 데이터로 PC 재계산 후69개.
- RWR: Latency 시작 / steps1,000 / restart0.05 / 방문 횟수로 정렬.
- RWR 새 seed 지정 없음. 실행 전후 난수 상태 저장.
- 최종 순위는 LLM이 직접 나열한 답변이 아니라 그래프 기반 계산.

[MATMCD.npy](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/graphs/MATMCD.npy) · [최종 그래프](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/graphs/MATMCD.png) · [RWR 원본 코드](E:/연구/MATMCD/official/matmcd/Utils/RCA.py)

## 9. Results — PC 대비 MATMCD

| 지표 | PC | MATMCD |
| --- | ---: | ---: |
| 잠정 정답 Pod 순위 | 4위 | 5위 |
| KPI 포함 순위 | 5위 | 6위 |
| Pod Hit@1 / Hit@3 | 0 / 0 | 0 / 0 |
| Pod Hit@5 | 1 | 1 |
| Pod reciprocal rank | 0.25 | 0.20 |

**실제 평가 JSON — MATMCD 필드 발췌**


```json
{
  "root_rank_including_kpi": 6,
  "root_rank_pods_only": 5,
  "pod_only_metrics": {
    "Hit@1": 0,
    "Hit@3": 0,
    "Hit@5": 1,
    "reciprocal_rank": 0.2
  }
}
```

[PC 평가](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/evaluation/PC.json) · [MATMCD 평가](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/evaluation/MATMCD.json)

| 처리 구간 | 소요 |
| --- | ---: |
| 관계 설명930개 | 약4시간49분24초 |
| Yes/No 제약930개 | 약13분32초 |
| 보정 PC·그림·RWR·평가 | 약21.86초 |
| 최종 후속 실행 합계 | 약5시간4분 |

- 합계에서 부모 PC·로그/RAG, 이전 실패·진단 시간 제외.
- 실행 완주: 성공 / 이번 실행의 순위 개선: 없음.
- 단일 정답 포함 사례. 통계적 우열·논문 전체 재현 주장 불가.

## 10. Findings — 부정확한 입력·해석

**순위 변화의 단일 원인 확정은 불가. 확인된 문제와 가능한 영향 구분.**

| 확인된 문제 | 간단한 실제 예시 | 가능한 영향 |
| --- | --- | --- |
| 장애 근거 누락 | MongoDB 요약에 `No space left on device` 존재 → 검색 문맥·최종 노드 정보에서는 부재 | 핵심 장애 신호 없이 역할·일반 지식 중심 판단 |
| 현재 질문과 다른 쌍의 문장 재사용 | MongoDB→Latency 질문에 amq-streams→apiserver 판정 문장 잔존 | 현재 관계와 무관한 설명으로 유도 |
| 그래프 방향 설명 불일치 | `G[MongoDB, ratings]=1`은 ratings→MongoDB. 프롬프트는 반대 방향으로 서술 | 초기 구조에 대한 잘못된 해석 가능 |
| 근거 밖의 LLM 추정 | Kafka Streams→MongoDB 데이터 경로, Latency를 P99 등으로 추정 | 확인되지 않은 시스템 지식이 판단에 혼입 |
| 후보 축소 | 정답 MongoDB는 포함, reviews·productpage 등 전파 경로 후보는 제외 | 전체 서비스의 원인 경로 보존 불확실 |

**실제 응답의 질문 불일치 — call480**


```text
**The Statement:** "It seems that changes in `amq-streams-cluster-operator` do not directly affect `apiserver`."
```


- 실제 평가 대상: MongoDB→Latency.
- 응답 첫 분석 대상: amq-streams→apiserver.
- 같은 첫 쌍 판정 문장이 설명 입력930개 모두에 포함.
- 공개 코드 동작을 유지한 결과. 방향·첫 쌍 재사용은 임의 교정하지 않음.
- 각 요인의 순위 영향량은 미측정. ‘로컬 모델 성능만의 문제’로 단정 불가.

[실제 응답](E:/연구/MATMCD_DATA/runs/matmcd_oracle30_pr20211203_v1/20260926T143904740470Z/calls/call_0000480.json) · [문제 대조 기록](E:/연구/MATMCD/docs/evidence/rca_oracle30_result_analysis_20260927.json)

## 11. Author Inquiry — 주 저자 확인

**주 저자에게 문의 메일 발송 · 현재 확인 중.**

| 확인 항목 | 현재 불확실성 |
| --- | --- |
| 입력 전처리·EVT | 시간 정렬, 메트릭 통합, Pod 유지/제외 규칙 |
| 실제 정답·평가 | 장애 날짜, 정답 Pod, KPI 포함 여부, seed·반복·집계 |
| 그래프 프롬프트 | 방향 해석, 첫 질문 문장의 반복 사용이 실제 저자 실행에도 있었는지 |
| 로그·RAG 연결 | Pod별 근거 전달 방식, 검색 top-k, 실제 실행 경로 |
| 로그 부재·읽기 | 누락 Pod 처리, 예시 선택, 인코딩 조건 |

- 발송·확인 중 상태: 2026-10-02 사용자 제공 현황.
- 저자 답변에 따른 확정 내용은 아직 이 보고서에 반영하지 않음.
- 기존 임시 조건과 실행 결과 보존.

[문의 항목 원고](E:/연구/MATMCD/docs/AUTHOR_INQUIRY_RCA_SHORT.md)

## 12. Interruptions — PC 자원·Local LLM 한계

| 중단 단계 | 기준 | 실패 기록 | 후속 조치·결과 |
| --- | --- | --- | --- |
| 입력 문맥 검사 | 입력 + 최대 답변 ≤ 문맥 한도 | **Fail:** 한도16,384에 비해 두 사례 최대 필요73,266. 생성 전 보류 | 문맥81,920 → **Pass:** 입력278개 수용·최대 입력 실제 생성 |
| 전체 후보 PC | 메모리 내 계산 완료·그래프 저장 | **Fail:** 218 Pod + KPI 계산 중 WSL OOM. 프로세스 RAM약7.26GiB + swap약1.95GiB, 시스템 swap 잔여0 | 정답 포함30 Pod로 범위 변경 → **Pass:** 초기 그래프·순위. 전체 후보는 미완료 |
| 로그 요약 | 요청별 정상 종료 | **Fail:** 148개 완료 후149번째 반복 출력 → 출력8,192 소진 | 로그 presence0→1.5. 실패 요청 재검증533토큰 정상 종료. 이후30 Pod 실험의 로그20개 완료 |
| 관계 설명 | 930개 설명 정상 종료 | **Fail:** 40개 완료 후41번째 `non-parametric` 1,845회 반복 → 출력8,192 소진 | 설명 presence0→1.5, 진단3건 통과 → **Pass:** 930개 전부 새 생성 |

- 반복 생성 두 건: 입력 문맥 부족이 아니라 **단일 답변의 출력 한도 소진**.
- 전체 후보 Fail → 30 Pod Pass: 동일 조건 해결이 아닌 범위 변경.
- 최종 설명930개·제약930개: 실패0 / 요청별시도1.
- 단일 완주 결과이며 다른 사례·반복 실행의 성공을 보장하지 않음.

[문맥 검증](E:/연구/MATMCD/tasks/TASK_045_validate_context_81920.md) · [PC OOM](E:/연구/MATMCD/tasks/TASK_048_resolve_pc_memory.md) · [로그 반복](E:/연구/MATMCD/tasks/TASK_047_resolve_generation_repetition.md) · [설명 반복](E:/연구/MATMCD/tasks/TASK_052_domain_generation_repetition.md)
