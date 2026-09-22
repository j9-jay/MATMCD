# MATMCD 공식 실험 재현 준비

**현재 상태: 공식 코드·공개 자료·고정 패키지 설치 및 감사 완료. 논문 전체 실험을 동일 조건으로 실행할 준비는 미완료다.** 실제 실험, 모델/API 추론, 결과 평가는 실행하지 않았다.

사용자 제공 논문은 `Exploring Multi-Modal Data with Tool-Augmented LLM Agents for Precise Causal Discovery`(arXiv:2412.13667v2)다. [저자 공식 저장소](https://github.com/D2I-Group/matmcd) 소스를 변경 없이 보존하고, 공개 정보가 부족한 부분은 추측하지 않았다. 과거에 폐기한 구현·환경·결과를 재사용하지 않았다.

## 확인할 문서

- [논문/부록/공식 코드 재현 명세](docs/REPRODUCTION_SPEC.md)
- [확보한 데이터·모델·출처·예상 경로](docs/ASSETS.md)
- [실제 설치 환경과 검사 결과](docs/ENVIRONMENT.md)
- [실행을 막는 문제와 논문/코드 차이](docs/ORIGINAL_LOCAL_ISSUES.md)
- [환경 점검 및 향후 실행 순서](docs/RUNBOOK.md)
- [번호별 작업 현황](tasks/INDEX.md)

## 실제 폴더 역할

| 프로젝트 안 | 내용 |
|---|---|
| `official/matmcd/` | 원본 43개 파일. 소스·프롬프트·평가 코드·requirements·라이선스 보존 |
| `configs/` | 외부 경로, 입력 대응, 논문/코드 출처 manifest |
| `scripts/` | 설치, 원본 자료 다운로드, 파일 링크 구성, 실험 없는 점검 |
| `docs/` | 검증된 분석 및 작은 감사 증거 |
| `tasks/` | 번호별 실제 상태와 후속 TODO |

Git 저장소는 `E:\연구\MATMCD`, 외부 자산은 `E:\연구\MATMCD_DATA`다. 예시 폴더를 빈 채로 미리 만들지 않는다. 모델·체크포인트·실험 결과 폴더는 현재 생성하지 않았다. 설치 환경, 다운로드, 실제 분석 산출물 등 사용된 경로만 존재한다.

`origin`은 사용자 저장소 `https://github.com/j9-jay/MATMCD.git`를 유지한다. `upstream`은 저자 저장소다. 사용자 저장소의 기존 `.git`과 커밋을 보존하며, 재현 준비 파일은 `origin/main`에서 관리한다.

## 현재 확인 결과

- 공식 커밋 `ef2c3ecad0f5ddb9c3d20a8523c2c1043d213190`을 내보내고 모든 파일의 SHA256 일치를 확인했다. 논문 v2 직전 `1aa3596` 이후 실행 코드/requirements 변경은 없고 README와 웹페이지 변경만 있다.
- WSL2/Python 3.11.13에 공식 140개 고정 패키지를 동일 버전으로 설치했다. 전이 의존성 포함 141개 패키지의 일관성 검사 통과. PyTorch CUDA 12.6/GPU 인식 확인.
- 연속형 벤치마크 3종 CSV/정답, Asia/Child BIF, 공식 코드에 등장하는 LEMMA-RCA 5개 사례의 10개 ZIP을 확보했다. 다운로드 원본/해시 보존.
- 원본 입력 9개 누락, 누락 의존성 3종과 Graphviz, 외부 API 접근, 여러 논문/코드 조건 차이 때문에 end-to-end 준비 완료 판정을 하지 않았다.
- 실험 실행(TASK_007), 평가(TASK_008), 논문 비교(TASK_009)는 모두 TODO다.
