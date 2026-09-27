# 공식 장애 시나리오 자료 확인

이미 고정 revision으로 확보한 메트릭 ZIP 안에 시나리오 PPTX가 있었다. 원본 파일을 source별 raw_downloads/.../scenario_documents에 그대로 꺼내 SHA256·ZIP 멤버·슬라이드 번호와 텍스트를 기록했다. PPTX를 편집하지 않았고, 정답 정보는 LLM 입력이나 검색 인덱스에 넣지 않았다.

| 사례 | ZIP 내 시나리오 | 슬라이드 수 |
|---|---|---:|
| CC 20231207 | 20231207/1207_README_en-US.pptx | 10 |
| PR 20210517 | 20210517/0517_readme.pptx | 21 |
| PR 20210524 | 20210524/0524_readme.pptx | 21 |
| PR 20211203 | 20211203/1203_readme.pptx | 27 |
| PR 20220606 | 20220606/0606_readme.pptx | 32 |

[전체 텍스트·출처 기록](evidence/rca_scenario_slides.json). 슬라이드 OOXML 텍스트·표 텍스트를 추출했고, CC 3/4쪽의 내장 구성도 이미지도 확인했다. 모든 슬라이드의 렌더링을 검사했다는 뜻은 아니다.

## CC에서 확인한 내용

4/5쪽은 복제된 productpage-v1 중 한 pod에서 잠재 버그로 CPU 사용량이 증가하고, 그 pod로 연결된 일부 요청이 느려지는 장애를 설명한다. 4쪽 내장 구성도에도 productpage-v1이 두 개로 표시돼 있다.

- 버그/CPU 부하 시작: 2023-12-07 16:48 JST → 07:48 UTC.
- SLI 영향 시작: 16:53:03 JST → 07:53:03 UTC.
- 사람이 알아차릴 것으로 가정한 시각: 19:32:44 JST → 10:32:44 UTC.

JST/UTC 해석은 배포 README의 시간대 설명을 따른다. 이러한 시각을 확인했다는 이유로 기존 입력 구간을 자르거나 전처리를 다시 하지 않았다.

현재 metric 열에는 다음 두 pod가 있으며 둘 다 정확한 로그 쌍이 있다.

```text
productpage-v1-94d68db49-j7t55
productpage-v1-94d68db49-vc8ct
```

이름 prefix 일치는 후보 조사일 뿐 정답 확정이 아니다. 확인한 슬라이드 텍스트와 3/4쪽 구성도에는 어느 전체 pod 이름에 장애를 주입했는지가 표시돼 있지 않다. 둘을 모두 정답 처리하거나 CPU가 더 큰 쪽을 정답으로 삼으면 별도의 평가 가정이 된다.

## PR 20220606에서 확인한 내용

5쪽은 측정 기간을 2022-06-03 18:30 ~ 06-05 19:40, 외부 부하 시작을 06-04 18:30으로 기재한다. 파일의 날짜 표기가 장애 발생 시각과 같다고 해석해서는 안 된다. 영향을 받는 pod는 reviews-v2/v3이며 외부 접근 부하로 Java OOM이 발생하는 시나리오다.

MATMCD 보조 코드의 이 사례 Ground_Truth는 istio-ingressgateway다. 시나리오의 물리적 외부 원인, 영향을 받은 서비스, 그래프 안에서의 정답 노드를 구분해야 한다. 이 자료만으로 정답을 reviews로 교체하지 않았다. KPI 이름 Latency와 Success_Rate 관련 데이터 의미 문제도 실제 입력값을 변경하지 않고 유지한다.

## 추가 Cloud Computing 원자료 조사

[공식 원자료 저장소](https://huggingface.co/datasets/Lemma-RCA-NEC/Cloud_Computing_Original/tree/9e5ad23fa390f6b596f41be014233fe446679bcd)의 20231207.zip을 고정 revision으로 확보했다. 1,397,313,780바이트이며 SHA256은 `4cb0d2c6ea84a256c567aa0b7ad5f2bfffdb0272caa0cba31dd5654e227a17b3`다. 자산 위치는 raw_downloads/huggingface_lemma_rca_cloud_computing_original이며 다운로드 영수증·실패/재개 이력도 함께 보존했다.

최초 전송은 ResponseEnded, 두 번째 전송은 curl 오류 18로 18,066,717바이트가 부족했다. 동일 고정 URL의 나머지 구간을 받아 공식 크기·SHA256 일치를 확인했다. 전송 오류를 해결하기 위해 자료나 활성 입력을 바꾸지 않았다.

2,085개 ZIP 엔트리를 조사하고 configuration의 all_pod_before.txt와 all_pod_after.txt를 원문 그대로 확보했다. book-info namespace에는 장애 전 j7t55/vc8ct가, 이후 vc8ct/zvtz8가 있다. **j7t55가 교체됐다는 사실은 장애 주입 대상의 명시적 정답 기록과 다르다.** 해당 pod를 정답으로 채택하지 않았다. 다른 namespace의 productpage pod도 섞지 않았다.

영문 시나리오 PPTX는 이미 확인한 전처리 ZIP의 PPTX와 해시가 같았다. 파일명 기준으로 fault/stress/chaos/inject 또는 .sh/.yaml 주입 설정 후보를 찾지 못했지만, 모든 원시 로그 본문에 단서가 없다고 결론 내리지 않는다. 활성 CSV·로그 매핑은 그대로 유지했다. [전체 엔트리·설정·조사 증거](evidence/rca_cc_original_inspection.json), 도구 scripts/inspect_cc_original.py.

## 평가와 정보 누출 방지 원칙

시나리오·정답·장애 시각은 평가 근거다. 모델이 정답을 미리 볼 수 있는 자료로 RAG에 추가하지 않는다. 활성 로그 자료는 실제 pod의 event template/structured CSV이며, 시나리오 PPTX와 분리한다.

추가 공식 원자료의 확인은 정답 근거 조사이며 활성 전처리 입력의 자동 교체가 아니다. 정확한 정답을 확인하지 못한 상태에서 실제 평가 수치를 생성하지 않는다.
