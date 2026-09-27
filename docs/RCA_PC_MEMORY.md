# D08 — 전체 입력 PC 그래프 계산의 WSL 메모리 부족

2026-09-26. D07 로그 반복 생성과 다른 문제다. A안은 제안이며 아직 적용하지 않았다.

## 실패 단계와 확인된 사실

- TASK_046의 PR 20211203, 전체 51,529행·219열 PC 그래프 계산이 종료됐다. 마지막 기록은 Depth=2, node204/219다. 이 숫자는 전체 알고리즘 완료율이 아니다.
- 기존 실행 세션은 exit1로 끝났고 프로세스는 더 이상 존재하지 않는다. PC.npy·RWR·평가 결과는 생성되지 않았으며 CC는 시작하지 않았다. 원래 IN_PROGRESS 보고서는 별도 보존하고 외부 관측으로 중단 상태를 기록했다.
- 커널의 21:06:49(KST) 기록: `Out of memory: Killed process 714 (python)`. anonymous RSS 7,614,332KiB(약7.26GiB), 프로세스 swap 510,944페이지(약1.95GiB), 시스템 free swap=0이다. 이는 정상 완료에 필요한 최대량이 아니라 중단 직전 관측값이다.
- OOM 표에는 Relay(435)와 단일 대용량 Python PID714가 연속으로 나온다. 기존 WSL 내부 PID435/종료 세션과 일치하는 정황으로 PC 계산의 OOM 종료를 뒷받침한다. 강제 종료 때문에 Python traceback·최종 보존 검사는 실행되지 않았다.
- 당시 앞선 LLM 서버는 이미 종료된 뒤였고, OOM 프로세스 표에도 llama-server가 없다. 따라서 PC/LLM 동시 실행만 없애면 해결된다고 판단할 수 없다.
- WSL 관측 메모리 약7.89GiB, swap2GiB. Windows 총가용 물리메모리 약15.91GiB. C: 여유 약30.86GiB, E: 약402.64GiB(조사 시점). 사용자 .wslconfig는 없었다. 기본값 추정보다 실제 관측을 우선한다.

[실행/중단 보고서](evidence/rca_real_integration_20260926T100156831887Z.json). 커널 원문은 MATMCD_DATA/logs/setup/rca_real_integration_20260926T100156831887Z/kernel_after_interruption.txt에 보존했다.

고정 설치된 causal-learn의 FisherZ는 각 조건부 독립성 검정 결과를 메모리 사전 pvalue_cache에 저장한다(causallearn/utils/cit.py:73,168,180). 장시간 계산에서 메모리가 증가할 수 있는 경로지만, 종료 프로세스의 heap을 측정하지 못했으므로 이것만이 전부였다고 단정하지 않는다. 원본 캐시를 삭제하거나 코드를 교체하지 않았다.

## A — RAM 한도 유지, 디스크 swap 확대 후 동일 PC 재검증 (권장)

논문 조건·전체 Pod·전체 행·검정·PC 기본값·라이브러리를 그대로 두고 WSL 자원 설정만 바꾼다.

| 항목 | 제안 |
|---|---|
| WSL RAM | 8GB로 명시; 물리 RAM 한도를 늘리지 않음 |
| WSL swap | 현재 관측2GiB → 16GB |
| 파일 위치 | E:\연구\MATMCD_DATA\environments\wsl_swap.vhdx |
| 변경 파일 | C:\Users\goo84\.wslconfig 생성; 기존 상태/변경 이력 보존 |
| 적용 시점 | 현재 로그/RAG 실행이 종료된 후. 다른 WSL 작업도 확인한 뒤 WSL 재시작 |
| 검증 | 원본 PC를 PR부터 같은 전체 입력으로 한 번 다시 계산; RAM/swap/진행 기록 |
| 추가 변경 | 자동 swap 증설·RAM 확대·캐시 교체·입력 축소 없음 |

예정 내용(아직 미적용):

```ini
[wsl2]
memory=8GB
swap=16GB
swapFile=E:\\연구\\MATMCD_DATA\\environments\\wsl_swap.vhdx
```

근거: 물리 RAM을 더 배정하면 Windows 여유를 줄이므로 먼저 유지한다. E:에는 swap 파일을 위한 여유가 있다. 디스크를 이용해 메모리 한계를 늦출 수 있지만 **16GB swap이면 완료된다는 근거는 아직 없다.** PC의 조건부 검정 수와 메모리 증가가 계속될 수 있다. SSD I/O와 실행 시간이 크게 늘고 Windows/WSL 반응이 느려질 수 있다. 저장된 부분 그래프/checkpoint가 없어 PC 계산은 처음부터 다시 해야 한다. 새로운 실행 기록으로 실패 이력을 유지한다.

[Microsoft WSL 설정 문서](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)에 따르면 memory/swap/swapFile은 WSL2 전역 설정이며 적용에 WSL 종료/재시작이 필요하다. 이는 다른 WSL 배포판에도 영향을 줄 수 있다. 승인 전 파일 생성·swap 배치·WSL 종료는 하지 않는다. 원복 시 생성한 .wslconfig와 swap 사용 상태를 확인하고 사용자 승인된 범위에서 처리하며 실행 중 파일을 삭제하지 않는다.

## 다른 후보

- B: 현재 PC 검증 보류, 승인된 로그/RAG 작업만 계속한다. 전체 RCA 준비 완료로 표시하지 않는다.
- C: RAM이 더 큰 별도 PC/서버에서 같은 고정 입력·코드·버전으로 PC를 검증한다. 예를 들어32/64GB급은 후보지만 최소 필요량은 미확인이다. 장비/비용/데이터 이동과 정확한 환경은 별도 결정이다.
- Pod·기간 축소, PC 깊이 제한, 검정 변경, 캐시 제거는 실험 조건/구현 변경이다. 이번 자원 대안에 자동 포함하지 않으며 사용자 Pod 축소 보류 결정을 유지한다.

## 현재 재현할 수 없는 부분

PC 그래프·RWR 기준선과 이를 입력으로 하는 후속 인과관계/RE/최종 RCA 순위는 미완료다. D07 로그 전용 presence1.5 검증과는 독립이며, 새 로그/RAG 생성은 현재 설정으로 계속 진행한다. D08은 전역 자원 설정/재시작과 추가 장시간 계산을 수반해 별도 결정을 요청한다.
