# 작업별 개발 기록

2026-11-14부터 기능·검증·Docs를 작업별 feature 브랜치와 커밋으로 관리한다. 실제 결과와 원격 반영 여부를 분리한다. 운영 규칙은 `05-git-flow.md`다.

| 작업 | 브랜치 | 범위와 완료 조건 | 상태 |
| --- | --- | --- | --- |
| 기준선 통합 | 기존 `feature/carcue-mvp` → develop | SDK/앱/영상/문서 전체 이력을 보존해 통합, main 보존 | 로컬 통합 `137e905`, MVP 기준 `0c7b39d` |
| GF-001 작업 흐름 | `feature/git-flow-workflow` | Git Flow 규칙·작업 기록·PR 양식, 기존 규칙 보존 | 독립 커밋 후 로컬 develop 통합 완료 |
| GF-002 기본 CI | `feature/basic-ci` | 계약·백엔드 검증을 PR/브랜치 CI로 연결 | 계약/148개 UI 자원·백엔드 26개 로컬 통과, YAML 검사 후 로컬 통합. GitHub 실행은 별도 |
| GD-001 검수 가이드 등록 | `feature/reviewed-guide-import` | 공유 게시 정책, 검사/원자적 등록 CLI, API의 게시 불가 항목 차단, 아키텍처 결정 | 백엔드 117개·계약/148개 UI 자원·기본 DRAFT 카탈로그·CI YAML 로컬 통과. 실제 매뉴얼 등록 없음 |
| GF-003 CI context 수정 | `feature/ci-runner-context` | 최초 원격 실행에서 발견한 job env의 runner context 오류를 step env로 이동 | `5496b41`, develop 통합 `bfb548b`. 공식 범위/로컬 YAML 검사 후 GitHub Actions run 43566021842 성공, 계약·카탈로그·서버 회귀 단계 통과 |
| GD-002 앱 가이드 검증·캐시 | `feature/guide-cache-consistency` | API/캐시 공통 게시 검사, 성공한 빈 응답의 캐시 철회, 중복 원시 JSON·역순 응답 차단 | Android 구현 `b42bfb9`, JVM 31개·Pleos Debug 빌드 통과, 재리뷰 지적 2건 해소. SDK 기기 재시험·실제 자료 게시/AI 호출은 별도 |
| GD-003 공식 아이오닉 5 문 안내 | `feature/ioniq5-official-door-content` | 공식 2024 한국시장 NE1 매뉴얼 검토, 자체요약 3언어 등록, 정확한 판본/상태 규칙과 보존 장치 | 서버 133개·계약·4개 가이드 레코드·1개 규칙 검사 통과. 공식 원문/독립 AI 의미 검토. OEM·인간 전문가 검수 아님 |
| GD-004 SDK 상태별 공식 가이드 | `feature/sdk-contextual-door-guide` | 실제 SDK OPEN과 매뉴얼 안내 연결, 조건 재검사/현재 상태/재조회/출처/UX 차단, 기기 검증 도구 | 구현 `2e9087a`, core run03 43.685초 PASS·JVM42·155문구. 시각 오프셋 수정 `82a32b9`는 빌드/설치·정상 런처/실제GET0 확인, 추가 OPEN 재시험은 AVD503으로 미완료 |
| GF-004 Console 준비/연결 유지 | `feature/pleos-console-readiness` | 독립1초heartbeat·문/속도/페달/기어 DDS 준비 확인·실패 시 상태 복구 보강 | 구현 `aa7e8e3`. 실제503→준비후200 재현, 6초 주 작업 대기 중 유지. 최신 e9 APK run05 19.188초 PASS·전체 회귀140. GD-004의 최신 APK 전체 재시험 미완료 해소 |

사용자가 2026-11-14 develop과 작업 브랜치의 원격 push를 요청했다. 최초 터미널 push는 HTTPS 자격 증명이 없어 실패했고 GitHub Desktop의 기존 토큰도 만료돼 있었다. 이후 사용자 로그인 복구 뒤 Desktop을 통한 develop push를 완료해 원격 SHA `4b8b65b` 일치를 확인했다. CI 수정 통합본 `bfb548b`도 원격에 반영했다. 이전 작업 브랜치는 기존 SHA 그대로 게시하며 main `ba28cdb`를 보존한다. 연결된 GitHub API의 저장소 권한 표시는 실제 integration 쓰기 권한과 달랐고 ref 생성은 403으로 실패했으므로 Desktop의 정상 인증 경로를 사용한다. 자격 증명을 복사하거나 커밋 이력을 재생성하지 않았다. 기본 CI의 실제 범위와 재현은 `CI.md`를 따른다.

## 다음 제품 작업

`feature/reviewed-guide-import`에서 검수된 차량 가이드 등록·검증 흐름을 구현했다. `GUIDE_CONTENT_WORKFLOW.md`에 재현 명령과 게시 기준, `ARCHITECTURE.md`에 MVVM/UDF와 서버 Ports & Adapters의 적용 범위를 기록했다. PUBLISHED라도 프로필/매뉴얼/출처/번역/단계가 불일치하면 API에 노출하지 않는다. 기존 DRAFT/UNVERIFIED 자료는 보존했다.

`feature/guide-cache-consistency`에서 Android 게시 메타데이터 재검사와 성공한 빈 응답의 캐시 철회를 구현했다. raw JSON 단계에서 중복 식별자를 먼저 제외하고, 같은 차량/언어의 최신 요청만 캐시와 화면에 적용해 오래된 응답의 복원을 막는다. 캐시/정책은 순수 Kotlin으로 분리했다.

사용자 지시에 따라 Mock 화면 추가 단계에서 실제 제품 연동 개발로 진행한다. 공식 한국시장 2024 아이오닉 5 매뉴얼 자료와 두 절을 확인해 `ioniq5-ne1-2024-kr` 및 문 안내 1개(3언어)를 등록했다. 출처와 검토 범위는 `MANUAL_REVIEW_IONIQ5_2024_KR.md`를 따른다. 기존 미검수 개발 프로필은 보존한다.

`feature/sdk-contextual-door-guide`에서 실제 Pleos SDK와 자료를 연결했다. core run03에서 GET→OPEN callback→공식 안내→CLOSED callback/재조회→주행 제한/복귀→해제를 모두 확인했다. 후속 시각 오프셋 두 문자열 수정본의 전체 재시험은 AVD 설치 무결성 검증 시간 초과·패키지 서비스 지연·재기동 후 Console/DDS 비활성503으로 확정하지 못했다. 실패를 성공으로 바꾸거나 검증 설정을 끄지 않았다. 이미 설치된 동일 핵심 테스트를 사용해 재시도했으며 원문·기존 결과·실험 후보를 모두 보존했다.

후속 `feature/pleos-console-readiness`에서 Console 비활성503을 재현하고 독립 heartbeat와 DDS 준비 대기로 복구했다. 최신 e9 APK의 실제 설치 SHA를 대조한 run05는 문 개폐·차량 표시·공식 안내·재조회·주행 제한/복귀·해제 및 Park/0/CLOSED 복구까지 19.188초에 완료했다. `PLEOS_CONSOLE_RECOVERY.md` 참조. 이전 실패 기록과 당시 판단은 유지한다.

AVD의 실제 SDK 수신과 실차를 구분하며 새 Mock 차량/가이드 시나리오를 추가하지 않았다. 다음은 실제 차량/다른 영역 검증 및 검수 콘텐츠 확대다. AI 키/모델과 외부 호출은 별도 단계다.

그 뒤 실제 AI·번역 연결은 서버 키/모델·검수 자료와 호출 증거를 갖춘 별도 feature로 진행한다. 미수신·미지원·오래된 값·주행 제한·이용 종료의 기존 동작을 유지한다.
