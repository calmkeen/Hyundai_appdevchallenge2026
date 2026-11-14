# 공식 원문·고객지원 앱 연결 검증

2026-11-14. 문서의 상태 상세·가이드·자료부족 후속 동작을 실제 앱에 연결한다. 카탈로그 검수 근거와 서버 검증은 [OFFICIAL_LINK_CATALOG.md](OFFICIAL_LINK_CATALOG.md)를 따른다.

## 구현 경계

- 기존 Compose MVVM/UDF 구조를 유지한다. ContentRepository가 동봉 등록 자료를 읽고, Android I/O가 없는 OfficialResourcePolicy가 현재 세션·차량·판본·출처를 검사하며, OfficialResourceOpener가 Android ACTION_VIEW를 전달한다.
- 현재 허용 대상은 사용자 선택 `ioniq5-ne1-2024-kr`와 `NE1-2024-KR-ko_KR-D202406100040-20240722`의 문 안내 출처 두 개, 현대자동차 한국 공식 고객문의 WEBSITE 한 개다. 지원 번호를 합성하거나 전화를 걸지 않는다.
- UI 언어 ko-KR/en/ja-JP를 바꿔도 차량 시장 KR과 원문 ko-KR은 유지한다. 원문 언어·판매지역을 버튼 옆에 표시한다. 다른 개발용 프로필에 지원을 대입하지 않는다.
- 외부 실행은 등록된 출처/지원 ID를 통해서만 한다. 서버·모델·기존 가이드 step의 임의 URL을 직접 실행하지 않는다. 원문의 URL도 현재 승인된 출처와 동봉 등록 URL이 정확히 일치해야 한다.
- 누를 때 세션 epoch·현재 프로필·매뉴얼 판본·UX known/허용·현재 가이드/답변을 다시 검사한다. 같은 언어의 철회된 가이드와 이전 응답의 버튼은 사용할 수 없다. UI 언어 변경 후 유지한 원문은 원래 판본으로 해석한다.
- 답변 요청 ID는 번역 등 일반 요청 ID와 별도로 보존한다. 후속 번역 요청이 기존 답변의 출처를 새 응답으로 재결합하지 않는다.
- 외부 앱에 넘기는 것은 공개 공식 URL뿐이다. 세션 토큰·질문·차량 상태를 URL이나 Intent extras에 붙이지 않는다.
- 결과는 INTENT_DISPATCHED/NO_HANDLER/REJECTED로 구분한다. 전달 성공을 웹페이지 로딩 성공으로 표시하지 않는다. 처리 앱 부재/보안 예외에는 CarCue 화면과 선택 가능한 공개 URL을 유지한다.
- 외부 앱 왕복에서 MainActivity onStop/onStart에 따라 실제 SDK Listener/release 및 새로운 Capability/GET·UX 확인을 수행한다. 가이드와 단계는 ViewModel 메모리에서 유지한다. 프로세스 강제 종료 뒤 단계 영속 복구까지 확대하지 않는다.

## 검증 범위와 재현

순수 정책 테스트는 합성 example.test 등록 자료로 세션·UX·시장·판본·철회·URL 대조·답변 요청 바인딩을 검사한다. 실제 SDK·브라우저·AI 호출 증거와 구분한다.

```bash
.venv/bin/python scripts/check_contracts.py
.venv/bin/python scripts/import_guides.py check
.venv/bin/python -m pytest backend/tests -q

env JAVA_HOME="$PWD/.tooling/jdk-17.0.21+9/Contents/Home" \
  ANDROID_HOME="$PWD/.tooling/android-sdk" ANDROID_SDK_ROOT="$PWD/.tooling/android-sdk" \
  android/gradlew -p android :app:testDemoDebugUnitTest :app:assemblePleosDebug \
  :app:assemblePleosDebugAndroidTest -PcarcueServerUrl=http://10.0.2.2:8001 \
  --offline --console=plain --no-daemon --max-workers=2
```

실제 앱 시험은 기존 userdata를 보존한 공식 API34 Pleos AVD `CarCue_Pleos21_LocalAI`/user10에서 수행한다. 실차 시험·SDK 차종 자동 인증·안전벨트 센서 연결을 의미하지 않는다. Console의 문/주행 값은 전용 AVD에서 호스트가 바꾸며 앱은 SDK SET을 호출하지 않는다.

유료 AI와 생성 질문 번역의 기본 보류 정책은 바꾸지 않는다.

## 공식 AVD 브라우저의 개발 빌드 호환

공식 이미지 `/product/app/Browser2/Browser2.apk`의 `org.chromium.webview_shell.WebViewBrowserActivity`에는 VIEW/BROWSABLE/HTTPS 필터가 있으나 DEFAULT가 없다. 일반 query 결과는 존재했지만 실제 implicit VIEW는 NO_HANDLER였다. [Android 공식 문서](https://developer.android.com/guide/components/intents-filters#Receiving)의 기본 Activity 필터 조건과 일치한다.

표준 VIEW를 먼저 시도한다. ActivityNotFound일 때만 **pleos debug + API34 + ranchu**에서 정확한 기존 SYSTEM/exported/enabled Browser2·권한 없음·고정 product 경로를 확인하고 명시 component로 전달한다. SecurityException은 즉시 REJECTED이며 우회하지 않는다. 새 브라우저 설치·기기 보안 설정 변경은 없다. 일반 출시 환경은 표준 VIEW/처리 앱 부재 안내를 사용하며 이번 호환 경로의 실차·다른 OEM 검증을 주장하지 않는다.

`pleosDebug`의 정확한 패키지 `<queries>` 하나는 URL 열기 권한이 아니라 해당 설치 활동 정보를 확인하기 위한 가시성 선언이다. [URL 실행 설명](https://developer.android.com/training/package-visibility/use-cases#open-urls), [개별 패키지 선언](https://developer.android.com/training/package-visibility/declaring#package-name). 실제 자료 수집은 사용자 지정 firecrawl_local MCP로 했고 원기록은 `output/qa/official-links-20261114/intent-compat-review/`에 둔다.

INTENT_DISPATCHED와 별도로 STANDARD/PLEOS_AVD_STOCK 경로를 남긴다. stock Browser Tester에서 Back만으로 복귀하지 않은 시행은 보존했고, 네이티브 시험은 기존 앱 task를 런처처럼 재선택해 동일 MainActivity의 RESUMED·새 GET·가이드 단계를 확인한다. 이는 `vm.foreground()` 직접 호출이나 합성 SDK 값이 아니다.

## 보존한 시행착오

| 시행 | 실제 관측 | 판단/후속 |
| --- | --- | --- |
| run01/02 | 프로필 선택 전 Activity CREATED·UX unknown. 초기 UX GET은 있었으나 SystemUI/Keyguard의 currentUser=-10000 및 DEAD binding 관측. wake/dismiss만으로 해소되지 않음 | 실패 보존. Console 자체·차량 OFF·앱 URL 기능의 원인으로 단정하지 않음. 정상 AVD 종료/동일 userdata cold boot 후 Keyguard showing=false/currentUser10·정상 앱 RESUMED 확인 |
| run03 | 실제 SDK CLOSED·UX 허용·공식 가이드 2/2 상태에서 표준 VIEW NO_HANDLER. 앱 생존·단계 유지 | stock DEFAULT 필터 차이를 확인해 개발 빌드 호환 경로 추가. 성공한 왕복 시험으로 계산하지 않음 |
| run04 | 실제 앱→stock 브라우저 전달·정확 공식 URL 확인. 실패 시 물리 캡처에 현대 매뉴얼 본문 표시 | Back 복귀 기대 실패. 앱 task 재선택으로 복귀 동작을 명시해 시험 보강. 페이지 전체 로딩의 자동 판정은 아님 |
| run05 | KO/EN/JA 원문/지원 총6회 왕복·SDK GET1→7·가이드 step1 유지. 실제 Qwen3 선택 호출1회/HTTP200/STRUCTURED_VALIDATED/34.208초 | AI 결과/citation/action 검사를 지난 뒤 활성 화면에서 실제 UX:DISCONNECTED·unknown 발생. 전체 시험 실패 유지. 연결 복구와 이전 연결 콜백 경계를 별도 feature로 보강 |

각 원기록은 `output/qa/official-links-20261114/official-resources-20261114-NN/` 및 `native-run-NN.log`다. 실제 모델 호출이 있었던 실패도 성공으로 바꾸지 않는다. 서비스 연결 해제의 근본 원인까지 확정하지 않는다.

## 최종 결과

| 항목 | 결과·증거 |
| --- | --- |
| 통합 빌드·정책 회귀 | JVM **110/실패0/오류0**. 서버 **416**. UI185 문구·3언어·등록지원1·가이드4·상태규칙1 계약 검사 통과 |
| 공식 링크 실제 앱 | `official-resources-20261114-06` **76.488초 PASS**, KO/EN/JA 원문/지원6회 + 실제 AI 답변 OPEN_MANUAL/OPEN_SUPPORT2회 =8회. 모두 PLEOS_AVD_STOCK와 APP_TASK_RESELECT 복귀. 매번 fresh SDK GET, 수신횟수1→9·동일 가이드/step index1 유지 |
| 실제 무료 AI | 동일 run의 요청 ID 해시와 provider audit를 대조한 Ollama/Qwen3:4b1회, HTTP200/STRUCTURED_VALIDATED/**19.246초**. 유료0·생성 질문 번역0. 실패 run05의 추가 실제호출1회도 원래 audit에 보존 |
| SDK 전체 회귀 | `sdk/official-guide-resources-20261114-01` **20.564초/9단계 PASS**. GET0→callback1/차량 이미지 변경·공식 안내→callback0/닫힘 이미지 정확복귀→재조회→Drive실제UX제한→이전 원문/지원 버튼 거절·dispatch0→Park복귀→unregister/release |
| 개인정보·정리 | 최종 서버 sessions/results/history 각0. 두 host driver의 자체 Console heartbeat 종료/closing 요청 성공. SDK fixture Park/speed0/CLOSED 복구. 기존 app userdata/cache·APK/영상·과거 실패 보존 |
| 이미지 검토 | 최종 앱 17 PNG와 event/provenance를 독립 시각 검토. 결과 `official-resources-20261114-06/visual-review.json`. 매뉴얼 본문 표시 관측과 웹 전체 로딩의 자동 성공 판정은 구분 |

최종 APK `output/apk/carcue-pleos-official-links-debug.apk` SHA256 **9d947d11386fcd7fbf70056b46c18ca32d1293a304904c8ba37db711b0ac191a**. 계측 APK **a993d6e4fd84a80ebf99a87780f6c5744e4bf0e742674c572e1c47cb28b6f70e**. SDK host가 실제 설치된 두 APK를 pull해 동일 해시임을 확인했다.

증거 루트는 `output/qa/official-links-20261114/`이다. `build-artifacts-final.json`, 최종 run의 `host-result.json`/`matched-provider-audit.json`/`console-lease.json`, SDK run의 `validation-result.json`·`console-session-final.json`, `server-cleanup-after-resource-run.json`을 함께 확인한다. 바이너리·상세 QA는 Git 제외 대상이며 source·계약·테스트·Docs를 커밋한다.

UX 연결 복구는 [UX_CONNECTION_RECOVERY.md](UX_CONNECTION_RECOVERY.md)를 따른다. 정책의 지연 콜백/예외/재시도 예산은 합성 gate회귀10개다. 실제 최종 시험은 foreground8회 왕복의 freshGET/UX허용과 Drive제한을 확인했다. Car서비스를 강제로 죽여 모든 재연결 장애를 주입한 시험으로 확대하지 않는다.

### 답변 의미 검토 한계

이 run은 외부 action 파이프라인의 기능 검증이다. 실제 질문 ‘문을 닫기 전에 무엇을 확인해야 하나요?’에 모델은 현재 step2의 ‘출발 전 모든 문/후드/테일게이트 닫힘과 계기판 표시 확인’을 선택했다. 등록 원문 범위의 답변이지만 step1의 끼임 주의는 포함하지 않아 **질문의 완전한 의미 적합성 통과로 계산하지 않는다**. 이 사례를 지우거나 질문을 바꿔 통과 이력으로 만들지 않았다. 현재 단계 문맥과 다른 자유 질문의 관련성·주의문 누락 검토는 후속 과제다. 저장 검수 단위 선택·출처·왕복의 성공과 범용 차량 질문 정확성을 구분한다.

## 실제 연동과 대역

- 실제: 공식 AVD Vehicle SDK2.3.2/VehicleService2.3.22·AndroidCarUX, 실제 HTTP/FastAPI/SQLite, stock Browser2 실행과 앱 복귀, 공식 사이트 URL, Mac의 무료 Ollama/Qwen3 호출.
- 대역/Mock: JVM의 합성 등록자료·UXgate 실패순서, ContextWrapper의 dispatch예외2건. 기존 demo의 문 데이터·주행 시나리오는 그대로 Mock이다. 새로운 runtime Mock 답변/차량값을 추가하지 않았다.
- 미연결/범위 밖: 실차·다른 OEM/차종·안전벨트 센서, 일반 출시 브라우저 호환·모든 웹페이지 로딩 자동 검증, 자유 질문 의미 정확성 전체 검수, 유료 AI. 안전벨트는 기존 안내 이미지다.

## 최종 재시험 명령

기존 전용 AVD를 데이터 초기화 없이 정상 기동하고 `LOCAL_AI_INTEGRATION.md`의 무료 서버를 port8001에서 실행한다. SDK/HTTP 경로와 공식 프로필을 확인한 뒤 고유한 RUN을 사용한다. resource driver는 자체 Console lease를 열고 DDS/bridge를 검사하며 fixture는 바꾸지 않는다. SDK driver만 격리 AVD의 문/속도/gear를 바꾸고 복구한다.

```bash
.venv/bin/python scripts/validate_official_resources.py --run-id NEW_UNIQUE_RESOURCE_RUN --install
.venv/bin/python scripts/validate_pleos_official_guide.py \
  --avd CarCue_Pleos21_LocalAI --run-id NEW_UNIQUE_SDK_RUN \
  --output-dir output/qa/official-links-20261114/sdk \
  --apk output/apk/carcue-pleos-official-links-debug.apk
```


최종 환경 정리는 `environment-cleanup.json`에 기록했다. 자체 lease 둘과 bootstrap lease의 closing 요청/스레드 종료를 확인한 뒤 AVD를 정상 종료했고 launcher exit0·ADB 장치 제거를 확인했다. AVD userdata와 app/cache를 지우지 않았다. 무료 서버8001/LIVE 및 Ollama0.40.16은 계속 실행 중이다.
