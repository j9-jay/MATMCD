# RCA 임시 입력과 정확한 로그 연결 결과

2026-09-25, TASK_032 완료. **CSV 5개와 존재하는 정확한 로그 쌍을 연결했다. 전체 RCA 준비 완료는 아니다.**

사용자의 명확한 준비 작업 자율 진행 지시에 따라 configs/inputs.json에 기존 lemma_rca_provisional_v1 입력을 명시했다. author_equivalence=UNCONFIRMED를 유지하며 CSV 값·행·열·후보 pod·전처리 설정을 바꾸지 않았다. 이전 전처리 recipe와 manifest는 그대로 보존했다.

## 완료한 작업

- CSV·timestamps·manifest 해시를 이전 검증 기록과 대조했다.
- 원본 로그 ZIP 5개의 SHA256을 manifest와 대조한 후, 기존 매핑의 exact_unique_pair=true인 파일만 압축 해제했다.
- 647개 pod의 template/structured **1,294개 파일, 44,066,393,230바이트(약 44.1GB)**를 외부 자산에 준비했다. ZIP 멤버 전체 읽기로 CRC를 검증하고 출력 SHA256·크기·필수 CSV 헤더를 기록했다.
- CSV 5개와 실제 로그 디렉터리 5개를 공식 코드 작업공간의 기대 위치에 심볼릭 링크로 연결했다.
- 공식 load_Lemma_data를 작업공간에서 호출하여 다섯 사례의 형태와 마지막 Latency 열을 확인했다. 이전 FileNotFoundError는 이 경로에서 해소됐다.
- 링크 준비 명령을 다시 실행해 기존 연결의 대상 일치를 확인했다. prepare_workspace.py가 외부 자산으로 향하는 정상 링크를 재실행 시 거부하던 경로 검증을 수정했다. 원본 코드가 아니라 경로 관리 도구의 변경이다.
- 공식 소스 37개의 내용·파일 집합을 작업 전후 대조해 보존을 확인했다.

## 사례별 결과

| 사례 | 공식 로더 shape | 연결한 로그 쌍 | 로그 쌍 미확인 | 준비한 로그 바이트 |
|---|---|---:|---:|---:|
| PR 20210517 | 166325 × 209 | 109 | 99 | 14,331,488,022 |
| PR 20210524 | 176692 × 208 | 112 | 95 | 14,286,761,661 |
| PR 20211203 | 51529 × 219 | 154 | 64 | 4,189,235,721 |
| PR 20220606 | 107789 × 229 | 148 | 80 | 6,633,886,191 |
| CC 20231207 | 79252 × 197 | 124 | 72 | 4,625,021,635 |

shape의 열 수에는 KPI 열 하나가 포함된다. 로그 누락을 이유로 metric pod를 제외하지 않았다. 해당 pod의 빈 로그·합성 로그도 만들지 않았다.

## 자산 경로

configs/paths.json의 asset_root를 기준으로:

```text
processed_data/lemma_rca_provisional_v1/<system>/<day>/  기존 CSV·sidecar·manifest
datasets/huggingface_lemma_rca_product_review_pod_logs/<day>/  정확한 원본 로그 쌍
datasets/huggingface_lemma_rca_cloud_computing_pod_logs/<day>/  정확한 원본 로그 쌍
workspaces/d2i_matmcd_original/data/LEMMA_RCA/...  위 자산으로 연결하는 링크
```

작업공간 이름의 original은 공식 코드 링크가 원본이라는 뜻이며, 연결된 CSV가 저자 원본과 동일하다는 뜻이 아니다. 활성 입력 프로필은 configs/inputs.json에 표시한다.

원본 전처리 검증기는 최초 준비 시의 '입력 미연결·Task TODO'를 고정 가정하고 있었다. 현재 승인 단계에 맞춰 입력이 비어 있는 과거 상태 또는 정확한 승인 프로필의 5개 링크를 검증하도록 갱신했다. Task 상태는 관찰값으로 기록하며 입력의 과학적 검증과 혼동하지 않는다. 향후 재검증은 원래 검증 JSON을 덮어쓰지 않고 시각별 새 파일을 남긴다. 현재 링크 검증은 VERIFIED_PROVISIONAL_LINKS를 통과했으며 전체 원자료 수치 재검증을 불필요하게 반복하지 않았다.

## 남은 범위

로그 누락 정책·실제 요약·로컬 모델의 RCA 단계별 연결·정답 대응·그래프 방향 및 평가 프로토콜은 아직 미완료다. 그래프 fitting·RWR·LLM 추론·평가·외부 API 호출은 수행하지 않았다.

근거: [실제 연결 기록](evidence/rca_input_connection_20260925T105701596179Z.json), [연결 도구](../scripts/connect_rca_inputs.py), [입력 설정](../configs/inputs.json), [TASK_032](../tasks/TASK_032_connect_provisional_rca_inputs.md).
