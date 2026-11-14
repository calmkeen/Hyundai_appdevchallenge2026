# 다국어·차량 UX·이용 종료 통합 검증

2026-11-15 (KST). 문서의 단계 6(다국어·차량 UX·이용 종료) → 단계 7(재현 가능한 시연) 순서로 진행한다. 기존 게시 문 안내·원본 렌더 자산·음원·영상·AVD userdata를 보존한다. 유료 AI와 생성 QUESTION 번역은 기본 보류다.

## 구현 범위

UI 언어와 저장 콘텐츠 언어를 분리한다. 기존 답변은 실제 답변 언어를 표시하며, 번역의 원문·요청 대상·완료 결과 대상을 각각 표시한다. 언어 변경 때 과거 번역을 새 대상 언어 결과로 표시하지 않고, 원문과 번역 초안은 보존한다. 새 번역을 열면 기존 성공 결과·검수 상태·provider 표시는 정리한다.

화면에서 캡처한 세션 epoch·프로필·언어·화면·번역 원문 범위와 현재 UX를 실행 직전에 재검사한다. 동의는 입력/맥락이 바뀌면 다시 받고, 이용 종료 후에는 새 이용자에게 이전 결과나 늦은 응답을 표시하지 않는다. 질문의 복귀 대상과 번역의 복귀 대상을 분리해 가이드 → 질문 → 번역 → 질문 → 같은 가이드 단계로 돌아가도록 한다. 순수 정책과 실제 SDK/HTTP 결과를 구분한다.

생성 질문 번역의 현재 보류 정책은 과거 개발 opt-in 캐시에도 적용한다. 같은 DB 재시작 검증은 [QUESTION_DEFERRAL_CACHE.md](QUESTION_DEFERRAL_CACHE.md)를 따른다. 이 시험의 provider HTTP는 대역이며 실제 모델 호출로 계산하지 않는다.

## 실제 검증의 완료 조건

- 공식 Pleos API34 AVD/user10, 설치 앱·테스트 APK hash 대조, 실제 SDK SUPPORTED/VALUE·fresh GET·열림/닫힘 callback·차량 이미지 변경/복귀.
- 같은 2024 KR 프로필에서 한국어·영어·일본어 실제 무료 ASK와 완전한 주의문/출처, 추가 모델 호출 없는 저장 ANSWER 번역.
- 언어가 다른 기존 답변의 원문 언어, 번역 원문/대상/결과 대상 표시, 새 언어/원문에서 이전 번역·동의 초기화.
- 실제 플랫폼 Drive 제한과 Park 복귀. 속도/기어로 앱이 제한을 추론하거나 앱에서 SDK SET을 호출하지 않는다.
- 실제 무료 모델 요청 진행 중 언어 변경·Drive·이용 종료 뒤 서버 처리가 끝나도 이전 결과를 표시하지 않는다. provider/HTTP 응답에 가짜 지연을 넣지 않는다.
- 세션 삭제·새 이용자 초기 상태·공용 자료 보존·Console Park/0/CLOSED 복구와 lease 종료. 기존 앱/AVD의 데이터를 초기화하지 않는다.

아래 표준 시연은 통과했다. **진행 중 요청의 언어 변경·Drive·이용 종료 경계 기기 시험은 미완료**다. 따라서 단계 6 전체를 실제 기기 검증 완료로 표시하지 않는다. 정적 코드·단위 회귀를 실제 SDK·모델·실차 시험으로 보고하지 않는다.

## 시험 범위의 구분

이 시험의 세 가지 UI 문맥은 첫 가이드 단계의 한국어, 두 번째 단계의 영어, 가이드 문맥 없는 일본어다. 3언어×3문맥 전체 API 행렬을 기기에서 다시 실행했다는 뜻은 아니다. 기존 완전 주의문 API9개 결과는 `AI_CAUTION_VALIDATION.md`에 보존한다.

이용 종료 경계는 실제 사용자 경로인 ASK → 설정 → 종료 확인을 따른다. 설정 이동에서 먼저 요청을 취소하므로, 성공은 이 종료·새 이용자 경로의 늦은 결과 차단이며 session epoch 검사 하나의 단독 원인 실험이 아니다. epoch와 기타 scope 조합은 JVM 회귀로 별도 검증한다. 진행 중 동의 해제 자체의 기기 시험은 이번 시나리오에 없고 순수 정책 검증 범위다.

SDK 값은 공식 AVD의 시뮬레이션이며 물리 차량 시험이나 SDK의 자동 차종 인증이 아니다. 안전벨트는 센서 미연결 안내 이미지다. ASK는 실제 무료 Ollama의 등록 단위 선택과 서버의 검토 문자열 조립이며, ANSWER 번역은 같은 판본의 저장 번역이다. 자동 회귀의 provider/HTTP fixture와 기존 demo/MOCK 서버를 실제 호출로 보고하지 않는다.

## 확정된 실제 시연 결과

`output/qa/multilingual-session-20261115/sdk-session-showcase-20261115-03/validation.json`은 functional/video/overall 모두 PASS다. `connectedShowcaseFlow` 1개가 **194.754초**에 통과했다. 동일 APK/앱 프로세스에서 14개 장면과 3개 ASK/3개 저장 ANSWER 번역을 실제 실행했다. 199.981초·2560×1440의 연속 원본이며 장시간 정적 화면과 모델 대기가 포함된 가변 프레임률 녹화다. 편집본의 30fps와 원본 평균 프레임률을 혼동하지 않는다.

- 기능 APK: `output/apk/carcue-pleos-session-boundaries-debug.apk`, SHA256 `5ef560ba1a24e3ce206aeeb6f4f336018b6e8a182bec7214aabc5dd4a261479f`. 실제 설치 APK를 pull해 일치시켰다.
- 시연 당시 테스트 APK: `output/apk/carcue-pleos-session-showcase-validated-test.apk`, SHA256 `82409ca5409eebdd7ead1a02a5da4ffb768804089a84e303ec9814c2bb92b884`. 후속 late 관측 도구와 따로 보존한다.
- 모델은 실제 Mac Ollama 0.40.16/qwen3:4b, digest `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`. 성공 시연 audit3개는 실제 ASK UUID hash와 1:1이며 positive 사용량·응답 digest·HTTP 200·정확한 모델/operation을 확인했다. 저장 번역은 추가 모델 0회다.
- 완전한 답변과 저장 번역은 기존 게시 3언어의 본문/두 단계/모든 주의문을 직접 재조립한 문자열 및 출처2개와 일치한다. 별도 에이전트의 의미 대조와 원해상도 PNG 검토는 원본을 바꾸지 않는 별도 `visual-semantic-review.json`에 있다. 이미지 38개 중 동일 hash alias를 제외한 유일35개를 실제 열었다. 번역 결과를 위한 스크롤로 상단 제목 일부가 viewport 밖인 캡처가 있지만 필수 주의문 전체는 보인다.
- 실제 SDK 개폐 callback과 차량 이미지 변경/닫힘 정확 복귀, Drive/Park의 실제 UX callback, 동일 listener 해제/release, 가이드 2단계→ASK→저장 번역→ASK→원래 단계 복귀가 확인됐다. 마지막 Console은 Park/0/CLOSED, 자체 lease는 정상 해제됐고 서버 sessions/results/history는 각각 0건이다.

## 실패 기록 보존

| 실행 | 실제 결과와 보완 |
| --- | --- |
| showcase01 | SDK OPEN 수신 후 350ms만 기다린 캡처가 720ms 애니메이션 첫 프레임과 같아 픽셀 비교 실패. 테스트만 900ms 실제 시간 동안 Compose frame을 진행하도록 수정. 모델0회·DB0·Park 복구 |
| showcase02 | KO/EN 실제 ASK2회와 저장 번역/2back 뒤 고정 sidebar에 performScrollTo를 적용해 실패. visible 메뉴/확인 dialog 클릭 처리 보완. 모델2회·DB0·Park 복구 |
| showcase03 | 새 실행에서 전체 시연 PASS. 앞선 영상·PNG·로그·테스트 APK를 보존 |
| late01 | 모델 처리 중 경계를 확정 관측하기 전에 실제 응답이 완료돼 INFLIGHT_NOT_EXERCISED로 거절. 가이드 로딩까지 기다리지 않고 실제 언어 선택 직후 marker를 쓰도록 관측 도구만 수정. 요청1회가 남긴 DB1/1/1을 숨기지 않음 |
| AVD 재기동 | 이어진 ADB shell/Console timeout 및 ColorBuffer 오류를 별도 기록. emu kill로 종료 코드0 확인 후 동일 userdata로 재기동. 앱의 기존 abandoned-session 삭제 복구가 실제 HTTP DELETE를 수행해 DB0/0/0 확인. 직접 DB 수정·자격정보 읽기·데이터 초기화 없음 |
| late02 | 설치 hash는 일치했으나 native class 시작 전 OEM remove-task로 새 시험 프로세스 종료. 앱의 Java crash로 단정하지 않음. 모델0·DB0·Park/lease 복구. late만 owned package 종료/PID 부재 확인 뒤 InstrumentationRule로 실행하며 정상 런처 검증은 showcase에 보존 |

초기 실패를 성공으로 바꾸거나 이전 영상과 새 시연을 섞지 않았다. late 관측용 테스트 APK만 보완했으며 기능 APK는 계속 같은 hash다. AVD의 graphics/시스템 앱 문제 원인을 확정하거나 실제 차량의 안정성 시험으로 확대하지 않는다.

## 추가 관측 도구와 환경 분리

late03은 실제 모델1회(31.047초) 뒤 ADB 명령 시간 초과로 중단됐다. 당시 정확한 명령은 저장하지 않아 단정하지 않으며 이후 도구에는 payload 없이 ADB operation/timeout만 기록한다. late04는 화면 Awake 준비가 확인되지 않아 시작 전 거절했다(모델0·DB0). WAKEUP은 비동기이므로 실제 power 상태를 제한된 시간 동안 다시 확인하도록 보완했다. late05는 지도 앱이 전면인 상태에서 SDK READ_TIMEOUT/UX 연결 해제와 CarCue STOP/release가 관측돼 성공으로 세지 않았다(모델0).

late06은 같은 PID의 계측 task 재선택과 실제 window focus, fresh SDK GET까지 통과했지만 모델19.364초의 완료 전 경계를 확정 관측하지 못했다. 추가 관측에서는 처리 중 `runOnIdle` 동기화로 시점을 늦추지 않도록 실제 production navigation handler를 `Instrumentation.runOnMainSync`에서 호출하고 영어 선택/종료 확인은 실제 UI 버튼을 사용한다. 이는 handler 기반 계측이며 물리 터치 경로 전체를 독립 검증했다는 뜻이 아니다. SDK·HTTP·모델 대역이나 인위적인 provider 응답 지연은 추가하지 않았다.

Mac은 RAM16GiB/8코어이며 전용 AVD는 RAM4096MiB/2코어다. 미디어/AVD/로컬 모델 병렬 실행 때 paging 증가를 읽기 관측했지만 시간 초과의 단독 원인으로 확정하지 않는다. 모델 load/unload와 컴파일·설치·미디어 작업을 순차화했다. 사용자 앱이나 시스템 앱을 종료하거나 보안/인증 설정을 약화하지 않았다. 하드웨어 GPU의 ColorBuffer 오류·통신 지연과 별도로, 설치된 emulator가 지원하는 `-gpu software` override를 사용한 추가 후보를 분리한다. AVD 원본 설정·이미지·userdata·캐시를 덮어쓰거나 초기화하지 않는다.

late07은 같은 AVD를 software GPU로 재기동한 뒤 `KEYGUARD_NOT_READY`로 계측 시작 전에 거절됐다. `wm dismiss-keyguard` 성공 종료 뒤에도 10회 관측에서 `showing=true`, policy의 `currentUser=-10000`이 남았고 실제 screencap은 검은 화면이었다. current Android user는 10이었다. 모델0회·DB0·Park/0/CLOSED 복구·시험 lease 종료를 확인했다. 이 실패는 앱의 언어 클릭이나 늦은 응답 차단 실패로 단정하지 않는다. 최종 관측용 테스트 APK SHA256은 `ac32079785ac1db375acf0da4437b0329ccfdbefefb0ab3f2a06660afe9577b4`이며, 성공 시연의 테스트 APK와 다르다.

추가 경계 시나리오의 성공을 얻기 위해 provider 지연, SDK/UX 대역, 잠금 해제 검사의 생략이나 보안 설정 변경을 적용하지 않았다. 최신 handler 기반 계측은 컴파일·독립 코드 검토만 통과했으며 실제 3개 경계의 통과 증거는 없다. 다음 기기 시험은 화면/SDK 준비 상태를 복구한 후 **새 run-id**에서 late 모드를 다시 실행해야 한다. 현재까지 완료된 표준 시연·JVM 경계 정책 검증과 이 잔여 항목을 구분한다.

## 최종 정리와 재현

- backend 전체 **468개**, JVM **127개** 통과. UI **191개**의 3언어·placeholder 및 게시 안내/답변 bundle 계약 검사 통과. backend provider fixture는 실제 AI 호출이 아니다.
- 모든 시도 합계 실제 provider audit는 **8개**다. 성공 시연의 ASK3개 외에 실패 showcase02의 2개와 late01/03/06 각1개가 포함된다. 실패 요청을 성공한 경계 시험으로 합산하지 않는다. 유료 AI·생성 QUESTION 번역 호출은 없다.
- 최종 `final-local-validation.json`은 서버 sessions/results/history **0/0/0**, 기능 APK hash 불변을 확인한다. 중단된 시험이 남긴 세션은 기존 앱 삭제 복구 경로로 정리했으며 직접 DB 삭제는 하지 않았다.
- 마지막 별도 bootstrap heartbeat는 stop-file을 받고 thread 정지·closing HTTP acknowledgement·프로세스 exit0을 확인했다. 이어 `adb emu kill`과 emulator exit0, 빈 `adb devices`를 확인했다. 이전 실행·실패 폴더·AVD userdata는 보존한다. 로컬 backend와 Ollama 서버는 유지한다.
- 기존 영상·설정·렌더러·BGM 및 main의 보존 hash는 `preserved-baseline.json`과 별도 최종 보존 검사로 대조한다. 최신 소개 영상·독립 시각 검토와 한계는 [SDK_LIVE_INTRO.md](SDK_LIVE_INTRO.md)를 따른다.

```bash
# 로컬 LIVE 서버와 qwen3:4b, 공식 API34 AVD/user10 및 Console 준비 필요.
# 설치는 자동 수행하지 않는다. 입력 APK와 실제 설치 APK가 일치해야 한다.
.venv/bin/python scripts/validate_sdk_session_flow.py --mode showcase --record \
  --apk output/apk/carcue-pleos-session-boundaries-debug.apk \
  --test-apk output/apk/carcue-pleos-session-showcase-validated-test.apk \
  --audit-file output/qa/multilingual-session-20261115/live-server-01/provider-events.jsonl \
  --database output/qa/multilingual-session-20261115/live-server-01/sessions.sqlite3 \
  --run-id NEW_SHOWCASE_RUN

# 미완료 경계 시험. 최신 테스트 APK를 별도로 설치한 뒤 새 실행으로 검증한다.
.venv/bin/python scripts/validate_sdk_session_flow.py --mode late \
  --apk output/apk/carcue-pleos-session-boundaries-debug.apk \
  --test-apk output/apk/carcue-pleos-session-boundaries-late-main-thread-test.apk \
  --audit-file output/qa/multilingual-session-20261115/live-server-01/provider-events.jsonl \
  --database output/qa/multilingual-session-20261115/live-server-01/sessions.sqlite3 \
  --run-id NEW_LATE_RUN
```

host는 모델 완료 전 native 경계 관측과 provider 실제 처리시간의 보수적 대조를 모두 요구한다. 부적절한 타이밍은 `INFLIGHT_NOT_EXERCISED`로 거절한다. QA 원본의 `PENDING_INDEPENDENT_REVIEW` 필드는 덮어쓰지 않고 독립 검토 파일에 근거를 남긴다. Git에는 소스·Docs만 포함하며 APK·모델·원본·개인 세션 정보는 올리지 않는다.
