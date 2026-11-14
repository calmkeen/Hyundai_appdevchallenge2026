# CarCue 실행과 개발

## 구조

`android/` Compose 차량 앱, `backend/` FastAPI, `content/` 데이터, `contracts/` 인계 Schema, `assets/` 원본 시각 자산, `reference/` 원본 제안서다. 기획 문서는 `Docs/`에서 관리한다.

## 현재 실제 개발 흐름: SDK 문 상태와 공식 가이드

2024 한국시장 아이오닉 5의 공식 매뉴얼 요약을 실제 HTTP 서버에서 받고, 전용 AVD의 실제 Pleos 문 상태와 연결한다. 자료 검토는 `MANUAL_REVIEW_IONIQ5_2024_KR.md`, SDK 기기 시험은 `SDK_OFFICIAL_GUIDE_VALIDATION.md`를 따른다.

저장소 루트에서 가이드용 LIVE 서버를 기존 Mock 서버와 별도 포트로 실행한다. 키를 비운 이 명령은 외부 AI를 호출하지 않는다.

```bash
mkdir -p output/qa
CARCUE_MODE=LIVE OPENAI_API_KEY= OPENAI_MODEL= \
CARCUE_DB=output/qa/official-guide-live.sqlite3 \
.venv/bin/python -m uvicorn app.main:app --app-dir backend \
  --host 127.0.0.1 --port 8001 --no-access-log
```

JDK/SDK를 지정하고 실제 SDK 앱을 빌드한다.

```bash
JAVA_HOME=/Users/younsung/hyundai/.tooling/jdk-17.0.21+9/Contents/Home \
ANDROID_HOME=/Users/younsung/hyundai/.tooling/android-sdk \
ANDROID_SDK_ROOT=/Users/younsung/hyundai/.tooling/android-sdk \
android/gradlew -p android :app:assemblePleosDebug \
  :app:assemblePleosDebugAndroidTest -PpleosSdkVersion=2.3.2 \
  -PcarcueServerUrl=http://10.0.2.2:8001 --offline --no-daemon --max-workers=2
```

전용 AVD의 사용자 10에 APK를 설치하고 `ioniq5-ne1-2024-kr`/한국어·영어·일본어 중 하나를 선택한다. Park 상태에서 SDK 문 상태를 확인하고, 외부 Virtual Console로 앞좌석 왼쪽 문 열림 시험 조건을 주면 앱의 관련 안내 버튼이 나타난다. 가이드에서 재조회를 누르면 SDK GET을 수행한다. 앱이 문을 제어하지 않는다. CLOSED·미확인·오래된 값·다른 영역·주행 제한에서는 해당 추천을 하지 않는다.

프로필은 사용자가 선택한 매뉴얼 범위이며 SDK의 자동 차종 인증이 아니다. 실제 자동차의 문을 조작한 검증과도 구분한다. 별도 Mock 흐름은 기존 회귀용으로 아래에 보존한다.

Console503 재시험은 `PLEOS_CONSOLE_RECOVERY.md`를 따른다. 공식 설정대로 Cold boot한 전용 AVD의 부팅과 사용자10을 확인한다. 호스트 검증 도구는 독립 heartbeat를 유지하고 문/속도/페달/기어의 실제 DDS 준비를 확인한 뒤 fixture를 조작한다. 단일 heartbeat200을 준비 완료로 간주하지 않는다. 최신 e9 APK의 전체 SDK 시험은 run05에서 완료했다.

## Android

JDK 17 또는 Gradle 8.10.2가 지원하는 JDK, Android Platform 35 / Build Tools 35.0.0이 필요하다. 최종 검증은 Temurin 17.0.21+9 ARM64로 수행했다. 이 작업 환경에서는 `JAVA_HOME=/Users/younsung/hyundai/.tooling/jdk-17.0.21+9/Contents/Home`을 사용한다.

```bash
cd /Users/younsung/hyundai/android
# Android Studio에서 SDK 위치를 지정하거나 local.properties에 sdk.dir을 설정한다.
./gradlew :app:assembleDemoDebug :app:testDemoDebugUnitTest
```

Mock APK: `android/app/build/outputs/apk/demo/debug/app-demo-debug.apk`. 일반 Android AVD에서 실행 가능하며 Pleos SDK를 포함하지 않는다. 기본 서버 URL은 Android 에뮬레이터의 호스트를 뜻하는 `http://10.0.2.2:8000`이다.

```bash
./gradlew :app:assembleDemoDebug -PcarcueServerUrl=http://10.0.2.2:8000
adb -s <일반-테스트-AVD> install -r app/build/outputs/apk/demo/debug/app-demo-debug.apk
adb -s <일반-테스트-AVD> shell am start -n com.carcue.app.demo/com.carcue.app.MainActivity
```

로컬 HTTP는 debug에서만 허용한다. release는 HTTPS 서버가 필요하다. OpenAI 키를 Gradle property나 APK에 넣지 않는다.

실제 Pleos 빌드는 별도다. 기본 버전은 실제 빌드·수신한 Vehicle SDK 2.3.2다.

```bash
./gradlew :app:assemblePleosDebug -PpleosSdkVersion=2.3.2 -PcarcueServerUrl=http://10.0.2.2:8001
```

이번 환경은 Pleos Connect 2.1.0 / API 34 / Vehicle Service 2.3.22에서 설치·실행했다. 다른 환경에서도 해당 버전과 Maven 접근을 확인해야 한다. 일반 폰에서 Pleos SDK가 실행된다고 가정하지 않는다. 차량 속성 권한은 읽기용 `CAR_DOORS`이며 SDK 바인딩·네트워크 권한을 별도로 사용한다. CONTROL_* 권한과 제어 API 호출은 없다.

## 서버

저장소 루트에서 Python 3.10 이상을 사용한다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock.txt
CARCUE_MODE=MOCK .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-access-log
```

기본 모드는 MOCK이며 외부 AI를 호출하지 않는다. `/health`, `/docs`로 API를 확인할 수 있다. 세션은 `POST /v1/sessions`에서 발급하며 질문·번역·삭제에 `Authorization: Bearer <token>`이 필요하다. 프로필 ID만으로 대화에 접근할 수 없다.

공식 가이드 API는 `CARCUE_MODE=LIVE`에서 AI 키 없이도 동작한다. 실제 AI 연결은 별도로 서버 환경의 `OPENAI_API_KEY`, `OPENAI_MODEL`을 설정하고 호출 결과를 검증해야 한다. `backend/.env.example`은 빈 설정 예시이며 실제 비밀값은 Git과 채팅에 남기지 않는다. 모델은 운영자가 Structured Outputs 호환 모델로 선택한다. `.env` 파일은 자동으로 읽지 않으므로 프로세스 환경으로 주입한다.

LIVE에서 공개 가능한 VERIFIED 프로필과 PUBLISHED 가이드를 등록하기 전에는 세션을 시작할 수 없다. 검수 자료가 없으면 OpenAI를 호출하지 않는다. 초기 LIVE 답변은 검수된 같은 언어 원문의 추출 방식이며, 출처 메타데이터와 허용 action은 서버에서 조립한다. 외부 API 요청은 25초 timeout, 자동 재시도 0회, 1,500 output token 상한이다.

기본 세션 만료는 120분, 세션 요청 상한은 30회, 전체 분당 상한은 200회다. `CARCUE_SESSION_MINUTES`, `CARCUE_SESSION_REQUEST_LIMIT`, `CARCUE_GLOBAL_REQUEST_LIMIT`로 변경할 수 있다. 운영 배포 전 HTTPS, 서버 접근 제어와 부하·보관 정책을 별도로 검증한다. 이 세션에서 외부 배포하지 않았다.

## 콘텐츠와 언어

- `content/profiles/catalog.json`: 언어와 분리된 차량 사양. 기존 두 항목은 개발용 UNVERIFIED로 보존하고 공식 2024 한국시장 아이오닉 5 매뉴얼 선택 프로필을 추가했다.
- `content/guides/`: Schema를 지키고 정확한 profile/manual/source version과 검수된 출처 절을 등록한다. DRAFT는 검색/답변에 사용하지 않는다.
- `content/locales/catalog.json`: 48개 언어 후보의 RTL·UI/가이드 지원 상태. Mock 선택 목록은 `mock_visible=true`인 한국어·영어·일본어 3개이며, 다른 후보 데이터는 보존한다.
- `content/locales/ui.json`: 155개 UI 문구의 한국어·영어·일본어 초안. UI 번역과 개별 가이드의 검토 상태를 구분한다. 공식 문 안내는 한국시장 원문의 3언어 자체 요약이며 다른 후보 언어/주제는 준비 중이다. 언어를 추가할 때 화면 코드를 바꿀 필요가 없다.
- `content/locales/country-locales.json`: 50개 지역의 개발 후보 매핑이며 방문 순위나 지원 완료 목록이 아니다.
- `scripts/prepare_content.py`: 개발 초기 데이터 생성 도구. VERIFIED 프로필이나 PUBLISHED 가이드가 있으면 쓰기 전에 중단한다.

QR 예시:

```bash
adb shell am start -a android.intent.action.VIEW -d 'carcue://guide?profile_id=demo-ioniq5-2024-kr' com.carcue.app.demo
```

등록 ID만 선택하며 임의 URL 다운로드, VIN 인증, 폰-차량 권한 부여를 하지 않는다.

## 검증

```bash
.venv/bin/python -m pytest backend/tests -q
cd android
./gradlew :app:testDemoDebugUnitTest
./gradlew :app:connectedDemoDebugAndroidTest
```

Android 기기 테스트는 Mock 서버를 먼저 실행하고 일반 테스트 AVD 하나를 연결한다. 저장된 사용자 기기와 혼동하지 않게 `ANDROID_SERIAL`을 지정한다. 테스트 이미지에는 MOCK과 개발 프로필이 표시된다.

## 기존 Mock 회귀 시연 순서

1. 미검수 시연 프로필을 선택하고 한국어 또는 영어를 선택한다.
2. 현재 상태에서 MOCK 문 열림과 수신 출처·시각을 확인한다.
3. 문 상세와 미등록 공식 안내 표시를 확인한다.
4. 사용 가이드의 **Mock 화면 예시**에서 단계 이동 후 질문하고 돌아온다.
5. 서버가 연결돼 있으면 자료 부족 답변과 MOCK 모드를 확인한다. 번역은 기본 모드에서 불가이며 가짜 결과를 표시하지 않는다.
6. 이용 설정에서 UNAVAILABLE/CHECK_FAILED/UNSUPPORTED/STALE/RESTRICTED/UX_UNKNOWN을 전환한다. PARKED는 Mock 제한 해제다.
7. 이용 종료 후 프로필 선택으로 돌아오고 이전 질문·언어·상태가 사라지는지 확인한다.

실제 SDK 시연은 `SDK_CAPABILITY_REPORT.md`의 수신 검증 순서에 따라 별도 촬영해야 한다.

## 실제 SDK 회귀 재현

SDK와 테스트 APK를 전용 AVD에 설치한 뒤 저장소 루트에서 실행한다.

```bash
.venv/bin/python scripts/validate_pleos.py --serial emulator-5584
```

테스트는 공식 Virtual Console 8088 포트를 forward하고 heartbeat를 유지하면서 앞좌석 왼쪽 문을 닫힘→열림으로 시뮬레이션한다. 실제 차량/폰 serial에서는 실행을 거부한다. 앱은 차량 SET을 호출하지 않는다. 원격 이미지 설치 파일은 Git에 포함하지 않는다.

이 이미지에는 표준 android.car 공유 라이브러리 등록이 없어 선택 선언을 사용한다. 런타임 클래스는 제공되어 실제 UX GET/변경/복귀를 확인했다. 다른 환경에서 클래스나 제한 상태를 읽지 못하면 입력·긴 안내를 차단하며 초기 제한 화면의 ‘내 차 상태 보기’로 읽기 전용 상태만 볼 수 있다. 이 경로는 차종·운행 안전 여부를 판정하지 않는다. 실제 수신 여부는 로그에서 별도로 확인한다.

결과: `output/qa/`의 Mock 캡처·영상, 실제 SDK 로그·캡처. APK는 `output/apk/`에 복사하며 Git에서는 제외한다.

실제 UX 제한 시뮬레이션 재현 도구는 `scripts/validate_pleos_ux.py`다. 기본 serial은 emulator-5584이며 테스트 전용이다. 주차 상태로 복구한 뒤 종료한다.

## 실제 APK의 다국어 Mock 영상 녹화

부팅된 테스트 AVD `CarCue_UI35`에서 다음을 실행한다. 지정한 demo APK를 설치하고 **해당 테스트 앱의 데이터만 초기화**한다. 연결된 대상이 emulator인지 확인하며 실기기는 거부한다.

```bash
python3 scripts/record_mock_languages.py
```

한국어 → 영어 → 일본어 → 한국어 순서로 실제 언어 버튼을 누른다. 각 언어에서 홈과 문 상태 화면을 보여 주며 언어 목록과 터치 위치도 녹화한다. 영상은 Android `screenrecord`의 원본 MP4이며 화면 합성·속도 변경·AI 프레임 생성을 사용하지 않는다. 차량 상태는 demo의 MOCK 값이고 외부 AI는 호출하지 않는다.

결과는 `output/qa/carcue-mock-languages.mp4`와 같은 이름의 JSON이다. JSON에 원본 APK와 설치된 APK의 SHA256 일치, AVD 정보, 화면 문구별 시각, 영상 해시를 기록한다. 앱 소스 커밋은 JSON의 `git_commit`을 따른다. `--serial`, `--adb`, `--apk`, `--output`으로 경로를 지정할 수 있다.

기능당 2초의 이미지·3D 포함 편집본은 `python3 scripts/render_mock_short.py`로 만든다. 구성과 원본 구분은 `VIDEO_STORYBOARD.md`, 시간·소스·확대 영역은 `video-short.json`에서 관리한다. 이전 `carcue-mock-visuals-3d.mp4`는 32초 편집본, `carcue-mock-short.mp4`는 이전 28초 편집본, `carcue-mock-languages.mp4`는 무편집 녹화다. 3D 차량 구간은 기존 `carcue-pleos-sdk.mp4`가 필요하며 Pleos 에뮬레이터 시스템 UI로 출처를 표시한다.

## 실제 실행 원본 촬영: 앱 안의 시각 요소와 연속 실행

현재 기준은 실제 APK 내부의 3D·사진 기능을 사용한다. 위의 영상 합성 도구는 이전 결과 재현용이다. 구현은 `NATIVE_VISUALS.md`를 따른다. demo와 기기 테스트 APK를 빌드한 뒤 테스트 AVD가 부팅된 상태에서 실행한다.

```bash
python3 scripts/record_native_showcase.py
```

`NativeShowcaseTest`가 실제 버튼과 드래그로 기능을 진행하고 각 화면을 2초 유지한다. 호스트가 테스트 AVD의 demo 앱 데이터를 초기화하고 설치 APK 해시를 대조한 뒤, 하나의 `screenrecord` 원본을 `output/qa/carcue-native-run.mp4`에 저장한다. 같은 이름의 JSON과 `native-showcase-instrumentation.txt`에서 실행 증거를 확인한다. 별도 사진 장면이나 Pleos 시스템 UI 삽입은 하지 않는다.

## 앱 소개 영상 제작

원본 실행 녹화를 보존한 상태에서 `python3 scripts/render_app_intro.py`로 소개 영상을 만든다. 결과는 `output/qa/carcue-app-intro.mp4`이며 32초·1920×1080·30fps다. 실제 기능 화면에 제목·설명·시작·마무리·외부 무료 배경음악을 더한다. 기획은 `APP_INTRO_VIDEO.md`, 편집 구성은 `app-intro.json`을 따른다. 영상의 Mock 표시와 AI 준비 중 표시를 유지한다.

음원과 실차 사진의 출처·라이선스는 `MEDIA_CREDITS.md`를 따른다. 음악 파일이 없으면 소개 영상 도구가 검증된 원작자 URL에서 다운로드하고 SHA256을 대조한다. 유튜브 게시 시 `output/qa/carcue-app-intro-credits.txt`의 음악 표기를 설명란에 포함한다.
