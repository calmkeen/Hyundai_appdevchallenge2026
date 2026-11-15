# CarCue 구현 현황

2026-11-15 (KST). 최종 검증 명령과 결과는 `VALIDATION_REPORT.md`를 따른다. 코드 작성과 실제 외부 연동 완료를 구분한다. 현재 확정된 SDK 시연은 `SDK_SESSION_VALIDATION.md`, 후속 in-flight 시험 복구와 호스트 부하로 남은 기기 검증은 `SDK_INFLIGHT_RECOVERY.md`, 새 소개 영상은 `SDK_LIVE_INTRO.md`에 기록한다.

## 1차 제출 시제품과 추가 개발

사용자 요청으로 AVD 재시험·유료 AI를 보류했다. 제출 검토 초안은 **기존 검증 APK5ef560ba… / 같은 SDK 앱의 34초 영상638c1f54… / 고정 GitHub 소스 / 현재 기획서**다. 네 파일의 묶음·해시·실행 조건은 `FIRST_SUBMISSION_PACKAGE.md`, 기획 내용은 `FIRST_SUBMISSION_PLAN.md`에서 관리한다. 메일 발송과 최종 전달 위치는 아직 사용자 지시 전이다.

새 `feature/http-retry-cooldown`은 Retry-After에 따른 남은 초 표시와 전송·재시도 차단을 구현했다. 로컬 순수정책25개·서버 한도1개·UI193 계약, 실제 원격 Basic475와 Android demo JVM/Mock APK 빌드가 통과했다. 이 기능은 기존 시연 APK에 포함되지 않으며 새 화면/429의 기기 검증은 남아 있다. 상세는 [별도 개발 브랜치의 HTTP_RETRY_COOLDOWN.md](https://github.com/calmkeen/Hyundai_appdevchallenge2026/blob/feature/http-retry-cooldown/Docs/HTTP_RETRY_COOLDOWN.md)를 따른다.

`feature/android-ci-validation`은 JDK17/Gradle8.10.2/API35의 원격 demo JVM/Mock APK 빌드·해시/메타데이터·보고서 artifact를 제공한다. 실제 첫 원격 JUnit127개를 확인했다. Pleos 컴파일은 수동 선택이며 이번에는 실행하지 않았다. SDK 수신/실제 모델/기기 시험을 대신하지 않는다. 제출 도구는 독립 리뷰·합성27개와 원격 Basic502/Android 빌드를 통과했다. 각 커밋의 실제 CI는 `VALIDATION_REPORT.md`를 따른다.

현재 제출 준비와 전체 제품 완료를 구분한다. **처리 중 응답의 기기 경계3건**, 추가3주제×3언어의9개 안내, 모바일QR·RTL/접근성·추가 차종/실차 시험은 남아 있다. 아래 표와 날짜별 결과는 해당 시연 APK·당시 바이너리의 검증 범위이며 새 개발본 전체 기기 검증을 뜻하지 않는다.

| 단계 | 구현 | 검증 / 남은 조건 |
| --- | --- | --- |
| 1 환경 | 기존 작업 보존, 인계 문서·자산·계약 보관, 분리한 빌드 SDK, Git feature 브랜치 | JDK 17·SDK 2.3.2·전용 AVD 준비 및 앱 설치·실행 확인 |
| 2 제품 뼈대 | Compose S01~S11, 반응형 차량 메뉴, 실제 버튼·입력·검색·단계 이동, 프로필/언어 분리, 앱 내 Pleos 원본 차량·안전벨트 이미지와 문 프레임 전환·가이드 이미지 | Mock APK/UI 검증 결과는 검증 보고서 참조 |
| 3 한 상태 연동 | 문 위치의 권한·Capability·GET·Listener·해제 어댑터 | 전용 AVD에서 실제 Capability·GET·0→1→0 콜백·차량 이미지 개폐/복귀 픽셀 비교 통과. 동일 Listener 해제와 release 확인 |
| 4 상태 안내 | 실제 SDK OPEN/ROW_1_LEFT와 정확한 프로필·판본·언어의 공식 문 안내 연결. 수신 상태·재조회·원문 표시, 미수신/오류/오래된 값/주행 제한 차단 | 최신 showcase03에서 GET·개폐 callback·차량 픽셀 변경/복귀·실제 Drive/Park·해제 확인. 이전 APK의 SDK9단계 회귀 및 Console503 복구 run05는 해당 바이너리의 역사적 근거로 구분 |
| 5 AI·번역 | FastAPI·SQLite, 무료 Ollama/Qwen3 실제 호출, 전체 주의문 답변 단위·출처/캐시 검증, 저장 안내 번역 | 최신 SDK showcase03의 3언어 실제 ASK3·저장 ANSWER3, 추가 번역 모델0회. backend468/JVM127 통과. 이전 API9/저장6방향은 AI_CAUTION_VALIDATION 참조. 유료 AI·생성 질문 번역 기본 보류 |
| 6 언어·UX·종료 | 48개 언어·50개 지역 후보/RTL 구조, UI/답변/번역 원문·대상 언어 분리, 새 맥락의 동의 재확인, 중첩 가이드 복귀, 제한 시 입력/긴 안내 차단, 종료/삭제 재시도 | 191개 3언어 UI 자원 검사, JVM127. 실제 showcase03 194.754초 PASS로 언어 선택·동의 초기화·단계 복귀·Drive/Park·종료 DB0 확인. 진행 중 응답의 locale/Drive/종료 경계 추가 시험 late01~07은 아직 미완료 |
| 7 재현 | Wrapper, 버전 고정, 실행 안내, 계약·회귀 테스트, 단일 SDK APK/프로세스 촬영 및 새 편집 경로 | showcase03 단일 연속 원본과 새 34초 소개 영상 검증. 14기능 각2초·실제 언어 선택 장면·기존 음악 PCM 일치. 실제 호출과 선택 사례의 의미/시각 검토를 구분 |

## 최신 확정 기준 · 2026-11-15

다국어·동의·응답 적용/복귀 경계 구현은 `78bd767`, 생성 QUESTION 번역의 과거 opt-in 캐시 차단은 `d6be741`이다. backend **468개**, Android JVM **127개**, 계약·3언어 UI **191개** 검사와 Pleos 앱/테스트 빌드를 통과했다. 캐시 재시작 회귀의 provider HTTP는 대역이며 실제 모델 호출 수에 포함하지 않는다. `MULTILINGUAL_ASSISTANT_BOUNDARIES.md`, `QUESTION_DEFERRAL_CACHE.md`를 따른다.

후속 관측기 회귀 7개를 더한 `feature/sdk-inflight-recovery`의 checkpoint `02947ed`는 원격 SHA 일치 및 CI **475개 통과**를 확인했다(run `43676020770`). 실제 파일·thread의 audit 관측 회귀이며 SDK·모델 호출 시험은 CI에 포함하지 않는다. 선행 feature4개와 develop `736dc95`도 실제 원격 반영·CI5개 success를 확인했다. 후속 기기 시험 상태는 위 복구 문서를 따른다.

검증 도구 최종 `37b26c7`과 no-ff develop 통합 `71cd181`도 실제 원격 반영·CI success를 확인했다(backend475/UI191). 기능 APK5ef560ba…는 변경하지 않았다. 추가 실제 세 경계 시험은 **미완료**다. run01~13과 별도 초기 AVD 준비 실패를 보존하며, AVD 종료 뒤에도 호스트 CPU idle0%·높은 swap이 관측돼 여유 있는 호스트 상태에서 재시험이 필요하다. 언어/Drive의 부분 증명과 정상 시연을 이용 종료의 진행 중 시험 성공으로 계산하지 않는다. 상세와 Mock 구분은 `SDK_INFLIGHT_RECOVERY.md`를 따른다.

최신 실제 SDK 시연 `sdk-session-showcase-20261115-03`은 **194.754초 PASS**다. 기능 APK `5ef560ba…`와 촬영 당시 테스트 APK `82409ca5…`의 설치 해시를 대조했다. 같은 APK/프로세스에서 실제 ASK3·저장 ANSWER 번역3, 문 개폐와 차량 이미지 복귀, 실제 UX Drive/Park, 언어 표기/동의/가이드 단계 복귀와 종료 후 sessions/results/history **0/0/0**을 확인했다. 이 결과를 3언어×3문맥 API9 전체나 이전 SDK9단계 회귀의 최신 APK 재실행으로 확대하지 않는다.

추가 `late01~07`은 실패 기록을 보존하며 **완료로 판정하지 않는다**. `late07`은 Keyguard 준비 단계에서 거절돼 모델 호출0회다. 요청 처리 중 locale/Drive/이용 종료 뒤 늦은 응답 차단의 실제 기기 전체 통과는 남아 있다. 해당 보호 로직의 JVM 통과와 정상 응답 후 종료 시연 통과를 이 경계 시험의 성공으로 대체하지 않는다.

## 실제 동작과 Mock의 구분

- **실제 앱 기능:** 네이티브 화면 이동, 언어 카탈로그 검색·선택, 차량 프로필 변경 시 문맥 삭제, 가이드 단계 복귀, 오류 표시, 로컬 세션 종료, API 클라이언트.
- **다국어 어시스턴트 경계:** 기존 답변의 실제 언어와 번역 원문/요청 대상/완료 대상을 구분한다. 언어 변경은 옛 번역 결과만 정리하고 원문·초안을 보존하며 새 맥락에 동의를 다시 받는다. 화면 scope와 UX를 실행·응답 시점에 재검사하고 ASK/번역/언어 복귀 대상을 분리한다. 정상 실제 흐름은 showcase03에서 확인했으며 추가 in-flight 경계의 실제 기기 통과는 아직 없다.
- **종료와 서버 삭제 복구:** 앱 범위 단일 처리기가 foreground·연결 복구·수동 확인·늦은 세션 생성을 처리한다. 기본 최대3회 재시도하며 request/VM 취소와 독립이다. 명시 DELETED 응답/정확한 만료 확인 전에는 최소 삭제 자격 정보와 대기 표시를 유지한다. 공용 가이드와 프로필은 지우지 않는다. 실제 서버 중단/새 프로세스/동일DB삭제 확인을 run04에서 완료했다.
- **공식 원문·고객지원:** 차량/판본/등록 ID와 현재 세션·UX를 누를 때 재검사한다. KO/EN/JA에서도 KR/ko 원문 범위를 유지한다. 이전 공식 연결 APK에서 AVD 기본 Browser2의 debug 호환 경로·앱 task 복귀8회/GET1→9·SDK9단계(Drive 외부action거절 포함)를 확인했다. 당시 JVM110/서버416. 설치 해시와 한계는 `OFFICIAL_RESOURCE_APP_VALIDATION.md` 참조.
- **UX 연결 복구:** attempt별 Car/manager/listener와 epoch, fresh GET 전 unknown, 1/3/10초 최대3회 복구·stop취소. 정책/latecallback10개는 합성 회귀, 실제최종앱은 정상왕복/Drive/Park흐름을 검증했다. 강제Car서비스장애주입 완료와 구분한다.
- **실제 서버 기능:** HTTP API, 세션 토큰 소유 검사, 만료·삭제, 요청 중복 방지, 프로필/버전/검수 상태에 따른 검색, 출처 ID 대조, 원문 추출 검증, 요청 제한.
- **가이드 등록 기능:** 검사 CLI와 조회 Catalog가 프로필·매뉴얼·언어·번역·출처·단계의 동일한 게시 정책을 사용한다. 중복 식별자와 충돌, 잘못된 URL/출처/검수 상태를 거절하며 기존 파일을 덮어쓰지 않는다. 초기 CLI feature는 합성 테스트로 확인했고, 후속 공식 자료 feature에서 출처 대조와 AI 보조 의미 검토를 거쳐 문 안내 3언어를 게시했다. `GUIDE_CONTENT_WORKFLOW.md` 참조.
- **앱 가이드 검증·캐시:** API·동봉·캐시 안내에 같은 게시 조건을 적용한다. 빈 응답도 영속 스냅샷으로 보존해 철회가 동봉 안내로 복원되지 않게 한다. BUNDLED/CACHE/SERVER 출처와 guideConnection을 구분한다. 신규 설치의 최초 오프라인 안내를 지원하며, 구버전 갱신 설치의 모호한 캐시는 보수적으로 차단한다. 동일 범위의 열린 가이드·오래된 버튼·질문/언어 복귀 경로에도 철회를 반영한다. JVM84 및 실제 QA run04 16단계가 통과했다. 단위/실제 기기 검증의 범위는 OFFLINE_SESSION_VALIDATION.md 참조.
- **실제 SDK와 공식 가이드 연결:** `DoorGuidePolicy`로 PLEOS·SUPPORTED/VALUE·60초 이내·raw1/OPEN·ROW_1_LEFT·UX 허용과 프로필/매뉴얼/언어/게시 자료가 모두 맞을 때만 관련 버튼을 표시한다. 실제 SDK GET0→callback1→공식 가이드/두 출처→callback0→재조회 GET0→실제 UX 제한/복귀→해제는 당시 APK의 run05에서 검증했다. 앱은 문 제어 API를 호출하지 않는다. `SDK_OFFICIAL_GUIDE_VALIDATION.md`, `PLEOS_CONSOLE_RECOVERY.md` 참조.
- **실제 UX 제한 API:** 초기 GET false/0, 주행 조건 callback true/80, 주차 복귀 callback false/0을 전용 AVD에서 확인했다.
- **실제 SDK 데이터:** `pleos` flavor에서 전용 AVD의 문 상태 Capability·GET·변경 콜백을 수신했다. 실차 값이 아니라 전용 AVD가 제공한 값이다. 2026-11-14 재시험에서 실제 callback 1·0에 따라 앱 내부 차량 이미지의 8,083픽셀 변경과 최초 닫힘 이미지로의 정확한 복귀를 확인했다. 세션 종료·unregister·release까지 통과했다. `SDK_VISUAL_RETEST.md` 참조.
- **MOCK 차량 데이터:** `demo` flavor의 모든 문 상태. 주차/제한 시나리오도 Mock이며 실제 CarUxRestrictions 수신이 아니다. APK·화면에 MOCK을 표시한다.
- **MOCK AI:** 기본 서버는 답을 생성하지 않고 `NO_RELIABLE_SOURCE` 또는 번역 불가를 반환한다. `mode=MOCK`가 표시된다.
- **실제 무료 로컬 AI:** Mac의 Ollama 0.40.16/qwen3:4b를 서버에서 호출한다. ask는 검수 단위 ID를 선택하고 완전한 원문·주의문·출처를 반환한다. ANSWER/GUIDE는 동일 판본 저장 번역이며 추가 모델 호출이 없다. QUESTION은 실제 의미 오류로 기본 보류했다. 명시적 개발 옵션에서만 동적 생성·UNREVIEWED로 시험하며 언어·숫자·용어 누락 검사도 전체 의미를 보증하지 않는다. 실제 기능 통과와 사례별 의미 검토는 별도 기록한다.
- **주의문 누락 보완:** 등록된 2024 KR 문 안내는 본문·두 단계·각 주의문을 순서대로 묶은 단위만 선택 가능하다. 누락/해시/판본/출처 불일치는 거절하고 과거 부분 답변 캐시도 차단한다. 공식 두 절을 다시 읽고 3언어 API9개·저장 ANSWER6방향, 실제 SDK 앱3답변/3저장번역·물리 화면을 확인했다. 다른 주제나 모든 자유 질문의 의미 적합성 완료로 확대하지 않는다. `AI_CAUTION_POLICY.md`, `AI_CAUTION_VALIDATION.md` 참조.
- **보류한 OpenAI 어댑터:** 기존 구현과 HTTP 대역 테스트를 보존했다. 사용자 지시에 따라 유료 호출과 자동 전환은 사용하지 않는다.
- **가이드 시연과 실제 안내:** 기존 개발용 화면 탐색 예시는 demo flavor에 보존하고 SDK 앱에서는 숨겼다. SDK 앱은 게시된 공식 자료의 자체 요약을 조회한다. 인계 템플릿은 DRAFT로 비게시하며, 기존 소개 영상의 예시는 이전 APK의 기록이다.
- **앱 내 차량·안전벨트 시각화:** 사용자가 지정한 `carcue-pleos-sdk.mp4`의 원본 렌더 장면을 표시한다. 문 상태별 21개 이미지 프레임을 전환하며 실시간 SDK 3D 위젯은 아니다. 안전벨트는 착용 상태 미연결 안내 이미지다. 기존 사진·OpenX 모델·라이선스는 보존하고 기본 화면에서 제외했다. `NATIVE_VISUALS.md`, `PLEOS_VISUAL_SOURCE.md` 참조.
- **소개 영상과 실행 증거:** 최신 `live-sdk-intro-20261115-03`은 showcase03의 같은 `pleos` APK/프로세스 연속 원본에서 편집한 34초 영상이다. 공식 문 안내·실제 무료 ASK·저장 번역·언어 선택·SDK 문 개폐·실제 주행 제한/종료를 14기능 각2초로 보여주며 기존 음악 PCM을 유지한다. 첫 문구는 ‘언제, 어디서든, 평소와 같은 경험을.’이다. 벨트 센서는 미연결이고 차량은 사전 렌더 프레임이다. `SDK_LIVE_INTRO.md` 참조. 이전 79.742초/20장면·실제 AI 호출 없음의 영상과 APK는 `SDK_FULL_APP_SHOWCASE.md`, `APP_INTRO_VIDEO.md`에 역사적 기록으로 보존한다.
- **프로필/공식 안내:** 두 개발용 프로필은 UNVERIFIED로 보존했다. 새 `ioniq5-ne1-2024-kr`는 공식 2024 한국시장 매뉴얼과 문 열림/끼임 주의 범위를 대조한 사용자 선택 프로필이다. SDK의 차종/VIN/옵션 자동 인증을 뜻하지 않는다. 문 안내 1개를 ko/en/ja로 게시했으며 OEM 승인·인간 전문가 검수나 전 차종/전 주제 검수 완료를 뜻하지 않는다. `MANUAL_REVIEW_IONIQ5_2024_KR.md` 참조.

`mode=LIVE`는 서버 처리 모드이며 차량 데이터의 진위를 보증하지 않는다. 각 값의 `source=PLEOS/MOCK`를 따로 표시한다.

## Mock 언어 범위 변경 · 2026-11-13

사용자 요청에 따라 Mock 선택 목록을 `ko-KR`, `en`, `ja-JP`로 제한했다. `catalog.json`의 `mock_visible`로 목록을 관리하며 48개 후보와 RTL 확장 구조는 보존한다. 일본어 UI 초안과 서버의 자료 부족·일시 불가 고정 응답을 추가했다. 언어 변경은 판매지역·차량 사양이나 이미 열린 가이드의 원문을 바꾸지 않는다. 당시 일본어를 포함한 모든 차량 가이드의 검수 상태는 PLANNED였으며, OpenAI 실제 호출을 추가한 작업은 아니었다.

넓은 시연 화면은 차량 디스플레이를 재현하는 Pleos 전용 AVD 환경이다. 실제 SDK 검증 환경은 2560×1440이며, Mock 회귀 환경은 1280×800이다. 일반 Android 기기에서 실행 가능한 demo 빌드와 차량용 SDK를 사용하는 pleos 빌드를 구분한다.

## 아직 완료되지 않은 제품 요구

1. 실차·다른 영역·차종의 수신과 다른 지역 UX 정책 검증.
2. 이번 한국시장 2024 아이오닉 5 문 안내 범위를 넘어선 차종·연식·판매지역·옵션 검토. 충전/좌석·거울/화면·표시등 콘텐츠와 전문 검토 확대.
3. 등록된 문 안내의 닫기 전 주의 누락은 전체 bundle 정책과 3언어/문맥 시험으로 보완했다. 다른 주제·임의 자유 질문의 관련성과 주의문 정책 확대, 생성 질문 번역의 의미·부정·순서·부품명 검토는 남아 있다. 실제 로컬 모델을 연결했어도 모든 질문의 정확성을 보증하지 않는다. 유료 AI 연결은 사용자 요청으로 보류했다.
4. 오프라인 검수 안내·서버 중단/복구·종료 뒤 삭제 큐 복구는 전용 AVD와 로컬 서버에서 검증한다. 실제 인터넷 회선 장애·실차·저장소 장애까지 확대하지 않는다. 구버전 미기록 갱신 설치는 동봉 fallback을 차단하므로 유효 캐시나 온라인 동기화가 필요하다.
5. ROW_1_LEFT / 0..1과 공식 문 안내의 OPEN 규칙은 최신 APK/전용 AVD에서 확인했다. Console 준비 실패를 보완해 추가 재시험을 완료했다. 다른 영역/상태의 의미와 매뉴얼 규칙 확대는 남아 있다.
6. 공식 AVD 개발 빌드에서 원문·지원8회 왕복/SDK새GET/주행중거절을 확인했다. 일반 출시 브라우저·다른 OEM/실차·웹페이지 전체 로딩 자동 검증은 남아 있다. `OFFICIAL_RESOURCE_APP_VALIDATION.md` 참조.
7. 일반 폰에서 QR 카메라 스캔 후 안내 웹/앱 진입. 현재 검증 범위는 차량 앱의 제한된 프로필 딥링크 처리이며 인증 페어링은 아님.
8. 실제 Pleos 디스플레이의 터치·초점·로터리·접근성·지역별 UX 제한. 일반 AVD 검증과 구분한다.
9. 실제 AI 처리 중 언어 변경·Drive·이용 종료 이후 늦은 응답이 다시 표시되지 않는 세 경계의 native 전체 통과. late01~07은 미완료이며 정상 시연·단위 시험 성공으로 대체하지 않는다.

여행·내비·음성·차량 제어·인증 폰 연결·외부 배포·공모전 제출은 수행하지 않았다.
