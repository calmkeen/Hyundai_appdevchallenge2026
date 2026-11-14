# Git Flow 작업 규칙

2026-11-14. 사용자 요청에 따라 앞으로 개발을 작업별 브랜치·검증·커밋 단위로 진행한다. 이전 MVP 이력과 기존 브랜치는 보존한다. 도구 확장을 설치하지 않고 표준 Git 명령으로 운영한다.

| 브랜치 | 기준점과 역할 | 통합 대상 |
| --- | --- | --- |
| `main` | 제출·배포 기준. 검증한 release/hotfix만 반영 | 배포 태그 |
| `develop` | 검증을 마친 작업의 개발 통합 기준 | 다음 release |
| `feature/<task>` | 최신 develop에서 만든 기능·수정·문서 작업 하나 | develop |
| `release/<version>` | develop에서 만든 출시 후보. 검증·버전·출시 문서 정리 | main과 develop |
| `hotfix/<task>` | main에서 만든 출시 버전 긴급 수정 | main과 develop |

## 작업마다 반복하는 절차

1. `git status`, 현재 브랜치, 관련 코드/Docs를 확인한다. 사용자 변경이 있으면 보존하고 작업 파일을 구분한다.
2. 작업 범위·완료 조건을 `Docs/DEVELOPMENT_LOG.md`에 기록한다. 서로 독립적인 기능은 브랜치를 나눈다.
3. develop에서 `feature/<task>`를 만든다. 한 브랜치는 한 작업을 다루되 구현·검증·관련 Docs를 함께 포함한다.
4. 기능을 구현하고 해당 변경에 필요한 검사만 실행한다. SDK/AI 연동은 빌드나 등록 성공과 실제 수신/응답 증거를 구분한다.
5. 관련 파일만 stage하고 diff를 확인한 뒤 작은 의미 단위로 커밋한다. `feat:`, `fix:`, `test:`, `docs:`, `ci:`, `chore:` 접두사를 사용한다.
6. 검증이 끝난 작업은 develop에 `--no-ff`로 병합해 작업 경계를 남긴다. 이번 사용자의 Git Flow 요청에 따라 일상적인 로컬 develop 통합은 이 절차로 진행한다.
7. 결과 보고에 브랜치·커밋·검증·남은 조건과 원격 반영 여부를 남긴다. 로컬 커밋과 GitHub push/CI 성공을 같은 것으로 보고하지 않는다.

```bash
git status --short
git switch develop
git switch -c feature/<task>
# 구현하고 필요한 검증 실행
git add <관련 파일>
git diff --cached
git commit -m "feat: <변경한 동작>"
git switch develop
git merge --no-ff feature/<task> -m "merge: <완료한 작업>"
```

검증 실패나 미완료 항목이 있으면 그 상태를 기록하며 완료로 통합하지 않는다. 외부 SDK/AI/매뉴얼이 없어 진행할 수 없는 부분은 실제 연동으로 표시하지 않고, 독립적으로 완료할 수 있는 준비 작업을 별도로 나눈다.

## 원격과 출시

원격 반영을 요청한 작업은 feature 브랜치를 push하고 `.github/PULL_REQUEST_TEMPLATE.md`로 develop 대상 PR을 작성한다. CI 결과와 실제 SDK 수신 검증 결과를 각각 기록한다. GitHub의 브랜치 보호는 실제로 설정한 경우에만 적용됐다고 보고한다. 현재 로컬 규칙만으로 GitHub 보호/필수 검사가 활성화된다고 가정하지 않는다.

main 통합·출시 태그·배포는 출시 작업으로 따로 진행한다. 현재 debug 앱·예시 가이드·AI 미연결 상태를 배포 완료로 취급하지 않는다. 원본 시각화의 외부 사용 범위는 `PLEOS_VISUAL_SOURCE.md`를 따른다.

강제 push·이력 재작성·기존 브랜치/작업 삭제는 하지 않는다. SDK·AVD·키·DB·APK/영상은 기존 ignore 정책을 유지한다. 기존 LICENSE와 재사용 모델의 원본·라이선스 기록을 보존한다.

## 기준선과 다음 작업

기존 `feature/carcue-mvp`의 `0c7b39d`까지를 develop에 이력 그대로 통합했다(`137e905`). main과 기존 기획/탐색 브랜치는 보존한다. 이후 작업은 `feature/git-flow-workflow`, `feature/basic-ci`처럼 분리한다. 이전 Git 규칙은 `history/GIT_FLOW_BEFORE_TASK_BRANCHES.md`에 보존했다.

다음 기능 우선순위는 `DEVELOPMENT_ORDER.md`를 따른다. 첫 후속 제품 작업은 검수된 차량 가이드 등록·검증 흐름이며, 실제 매뉴얼/차종·시장 일치 검수와 AI 실제 호출은 별도 완료 조건으로 유지한다.
