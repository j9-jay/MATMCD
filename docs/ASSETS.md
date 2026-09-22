# 외부 자산과 모델 준비 상태

자산 루트는 [configs/paths.json](../configs/paths.json)의 `asset_root` 한 곳에서 관리한다. 값은 설정 파일 기준 상대경로이며 이 PC에서는 `E:\연구\MATMCD_DATA`로 해석된다. Python 스크립트는 공통 `scripts/project_paths.py`를 사용한다. WSL에서는 같은 파일을 `/mnt/e/연구/MATMCD_DATA`로 읽는다.

다운로드 URL·revision·SHA256·크기는 [downloads.json](evidence/downloads.json), 코드 출처는 [upstream.json](../configs/upstream.json)에 기록했다. ZIP 원본은 보존했으며, 누락된 전처리 입력을 만들어 넣지 않았다. 실험 데이터·환경·캐시·다운로드는 프로젝트 Git 밖에 있다.

사용자 PDF의 원본 사본은 `raw_downloads/user_matmcd_paper/MATMCD.pdf`, PDF에서 추출한 페이지 텍스트와 확인용 렌더는 `analysis/user_matmcd_paper`에 분리했다. `E:\연구\MATMCD.pdf` 원본도 그대로 보존했다.

## 벤치마크

저자가 [공식 README](https://github.com/D2I-Group/matmcd#-quick-start)에서 CSV 배포처로 지정한 [mas-takayama/LLM-and-SCD](https://github.com/mas-takayama/LLM-and-SCD)를 받았다. 커밋은 `5aaeaea89e71e2cff443289e473c06d2f79172c5`다.

| 원본 위치 (`raw_downloads/github_mas_takayama_llm_and_scd/` 아래) | 원본 로더가 기대하는 파일명 | 확인 크기 |
|---|---|---|
| `benchmark datasets/Auto MPG data.csv` | `data/Auto_MPG_data.csv` | 392×5 |
| `ground truth matrix/GTmatrix_Auto MPG data.csv` | `data/Auto_MPG_GTmatrix.csv` | 5×5 |
| `benchmark datasets/DWD climate data.csv` | `data/DWD_climate_data.csv` | 349×6 |
| `ground truth matrix/GTmatrix_DWD climate data.csv` | `data/DWD_climate_GTmatrix.csv` | 6×6 |
| `benchmark datasets/Sachs data.csv` | `data/Sachs_data.csv` | 7,466×11 |
| `ground truth matrix/GTmatrix_Sachs data.csv` | `data/Sachs_GTmatrix.csv` | 11×11 |

CSV 내용·열 순서·수치를 바꾸지 않고 WSL 작업공간에 파일 링크로 연결했다. AutoMPG 변수 순서는 Displacement, Mpg, Horsepower, Weight, Acceleration이다. DWDClimate는 Altitude, Temperature, Precipitation, Longitude, Sunshine, Latitude, Sachs는 raf, mek, plc, pip2, pip3, erk, akt, pka, pkc, p38, jnk다. DWDClimate의 논문 350행과 공개 349행 차이를 보정하지 않았다. 출처 README의 비공개 건강검진 데이터는 MATMCD의 이 3개 공개 벤치마크 누락을 뜻하지 않는다.

Asia와 Child는 [bnlearn Asia](https://www.bnlearn.com/bnrepository/discrete-small.html#asia), [bnlearn Child](https://www.bnlearn.com/bnrepository/discrete-medium.html#child)의 공식 BIF 압축본을 각각 `raw_downloads/bnlearn_asia_network`, `raw_downloads/bnlearn_child_network`에 저장했다. 내용만 gzip 해제한 BIF는 `datasets/bnlearn_asia_network/asia.bif`, `datasets/bnlearn_child_network/child.bif`에 있다. 이는 Bayesian network 정의이며 논문의 1,000개 관측 샘플이 아니다.

`SampleFromBIF.py`는 seed 없이 데이터를 생성하고 `_1000_data.csv`, `_1000_GTmatrix.csv`를 출력하지만 실행 로더는 `_data.csv`, `_GTmatrix.csv`를 기대한다. 실제 표본·샘플링 seed와 이름 매핑 기준이 확보되지 않았으므로 샘플링과 파일명 변경은 수행하지 않았다.

## LEMMA-RCA

[공식 데이터 사이트](https://lemma-rca.github.io/) → Hugging Face 공식 조직의 **전처리 배포본**을 사용했다. 여기서 "전처리 배포본"은 LEMMA-RCA 제공자의 표현이다. MATMCD 전용 EVT 필터링까지 완료된 파일이라는 뜻이 아니다.

| 배포처 | 고정 revision | 내려받은 사례 | 자산 루트 기준 위치 |
|---|---|---|---|
| [Product Review](https://huggingface.co/datasets/Lemma-RCA-NEC/Product_Review_Preprocessed) | `df25484004e50483de6f6756c3a4d7ab03174b83` | 20210517, 20210524, 20211203, 20220606; 각각 Log/Metric | `raw_downloads/huggingface_lemma_rca_product_review_preprocessed` |
| [Cloud Computing](https://huggingface.co/datasets/Lemma-RCA-NEC/Cloud_Computing_Preprocessed) | `03f82a2c4b16afe09e9315def9f5d6990427000a` | 20231207 Log/Metric | `raw_downloads/huggingface_lemma_rca_cloud_computing_preprocessed` |

선택은 `Log_tools.py`/`Web_tools.py`/`LEMMA_experiment.py`에 공개된 사례 목록을 따른다. MATMCD가 사용했다는 근거 없는 Cloud Computing의 다른 날짜는 추가하지 않았다. 이는 실험 입력의 임의 축소가 아니라 공개된 실험 범위와의 대응이다.

10개 ZIP 및 README, 2개 BIF 압축 파일의 총 다운로드 크기는 6,969,019,063 bytes다. 10개 ZIP의 전체 비압축 크기는 97,017,449,874 bytes다. ZIP 내부 목록을 조사했으며, `Product_Review_<day>.csv`, `Cloud_Computing_<day>.csv`는 없다. 현재 전체 ZIP을 풀어 중복 공간을 차지하게 하지 않았다. 압축본은 모두 다운로드·해시 검증되어 로컬에 있다.

실제 내용에는 metric별 NPY, KPI CSV, 장애 시나리오 PPTX, pod/node별 `*_messages_templates.csv`와 `*_messages_structured.csv` 등이 있다. [lemma_archives.json](evidence/lemma_archives.json)에 요약했다. MATMCD에서 요구하는 선택 pod와 열 순서, KPI 마지막 열, metric 선택/결합 방식, 시간 구간, EVT 기준이 확인되지 않아 최종 CSV를 재구성하지 않았다.

LEMMA-RCA 공식 [전처리 저장소](https://github.com/lemma-rca/rca_baselines)는 `raw_downloads/github_lemma_rca_preprocessing`에 커밋 `c560d8cc39c19f04c9ae74fac2404b1e5e8c3b4d`로 보존했다. Drain3 로그 파싱, metric JSON→NPY, KPI 구축, FastPC SPOT 코드는 존재한다. 이 저장소의 default 값을 MATMCD 저자가 실제 사용했다고 볼 근거는 없으므로 이식하거나 실행하지 않았다.

배포 사이트/README/front matter에 CC BY-ND와 CC BY-NC 표기가 혼재한다. 출처 파일을 그대로 보존했고 재배포는 하지 않았다. 데이터 revision은 현재 공개 상태를 고정한 것이며 논문 당시 사용본과의 일치 여부는 미확인이다.

## 모델 및 서비스

| 용도 | 공식 구성 | 준비 상태 |
|---|---|---|
| 기본 CC LLM | OpenAI `gpt-4o-mini` | SDK 설치. API 키 빈 값, 호출 안 함. snapshot 미공개 |
| Search LLM | 코드상 `gpt-4` | 코드 보존. 논문 기본 모델과 차이 있음. 호출 안 함 |
| Web summary | `gpt-4o-mini`, temperature=0.0 | 코드 보존. 호출 안 함 |
| RAG embedding | `text-embedding-ada-002` | 원격 API 구성. 로컬 가중치/정확 snapshot 미제공. llama-index embedding 패키지 버전도 목록에서 누락 |
| 최종 RAG summary | 공식 코드 미지정 | 설치된 LlamaIndex 기본 모델/설정과 논문값을 구분해야 함 |
| 절제 모델 | GPT-4, Mistral API, LlamaAPI(Llama/Gemma) 별칭 | provider별 정확 모델 revision·tokenizer·serving 설정 미공개 |
| 검색 | Serper, Tavily | 클라이언트 코드와 지정 SDK 보존. 키 설정/호출 안 함 |
| MATMCD 체크포인트 | 별도 학습 체크포인트 없음 | 만들거나 다른 모델을 다운로드하지 않음 |

공식 `config.py`와 `web_utils/config/config.yaml`에는 API 키 설정이 **따로** 존재한다. 현재 둘 다 빈 값이다. 환경변수만 넣어도 작동한다고 안내하지 않는다. 추후 자격정보 구성은 원본 snapshot과 비밀정보를 분리할 방법을 먼저 결정해야 한다. 이번 작업에서는 유료 API를 호출하지 않았고 사용자의 다른 계정/키를 탐색하지 않았다.

## 비교 방법 추가 자료

Efficient-CDLMs 저자 저장소 [superkaiba/causal-llm-bfs](https://github.com/superkaiba/causal-llm-bfs)는 `raw_downloads/github_superkaiba_causal_llm_bfs`에 `80c9f5d1eb49b74335ec178798671b34c3742776`으로 확보했다. 이 원본의 기본 모델은 `gpt-4-0125-preview`, temperature=0.7, Python 3.10.13이다. MATMCD 논문의 GPT-4o mini/0.5 및 모든 비교 데이터에 적용한 수정본·실행 설정은 공개 MATMCD에 없다. 따라서 별도 논문의 기본 환경을 설치해 MATMCD 비교 실험 환경이라고 주장하지 않는다.
