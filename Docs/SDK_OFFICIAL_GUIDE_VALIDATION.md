# 실제 SDK 문 상태와 공식 가이드 연결

2026-11-14. 공식 자료 등록은 `feature/ioniq5-official-door-content`, 앱 연결과 기기 시험은 `feature/sdk-contextual-door-guide`에서 분리했다. Mock 화면을 추가한 작업이 아니다. 전용 AVD의 실제 SDK 수신과 실차 검증은 구분한다.

**최신 결과:** `feature/pleos-console-readiness`에서 Console heartbeat/준비 확인을 보완한 뒤 최신 앱 `e9ab702d…`의 전체 SDK 시험 run05가 **19.188초 통과**했다. 문 개폐·차량 표시·공식 안내·재조회·주행 제한/복귀·해제와 최종 Console 복구까지 확인했다. 아래 run04 미완료 기록은 당시 이력이며 현재는 해소됐다. 상세 원인·재현·증거는 `PLEOS_CONSOLE_RECOVERY.md`를 따른다.

## 로컬 AI 최종 APK의 SDK 회귀 · 2026-11-14

`output/apk/carcue-pleos-local-ai-final-debug.apk`(SHA-256 `ddbca88ce3f522872ee35c90a0a5b7875fcc1664d411a28e983e0b89dc960a1f`)로 전체 SDK 시험을 다시 수행했다. 테스트 APK `1d7d5d9b6723eadbfbcba046f6f0f16484a536552c24d066d635387153b38986`와 설치본 해시가 일치했고 **23.192초 OK(1 test)**였다. 증거는 `output/qa/pleos-official-guide/official-guide-local-ai-final-20261114-02/`다.

별도 `CarCue_Pleos21_LocalAI`/API34/user10에서 실제 Capability·GET CLOSED→OPEN/CLOSED callback·차량 프레임 변경과 원본복귀·정확한 공식 가이드/두 출처·재조회·주행 차단·Park복귀·이용종료/unregister/release를 확인했다. Console도 Park/속도0/CLOSED로 복구했다. 기존 AVD userdata를 보존했고, `car_service` 부재를 우회하거나 UX 조건을 완화하지 않았다. 이 SDK 시험은 로컬 AI 호출 0회이며 AI 앱 시험과 구분한다. 이후 guarded AI 시험용 test-only APK는 별도 해시/실행으로 기록한다. 앱 APK는 동일하다. 앱 Window 캡처이지 실차/물리 디스플레이 녹화 검증은 아니다.

## 구현한 데이터 흐름

1. 사용자가 `ioniq5-ne1-2024-kr`(2024 한국시장 아이오닉 5)을 선택한다. 이 선택은 매뉴얼 적용 범위를 정하며 SDK의 차종/VIN 인증이 아니다.
2. 앱은 실제 FastAPI의 `/v1/guides`에서 해당 프로필·언어의 게시 가이드를 받아 검증·캐시한다.
3. SDK 어댑터가 Capability와 실제 GET/Listener 결과를 공통 Reading으로 변환한다.
4. `DoorGuidePolicy`가 PLEOS, SUPPORTED, VALUE, 60초 이내 수신, `door.position/ROW_1_LEFT/OPEN`, raw 1, UX 허용을 확인한다. 등록 룰과 프로필·매뉴얼 세트/판본·언어·검증된 가이드가 정확히 하나로 일치해야 관련 버튼을 표시한다.
5. 버튼을 누를 때도 정책을 다시 검사한다. CLOSED·미수신·오류·오래된 값·다른 영역·MOCK·UX 불명/제한은 해당 추천을 만들지 않는다.
6. 실제 가이드 화면에는 현재 SDK 수신 상태·시각·재조회, 원문 판본과 공식 두 URL을 표시한다. 문 닫힘으로 잠금·다른 문/후드/테일게이트·운행 안전을 추정하지 않는다.

SDK 앱에서는 과거의 `__layout_preview__` 메뉴를 표시하지 않는다. 이전 demo flavor와 소스는 보존한다. 한국어·영어·일본어 UI 및 문 안내를 제공하며 선택 언어가 한국 판매사양을 바꾸지 않는다. 공식 원문 대조·AI 보조 검토 범위와 한계는 `MANUAL_REVIEW_IONIQ5_2024_KR.md`를 따른다.

## 검증 환경과 재현

- Kotlin/Compose, SDK 2.3.2, 전용 CarCue_Pleos21/API 34, Vehicle Service 2.3.22, 사용자 10, 2560×1440.
- 로컬 실제 서버: `http://127.0.0.1:8001`, `CARCUE_MODE=LIVE`. APK는 `http://10.0.2.2:8001`로 HTTP 연결한다. 개발용 debug 연결이며 외부 배포가 아니다.
- OpenAI 키·모델은 비운 상태다. 이 시험은 실제 AI 호출을 수행하지 않는다. LIVE 서버와 차량값 PLEOS, AI 실제 호출 여부는 각각 별도 항목이다.
- 기기 시험: `PleosOfficialGuideTest#sdkDoorCallbacksOpenPublishedOfficialGuideAndRespectDrivingRestriction`.
- 호스트 드라이버: `scripts/validate_pleos_official_guide.py`.
- 수신 시각은 기기 현지 시간에 UTC 오프셋을 함께 표시한다. 언어/한국 판매사양으로 기기 시간대를 추정하지 않는다. 전용 AVD의 기본 시간대가 UTC-08:00이므로 증거의 UTC·한국시각과 달력 날짜가 다를 수 있다.

```bash
JAVA_HOME=/Users/younsung/hyundai/.tooling/jdk-17.0.21+9/Contents/Home \
ANDROID_HOME=/Users/younsung/hyundai/.tooling/android-sdk \
ANDROID_SDK_ROOT=/Users/younsung/hyundai/.tooling/android-sdk \
android/gradlew -p android :app:testDemoDebugUnitTest \
  :app:assemblePleosDebug :app:assemblePleosDebugAndroidTest \
  -PcarcueServerUrl=http://10.0.2.2:8001 \
  --offline --console=plain --no-daemon --max-workers=2

# 공식 서버/전용 AVD 준비 후, 실행별로 고유 run ID를 사용
.venv/bin/python scripts/validate_pleos_official_guide.py \
  --adb /Users/younsung/hyundai/.tooling/android-sdk/platform-tools/adb \
  --apk /absolute/path/app-pleos-debug.apk \
  --test-apk /absolute/path/app-pleos-debug-androidTest.apk \
  --install --run-id <unique-run-id> \
  --output-dir /Users/younsung/hyundai/output/qa/pleos-official-guide
```

드라이버의 외부 Virtual Console 조작은 격리된 AVD에 시험 조건을 주는 역할이다. 앱은 SET API를 사용하지 않고 실제 SDK GET/변경 callback을 읽는다. 실제 자동차에서 문을 조작한 시험으로 보고하지 않는다. 물리 기기 serial은 드라이버에서 거절한다.

## 정상 런처와 물리 표시 확인

기능 시험의 Compose `captureToImage()`는 앱 Window 렌더링을 검증한다. 최종 물리 디스플레이 합성과 같은 증거로 취급하지 않는다. [공식 Pleos 실행 가이드](https://document.pleos.ai/en/docs/pleos-only/vehicle-app-developer-guide/adb-command-reference-guide#launch-an-app)는 GNB 선택과 유사한 런처 실행을 아래처럼 안내하며 `am start` 직접 실행과 구분한다.

```bash
adb -s emulator-5584 shell monkey -p com.carcue.app -c android.intent.category.LAUNCHER 1
```

첫 원본 녹화에서 CarCue가 표시되지 않아 추가 조사했다. AVD 패키지 설치 서비스의 `StorageManagerService.allocateBytes`/PackageManagerInternal null 오류도 관측해, 사용자 데이터와 디스크를 유지한 채 정상 종료 후 `-no-snapshot-load -no-snapshot-save` 콜드 부팅을 수행했다. SDK/앱 정책과 기기 준비 기준을 완화하지 않았다.

콜드 부팅과 새 APK 설치 해시 검증 뒤 공식 런처로 실행한 실제 `adb screencap`에서 CarCue 프로필 선택 화면을 확인했다. 증거는 `output/qa/pleos-official-guide/normal-launch-20261114-01/physical-normal-launch.png`다. 나머지 시스템 표시 영역의 검정과 앱 자체의 가시성을 구분했다. UIAutomator XML 조회의 30초 timeout은 성공한 것으로 처리하지 않았다.

Compose 1.6.6은 drawing이 꺼져 있을 때 캡처 동안만 켰다가 복원하는 코드 경로가 있고, [Android 공개 HardwareRenderer API](https://developer.android.com/reference/android/graphics/HardwareRenderer#isDrawingEnabled())도 테스트 중심 emulator에서 drawing이 꺼질 수 있다고 설명한다. 이것만으로 이번 원인이 ComposeRule였다고 단정하지 않는다. 읽기 전용 `debug.hwui.drawing_enabled`는 빈 값이었으며 초기 기본값 true 경로와 실행 중 프로세스의 override는 별개다. 정상 런처, 테스트 중 drawing 관측, 물리 캡처, 영상 QA를 나눠 기록한다. 프로덕션 Manifest/TaskView를 추측 변경하지 않았다.

추가 렌더링 측정용 test APK 후보 `311262c9…`는 빌드/읽기 전용 검토를 통과했으나 설치에서 `INSTALL_FAILED_VERIFICATION_FAILURE: Integrity verification timed out`이 발생했다. 검증 설정을 끄거나 우회하지 않았다. 실험 코드와 후보는 QA에 보존하고 활성 테스트에서 제외했다. 이미 정상 설치된 핵심 검증용 `2cc2ef14…`와 같은 소스로 복원했고, run04는 Console 준비 단계에서 중단됐지만 후속 run05는 완료했다. 빌드만 통과한 렌더링 실험을 기기에서 검증한 것으로 보고하지 않는다.

녹화는 선택적인 `--record` 옵션이다. 영상 시작/수집/앱 가시성은 SDK core 결과와 구분하며, 검정 또는 다른 앱이 찍힌 MP4를 CarCue 소개 영상으로 제공하지 않는다. 기능·출처·UX·구독 해제·최종 콘솔 복구의 완료 조건은 그대로 유지한다.

## 결과 기록

공식 콘텐츠를 포함한 APK/test APK 빌드와 계약·155개 UI 문구·게시 카탈로그 검사를 통과했다. 순수 정책/파일 캐시/요청 순서/상태 연결의 JVM 테스트는 42개다. 서버/도구 회귀는 Console 7개를 추가해 최신 140개다.

| 범위 | 실제 결과와 증거 |
| --- | --- |
| 최신 APK 전체 흐름 | 앱e9ab702d…/테스트2cc2ef14…, run05 **19.188초 OK**. 실제 설치 SHA·SDK/차량/가이드/주행 제한/해제·최종 Console 복구까지 통과 |
| 공식 SDK 전체 흐름 | 소스 `9639181`, `official-guide-20261114-sdk-e2e-03`의 instrumentation 1개, **43.685초 OK**. 설치 앱/테스트 SHA를 대조했고 최종 콘솔 Park·속도0·문 CLOSED 복구도 확인 |
| 시각화/안내 | 실제 GET CLOSED → OPEN callback 및 차량 픽셀 변경 → 공식 가이드·판본·두 원문 링크 → CLOSED callback 및 최초 이미지와 SHA 일치 → 명시 재조회 GET CLOSED |
| UX/수명주기 | 실제 Drive/속도20에 UX 제한 callback, 안내 차단 및 제한 중 진입 거절 → Park 복귀 → 이용 종료·동일 Listener unregister·SDK release |
| 이전 시각 개선본 부분 확인 | 소스 `82a32b9`, 앱 `e9ab702d…`. 당시 빌드·설치 SHA·정상 런처의 물리 앱 표시·실제 SDK Capability/GET0/callback0 확인. OPEN부터의 미완료 범위는 후속 run05에서 해소 |
| 이전 준비 실패 | `official-guide-20261114-sdk-e2e-04`는 instrumentation 전 Virtual Console HTTP503 `emulator_inactive`/DDS 미준비로 실패. 해당 시도를 성공이나 crash/ANR 부재로 바꿔 기록하지 않음 |

전체 흐름 통과본의 앱 SHA256은 `118b9c86bc249921820e83c05d4ccf646698e33a708f73bb0a8a825f522e3e8c`, 테스트는 `2cc2ef14e0681aa33c196298a28b615c947c237691e5438d11cdac0a64ad5a33`다. 증거는 `output/qa/pleos-official-guide/official-guide-20261114-sdk-e2e-03/validation-result.json`, `instrumentation.txt`, `sdk-events.txt`, `run-status.json`이다. 앱 Window 캡처는 `official-guide-open.png`, `driving-guide-blocked.png`, 차량 개폐 PNG에 남겼다. 같은 실행의 MP4는 앱 표시 QA를 통과하지 못해 소개 영상으로 사용하지 않았다.

현재 전달 APK `output/apk/carcue-pleos-official-guide-debug.apk`의 SHA256은 `e9ab702dc191294372d9e7a8dce9216394f3b440825cbf892ffea5867a66ee97`이며 run05에서 실제 설치본과 대조해 전체 기기 시험을 통과했다. run03과 생산 코드·콘텐츠 차이는 시각 포맷 두 곳의 UTC 오프셋 추가뿐이며, 소스 비교에 그치지 않고 이 바이너리를 직접 재시험했다. 이전 `118b9c86…` APK 파일은 후속 빌드로 교체돼 현재 전달하지 않으며, 별도 경로의 동일 기준 소스 재빌드 `48171624…`도 해시가 달라 검증본으로 제공하지 않았다. 로그/캡처 원본은 유지한다.

이전 부분 검증의 정상 런처 증거는 `output/qa/pleos-official-guide/normal-launch-20261114-01/`의 `installed-app.json`, `normal-launch-smoke.json`, `physical-normal-launch.png`다. 추가 실패·렌더링 후보는 각각 실행 폴더에 보존한다. 당시 작업 전 정지 상태였던 전용 AVD는 종료 명령 성공·프로세스 종료·ADB 목록 제거를 확인해 다시 정지했다. 사용자 데이터/스냅샷 파일과 검증 설정은 유지했다. 이전 `normal-session-preflight-20261114-01` 당시 warmup의 SDK 해제 호출은 미확인이며 VM 종료에 따른 정리로만 기록했다(`normal-session-preflight-20261114-01/vm-cleanup.json`). 후속 run05는 SDK unregister/release를 직접 확인했고 새 정상 런처 증거와 함께 `PLEOS_CONSOLE_RECOVERY.md`에 기록했다.

시험 증거는 `output/qa/pleos-official-guide/<run-id>/`와 앱의 실행별 QA 폴더에 새로 기록한다. 실행별 QA 보존 경로와 원본 영상·사용자 데이터는 유지하며 `pm clear`, `logcat clear`, wipe-data를 사용하지 않는다. Gradle 빌드 출력 APK는 후속 빌드에서 교체되므로 별도 보존 여부와 설치 해시를 위와 같이 구분한다. 수집 로그는 문·UX·수명주기의 허용된 이벤트로 제한해 VIN 등 원시 차량정보를 저장하지 않는다.
