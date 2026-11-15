# 작업별 개발 기록

2026-11-14부터 기능·검증·Docs를 작업별 feature 브랜치와 커밋으로 관리한다. 실제 결과와 원격 반영 여부를 분리한다. 운영 규칙은 `05-git-flow.md`다.

## 공식 기본 사용 안내 9개 · 2026-11-15

사용자가 충전·좌석/거울·화면/표시등의3주제×KO/EN/JA를 공식 매뉴얼로 검토·개발하도록 요청했다. AVD 재시험·유료 AI와 기존 제출 APK/영상 변경은 보류했다.

| 작업 | 브랜치 | 구현·검증 |
| --- | --- | --- |
| GD-005 AC 충전 | `feature/ioniq5-charging-guide` | `d15ca8e`. 공식 AC 시작 전·시작 확인3언어,3단계10주의. 독립 의미 대조·게시 검사7개·주제 회귀43 통과 |
| GD-006 좌석/일반미러 | `feature/ioniq5-seats-mirrors-guide` | `44a6a27`.5단계21주의·3언어, 조절 전 정차/부정/신체 부위/수동전동/미러거리 대조. 동일 게시·회귀 통과 |
| GD-007 클러스터 | `feature/ioniq5-display-guide` | `a8226c6`.3단계3언어, 밝기 정상 설명은본문/READY·서비스·파워다운주의 보존. 동일 게시·회귀 통과 |
| GD-008 공통 연결 | `feature/guide-expansion-integration` | `18dd6de` topic/실제door binding 분리, `1927cbc`/`d3ef3e6` 합성·기존door fixture독립화, `072c321` 새9개 전체답변핀/범위검증. 전체606·UI194/4정책 통과 |

초안·독립 수정 요청·최종 대조를 QA에 보존하고 게시3개씩만 각content/guides에 추가했다. 신규센서/제어는없으며 기존문3JSON과closing-bundle은그대로다. 카탈로그13개(게시12/초안1)·실제HTTP9조회/36저장번역/9범위밖거절·DB0/0/0을 확인했다. actual모델/SDK/AVD0, 기존서버재시작0이다. 실제/Mock·남은기기시험은 `GUIDE_EXPANSION_VALIDATION.md`를 따른다.

세주제 feature의 원격SHA와 Basic/Android CI 성공을 확인했다. 최종통합 feature와develop도 push후정확SHA·CI로 별도확인한다. main과고정release는변경하지않고 기존APK5ef/영상638/PDF3a9/ZIP79의네해시를재확인했다. 구제출APK는고정release의서버/content와짝으로재현한다.

## 1차 제출 준비 · 2026-11-15

사용자가 오늘 밤 APK·영상·GitHub·기획서를 메일로 제출하며, 최종 전달 위치와 발송 방법은 저녁에 알려주기로 했다. AVD 재시험은 뒤로 미루고, 단계6의 남은 429 응답 처리와 단계7의 재현 가능한 납품을 진행한다. 유료 AI/생성 질문 번역 보류·기존 원본·main을 유지한다.

| 작업 | 브랜치 | 구현·검증 |
| --- | --- | --- |
| CI-002 Android 원격 빌드 | `feature/android-ci-validation` | `2209a65`. JDK17·Gradle8.10.2·API35, demo JVM/Mock APK·출처 메타데이터·7일 artifact. 실제원격success/JVM127, Pleos compile은명시적수동선택이며미실행 |
| LC-003 429 재시도 대기 | `feature/http-retry-cooldown` | `852272f`, CI병합 `b016e12`. Retry-After·단조시계·세션/언어범위·전송/재시도차단·3언어남은초. JVM25/계약UI193/서버1, 원격Basic475·Androidsuccess. 새기기시험미완료 |
| DV-002 제출 묶음 검증 | `feature/submission-bundle` | `a614082`/`8b5003f`. 네자산명시핀·증거연결·제품소스동일성·원본보존·덮어쓰기거절·ZIP/체크섬. 독립리뷰/합성27개, 원격Basic502·Androidsuccess |
| PL-001 현재 기획서 | `feature/first-submission-plan` | 실제SDK시연과개발기능·후속기획구분. 편집원문은Docs, 검토PDF와전체페이지검수는output/pdf에서관리 |

검증된 시연 APK5ef560ba…와 34초 영상638c1f54…를 한 쌍으로 고정한다. 제출 소스는 동일 제품 코드의 release 후보로 분리하며 429 새 개발본은 별도로 develop에 통합한다. 실제 진행 중 응답 세 경계는 미완료로 유지한다. 메일·최종 제출·main 병합·출시 태그는 실행하지 않는다. 최종 SHA/검증은 `VALIDATION_REPORT.md`, `FIRST_SUBMISSION_PACKAGE.md`를 따른다.

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

그 뒤 AI·번역 연결은 아래 무료 로컬 AI feature로 진행했다. 유료 연결은 사용자 요청으로 보류했다. 미수신·미지원·오래된 값·주행 제한·이용 종료의 기존 동작을 유지한다.

## 무료 로컬 AI 작업 · 2026-11-14

사용자 지시에 따라 유료 AI 연결을 보류하고 공식 배포 Ollama/Qwen3를 작업공간 내부에 설치했다. 키나 유료 계정을 사용하지 않는다. 기존 Mock·SDK·영상·음악·main을 보존했다.

| 작업 | 브랜치 | 구현·검증 |
| --- | --- | --- |
| AI-001 검수 단위와 로컬 모델 | `feature/local-ai-manual-grounding` | `50b9830` 실제 로컬 어댑터·근거 선택·저장 번역, `49fdffd` 감지 언어 enum·Console 초기 준비/종료 보강 |
| AI-002 질문 용어 보존 | `feature/local-ai-translation-terms` | `8ecc5d3` 판본별 질문 용어집·누락 차단·회귀24개. backend362 통과, 실제 API04에서 JA→KO 수식어 생략을 안전 거절한 이력 보존 |
| AI-003 실제 앱 연결 | `feature/android-local-ai-session-flow` | `656937f` 불변 요청·재시도·세션·제공자/검수 상태 표시·실제 앱 시험. JVM52·Pleos APK/testAPK 빌드 |
| AI-004 자유 번역 보류 | `feature/local-ai-question-deferral` | `90f83fe` 질문→명령 의미 오류 확인 후 실제 Ollama QUESTION 기본off·개발 opt-in. 전체370개 회귀 통과 |
| AI-005 최종 실행 증거 | `feature/local-ai-validation-evidence` | API·앱·SDK 실제 결과 및 재검증 도구·Docs. 기능 통과와 선택 출력의 의미 검토를 분리 |

처음 로컬 모델이 만든 안내 번역에서 금지문 역전이 확인돼 ANSWER/GUIDE를 완전한 저장 검수 단위 번역으로 제한했다. 이후 질문 번역의 수식어 생략과 저장 번역 제목의 잘못된 검수 전 표기를 발견해 보완했다. 실패 결과도 `output/qa/`와 담당 Docs에 보존하며, 과거 실패를 성공으로 바꾸지 않는다. 실제 SDK는 전용 AVD 값이며 실차·안전벨트 센서 연결을 뜻하지 않는다.

최종 기본 앱 run08은 **66.646초/5단계/실제모델3회**로 통과했고 저장 번역2개는 추가 호출이 없었다. 자유 질문 번역 기본 보류는 실제3언어 HTTP 무호출로 확인했다. 앱/서버 세션데이터0건·Console복구·lease종료·AVD정상종료를 확인했다. 임의 자유번역 품질 완료를 주장하지 않는다. 원격 push는 실제 반영 SHA와 별도로 확인한다.

## 오프라인 안내와 종료 복구 · 2026-11-14

| 작업 | 브랜치 | 구현·완료 조건 |
| --- | --- | --- |
| OF-001 최초 오프라인 기본 안내 | `feature/offline-reviewed-guides` | 같은 프로필/판본/언어의 동봉 검수 안내, 캐시/서버 출처 구분, 영속 빈 스냅샷·열린 안내 철회, 유료 AI 보류 유지. 새 QA 패키지의 첫 설치와 서버 중단/복구를 실제 Pleos SDK에서 검증 |
| SE-001 종료 뒤 서버 삭제 복구 | `feature/session-deletion-recovery` | 연결 복구·늦은 세션 생성의 bounded 단일 삭제 작업, 명시 DELETED 응답 확인, 프로세스 재시작 후 큐 복구·본문 없는 최소 삭제 정보·공용 가이드 보존 검증 |

위 작업은 구현 중이며 아래 완료 기록 전에는 통과로 계산하지 않는다. 기존 앱 데이터·캐시·AVD와 무료 AI 정책을 보존한다. SDK는 전용 AVD의 실제 API이며 실차 시험과 구분한다. 네트워크 시험은 CarCue 서버 프로세스 중단·재시작이며 차량 SDK나 인터넷 전체 장애의 재현으로 확대하지 않는다.

OF-001 구현 `e816d61`, 철회 navigation 보완 `684556c`/`e7c58ad`, SE-001 구현 `54bab55`를 보존했다. 통합 JVM84·QA run04 13+3단계(57.131/6.889초)·실제 로컬 모델1회·DB각1→0, 기본 앱 SDK20.285초를 확인했다. 최종테스트·문서 커밋 후 develop에 no-ff 통합하고 작업별 feature와 develop을 원격 반영한다. 원격 반영과 CI는 실제 SHA/결과로 따로 확인한다.


## 공식 원문·고객지원·UX 연결 복구 · 2026-11-14

| 작업 | 브랜치 | 구현·검증 |
| --- | --- | --- |
| LK-001 공식 지원 등록 | `feature/official-support-catalog` | `d6f0e52` + `2c15c99`. firecrawl_local 실제공식본문확인·KR WEBSITE1개·등록IDaction·출처/시장/판본검증. 서버416 |
| UX-001 연결 소유권·복구 | `feature/ux-service-recovery` | `04e7b7f`. 실제DISCONNECTED 관측 뒤 epoch/attempt분리·freshGET·bounded3회·stop정리. 정책10합성회귀와 최종실제앱 정상왕복/주행제한검증 구분 |
| LK-002 실제 앱 외부 연결 | `feature/official-resource-actions` | typed source/citation·답변고유request binding·latest세션/UXguard·공식AVD debug브라우저호환·결과/경로구분. 통합JVM110·링크8회76.488초·SDK9단계20.564초 |

기존코드·게시가이드·이미지·음원·영상·main과 모든실패증거를 보존한다. 유료 AI/생성질문번역 보류를 유지했다. 최종 무료AI호출의 출처/action실행과 질문의 완전한 의미적합성을 구분하며 상세는 `OFFICIAL_RESOURCE_APP_VALIDATION.md`를 따른다. 작업별검증·커밋 후 develop에 no-ff 통합하고 feature/develop을 원격반영하며 실제 remoteSHA와 CI결과를 확인한다.

## AI 답변 주의문 보완 · 2026-11-14

| 작업 | 브랜치 | 구현·검증 |
| --- | --- | --- |
| AI-006 완전한 주의문 답변 | `feature/ai-complete-caution-answers` | `c8af3b1`. 등록 문 안내의 전체 bundle/3언어 payload·text 핀, 불완전 답변/과거 캐시 차단, GUIDE 보존. backend462·신규정책82·계약 통과 |
| AI-007 실제 호출·SDK 화면 | `feature/ai-caution-validation` | 공식 두 절 재대조, 실제 API9개/ANSWER6방향, 실제 SDK 앱3답변/3저장번역73.640초·물리 화면, 독립 의미 검토·실패 증거·재현 도구/Docs |

기준 develop `7852159`, 기존 main `ba28cdb`와 게시 가이드3파일·앱 자산·영상·음원을 보존했다. 기존 step2 누락 사례를 같은 질문으로 검증하고 답변 후보/서버 검증/저장 번역/캐시 경로에서 모두 전체 주의문을 요구한다. 유료 AI·생성 질문 번역 기본 보류는 유지한다. API/앱/대역과 실제 모델 선택/저장 문자열을 [AI_CAUTION_VALIDATION.md](AI_CAUTION_VALIDATION.md)에 구분한다. 작업별 검증·커밋 뒤 develop에 no-ff 통합하고 두 feature와 develop의 실제 원격 SHA·CI를 확인한다.

## 다국어·차량 UX·이용 종료와 시연 갱신 · 2026-11-15

`DEVELOPMENT_ORDER.md`의 단계 6 → 7 순서로 진행한다. 유료 AI·생성 질문 번역 기본 보류, 기존 게시 가이드·영상·음원·AVD userdata를 보존한다.

| 작업 | 브랜치 | 범위·완료 조건 |
| --- | --- | --- |
| LC-001 답변·번역 언어 경계 | `feature/multilingual-assistant-boundaries` | `78bd767`. 실제 답변/번역 언어 표시, 과거 결과 혼동 방지, 동의·stale UI action 재검사, 가이드 복귀 보완. JVM127·UI191 |
| AI-008 질문 번역 보류 캐시 | `feature/question-deferral-cache-boundary` | `d6be741`. 과거 개발 opt-in 번역을 현재 보류/MOCK 서버에서 재생하지 않음. 같은 DB 재시작 6개 포함 backend468개 통과 |
| LC-002 실제 SDK 세션 검증 | `feature/sdk-session-validation` | showcase03 194.754초 PASS: KO/EN/JA 실제ASK3·저장번역3·SDK개폐/이미지·Drive/Park·가이드 복귀·세션삭제. **진행 중 요청의 3개 경계 시험은 AVD 준비/관측 실패로 미완료** |
| DV-001 최신 앱 소개 | `feature/sdk-intro-refresh` | `27b0616`/`5bdc5c1`. 같은 최신 SDK APK/프로세스의 연속 원본에서 34초 편집·기능당2초·기존 음악 PCM exact·첫 문구 유지. 독립 시각 검토 PASS |

구현/정적 회귀와 실제 모델/SDK/녹화 성공을 분리했다. 상세 결과와 실패 이력은 `SDK_SESSION_VALIDATION.md`, 영상은 `SDK_LIVE_INTRO.md`를 따른다. 최종 서버DB0/0/0·Console 복구·lease 종료·AVD 정상 종료를 확인했다. 단계6의 추가 진행 중 경계 기기 시험은 남아 있으며 완료로 세지 않는다. 작업별 feature를 유지하고 develop에 no-ff 통합·원격 반영 후 실제 remote SHA/CI를 별도 QA 기록으로 확인한다. main은 변경하지 않는다.

## 진행 중 AI 응답 경계 재시험 · 2026-11-15

사용자 잠금 해제 후 위 4개 작업 feature와 develop `736dc95`의 실제 원격 SHA 및 CI5개 success를 확인했다. `feature/sdk-inflight-recovery`에서 남은 locale/Drive/이용 종료 경계를 별도 진행한다. 기능 APK는 보존하고 ActivityScenario의 반복 idle barrier를 없앤 계측 APK, 실제 AVD 화면/사용자/CarService/SDK 준비, 실제 무료 모델 처리시간과 경계 전후 관측, 세션 삭제·Park 복구까지 완료 조건으로 둔다. 최신 실행 결과 전에는 통과로 세지 않으며 유료 AI·생성 QUESTION 번역 보류와 기존 userdata/실패 증거를 유지한다.

후속 test-only 보완은 실제 경계 뒤의 Compose 프레임 진행, 동일 원래 Activity의 실제 focus/화면 증거, 캡처 뒤 늦은 결과 재검사, 안전 SDK 실패 코드 수집이다. APK 빌드·독립 소스 검토·관측기 회귀7개를 통과했지만 run01~13 전체는 FAIL로 보존한다. 기능 앱5ef560ba…는 변경하지 않았다. 별도 공식 Stable runtime 비교와 호스트 Clamshell Sleep 교란, 삭제/복구 결과를 `SDK_INFLIGHT_RECOVERY.md`에 기록하며, 추가 실제 세 경계 완료 전에는 완료로 올리지 않는다.

검증 도구 `37b26c7`과 no-ff develop 통합 `71cd181`의 실제 원격 SHA·CI success를 확인했다(backend475/UI191, 기기 시험은 CI 미포함). 검증 도구 통합과 실제 SDK 경계 미완료를 구분한다. 남은 SystemUI/CarService 부팅 진단·실행 증거는 새 `feature/pleos-runtime-diagnostics`에서 계속한다. main·앱 기능 코드·기존 AVD 데이터와 실패 원본을 보존한다.

후속 진단은 같은 공식 이미지의 독립 factory 데이터·host GPU/원해상도·기준선 CPU/태그·kernel 로그까지 분리했으나 준비 gate를 통과하지 못했다. 에뮬레이터 종료 뒤에도 별도 host CPU 표본 idle0%와 약25GB swap을 확인했다. 다른 앱을 임의 종료하거나 OS 보안을 바꾸지 않고, 여유 있는 호스트 상태를 확보한 뒤 실제 세 경계 재시험을 이어가는 조건을 기록한다. 처리 중 End 미실행과 과거 부분 증명의 한계를 그대로 유지한다.
