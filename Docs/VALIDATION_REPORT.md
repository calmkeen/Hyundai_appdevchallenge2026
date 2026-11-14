# 검증 결과

2026-11-15 (KST). 실차, 공식 전용 AVD의 실제 SDK, 일반 AVD의 Mock, 외부 AI 대역을 구분한다.

## 최신: 다국어·SDK·종료 시연과 소개 영상 · 2026-11-15

프런트 경계 구현 `78bd767`은 UI/답변/번역 원문·대상 언어, 맥락별 동의와 응답 적용, 가이드 → ASK → 번역 → ASK → 같은 단계 복귀를 분리한다. `d6be741`은 생성 QUESTION 번역이 기본 보류일 때 과거 opt-in 성공 캐시도 재생하지 않도록 한다. backend **468개**, Android JVM **127개**, 계약과 세 언어 UI **191개** 자원 검사 및 Pleos 앱/테스트 빌드를 통과했다. 합성 정책·provider HTTP 대역 회귀를 실제 SDK/모델 시험으로 계산하지 않는다.

`sdk-session-showcase-20261115-03`은 native **194.754초**, host의 functional/video/overall 모두 PASS다. 같은 설치 APK/앱 프로세스에서 한국어·영어·일본어 실제 ASK **3회**, 전체 주의문을 보존한 저장 ANSWER 번역 **3회**(추가 모델0회), SDK 문 개폐와 차량 픽셀 변경/정확한 닫힘 복귀, 실제 CarUX Drive/Park, 원문 언어 표시·새 맥락의 동의 초기화·가이드 단계 복귀·이용 종료를 확인했다. 종료 후 sessions/results/history는 **0/0/0**, Console은 Park/0/CLOSED이며 자체 lease 해제와 cleanup 오류0을 확인했다.

- 기능 APK: `output/apk/carcue-pleos-session-boundaries-debug.apk`, SHA256 `5ef560ba1a24e3ce206aeeb6f4f336018b6e8a182bec7214aabc5dd4a261479f`. 실제 설치본 pull 해시와 같다.
- 시연 검증 테스트 APK: `output/apk/carcue-pleos-session-showcase-validated-test.apk`, SHA256 `82409ca5409eebdd7ead1a02a5da4ffb768804089a84e303ec9814c2bb92b884`. 후속 late 관측용 테스트 APK와 구분해 보존한다.
- 실제 Mac Ollama `0.40.16`/`qwen3:4b`의 audit3개와 ASK 요청 hash를 1:1 대조했다. ASK는 등록 단위 선택 후 서버의 검토 문자열 조립이며, 번역은 같은 판본의 `STORED_GUIDE`다. 유료 AI·자동 전환·생성 QUESTION 번역은 호출하지 않았다.

연속 원본은 **199.981초/2560×1440**, 기능 장면14개다. 새 소개 영상 `live-sdk-intro-20261115-03`은 **34초/1920×1080/30fps**, 기능당2초와 실제 언어 메뉴 선택, 기존 무료 음악의 PCM exact 일치를 확인했다. 원본과 최종 편집은 별도 시각·의미 검토 기록에 연결하며 예전 APK/영상을 섞지 않았다. 실행·해시·원해상도 검토와 한계는 [SDK_SESSION_VALIDATION.md](SDK_SESSION_VALIDATION.md), 편집·음악·최종 영상 SHA는 [SDK_LIVE_INTRO.md](SDK_LIVE_INTRO.md)를 따른다.

**추가 late-response 경계 시험은 아직 미완료다.** late01~07의 실패를 보존하며, late07은 Keyguard 준비 단계에서 거절돼 모델0회다. 실제 모델 처리 중 locale/Drive/이용 종료 뒤 늦은 응답 차단의 세 경계가 native 전체 PASS했다고 쓰지 않는다. 일부 `Process crashed`는 host의 정리 force-stop 뒤 출력이므로 앱 Java 예외로 단정하지 않는다. 정상 응답 후 종료의 showcase 통과와 JVM의 scope/epoch 회귀는 이 추가 시험의 성공을 대신하지 않는다.

SDK 값은 공식 AVD 시뮬레이션이며 실차·차종/VIN 인증이 아니다. 안전벨트 센서는 미연결이고 앱 차량은 사전 렌더 프레임이다. 선택된 3언어 사례의 의미 검토를 모든 질문·언어의 품질이나 OEM·인간 전문가 인증으로 확대하지 않는다. 아래 날짜별 API9·SDK9단계·이전 촬영은 각 당시 바이너리의 역사적 검증이며 최신 APK에서 같은 전체 시험을 다시 수행했다는 뜻이 아니다.

## AI 답변 주의문 보완 · 2026-11-14

문 안내의 앞 단계 주의문이 빠지던 문제를 전체 본문/두 단계/모든 주의문을 묶는 정책으로 보완했다. 공식 매뉴얼 두 절을 `firecrawl_local`로 다시 읽고 한국어·영어·일본어 × 첫 단계/두 번째 단계/문맥 없음 **실제 API9개**, 저장 ANSWER **6방향**, 실제 SDK 앱 **3답변+3저장 번역/73.640초**를 확인했다. 최종 앱 SHA는 `8e4ff19f…`다. 앱 6단계의 Compose/기기 전체 화면과 출처/검수 표기를 대조했다. backend462·JVM110·계약/185자원·빌드 통과. 유료 AI와 생성 QUESTION 번역 보류를 유지한다.

실제 Ollama는 등록 단위를 선택하고 서버가 기존 검토 문자열을 조립한다. 번역은 저장 안내다. API9개에는 SDK값을 넣지 않았고, 실제 앱은 공식 AVD의 SDK로 시험했으며 실차와 구분한다. 초기 도구 실패·이전 부분 답변·native01의 너무 이른 물리 캡처도 보존했다. 범위/정확한 APK·시험 hash/정리 결과는 [AI_CAUTION_VALIDATION.md](AI_CAUTION_VALIDATION.md)를 따른다.

## 공식 원문·지원·UX 연결 · 2026-11-14

최신 APK `9d947d11…`로 실제 앱 원문/지원 **8회 왕복76.488초**, fresh SDK GET1→9·가이드2단계 유지·실제 무료 모델1회를 확인했다. 같은 설치본의 SDK **20.564초/9단계**는 문 개폐/차량 이미지/가이드/재조회/Drive에서원문·지원dispatch0/Park복귀/해제를 통과했다. JVM110·서버416·UI185문구/계약이 통과했다. 실차와 Mock 대역, AVD Browser2 debug호환, 페이지 로딩과 질문 의미 적합성 한계를 `OFFICIAL_RESOURCE_APP_VALIDATION.md`에 구분했다.

실패 run01~05를 보존했다. 초기 foreground/SystemUI 실패 뒤 데이터 보존 cold boot, DEFAULT 없는 stock브라우저호환, app-task재선택, UX연결복구를 단계별로 보완했다. 최종8회 실행 성공은 자유질문 전체정확성 통과를 의미하지 않는다. 원격게시와 CI는 실제 commit/SHA로 별도 확인한다.

## 오프라인 안내·종료 복구 · 2026-11-14

최종 전용 QA 설치의 run04는 **57.131초 + 새 프로세스 6.889초**, 총16단계 통과다. 실제 Pleos SDK 문 GET/OPEN·CLOSED callback, KO/EN/JA 동봉·서버 안내와 EN 캐시, 서버 중단 시 AI 실패·저장 안내 연결, 정상 생성 세션의 오프라인 종료→프로세스 재시작→동일 SQLite 서버 복구→실제 DELETE 확인과 sessions/results/history 각1→0을 검증했다. 모델은 무료 로컬 Ollama/Qwen3를1회 실제 호출했고 유료 AI·생성 질문 번역은 보류했다.

기존 앱 com.carcue.app의 최종 APK `9dea39807f7ecb545784e84da489b81c044fb4a61e92f596cd42fb4870d696ce`도 SDK 전체 회귀 **20.285초/8단계 통과**했다. 실제 설치 해시·차량 픽셀 변경/복귀·공식 안내·재조회·Drive 주행 제한/Park복귀·unregister/release·fixture Park/0/CLOSED 복구를 확인했다. 기본 패키지의 기존 데이터는 지우지 않았다.

JVM **84개 통과**, UI177 문구/계약/가이드4레코드·상태규칙1개 검사 통과. 서버철회·손상·쓰기실패·늦은POST·비정상2xx/202는 단위/계약 시험 범위이고 실제 기기의 모든 장애 주입을 주장하지 않는다. 기존 demo의 Mock과 이번 전용 AVD 실제 SDK 및 실제 로컬 HTTP를 구분한다. 자세한 해시·16PNG 독립검토·시행착오·재현 명령은 `OFFLINE_SESSION_VALIDATION.md`를 따른다.

run01 성공 및 run02 Console 준비 실패/run03 후반 진입 실패/같은앱 추가진단을 보존했다. 마지막 run04와 기본 패키지 SDK 회귀는 자체 cleanup이 통과했다. 보조 warmup helper의 종료1/close확인불가와 emulator launcher 종료137은 별도 한계로 기록했다. 종료 명령OK/ADB장치 제거·기존userdata보존을 확인했으며 완전한 clean process exit0으로 확대하지 않는다. 원격 push·CI 결과는 별도 확인한다.

## 무료 로컬 AI와 최종 Pleos 앱 · 2026-11-14

사용자 요청으로 유료 OpenAI 연결은 보류했다. Mac의 공식 Ollama 0.40.16/qwen3:4b를 실제 실행하며 API 비용·키·유료 자동 전환은 없다. 모델은 APK에 포함하지 않는다. 실제 API/앱의 성공·실패 원기록과 사례별 의미 검토는 `LOCAL_AI_INTEGRATION.md`, `LOCAL_AI_APP_VALIDATION.md`를 따른다. 기존 영상·음악은 변경하지 않았다.

- 전체 backend **370 passed, 1 warning, 9.65초**: `output/qa/live-ai-20261114/backend-question-deferral-tests-20261114T100213Z.log`. 앞선 용어 검증 단계는364개였다. 앞선 sandbox 실행의 임시 HTTP bind 9오류는 별도 실패 로그에 보존했고 localhost 서버 사용 권한으로 재실행했다. 기존 AnyIO deprecation warning은 남는다. 테스트 대역과 실제 모델 호출은 구분한다.
- Android JVM **52개 통과**, Pleos 앱/계측 APK 빌드. 계약·3언어 UI168 문구·가이드 레코드4개(게시3·초안1)·SDK 상태 규칙1개 검사 통과.
- 기본 서버의 실제 앱 run08 **66.646초/5단계 PASS**: 3언어 ask와 저장 ANSWER/GUIDE 2건, 실제모델3회·저장번역 추가호출0·출처·제목·세션삭제. 서버 sessions/results/history 모두0, Console복구·lease종료·AVD정상종료까지 확인했다. 자유질문번역 기본보류도 실제3언어 요청/모델0회로 확인했다.
- 최종 앱 SHA `ddbca88ce3f522872ee35c90a0a5b7875fcc1664d411a28e983e0b89dc960a1f`: 실제 SDK 전체 회귀 **23.192초** 통과. 문 개폐/차량 시각화/공식 안내/재조회/주행 제한/복귀/리스너해제/Console복구. 실행 `official-guide-local-ai-final-20261114-02`는 AI 호출이 없다.
- `ask`는 완전한 검수 단위 ID 선택, ANSWER/GUIDE는 같은 판본의 저장 검수 번역이다. 동적 안내 번역의 금지문 역전 실패 후 이 경계를 적용했다. 생성 QUESTION 번역은 수식어 생략을 실제 확인했고 엄격 시험 API04/05가 실패했다. 누락 출력은 본문 없이 거절하며 품질 완료로 보고하지 않는다. 명시적 guarded 시험 성공도 자유 번역의 의미 정확성 통과를 뜻하지 않는다.
- 전용 AVD가 제공한 실제 SDK 값이며 실차·안전벨트 센서·차종/VIN 자동 식별·OEM/인간 전문가 인증은 포함하지 않는다.


## 검증 상태

| 구분 | 명령/환경 | 결과 |
| --- | --- | --- |
| 서버/도구 회귀 | `.venv/bin/python -m pytest backend/tests -q` | 최신 468개 통과. 생성 QUESTION 보류의 같은 DB 재시작/과거 캐시 차단 포함. 실제 모델 호출과 대역 회귀 구분 |
| 가이드 카탈로그 | `.venv/bin/python scripts/import_guides.py check --json` | VALID, 공식 문 안내 3언어 PUBLISHED + DRAFT 1개 = 4개 레코드 |
| 공식 매뉴얼 자료 | 포털 연식/시장/DocID 대조, HTML 및 PDF 인쇄 2-7/4-21 시각 대조, ko/en/ja 독립 의미 검토 | 한국시장 NE1/2024 범위 확인. AI 보조 검토이며 OEM/인간 전문가 검수 아님 |
| 상태-가이드 규칙 | `scripts/check_contracts.py` | 1개 OPEN/ROW_1_LEFT 규칙의 스키마·프로필/판본·언어별 게시 가이드/관련 property 통과 |
| 이전 GitHub Actions | develop `bfb548b`, run `43566021842` | 해당 SHA의 실제 원격 success. 최신 로컬 변경의 push/CI 성공으로 확대하지 않음 |
| Android 단위 | `:app:testDemoDebugUnitTest` | 최신 127개 통과, 실패/오류/건너뜀0. 합성 boundary/복귀 정책과 실제 기기 시험 구분 |
| 최신 SDK/AI 통합 시연 | `PleosSessionBoundariesTest.connectedShowcaseFlow`, showcase03 / 앱5ef560ba… / 테스트82409ca5… | 194.754초 PASS. 단일 APK/프로세스·3언어 ASK3/저장3·SDK 개폐/픽셀·Drive/Park·복귀·종료 DB0 |
| 추가 in-flight 경계 | `lateResponseBoundaries`, late01~07 | 미완료. locale/Drive/종료 전체 PASS 없음. late07은 Keyguard 준비 거절/모델0 |
| 이전 SDK 공식 가이드 전체 | `PleosOfficialGuideTest`, run05 / 앱e9ab702d… / 테스트2cc2ef14… | 당시 1개·19.188초 성공. 실제 설치SHA·GET0→OPEN/CLOSED callback/차량표시→공식 안내/재조회→실제 UX→해제·최종Park0CLOSED복구 |
| 이전 SDK 공식 가이드 core | run03 / 앱118b9c86… / 테스트2cc2ef14… | 1개·43.685초 성공. 후속 e9 APK는 위 run05에서 직접 재시험 완료 |
| Console 실제 회귀 | 전용 AVD 비활성→독립heartbeat/준비확인 | 같은 속도/페달0 요청503→200, 6초 주 작업 대기 중7회heartbeat/준비flag유지. run05 종료 뒤thread종료/lease종료오류없음 |
| 시험 환경 실패 보존 | run01/02/04 및 추가 renderer 후보 | 설치90초timeout, host lease503은도구보완후run03성공. 이후AVD PackageManager/Integrity timeout/DDS inactive503은성공으로보고하지않음 |
| Mock 기기 회귀 | API 35 / 1280×800 / `CarCueFlowTest` | 5개 통과, 원본 개폐 프레임 픽셀 차이·안전벨트 미연결·세 언어·기존 흐름 |
| 실제 APK 연속 촬영 | API 35 / `NativeShowcaseTest` | 1개 통과, 20개 실제 화면·개폐·세 언어 전환 |
| 이전 SDK 앱 전체 촬영 | `PleosShowcaseTest`, 전용 AVD/사용자 10 | 당시 1개 통과, 79.742초, 같은 APK/프로세스 20개 장면·4회 실제 변경 콜백. 실제 AI 호출 없음 |
| 이전 실제 SDK 기기 회귀 | Pleos 2.1 / API 34 / SDK 2.3.2 / Service 2.3.22 / `PleosSdkTest` | 당시 1개 통과, 16.747초. 실제 callback 0→1→0과 차량 이미지 픽셀 변경·복귀 |
| 이전 SDK 전체 검증 도구 | `.venv/bin/python scripts/validate_pleos.py` | 해당 당시 Capability·GET·양방향 콜백·차량 픽셀·영상·unregister·release 통과 |
| 앱 빌드 | `assemblePleosDebug` | 최신 기능 APK5ef560ba… 빌드·showcase03 설치 해시 일치. 이전 demo/Pleos APK도 보존 |
| 기기 테스트 빌드 | `assembleDemoDebugAndroidTest`, `assemblePleosDebugAndroidTest` | 성공 |
| 계약 | `scripts/check_contracts.py` | 기존 Schema/예제·공식 상태-가이드 규칙 1개·191개 세 언어 UI 문자열 키/치환 변수 검사 통과 |
| 최신 앱 소개 영상 | `live-sdk-intro-20261115-03`, 실제 APK 단일 원본·AVFoundation 검증 | 34초·1920×1080·30fps, 14기능 각2초·실제 언어 선택·기존 음악 PCM exact·별도 시각 검토 |
| 인계 패키지 | SHA256SUMS 전체 대조 | 일치 |

최종 기준 JDK는 Temurin 17.0.21+9 ARM64, Gradle 8.10.2, AGP 8.8.2, Kotlin 2.0.0이다. compile/target SDK 35, min SDK 28이다.

다음 단락과 날짜별 기록은 초기 feature 당시 결과다. 검수 가이드 등록 feature는 API에서 불일치·미검수·중복 레코드 차단, CLI의 반복 등록·충돌·번역 분리·경로 이탈 방지·입출력 실패 시 보존을 검증했다. 테스트의 VERIFIED 프로필과 example.test 자료는 합성 fixture이며 기본 content에 반영하지 않았다. 당시 계약 3종·148개 세 언어 UI 자원 검사 및 CI YAML 파싱도 통과했다. 해당 서버 변경만으로 SDK/AI 실제 외부 연결을 재시험하거나 성공 판정하지 않았다.

앱 가이드 캐시 feature는 순수 Kotlin 게시 정책, 실제 File 캐시, coroutine API 대역으로 검증했다. 정상 레코드와 malformed 중복 레코드가 섞인 경우 모두 차단하고, 새 빈 응답 뒤 늦은 응답이 도착하거나 이미 쓰기 중인 이전 요청이 있어도 최종 캐시를 복원하지 않음을 확인했다. `org.json` 플랫폼 변환의 기기 시험 및 새 APK의 SDK 수신 재시험은 하지 않았다.

새 APK는 `output/apk/carcue-pleos-guide-cache-debug.apk`, SHA-256 `0f340dc97a8bab0094869db8828b6ce7bd27051312ba5186bf698f4724d4f4ec`다. Android 소스 커밋은 `b42bfb9`이며 빌드/시험 요약은 `output/qa/git-flow/guide-cache-build.json`에 남겼다. 기존 영상·촬영 APK 별칭은 보존했다. 캐시 키가 바뀌므로 첫 온라인 갱신 전 이전 오프라인 가이드는 사용하지 않는다. 디스크 자체가 삭제/쓰기를 거부하면 같은 프로세스에서는 예전 캐시를 차단하지만 재시작 후 철회까지 보장할 수 없다.

세 언어로 Mock 범위를 조정한 뒤 서버 26개·Mock 기기 3개·계약 검사를 다시 통과했고 두 APK를 재빌드했다. 일본어 홈과 세 언어 선택 캡처를 육안으로 확인했다. SDK·CarUx 수신과 Android 단위 시험은 같은 날 언어 변경 전에 확보한 결과이며, 이번 변경에서 재실행하지 않았다.

앱 내 시각 요소를 추가한 뒤 demo·pleos·기기 테스트 APK를 빌드했다. Mock 회귀 3개에는 3D 열림·닫힘·미수신·오래된 값과 가이드 사진 검사도 추가해 통과했다. 3D 가림을 다듬은 최종 APK로 `NativeShowcaseTest`의 19개 실제 UI 동작을 통과하고 연속 녹화했다. SDK 수신과 서버 코드는 이번 UI 변경에서 수정하지 않았다. UI 문구 129개의 세 언어 누락·치환 변수를 검사했다.

## 이전: 공식 SDK 문 안내 연결 · 2026-11-14

당시 앱e9ab702d…/테스트2cc2ef14…로 run05가 19.188초 통과했다. Console 독립 heartbeat와 DDS 준비 확인을 보완해 이전503 미완료 범위를 해소했다. 실제 SDK 문 개폐·차량 픽셀 변경/복귀·공식 안내/출처·재조회·주행 제한/복귀·구독 해제와 최종 Console 상태 복구까지 확인했다. 정상 런처 물리 표시도 같은 APK SHA에 연결했다. 상세는 `PLEOS_CONSOLE_RECOVERY.md`, 이전 APK 이력은 `SDK_OFFICIAL_GUIDE_VALIDATION.md`를 따른다. 기존 소개 영상은 아래 이전 APK의 기록으로 보존한다.

## 이전: 전체 기능을 같은 SDK 앱에서 촬영 · 2026-11-14

SDK `pleos` 앱에서 차량·언어 선택부터 문 상태, 가이드 목록/단계, 질문, 영어·일본어 전환, 이용 종료까지 20개 장면을 연속 촬영했다. `PleosShowcaseTest` 1개가 79.742초에 통과했다. 설치 APK SHA256과 전달 APK의 일치, 녹화 시작/종료 직전 PID 27585의 일치, 모든 장면의 `source=PLEOS`를 확인했다. 실제 GET 0 → 한국어 callback 1→0 → 영어 callback 1 → 일본어 callback 0 → unregister → release의 순서를 검사했다. 차량의 닫힘 복귀 PNG는 최초와 정확히 일치한다. KR 프로필·가이드 단계 복귀·종료 후 프로필/값 삭제도 확인했다.

SDK 개발 빌드에서 기존 가이드 화면 예시를 열 수 있게 하고 예시·검수 자료 준비 중임을 세 언어로 표시했다. SDK 차량 저장소/GET/Listener와 제어 권한은 바꾸지 않았다. 새 APK/테스트 빌드는 `pleos-full-showcase/build.txt`, 148개 UI 자원의 세 언어/치환 변수 검사는 `contracts.txt`에 저장했다. 차량·안전벨트 원본 22개 PNG의 APK 바이트 일치 검사도 통과했다. crash 버퍼는 비어 있다. 이 변경의 새 전체 흐름 시험과 과거 Mock/SDK 시험은 구분한다.

최종 `carcue-full-sdk-intro.mp4`는 34초·1920×1080·30fps다. 기능 장면 14개는 모두 같은 SDK 앱 원본에서 2초씩 잘랐고, 입력을 한 개로 제한해 demo APK 장면이 섞이지 않게 검사한다. 첫 문구는 ‘언제, 어디서든, 평소와 같은 경험을.’로 바꾸고 마무리도 같은 메시지로 맞췄다. 원본/설치 APK/검증 JSON/편집 계획/이미지 자산의 해시를 대조했다. 시작·SDK 개폐·안전벨트·가이드·질문·영어/일본어 선택과 홈·마무리 17개 시점을 디코딩해 육안 확인했다(`pleos-full-showcase/intro-video-check.txt`).

음악은 기존 외부 원곡·12초 시작·gain 0.32·페이드를 유지했다. AAC 디코딩은 34초·2채널·44,100Hz, peak 0.23239, RMS 0.019323, 클리핑 0이며 5,997,600바이트의 PCM이 이전 영상과 정확히 같다(`intro-audio-check.json`). 이전 혼합 소개·SDK/Mock 원본과 이전 APK는 보존한다. 자세한 원본·시험·재현은 `SDK_FULL_APP_SHOWCASE.md`, 편집 표는 `APP_INTRO_VIDEO.md`다.

모든 기능이 SDK 연결 앱에서 실행되는 것과 가이드 콘텐츠/AI 연결 상태는 구분한다. 가이드는 debug UI 예시, 안전벨트 센서 미연결, 실제 AI 호출 없음이다. 물리 차량 센서·검수된 매뉴얼·AI 답변 품질을 새로 검증한 것은 아니다. 서버/Android 단위/기존 Mock 기기 결과는 이전 시험이며 이번에는 같은 SDK 앱의 전체 흐름을 직접 시험했다.

## 이전: 실제 SDK 장면을 반영한 소개 영상 · 2026-11-14

`carcue-sdk-app-intro.mp4`는 34초·1920×1080·30fps다. 7–13초의 닫힘 GET·열림 callback·닫힘 callback, 13–15초의 안전벨트 안내는 위에서 검증한 실제 pleos APK의 SDK AVD 녹화다. 다른 차량 선택·가이드·질문·세션 종료와 한국어/영어/일본어 전환은 기존 demo APK 실제 녹화를 유지했다. 기능 장면은 모두 2초다. 각 SDK 장면은 ‘Pleos SDK 수신 · 전용 AVD’, demo 장면은 ‘MOCK 데이터’를 표시한다.

렌더 전 두 입력 MP4·설치/전달 APK·SDK 성공 증거 JSON과 모든 증거 파일·동봉 차량/안전벨트 PNG 해시를 검사했다. SDK 영상은 CarCue 앱 영역만 crop/확대하며 시스템 차량 패널을 넣지 않는다. 기존 단일 입력 편집기를 출처별 입력·좌표·표시를 받도록 보완했다. 근거를 결과 JSON의 `sources`, `sdk_validation`, `segments`에 저장한다.

최종 영상 16개 시점에서 시작, SDK 닫힘·열림·닫힘 전환, 안전벨트, 가이드·질문 준비 중, 영어·일본어 선택/홈, 마무리를 디코딩하고 육안 확인했다(`sdk-intro-video-check.txt`). SDK 장면에서 검은 여백이 남은 첫 편집은 앱 영역 비율을 맞춰 수정한 뒤 재검수했다. 전체 기능당 약 2초와 양방향 차량 변화가 보존된다.

음원은 기존 Scott Buckley 원본 SHA256·12초 시작·gain 0.32·페이드를 유지했다. 최종 AAC 디코딩은 34초·2채널·44,100Hz, peak 0.23239, RMS 0.019323, 클리핑 0이다. 디코딩한 PCM이 이전 34초 소개와 바이트 단위로 정확히 같음을 확인했다(`sdk-intro-audio-check.json`). 기존 소개·메타데이터·크레딧은 `archive-before-sdk-intro/`에 보존하고 원본 SDK/Mock 녹화는 변경하지 않았다.

이번 변경은 영상·출처 메타데이터·편집 코드와 Docs 수정이다. 앱/서버 코드는 바꾸지 않았으며 SDK 16.747초 통과와 Mock 기기 회귀·촬영 결과는 기존 검증을 재사용했다. 안전벨트 센서·외부 AI·실차 센서 검증을 추가한 것은 아니다. 자세한 편집 표는 `APP_INTRO_VIDEO.md`를 따른다.

## 실제 SDK 양방향 문 상태·앱 차량 시각화 · 2026-11-14

전용 Pleos AVD의 실제 SDK 2.3.2 / Service 2.3.22에서 `PleosSdkTest` 1개가 16.747초에 통과했다. 최초 GET 0(CLOSED), 공식 Virtual Console 변경에 따른 실제 callback 1(OPEN), 복귀 callback 0(CLOSED)을 확인했다. 세 단계 모두 `IS_MOCK=false`, `source=PLEOS`, SUPPORTED/VALUE와 수신 시각을 검사했다. 앱은 읽기·구독만 수행하며 콘솔 입력은 호스트 시험 도구가 변경한다.

앱 내부 차량 Image 노드를 캡처해 139,020픽셀 중 열림에서 8,083픽셀(약 5.81%)이 바뀌는 것을 확인했다. 다시 닫힌 캡처는 최초 닫힘 캡처와 픽셀·PNG SHA256이 정확히 일치했다. 단순 상태 문구 비교를 넘어 실제 렌더 결과를 검증했다. 종료 후 값/세션 삭제와 동일 Listener 해제·SDK release 반환도 확인했다. crash 버퍼는 비어 있다.

증거는 `output/qa/pleos-sdk-retest/`의 instrumentation, SDK/콘솔 로그, 앱/차량 캡처, `result.json`에 있다. 설치 base.apk와 현재 빌드/전달 APK SHA256 일치를 확인했다. 10.002초·2560×1440의 실제 AVD 연속 녹화에서 CarCue 안의 차량 개폐/복귀를 디코딩하고 육안 확인했다. 기존 Mock 소개 영상과 원본 `carcue-pleos-sdk.mp4`는 변경하지 않았다. 상세 재현·APK 경로는 `SDK_VISUAL_RETEST.md`를 따른다.

이전 실행 전 `Process crashed` 시도는 별도 보존한다. 이번에는 부팅 후 사용자 10에서 정상 앱 기동을 확인하고 설치·instrumentation·파일 수집 사용자를 일치시켜 완료했다. 이전 오류의 단일 원인을 확정한 것으로 보고하지 않는다. 서버·실차·안전벨트 센서·외부 AI·주행 UX 전환을 새로 검증한 결과는 아니다. UI는 기존 원본 프레임 전환이며 SDK 3D 위젯 이식이 아니다.

## 이전: 사용자 지정 Pleos 원본 차량·안전벨트 · 2026-11-14

사용자가 정확히 지정한 `carcue-pleos-sdk.mp4`의 안전벨트와 은색 차량 렌더 장면을 앱 내부 이미지로 넣었다. 입력 MP4의 SHA256은 `3657b7a2a8105066980b1f27ee3b78bb1e4dac57caa3383a01770cf446fa8a6e`로 유지한다. 차량은 19~20초의 21개 프레임, 안전벨트는 4초의 원본 부분이다. SDK 바이너리·원본 그래픽 리소스를 추출하지 않았다. 별도 공개 SDK 3D 위젯 연결이 아니라 원본 프레임 애니메이션이며, 안전벨트 착용 상태는 미연결이다.

demo·pleos와 두 테스트 APK 빌드가 성공했다(`pleos-reference-build.txt`, `pleos-reference-test-build.txt`). 두 전달 APK 안의 22개 PNG와 manifest가 저장소와 바이트 단위로 일치하고, 원본 MP4 해시·PNG 크기·개폐 프레임 차이를 검사했다(`pleos-reference-assets-check.txt`). 세 언어 145개 UI 자원과 참조/치환 변수 검사가 통과했다(`pleos-reference-contracts.txt`).

Mock 기기 시험 5개가 14.345초에 통과했다(`pleos-reference-flow-test.txt`). 실제 개폐 화면 픽셀 차이, 문 미확인 처리, 안전벨트 미연결 표시, 차종/시장 보존과 일본어, 기존 오류·UX 제한·가이드 복귀·로컬 HTTP Mock 왕복을 확인했다. 첫 픽셀 비교 실패는 테스트가 잠든 동안 Compose 시험 시계가 프레임을 진행하지 않는 문제였다. 실제 시간 동안 시험 프레임을 진행하도록 보완한 뒤 다시 통과했다. 홈·상태·일본어 캡처에서 원본 차량과 안전벨트 및 표시/버튼 경계를 육안 확인했다.

실제 APK 연속 촬영 1개가 49.646초에 통과했고 20개 장면을 기록했다. 전달 APK와 설치 base.apk 해시, 22개 원본 PNG/manifest의 바이트 일치를 대조했다(`carcue-native-run.json`). 기능 화면은 해당 APK 녹화에서만 가져왔다. 시작 카드도 동봉한 차량·안전벨트 PNG다. 차량 개폐 중간과 닫힘/열림, 안전벨트, 충전 가이드, AI 준비 중 표시, 영어·일본어 홈, 마무리 프레임을 디코딩하고 육안 확인했다(`pleos-reference-video-check.txt`, `pleos-reference-motion-check.txt`).

최종 소개 영상은 34초·1920×1080·30fps다. AAC를 PCM으로 디코딩해 34초·stereo 44,100Hz, peak 0.23239, RMS 0.019323, 클리핑 0을 확인했다(`pleos-reference-audio-check.json`). Scott Buckley의 기존 외부 음원 파일/해시를 유지하며 음악을 새로 합성하지 않았다. 결과별 MP4·APK 별칭과 체크섬을 갱신했다. 원본 기준 영상과 이전 앱·사진 중심 영상은 그대로 보존했다. 출처·사용 범위는 `PLEOS_VISUAL_SOURCE.md`에 기록한다.

기존 실제 SDK 문 수신 어댑터는 변경하지 않았다. 원본 시각화 추가 직후의 첫 Pleos AVD 재시험은 설치 서비스 지연과 `shortMsg=Process crashed`로 미완료였다. 이후 위 최신 양방향 SDK 재시험에서 완료했으며, 첫 시도 자체를 성공으로 바꿔 기록하지 않는다. 실패 시도는 `pleos-reference-sdk-attempt/`, 이전 성공 로그는 `archive-before-pleos-reference/sdk/` 및 기존 기본 SDK 로그에 보존한다. 서버 26개·Android 단위 6개·실제 SDK/CarUx 성공 결과는 이전 검증이며, 실차·실제 OpenAI 호출을 새로 검증하지 않았다.

## 이전: 실차 사진 중심으로 복원 · 2026-11-14

사용자가 초기 사진 중심 영상의 완성도를 선호해 홈·상태·문 상세·Mock 가이드 차량 자리를 실제 IONIQ 5/N 사진으로 복원했다. 사진은 외관 참고용으로 두고 문 수신 상태를 별도 표시한다. 기존 3D 개폐·회전·미확인 처리와 라이선스는 보조 탭에 유지한다. 소개 영상에는 3D를 넣지 않는다.

두 APK와 기기 테스트 APK 빌드가 통과했다(`photo-return-build.txt`). 실제 기기 5개 시험이 21.074초에 통과했다(`photo-return-instrumentation.txt`). 기본 홈에 사진이 표시되고 3D가 생성되지 않는 것, 차종·언어 변경 후 사진 매핑, 별도 탭에서 GPU 개폐·회전·미확인 자세가 유지되는 것을 검사했다. 기존 오류·UX 제한·가이드 복귀·로컬 HTTP Mock 왕복도 통과했다. 두 APK의 3D 원본·소스·라이선스 묶음이 그대로 포함됨을 검사했다.

실제 연속 촬영 시험 1개가 49.05초에 통과했다. 19개 장면의 새 녹화에서 설치/전달 APK의 해시와 실제 APK 안의 원본 사진 바이트를 대조했다. 소개 영상은 32초·1920×1080·30fps이며 시작·실차 사진·상태 카드·가이드·영어·일본어·마무리를 육안 확인했다(`photo-return-video-check.txt`). AAC 디코딩은 32초·2채널·44,100Hz, peak 0.23239, RMS 0.01959, 클리핑 0이다(`photo-return-audio-check.json`). 두 APK의 IONIQ 5/N 사진이 원본 JPEG와 동일하고 기록된 SHA256이 맞는지 검사했다. 기능 화면은 해당 APK에서 촬영하며, 사진을 문 개폐 영상으로 설명하지 않는다. 이번 변경은 실제 차량·새 SDK 수신·실제 AI 호출 검증이 아니다. 기존 SDK·서버 연결 상태와 이전 시험은 그대로 유지한다.

## 이전: 외부 IONIQ 5 전용 모델 교체 · 2026-11-14

기존 각진 자체 모형을 OpenX Assets의 Hyundai IONIQ 5 2022 모델로 교체했다. 원작자 andikapratamaw, 후속 가공 Dogan Ulus이며 MPL-2.0 AND CC-BY-4.0이다. 원본 Blend SHA256을 고정 커밋 LFS 포인터와 대조했다. 원본 GLB에서 37,350삼각형·30재질·44메시를 읽고 앞좌석 왼쪽 문·유리·미러 그룹과 원본 경첩을 유지했다. 물리적 왼쪽·바깥 개폐·유한 좌표·단위 법선·원본/변환 해시·정상 애니메이션 GLB를 검사했다. 8,602개 삼각형의 서로 다른 정점 법선이 변환 후에도 보존되어 곡면 보간에 사용되는지 확인했다.

`real-model-build.txt`에서 demo/pleos/기기 테스트 APK 빌드를 확인했다. 기기 회귀 5개가 48.078초에 통과했다(`real-model-instrumentation.txt`). GPU 프레임·0↔62도 개폐·픽셀 변화·회전·문 미확인의 22도 설명 자세·열림/닫힘 화면 경계를 검사했다. 기존 언어·오류/미지원·가이드 복귀·UX 제한·실제 로컬 HTTP Mock 왕복과 보조 사진 매핑도 통과했다. 서버는 이미 실행 중이던 로컬 Mock API를 사용했다.

`validate_3d_model.py --apk ...`로 두 전달 APK 안의 실제 모델, 원본 Blend/GLB, 변환 Python, 저작권·라이선스 전문이 저장소 파일과 바이트 단위로 일치함을 확인했다. 원본·소스를 APK에 동봉해 외부 서버 없이 얻을 수 있도록 했다. 앱 설정과 영상에 원작자·MPL/CC BY와 변경 사실을 표시한다.

실제 APK 연속 촬영 1개는 52.133초에 통과했다. 20개 실제 화면·개폐/회전·언어 전환의 원본과 설치/전달 APK 해시 일치를 `carcue-native-run.json`에 보관한다. 시작 카드도 같은 앱의 실제 GPU 뷰를 캡처한다. 기존 자체 모형·APK·영상은 Git 이력과 `archive-before-real-model/`에 보존했다.

최종 소개 영상은 34초·1920×1080·30fps다. 12개 시점에서 새 모델의 곡면·유리·개폐 전후/중간·회전·한국어/영어/일본어·모델 크레딧·마무리를 디코딩하고 육안 확인했다(`real-model-video-check.txt`). 최종 AAC 디코딩은 34초·stereo 44,100Hz, peak 0.23239, RMS 0.01932, 클리핑 0이다(`real-model-audio-check.json`). 원본 음악은 기존 Scott Buckley 음원을 그대로 유지한다. 소개 영상·실제 녹화·모델 캡처·설치/전달 APK의 해시 연관성을 확인하고 출력 체크섬을 갱신했다.

공식 현대 CAD나 선택 프로필과 정확히 맞는 연식·트림을 검증한 것은 아니다. 물리 차량/새 실제 SDK 수신/실제 OpenAI 호출을 추가 검증하지 않았다. 기존 SDK·서버 코드와 관련 시험 결과는 이전 검증을 유지한다.

## 이전: 자체 제작 3D 변경 검증

새 모델은 자체 제작 IONIQ 5 스타일 외형 참고 메시다. 현대 공식 CAD나 특정 연식·트림의 정확한 복제는 아니다. `validate_3d_model.py`로 두 파일의 해시·정상 GLB·유한 정점·물리적 왼쪽 문·경첩 축·바깥 방향 개폐를 검사했다. 모델은 14,734삼각형이며 문/차체는 독립 노드다.

최종 demo/pleos/기기 테스트 APK를 빌드했다(`3d-final-build.txt`). 기기 회귀 5개가 통과했다(`3d-final-instrumentation.txt`). 실제 TextureView가 렌더링한 프레임과 열린 문 62도→닫힌 문 0도, 화면 픽셀 변경, 드래그 회전, STALE의 회색 설명 자세 22도를 검사했다. 열린 문·닫힌 문 모두 GPU 비트맵 위·아래 경계의 어두운 차체/바퀴 픽셀이 없는지도 검사했다. 기존 세 언어·미수신/오류/미지원·UX 입력 제한·가이드 복귀·실제 로컬 HTTP Mock 왕복·사진 차종 매핑도 통과했다. 첫 시험의 상태 반영 전 대기와 고정 메뉴 스크롤 요청은 시험 동기화를 수정해 해결했다.

실제 APK 연속 촬영 1개가 통과했다. 20개 화면·동작의 원본 녹화와 설치 base.apk=전달 APK 해시 일치를 `carcue-native-run.json`에 보관한다. 소개 영상의 모든 기능 장면은 이 원본에서 자르며, 문 닫힘·다시 열림·회전은 각 2초다. 시작 카드 3D도 같은 APK의 GPU 뷰 비트맵이다. 최종 프레임 검수에서 하단 버튼 여백을 보완해 재빌드·재촬영했다. 이전 사진 중심 버전과 APK를 보존했다.

최종 소개 영상은 34초·1920×1080·30fps다. 개폐와 회전은 원본의 실제 터치 직전부터 편집해 움직이는 과정을 유지했다. 시작·개폐 전후와 중간 자세·회전·가이드·영어·일본어·마무리 프레임을 디코딩하고 육안 확인했다. `3d-intro-video-check-final.txt`, `3d-intro-motion-check.txt`, `3d-intro-midpoint-check.txt`에 시각을 보관한다. AAC를 PCM으로 디코딩한 결과는 34초, stereo 44,100Hz, peak 0.23239, RMS 0.01932, 클리핑 0이다. `3d-intro-audio-check.json`은 최종 MP4 해시도 기록한다. 외부 음원 원본·모델·설치/전달 APK·원본/최종 영상의 해시 일치를 확인했다. 최종 기기 5개는 17.86초, 촬영 1개는 54.224초에 통과했다.

이번 변경에서 backend/OpenAI/실제 Pleos 수신 어댑터는 바꾸지 않았다. 서버 26개, Android 단위 6개, 실제 SDK/CarUx 수신 결과는 이전에 확보한 검증이다. 이번에는 일반 AVD의 Mock 데이터와 실제 OpenGL/UI 동작을 검증했다. 물리 차량·새로운 실제 AI 호출을 검증한 것은 아니다.

## SDK 실제 수신 증거

`output/qa/pleos-sdk-events.txt`에서 다음 흐름을 확인했다.

1. Capability: `ROW_1_LEFT`, min 0 / max 1, READ_WRITE.
2. 최초 GET: 실제 SDK 값 0, 앱 수신 시각 기록.
3. Listener 등록과 실제 최초 콜백 0을 각각 기록.
4. 공식 Virtual Console에서 앞좌석 왼쪽 문을 열림으로 변경.
5. 실제 SDK 변경 콜백 1과 UI의 ‘앞좌석 왼쪽 문이 열려 있어요’ 확인.
6. 같은 Listener/영역의 `LISTENER_UNREGISTER_RETURNED`, `RELEASE_RETURNED` 확인.

값 0/1은 시험한 영역과 범위에서만 CLOSED/OPEN으로 정규화한다. 다른 영역/범위를 같은 의미로 확대하지 않는다. 등록 성공 문구나 GET만으로 변경 콜백 성공을 판단하지 않았다.

`output/qa/pleos-console-events.json`은 테스트 도구가 공식 콘솔에 보낸 시뮬레이션 요청이다. 앱에는 SDK SET을 넣지 않았다. 물리 차량을 제어하거나 실차 센서를 검증한 결과가 아니다.

## 실제 차량 UX 제한 검증

공식 Virtual Console에서 주차→Drive 및 20 km/h 조건→정차·Park를 시뮬레이션했다. 실제 `CarUxRestrictionsManager` 초기 GET false/0, 변경 callback true/80, 복귀 callback false/0을 확인했다. 로그는 `output/qa/pleos-ux-events.txt`, 화면은 `pleos-driving-restriction.png`다. 값이 없을 때 허용으로 처리하지 않으며, 실제 속도/기어로 앱이 제한을 추론하지 않는다. 속도/기어 변경은 테스트 도구의 가상 입력일 뿐이다. 실차·모든 지역 정책 검증은 아니다.

## Mock 기기 회귀 범위

- 실제 버튼으로 차량 선택 → 한국어 → 홈 → 상태 → 상세 → 종료.
- null/미수신, 지원 확인 실패, 실제 미지원, 오래된 값의 서로 다른 표시.
- Mock 주행 제한 변경 시 열린 질문 입력 제거와 제한 화면 표시.
- 가이드 단계 2에서 질문 후 돌아와도 단계 유지.
- 현재 Mock 언어 목록은 한국어·영어·일본어 3개. 실제 버튼으로 영어→일본어 변경, 일본어 홈·문 상태 표시, 단계 2 유지와 기존 가이드의 원문 언어 안내를 확인.
- 언어 변경 후 대한민국 사양 유지.
- 실제 HTTP로 로컬 FastAPI Mock 서버 왕복, NO_RELIABLE_SOURCE와 MOCK 모드 표시.
- 미등록 QR 프로필 오류 및 세션 종료 후 프로필·언어·상태·대화 초기화.

이는 48개 언어의 번역 완료나 모든 디스플레이·글자 확대 검증을 뜻하지 않는다. 한국어·영어·일본어 UI는 초안이며, 가이드 예시는 실제 조작 매뉴얼이 아니다. 세 언어 각각 129개 문구의 누락과 치환 변수 일치를 검사했다. 이전 빌드에서는 아랍어 영어 대체·RTL과 단계 숫자 방향을 확인했지만, 현재 Mock 선택 목록에서는 제외했다. RTL 확장 데이터와 배치 코드는 보존했다.

## 서버 회귀 범위

세션 소유·프로필 불일치, 자료 부족 Schema, 게시 전 템플릿 배제, 문서 버전/차종/언어/검수 상태에 따른 검색, 출처 ID 대조, 근거 없는 재서술 차단, 중복 요청·요청 ID 충돌, 삭제·만료·늦은 응답, 요청 한도, 번역 숫자·단위 보존 검사를 확인했다.

LIVE provider 시험은 **메서드/HTTP transport 대역**이다. 실제 OpenAI 요청은 수행하지 않았다. 실행 환경에 OPENAI_API_KEY와 OPENAI_MODEL이 설정되지 않은 것도 비밀값 출력 없이 확인했다. 자동 고장 진단·차량 제어 action을 생성하지 않으며 초기 답변은 검수 원문의 직접 추출로 제한한다. 번역의 부정·순서·부품명 등 의미 검수는 별도 과제로 남는다.

## 해결한 실패와 남은 검증

- 초기 JDK 18의 의존성 DNS 오류: 최신 JDK 17로 전환해 다운로드·빌드 성공.
- 초기 일반 API 37 AVD 부팅 미완료: 별도 API 35 AVD를 설치해 3개 기기 회귀 통과.
- Pleos 이미지의 표준 android.car 공유 라이브러리 필수 선언으로 설치 거부: 선택 선언과 클래스 존재 확인으로 수정, 설치·앱 실행·SDK 시험 통과. 런타임 제한 값은 SDK 조사 보고서에 별도로 기록한다.
- 서로 다른 사용자 저장소: Pleos 실행 사용자 10의 캡처를 `run-as --user 10`으로 분리해 수집.
- 이번 공식 매뉴얼 두 절의 AI 보조 원문 대조를 넘어선 차종/주제·인간 전문가 검수, OpenAI 실호출, 실차, 다른 지역별 UX 정책, 전체 언어·폰 QR 카메라·로터리·접근성은 미검증.
- 의존 라이브러리의 비치명 경고: Starlette/AnyIO alias deprecation, 표준 Car.createCar/connect deprecation. 빌드/테스트 실패는 아님.

## 결과 파일

### 다국어 Mock 영상 추가 · 2026-11-13

`carcue-mock-languages.mp4`는 당시 demo APK를 API 35 / CarCue_UI35 / 1280×800 AVD에 설치해 녹화한 약 79초의 Android screenrecord 원본이다. 한국어 → 영어 → 일본어 → 한국어 전환, 실제 언어 버튼 터치, 각 언어의 홈·문 상태 화면을 담았다. 차량 프로필은 계속 IONIQ 5 · 2024 · KR이다. 모든 차량 값은 MOCK이며 외부 AI를 호출하지 않았다.

녹화 전 전달 APK와 기기에 설치된 base.apk의 SHA256이 `8d63511b8e8cd0cd16ce75bf1ae5037a5a6dff3e353ac028ac3a247453e3a59e`로 일치함을 검사했다. 앱 소스는 `ef8fe88`이다. JSON에는 APK·영상 해시, AVD, 언어, 관찰한 화면 문구별 시각이 있다. 시각은 호스트 기준의 근사값이다. 저장된 MP4를 macOS 영상 프레임워크로 열어 길이 78.7623초·1280×800을 확인하고, 10개 시점의 프레임을 디코딩했다. 세 언어의 홈·선택 목록·마지막 한국어 복귀 화면을 육안 확인했다. 결과는 `mock-languages-video-check.txt`와 `language-video-frames/`에 있다.

재현 도구는 `scripts/record_mock_languages.py`다. 이전 영상은 `carcue-mock-flow-initial.mp4`로 보존했다. APK 코드는 이번 녹화 작업에서 변경하지 않았다.

### 기능당 2초 편집본 추가 · 이전 28초 버전

사용자 요청에 따라 인계 SVG의 충전 사진과 실제 APK 녹화·캡처를 합쳐 `carcue-mock-short.mp4`를 만들었다. 총 14장면 × 2초 = 28초, 1280×800, 30fps다. 한국어·영어·일본어 화면과 실제 언어 선택 터치를 유지한다. 이미지 예시는 별도 자막으로 구분한다. 원본 녹화와 편집본의 출처·시간표는 `VIDEO_STORYBOARD.md`, 재현 구성은 `video-short.json`을 따른다.

초기 편집본의 14개 장면 프레임을 모두 디코딩하고 이미지, 가이드, 질문, 언어 목록, 종료 화면을 육안 확인했다. 최종 자막과 전환 구간 조정 후 해당 장면들을 다시 확인했다. 무편집 원본은 `carcue-mock-languages.mp4`로 보존한다. 외부 AI 호출과 APK 수정은 이번 편집 범위에 없다.

### 3D 차량 포함 32초 편집본 · 이전 결과

차량 그림·가이드 이미지·3D를 모두 포함해 달라는 사용자 요청으로 `carcue-mock-visuals-3d.mp4`를 추가했다. 총 16장면 × 2초 = 32초, 1280×800, 30fps다. 문이 닫힌 3D 차량은 첫 2초, 문이 열린 3D 차량은 10–12초에 배치했다. 원본 `carcue-pleos-sdk.mp4`의 차량 영역을 확대했으며, 두 구간에 Pleos 에뮬레이터 출처 자막을 넣었다. 3D는 플랫폼 시스템 UI이고 CarCue 자체 3D 렌더러 구현이 아니다. 나머지 앱 상태는 MOCK으로 구분한다.

최종 MP4 길이 32초와 11개 시점의 프레임 디코딩을 확인했다. 3D 차량의 문 닫힘·열림, 출처 자막, 장면 경계에서 자막이 사라지는 것, 가이드 이미지와 영어·일본어 전환을 육안 확인했다. 검증 로그는 `mock-visuals-3d-video-check-final.txt`, 캡처는 `visuals-3d-frames-final/`다. 렌더러의 초기 텍스트 레이어 출력 누락은 비트맵 자막 합성으로 수정했고, 차량 확대 구간의 검은 여백도 화면 비율을 맞춰 제거했다.

이전 28초 편집본과 두 녹화 원본도 보존했다. 이전 구성은 `history/VIDEO_STORYBOARD_EDITED.md`, 구간·확대 영역은 `video-short.json`, 파일별 해시는 `carcue-mock-visuals-3d.json`에서 관리한다.

### 이전: 일반 Canvas 모형과 연속 실행

사용자의 의도에 맞춰 사진·3D를 실제 APK 안에 구현했다. 홈·상태·상세의 일반 차량 위치 모형은 Compose Canvas에서 원근 투영하며 드래그로 회전한다. 신선한 문 상태만 열림·닫힘으로 연결하고 미수신·미지원·오류·오래된 값은 미확인으로 표시한다. 가이드 사진도 APK의 자산을 읽어 실제 Image 컴포넌트로 표시한다. 모델은 차종의 정확한 외형이 아니다. 세부 구현과 출처는 `NATIVE_VISUALS.md`에 있다.

`carcue-native-run.mp4`는 동일 APK에서 19개 기능 화면·동작을 실제로 실행한 연속 screenrecord 원본이다. 각 화면은 2초 유지하며 영상에 다른 이미지·Pleos 시스템 UI를 삽입하지 않는다. 설치 APK 해시를 전달 APK와 대조했다. 촬영 중 고정 메뉴에 스크롤을 요청한 자동화 실패는 표시 중인 메뉴를 바로 누르도록 수정했다. 종료 직전 대화상자 잔상이 최종 프레임으로 남지 않도록 실제 앱의 마지막 터치까지 녹화한다.

### 이전: 실차 사진 중심 소개 영상

이전 수정은 외부 무료 음원과 실차 사진을 사용했다. Scott Buckley의 **A Kind Of Hope**를 원작자 페이지의 CC BY 4.0·출처 표기 조건으로 확인해 내려받았다. 영상 크레딧과 별도 게시용 텍스트를 만들었다. 음원 합성 코드는 제거했고, 원곡을 구간 선택·음량 조정·페이드만 적용한다. 차량 기본 화면과 시작 카드에는 CC0 IONIQ 5 실차 사진을 사용하고 N 프로필에는 별도 N 사진을 매핑했다. 출처는 `MEDIA_CREDITS.md`에 정리했다.

demo·pleos·기기 테스트 APK 빌드가 성공했다. 기기 회귀 4개와 실제 촬영 1개가 통과했다. 새 테스트에서는 IONIQ 5에서 N으로 변경 후 일본어를 선택해도 N 사진·GB 시장이 유지됨을 확인했다. 136개 UI 자원의 세 언어 누락·치환 변수 검사도 통과했다. 사진 변경 전의 영상·APK는 별도 파일로 보존했다.

최종 소개 영상은 32초·1920×1080이다. 9개 시점의 프레임에서 시작 카드의 실차 사진, 실제 APK의 사진·상태·가이드·일본어, 음원 크레딧·마무리를 확인했다. 최종 AAC 디코딩 결과는 32초·2채널·44,100Hz, peak 0.2324, RMS 0.0196, 클리핑 표본 0이다. 결과는 `real-photo-intro-video-check.txt`와 `real-photo-intro-audio-check.json`이다. 아래의 자체 음악 수치는 이전 버전의 이력이다.

사용자 요청에 따라 실제 앱 원본을 바탕으로 `carcue-app-intro.mp4`를 제작했다. 시작·기능별 짧은 설명·세 언어 전환·이용 종료·마무리와 직접 만든 배경음악을 포함한다. 32초·1920×1080·30fps이며 기능 구간은 2초씩이다. 모든 기능 화면은 같은 APK 녹화에서 잘라 썼다. Mock 표시를 유지하며 AI 질문에는 답변 연결 준비 중임을 명시한다. 실제 앱 원본과 APK는 변경하지 않았다.

15개 장면의 중앙 프레임을 디코딩하고 시작·자막·3D·사진·질문·일본어·마무리를 육안 확인했다. 최종 첫 프레임의 브랜드 노출과 주요 자막도 재확인했다. MP4의 AAC를 디코딩한 결과 길이 32초, 44,100Hz, peak 0.2411, RMS 0.0609, 클리핑 표본 0이다. `app-intro-video-check.txt`, `app-intro-video-check-final.txt`, `app-intro-audio-check.json`에 증거를 남겼다. 기본 `carcue-mock-flow.mp4`는 이 소개 영상으로 갱신한다. 기획·재현은 `APP_INTRO_VIDEO.md`를 따른다.

- APK: `output/apk/carcue-demo-debug.apk`, `output/apk/carcue-pleos-debug.apk`.
- Mock 캡처: `output/qa/qa/01-profile.png` 등 기본 흐름. 최신 언어 선택·일본어 화면은 `09a-three-languages.png`, `09b-japanese-home.png`, `09c-japanese-status.png`.
- 실제 SDK 캡처: `pleos-initial-get.png`, `pleos-changed-callback.png`, `pleos-session-ended.png`.
- 로그: `output/qa/mock-instrumentation.txt`, `pleos-instrumentation.txt`, `pleos-sdk-events.txt`, `pleos-console-events.json`, `pleos-ux-events.txt`.
- 영상: 최신 소개용 `output/qa/carcue-app-intro.mp4` (`carcue-mock-flow.mp4`와 동일), 실제 실행 원본 `carcue-native-run.mp4`, 이전 편집본 `carcue-mock-visuals-3d.mp4`·`carcue-mock-short.mp4`, 이전 언어 녹화 `carcue-mock-languages.mp4`, 최초 `carcue-mock-flow-initial.mp4`, 별도 실제 SDK 영상. SDK 화면과 Mock 화면의 출처를 혼동하지 않는다.

SDK·AVD·JDK 바이너리와 APK/영상은 Git에 포함하지 않았다. source, 계약, 테스트, 실행 안내는 feature 브랜치에서 관리한다. 원격 push·병합·배포·공모전 제출은 수행하지 않았다.

실차 사진을 추가하기 전 앱 원본의 길이는 45.9814초, 해상도는 1280×800이다. `native-run-video-check-final.txt`와 `native-run-scene-check.txt`의 프레임 디코딩을 확인했고, 문 열림·닫힘·회전·가이드 사진·영어·일본어·깨끗한 종료 화면을 육안 확인했다. 실차 사진 추가 전 demo APK의 SHA256은 `3a30d6912c214d89c1e12ad86a00b5f8b6860f812bec95f93be237b39d3fbdbb`이며, 설치된 APK와 일치했다.
