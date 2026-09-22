# TASK_002 - 공식 코드 보존 및 정적 감사

## 목적
사용자 Git 저장소를 유지하면서 저자의 공식 소스를 변경 없이 보존한다.

## 작업 항목
- [x] origin 보존 및 upstream 연결
- [x] 공식 커밋 ef2c3ecad0f5ddb9c3d20a8523c2c1043d213190 내려받기
- [x] official/matmcd에 원본 내보내기
- [x] 해시 검증 및 공개 구현 문제 기록

## 확인 사항
현재 공식 커밋의 실행 코드는 논문 v2 직전 커밋 1aa3596과 동일하며 후속 변경은 README 및 프로젝트 웹페이지다.

## 결과
가져온 ZIP과 공식 파일 43개의 SHA256 일치, Python 25개 파일의 문법 검사를 확인했다. 소스·requirements 무변경. `docs/ORIGINAL_LOCAL_ISSUES.md`에 오류와 불일치를 기록했다. origin 및 기존 사용자 커밋 보존. 재현 준비 파일의 Git 반영은 사용자 요청에 따라 진행한다.

커밋 전 추가 확인: 공식 파일 43개는 보관한 ZIP과 바이트 단위로 동일하다. upstream Git blob과 비교하면 텍스트 33개는 CRLF/LF 줄바꿈만 다르며, 줄바꿈을 제외한 내용은 동일하다. `.gitattributes`는 현재 export 바이트를 보존한다. 원본의 공백 및 줄바꿈으로 발생하는 `git diff --check` 경고는 코드 변경으로 정리하지 않았다. 프로젝트 작성 파일의 공백 검사는 통과했다.

## 상태
DONE
