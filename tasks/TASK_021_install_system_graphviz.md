# TASK_021 - DEP-04 Graphviz B안 설치·검증

## 목적

사용자가 승인한 Ubuntu 제공 Graphviz를 설치해 공식 RCA의 PNG 출력 의존성을 준비한다. 저자 버전 동일성은 별도 A안으로 관리한다.

## 작업 항목

- [x] 사용자 B안 승인 확인: 2026-09-24
- [x] 정확한 버전·APT 모의 결과·출처·다운로드 해시 기록
- [x] Graphviz 및 제안한 의존성 9개만 설치, 기존 시스템 패키지 유지
- [x] dot 및 공식 visualize_graph의 인공 그래프 PNG 출력 검증
- [x] Python 201개·공식 소스 보존 확인
- [x] 환경 문서·Blocker 상태 갱신, A안 TODO 연결

## 확인 사항

대상 패키지는 graphviz=2.42.2-9ubuntu0.1과 같은 계열 libcdt5/libcgraph6/libgvc6/libgvpr2/liblab-gamut1/libpathplan4, libann0=1.1.2+doc-9build1, libgts-0.7-5t64=0.7.6+darcs121130-5.2build1이다. 직전 모의 결과는 추가 9개, 업그레이드·삭제 0개였다. 후보가 바뀌어도 다른 버전을 임의로 설치하지 않는다.

설치는 WSL Ubuntu 시스템에 적용한다. Python requirements·공식 코드·실험 입력은 변경하지 않는다. 소규모 인공 그래프 출력만 확인하며 PC·RWR·LLM·RCA 실험은 실행하지 않는다. 실제 설치 파일과 로그는 configs/paths.json이 지정한 외부 자산 루트에서 관리한다.

## 결과

2026-09-24 설치·검증 PASS. Graphviz를 포함한 시스템 패키지 9개 추가, 기존 시스템 패키지 변경·삭제 0개, Python 201개 및 공식 소스 37개 보존을 확인했다. DEP-04의 실행 의존성은 해결했다. 저자 동일성은 UNCONFIRMED이며 [TASK_022](TASK_022_graphviz_author_version.md)의 별도 TODO로 남긴다.

패키지 버전은 2.42.2-9ubuntu0.1, /usr/bin/dot의 실제 출력은 dot - graphviz version 2.43.0 (0)이다. 두 식별자를 같은 값으로 표기하지 않는다. Python graphviz 0.20.3 및 pydot 4.0.0은 그대로다.

공식 Utils/visualize.py의 visualize_graph를 3개 인공 노드·행렬로 실행해 405×131 PNG를 생성했다. 일반 WSL 사용자(uid 1000)에서도 통과했고 두 실행의 PNG SHA256이 같았다. 육안으로 B→A 화살표와 B—C 점선 및 세 노드 표시를 확인했다. 입력 행렬은 바뀌지 않았다. 실제 PC·RWR·RCA·LLM·API는 실행하지 않았다.

- [설정](../configs/graphviz_packages.json), [설치 도구](../scripts/setup_graphviz.py), [일반 사용자 검증기](../scripts/check_graphviz_runtime.py)
- [설치 증거](../docs/evidence/graphviz_install.json), [일반 사용자 검증](../docs/evidence/graphviz_runtime.json), [URL·버전·SHA256/SHA512 lock](../docs/evidence/graphviz_ubuntu_packages.lock.json)
- 외부 DEB 보관: raw_downloads/ubuntu_noble_graphviz_2.42.2-9ubuntu0.1
- 성공 로그·시스템 설치 전후 목록·인공 PNG: logs/setup/graphviz_20260924T120441708131Z

설치 도구는 대상 패키지가 이미 있으면 재설치하지 않고 중단한다. 완료된 이 PC에서 다시 설치할 필요는 없다. 필요한 재확인은 일반 사용자 검증기만 사용한다. A안은 별도 자료 확인·변경 승인 후 진행한다.

첫 시도 logs/setup/graphviz_20260924T120230506499Z는 다운로드·9개 DEB 해시 확인 후 simulate_local에서 exit 100, Unable to fetch some archives로 중단됐다. 실제 설치 명령은 실행되지 않았다. 로컬 파일을 APT 기본 archive cache 밖에서 지정한 상태에서 --no-download를 사용한 것이 원인이다. 같은 파일로 해당 옵션을 제외하거나 cache를 명시한 두 모의 실행은 모두 9개 추가·업그레이드/삭제 0개로 통과했다. 최종 설치 도구에서는 이 부가 옵션만 제거하고 정확한 로컬 DEB·버전·해시·설치 계획 검증을 유지했다. 원본 소스나 실험 조건을 바꾸는 조치는 아니다. 첫 실패 보고서·로그는 위 외부 경로에 보존한다.

## 상태

DONE
