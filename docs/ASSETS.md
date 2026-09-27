# RCA 외부 자산과 모델

외부 루트는 configs/paths.json의 asset_root로 관리한다. 이 PC는 E:/연구/MATMCD_DATA, WSL은 /mnt/e/연구/MATMCD_DATA다.

## 확보한 데이터

| 출처 | revision | 날짜 | 자산 루트 아래 위치 |
|---|---|---|---|
| Lemma-RCA-NEC/Product_Review_Preprocessed | df25484004e50483de6f6756c3a4d7ab03174b83 | 20210517, 20210524, 20211203, 20220606 | raw_downloads/huggingface_lemma_rca_product_review_preprocessed |
| Lemma-RCA-NEC/Cloud_Computing_Preprocessed | 03f82a2c4b16afe09e9315def9f5d6990427000a | 20231207 | raw_downloads/huggingface_lemma_rca_cloud_computing_preprocessed |
| Lemma-RCA-NEC/Cloud_Computing_Original | 9e5ad23fa390f6b596f41be014233fe446679bcd | 20231207 | raw_downloads/huggingface_lemma_rca_cloud_computing_original |

공식 사이트: https://lemma-rca.github.io/ . Log/Metric ZIP 10개와 README·metadata를 보존한다. URL·revision·크기·SHA256은 [downloads.json](evidence/downloads.json), 내부 구조는 [lemma_archives.json](evidence/lemma_archives.json)에 있다. 공개 코드의 날짜 목록과 논문 표 4의 정확한 사례 선택·집계 대응은 미확정이다.

전체 비압축 크기는 약 97 GB다. metric별 NPY, KPI CSV, 장애 시나리오 자료, 구조화 로그·템플릿 등이 있으며 전체 압축 해제는 하지 않았다. 배포명 Preprocessed는 MATMCD의 EVT 필터 후 최종 입력이라는 뜻이 아니다.

저자가 사용한 최종 CSV·정확 전처리는 미확보다. [TASK_020](../tasks/TASK_020_apply_provisional_rca_preprocessing.md)의 승인 프로필로 임시 metric CSV 5개를 생성·검증했다. 설정은 configs/rca_preprocessing_proposal.json이며 저자 동일성은 UNCONFIRMED다. TASK_032에서 configs/inputs.json에 provisional/UNCONFIRMED를 명시하고 CSV 5개 및 로그 디렉터리를 연결했다.

## 생성한 임시 입력

| 시스템 | 날짜 | 자산 루트 아래 위치 |
|---|---|---|
| Product Review | 20210517, 20210524, 20211203, 20220606 | processed_data/lemma_rca_provisional_v1/Product_Review/<day> |
| Cloud Computing | 20231207 | processed_data/lemma_rca_provisional_v1/Cloud_Computing/20231207 |

각 위치에 <system>_<day>.csv, timestamps.csv, manifest.json을 보관한다. CSV 합계는 2,523,657,083바이트이며 Git 프로젝트 내부에 넣지 않았다. 원본 ZIP과 분리했다. [행·열·상수·로그 결과](PROVISIONAL_RCA_PREPROCESSING_RESULT.md), [출력 해시와 검증](evidence/rca_preprocessing_validation.json), [생성 이력](evidence/rca_preprocessing_applied.json).

## 연결한 원본 로그와 조사 자료

| 역할 | 자산 루트 아래 위치 | 실제 준비 범위 |
|---|---|---|
| PR pod 로그 | datasets/huggingface_lemma_rca_product_review_pod_logs/<day> | 정확한 이름의 template/structured 523쌍 |
| CC pod 로그 | datasets/huggingface_lemma_rca_cloud_computing_pod_logs/20231207 | 정확한 이름의 template/structured 124쌍 |
| 공식 장애 시나리오 | raw_downloads/huggingface_lemma_rca_<source>_preprocessed/scenario_documents | 원본 PPTX 5개; CC 내장 구성도는 하위 1207_media |
| CC 추가 원자료 조사 | raw_downloads/huggingface_lemma_rca_cloud_computing_original | 원본 ZIP·다운로드 영수증/시도 이력·configuration 원문 |

로그 합계 647쌍/1,294파일/44,066,393,230바이트를 원문 그대로 추출·검증했다. 남은 사례별 pod 410개에는 정확한 쌍이 없고 처리 정책은 TASK_035에서 결정한다. [출처 ZIP·멤버·파일별 해시·로더 검증](evidence/rca_input_connection_20260925T105701596179Z.json)을 보존한다. 요약·인덱스·실제 RCA는 미실행이다.

CC Original은 [공식 고정 revision](https://huggingface.co/datasets/Lemma-RCA-NEC/Cloud_Computing_Original/tree/9e5ad23fa390f6b596f41be014233fe446679bcd)의 20231207.zip(1,397,313,780바이트, SHA256 4cb0d2c6ea84a256c567aa0b7ad5f2bfffdb0272caa0cba31dd5654e227a17b3)이다. 정답 근거 조사용으로 추가했으며 활성 입력 교체나 새 전처리는 하지 않았다. [조사 증거](evidence/rca_cc_original_inspection.json), [시나리오·정답 해석의 한계](RCA_SCENARIO_EVIDENCE.md)를 참고한다. 시나리오·정답 자료는 모델 검색 입력에 넣지 않는다.

## 공식·비교 자료

D01 원인 조사에서 Product_Review_Original revision `63aa4abe7dd7217d9b0b108894c7d893e2b29aef`의 원격 ZIP 목록만 추가 조회했다. 전체 4개 ZIP(약 53.6GB)을 다운로드/해시 검증한 것은 아니다. 20210517/20211203의 JSON 표본 8개, 185,957,531바이트는 raw_downloads/huggingface_lemma_rca_product_review_original/diagnostic_samples/<day>에 원문·CRC 검증 후 보관했다. 목록·출처·표본별 SHA256은 [원격 목록](evidence/d01_pr_original_remote_index.json), [표본 영수증](evidence/d01_pr_raw_log_samples.json)에 있다. 조사 자료이며 활성 RCA 입력에 추가하지 않았다.

- raw_downloads/github_d2i_matmcd/ef2c3ec.zip: 전체 공식 출처 보관본. 작업용 소스는 승인된 제외 목록을 적용한 RCA 부분집합이다.
- raw_downloads/github_lemma_rca_preprocessing: https://github.com/lemma-rca/rca_baselines, commit c560d8cc39c19f04c9ae74fac2404b1e5e8c3b4d. Drain3, metric→NPY, KPI, FastPC SPOT 등 참고 자료. TASK_020은 승인된 SPOT 함수·pyspot·libspot만 원본 그대로 호출한다. FastPC 전체 실험이나 Drain 전처리를 실행하지 않는다.
- raw_downloads/github_dorado_lemzha_k_reference/a6e62ef6f29d7112a96a8db7b3c017c3e246fe08: TASK_038의 D01 외부 사례 조사용 제3자 노트북 3개·CC manifest·검증 JSON. [출처·해시](evidence/d01_external_reference_20260925.json). 공식 필수 자산이 아니며 읽기만 했다. 실행 환경·전처리에 연결하지 않는다.
- raw_downloads/github_superkaiba_causal_llm_bfs: https://github.com/superkaiba/causal-llm-bfs, commit 80c9f5d1eb49b74335ec178798671b34c3742776. 표 4에도 등장하는 Efficient-CDLMs의 공통 비교 참고. MATMCD 적용 수정본·조건은 미공개다.
- raw_downloads/user_matmcd_paper/MATMCD.pdf 및 analysis/user_matmcd_paper: 논문 사본·추출·렌더. 사용자 원본 PDF도 보존한다.

라이선스 표기가 혼재하므로 출처를 보존하고 데이터를 재배포하지 않는다.

## Graphviz 설치 자산

Graphviz B안의 Ubuntu DEB 9개는 raw_downloads/ubuntu_noble_graphviz_2.42.2-9ubuntu0.1에 원본 그대로 보관한다. [패키지 lock](evidence/graphviz_ubuntu_packages.lock.json)에 다운로드 URL·정확 버전·해시가 있어 Git 저장소만으로 출처와 기대 파일을 확인할 수 있다. 실행 파일은 WSL 시스템 /usr/bin/dot에 설치돼 있다. 설치 로그·시스템 목록·인공 PNG는 logs/setup/graphviz_20260924T120441708131Z에 있으며 RCA 실험 산출물과 구분한다.

## 모델·서비스

| 역할 | 공식 구성 | 상태 |
|---|---|---|
| CC LLM | gpt-4o-mini | SDK 설치, 키 미설정, exact snapshot 미공개 |
| Search LLM | 코드 gpt-4 | 논문 기본 모델과 차이 |
| 웹 중간 요약 | gpt-4o-mini / temperature 0.0 | 논문 기본값과 차이 |
| embedding | text-embedding-ada-002 | 어댑터 설치, 인증·벡터 생성 미실행 |
| 최종 RAG 요약 | 코드 LLM 미지정 | 라이브러리 기본과 논문값 구분 |
| 검색 | Serper / Tavily | 접근 미구성 |

공식 config.py와 web_utils/config/config.yaml의 키는 빈 값이다. 환경변수만으로 작동한다고 가정하지 않는다. 원본의 정확 tokenizer·서빙 정밀도·snapshot도 미공개다. 원본 외부 API 호출은 하지 않았다. 이후 승인된 로컬 생성 모델의 별도 구성은 아래에 기록한다.

위 표는 원본 외부 서비스의 준비 상태다. 2026-09-24 사용자가 별도로 승인한 **임시 로컬 생성 모델**은 Qwen3.5-4B Q5_K_M이며, 2026-09-25 승인으로 thinking에서 non-thinking으로 전환했다. `models/huggingface_unsloth_Qwen3.5-4B_Q5_K_M`에 고정 GGUF와 출처를, `raw_downloads/github_ggml_org_llama_cpp_b11146`에 서버/CUDA 원본 압축파일을, `tools/github_ggml_org_llama_cpp_b11146_cuda12.8`에 분리 실행 파일을 둔다. 모드 전환에서 자산은 재사용했고 기존 공식 모델 설정은 바꾸지 않았다. [로컬 명세](LOCAL_LLM.md), [설치 파일 해시](evidence/local_llm_install.json), [TASK_023](../tasks/TASK_023_local_qwen_thinking_setup.md), [TASK_029](../tasks/TASK_029_local_nonthinking_verification.md)를 따른다. 로컬 대체로 원본 모델·임베딩·검색 접근을 해결했다고 간주하지 않는다.

2026-09-25 승인된 **임시 로컬 임베딩** BAAI/bge-m3(revision 5617a9f61b028005a4858fdac845db406aefb181)는 models/huggingface_BAAI_bge-m3에 둔다. dense/CPU/FP32/batch 1, 공식 CLS+L2 계산을 사용한다. wheel·metadata는 raw_downloads/pypi_bge_m3_loader_tf4.51.3, 별도 로더는 environments/pypi_bge_m3_loader_tf4.51.3, 인공 인덱스는 caches/retrieval_bge_m3_dense_cpu_fp32_v1, 시도별 증거는 logs/local_embedding/bge_m3_dense_cpu_fp32_v1에 있다. 기존 wheel의 cl100k_base를 동일 bytes로 복사한 분할 캐시는 caches/tiktoken이다. [명세](LOCAL_EMBEDDING.md), [설치 해시](evidence/local_embedding_install.json), [인공 검증 PASS](evidence/local_embedding_runtime.json). 원본 ada-002 접근과 실제 RCA 통합은 미완료다.

공통 환경은 environments/, 설치 캐시는 caches/uv_packages, 설치·검증 로그는 logs/에 있다. 실행 작업공간은 workspaces/d2i_matmcd_original이며 공식 소스, CSV 5개, 정확한 원본 pod 로그 디렉터리와 요약 저장 경로가 연결돼 있다. 실제 요약·실험 결과·체크포인트는 없다.

승인된 D01의 데이터 가용성 manifest 5개는 processed_data/lemma_rca_log_evidence_v1/<system>/<day>.json에 있다. 입력 CSV·로그를 복사/변형한 파일이 아니라 기존 후보·출처 해시·로그 부재 표시를 담는 [별도 근거 명세](RCA_LOG_POLICY.md)다. inputs.json이 경로를 참조하며 모델 요약·실험 결과와 구분한다.

TASK_039 이후 inputs.json은 PR 20211203·PR 20220606·CC 20231207의 CSV·로그·D01 근거 3개만 활성 참조한다. PR 20210517/20210524의 자료와 과거 링크·근거는 보관 자산이며 현재 실행 목록에서 제외됐다. 물리적으로 파일이 존재한다는 이유로 실행 대상으로 간주하지 않는다. 전체 44.07GB 중 현재 사용할 연결 로그는 15.45GB다.
