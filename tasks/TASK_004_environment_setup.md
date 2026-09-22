# TASK_004 - 원본 의존성 환경 구성

## 목적
공식 Python 3.11 및 requirements.txt의 버전을 유지하여 설치 가능성을 확인한다.

## 작업 항목
- [x] Windows·GPU·메모리·WSL 확인
- [x] WSL Python 3.11 준비
- [x] requirements.txt 무변경 설치
- [x] 패키지 일관성 및 API 호출 없는 import 검사
- [ ] 누락 패키지의 저자 사용 버전 및 Graphviz binary 확보

## 확인 사항
저자의 Python 패치 버전, 운영체제 상세 버전 및 하드웨어는 미공개다. 설치를 위해 의존성을 바꾸지 않는다.

## 결과
Python 3.11.13 격리 환경에 원본 140개 pin 일치, 총 141개 패키지 설치 및 uv pip check 통과. 핵심/causal/agent import와 CUDA 12.6 GPU 인식 통과. chromadb, lxml, llama-index-embeddings-openai 및 Graphviz dot이 없어 전체 실행 환경은 BLOCKED다. 알려지지 않은 버전을 임의 추가하지 않았다. 로그와 freeze, `docs/evidence/setup_audit.json`에 실제 증거를 보존했다.

## 상태
BLOCKED
