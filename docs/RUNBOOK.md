# 실행 전 점검과 후속 실험 절차

현재 실험은 실행하지 않는다. 사용자가 이번 작업 범위를 환경 구성까지로 지정했으며 재현 차단 사유도 남아 있다. 아래 실험 명령은 후속 TODO의 참고이고 이번에는 실행하지 않았다. 공식 README의 `RCA_experiment.py`는 저장소에 없다.

## 준비와 점검

PowerShell에서 `wsl -d Ubuntu`로 들어간 뒤 다음 준비 명령을 사용한다.

```bash
cd /mnt/e/연구/MATMCD
python3 -B scripts/setup_environment.py
python3 -B scripts/prepare_workspace.py
```

패키지 설치와 파일 링크만 수행하며 실험을 호출하지 않는다. 원본 requirements를 사용한다. 현재 전체 버전은 `docs/evidence/installed_freeze.txt`로 보존했다. 저자가 고정하지 않은 Python 패치와 setuptools는 재설치 시 달라질 수 있으므로 로컬 snapshot과 비교해야 한다. 경로의 기준은 `configs/paths.json`이다.

```bash
MATMCD_ENV_PY=$(python3 -B -c 'import sys; sys.path.insert(0,"scripts"); from project_paths import asset_path; print(asset_path("environment")/"bin"/"python")')
"$MATMCD_ENV_PY" -B scripts/audit_setup.py
```

점검은 source hash, CSV 구조, version, import, CUDA 인식만 확인한다. 실험 fitting/LLM/RAG 호출은 하지 않는다. 해결되지 않은 차단 사유 때문에 **실행 준비 미완료(false)와 비정상 종료 상태**를 보고한다. 최초 import가 시간 제한에 걸린 경우에만 `--retry-timeouts`로 그 항목을 재점검한다.

공개 자료 다운로드 점검은 `python3 -B scripts/download_assets.py`다. 현재 저장된 Hugging Face metadata snapshot이 자산 루트에 있어야 한다. 고정 revision/파일 경로/해시는 `docs/evidence/downloads.json`에 있다. 검증된 파일은 다시 받지 않는다. metadata가 없다면 해당 revision의 공개 API 응답을 먼저 확보해야 하며 최신 revision으로 임의 대체하지 않는다.

## 외부 작업공간

현재 작업공간은 `MATMCD_DATA/workspaces/d2i_matmcd_original`이다. 공식 코드와 확보한 CSV/BIF를 상대 symlink로 연결했다. WSL에서 사용한다. 원본 코드는 `./data`, `./cache`, `./image`를 쓰므로 이후 실행 시 현재 디렉터리는 반드시 이 외부 작업공간이어야 한다. `official/matmcd` 안에서 실행하여 Git 내부에 실험 자산을 쌓지 않는다.

향후 출력은 작업공간의 `cache/`, `image/`, stdout에 생긴다. 출력 폴더를 미리 만들지 않았다. 필요한 원본 상대경로 구조를 보존하기 위한 실행 작업공간이며 원본 다운로드와 논문 분석 자료는 별도 위치에 있다.

`GTdatasets_experiment.py`, `LEMMA_experiment.py`, `LEMMA_Metrics.py`, `data/SampleFromBIF.py`는 module import만으로 실행될 수 있다. 환경 확인 목적으로 import하지 않는다.

## TASK_007: 향후 실제 실험

선행 조건은 누락 입력·버전·외부 API 정책·원본 오류와 논문 차이의 해소, 필요한 자료 확보, 별도 실험 실행 요청이다. 실행을 위해 임의로 코드/파라미터를 고치지 않는다.

환경을 활성화하고 외부 작업공간으로 이동한 후 공개 기본 진입점은 다음과 같다.

```bash
python -B GTdatasets_experiment.py
```

필요 입력: Auto_MPG, DWD_climate, Sachs, asia, child 각각의 `data/<name>_data.csv`, `data/<name>_GTmatrix.csv`. 현재 첫 3개만 준비되어 있다. 필요 서비스: OpenAI chat/embedding, Serper, fallback Tavily. 유료 API는 현재 사용하지 않는다.

원본 순서: Auto_MPG → DWD_climate → Sachs → asia → child. 각 데이터에서 기본 PC → 외부 정보 없는 CC-agent → 검색/요약 포함 MATMCD → reasoning 포함 MATMCD-RE. 예상 출력: stdout metrics/matrix, `image/<dataset>/*.png`, `cache/Domain_knowledge/`, `cache/RAG_Database/`, `cache/Summarized_info/`.

이 명령은 현재 완주 가능하지 않다. `_with_info` 캐시 강제 로드, 검색 응답 파서, 누락 패키지 등이 해결되지 않았다. baseline/ablation 전체 sweep용 공식 CLI도 없다.

RCA 공개 진입점은 다음과 같다.

```bash
python -B LEMMA_experiment.py
```

기본값 Product_Review/20210517, 주석 설정 Cloud_Computing/20231207. 입력은 `data/LEMMA_RCA/<system>/Metrics/<system>_<day>.csv`, 대응 로그/요약 캐시다. ZIP 다운로드만으로 준비되는 입력이 아니다. `Log_tools.py` 별도 로그 요약과 main의 웹 경로 간 연결도 미확정이다. 출력은 stdout 순위, `image/<system>_<day>/*.png`, cache다. RWR 시작 노드는 마지막 열이므로 원래 열 순서/KPI 정의가 필요하다.

표 3 후속 대상은 단일 검색, Knowledge LLM 제거, ES/DirectLiNGAM, GPT-4/Llama3.1-8B/70B/Gemma2-9B/Mistral 계열 교체다. 원본에는 일부 주석/클래스만 있고 완전한 sweep 설정은 없다. 임의 wrapper로 조합하지 않았다. Efficient-CDLMs의 MATMCD 비교용 수정본/설정도 미공개다. MAC 수치는 논문 자체가 기존 논문 결과를 인용했다.

## TASK_008: 평가

벤치마크는 실제 생성한 그래프와 원본 GT의 변수 순서를 맞춰 `Utils.metrics.Metrics(...).calc_all_metrics()`를 사용한다. 아직 새 결과가 없어 호출하지 않았다. 다른 라이브러리의 metric 정의로 대체하지 않는다.

RCA는 실제 RWR 순위로 MAP@5/MAP@10/MRR을 계산해야 한다. `LEMMA_Metrics.py`를 실행하면 코드 안에 고정된 rank를 집계할 뿐이다. 이를 새 결과 평가 명령으로 안내하지 않는다. 실제 결과→평가 연결 및 집계 입력은 후속 Task에서 저자 자료를 기준으로 확정해야 한다.

## TASK_009: 논문 비교

표 1/2(벤치마크), 표 3(절제), 표 4(RCA)와 비교한다. Efficient-CDLMs는 10회 중 best, 나머지의 반복/집계는 미공개다. 비교 전 dataset hash, code hash, 모델 snapshot, 검색 corpus, 조건 차이, 실제 실행 로그를 연결한다. 논문 수치는 [REPRODUCTION_SPEC.md](REPRODUCTION_SPEC.md)에 비교 대상임을 명시하여 기록했다.
