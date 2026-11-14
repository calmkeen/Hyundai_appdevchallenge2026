# Git Flow 작업 규칙

- main: 제출·배포 가능한 안정 버전.
- develop: 검토 완료된 개발 통합.
- feature/*: 기능·문서 단위 작업.
- release/*: 제출 후보 점검·정리.
- hotfix/*: 안정 버전의 긴급 수정.

## 현재 작업
- feature/docs-tourism-concept: 새 기획 문서.
- feature/android-sdk-probe: SDK 검증용 기반 브랜치.
- 기존 main의 LICENSE를 보존한다.
- 모든 작업은 로컬 변경과 원격 반영 여부를 따로 보고한다.

## 협업
1. 작업 전 status와 현재 브랜치를 확인한다.
2. 기능·문서 변경을 작은 커밋으로 나눈다.
3. diff 및 비밀키·사용자 데이터 포함 여부를 점검한다.
4. 권한이 확보되면 feature 브랜치를 push하고 draft PR로 검토한다.
5. develop/main 병합과 배포는 명시된 승인 범위에서 수행한다.
6. 강제 push·히스토리 재작성·기존 변경 삭제는 임의로 하지 않는다.
7. SDK·에뮬레이터 이미지·빌드 산출물은 소스 저장소에 포함하지 않는다.
