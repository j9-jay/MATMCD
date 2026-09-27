# RCA 공개 지표 함수 준비

TASK_033에서 scripts/rca_metrics.py를 준비했다. 공식 LEMMA_Metrics.py의 고정 rank 목록을 실행하지 않고, PRK/MAPK/MRR 함수 AST만 변경 없이 불러온다. 원본 ZIP과 코드의 바이트 일치를 매번 확인한다.

명시적으로 확정된 양의 1-based rank 목록을 evaluate_ranks에 전달하면 공개 정의에 따른 MAP@5, MAP@10, MRR 및 함수 출처를 반환한다. 이 함수는 정답 이름을 추측하거나, pod를 service로 합치거나, 사례·반복을 선택하지 않는다. 빈 목록·0·음수·실수·bool·미확인 rank는 거부한다.

## 공개 지표 정의와 일반 AP의 차이

공개 PRK는 rank <= k가 아닌 rank < k를 사용하고, MAPK는 k=1부터 K까지 PRK를 평균한다. 양의 정수 rank에 대해 다음과 같다.

```text
MAPK(K) = mean(max(K - rank, 0) / K)
MRR = mean(1 / rank)
```

이는 일반적인 Average Precision의 정의와 다르다. 예컨대 정답이 1등인 단일 사례라도 공개 MAP@5는 0.8이다. 논문 표 4를 비교하는 준비이므로 이 경계를 임의로 고치지 않았다. 다른 표준 지표를 추가할 경우에는 별도 이름·프로토콜로 정의해야 한다.

## 검증 결과

공개 예시 [2,7]은 0.30/0.55/0.3214285714, [3,6]은 0.20/0.55/0.25를 반환했다. 1등 및 K와 같은 순위의 경계, 잘못된 입력 거부를 포함해 **11개 검사 PASS**다. 이는 함수 검증이며 새 실험 결과가 아니다.

[검증 증거](evidence/rca_metric_adapter_20260925T105908213664Z.json), [호출 도구](../scripts/rca_metrics.py).

실제 평가 TASK_008은 여전히 TODO다. 실제 순위 저장, 정확한 장애 pod/서비스 정답, KPI의 순위 포함 여부, 동점·실패·반복·사례 집계 규칙이 확정돼야 연결할 수 있다. 특히 CC에는 productpage-v1 복제 pod 두 개가 있고 공식 시나리오는 한 pod만 장애 대상이라고 설명한다. 둘 중 높은 순위를 임의로 정답으로 선택하지 않는다.
