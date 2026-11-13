# CarCue 실행과 개발

## 구조

`android/` Compose 차량 앱, `backend/` FastAPI, `content/` 데이터, `contracts/` 인계 Schema, `assets/` 원본 시각 자산, `reference/` 원본 제안서다. 기획 문서는 `Docs/`에서 관리한다.

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
./gradlew :app:assemblePleosDebug -PpleosSdkVersion=2.3.2
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

LIVE는 서버 환경에 `CARCUE_MODE=LIVE`, `OPENAI_API_KEY`, `OPENAI_MODEL`을 설정한다. `backend/.env.example`은 빈 설정 예시이며 실제 비밀값은 Git과 채팅에 남기지 않는다. 모델은 운영자가 Structured Outputs 호환 모델로 선택한다. `.env` 파일은 자동으로 읽지 않으므로 프로세스 환경으로 주입한다.

LIVE에서 공개 가능한 VERIFIED 프로필과 PUBLISHED 가이드를 등록하기 전에는 세션을 시작할 수 없다. 검수 자료가 없으면 OpenAI를 호출하지 않는다. 초기 LIVE 답변은 검수된 같은 언어 원문의 추출 방식이며, 출처 메타데이터와 허용 action은 서버에서 조립한다. 외부 API 요청은 25초 timeout, 자동 재시도 0회, 1,500 output token 상한이다.

기본 세션 만료는 120분, 세션 요청 상한은 30회, 전체 분당 상한은 200회다. `CARCUE_SESSION_MINUTES`, `CARCUE_SESSION_REQUEST_LIMIT`, `CARCUE_GLOBAL_REQUEST_LIMIT`로 변경할 수 있다. 운영 배포 전 HTTPS, 서버 접근 제어와 부하·보관 정책을 별도로 검증한다. 이 세션에서 외부 배포하지 않았다.

## 콘텐츠와 언어

- `content/profiles/catalog.json`: 언어와 분리된 차량 사양. 제공한 두 항목은 개발용 UNVERIFIED다.
- `content/guides/`: Schema를 지키고 정확한 profile/manual/source version과 검수된 출처 절을 등록한다. DRAFT는 검색/답변에 사용하지 않는다.
- `content/locales/catalog.json`: 48개 언어 후보의 RTL·UI/가이드 지원 상태. Mock 선택 목록은 `mock_visible=true`인 한국어·영어·일본어 3개이며, 다른 후보 데이터는 보존한다.
- `content/locales/ui.json`: 119개 UI 문구의 한국어·영어·일본어 초안. 실제 AI 번역이나 검수된 차량 안내를 뜻하지 않는다. 다른 후보는 준비 중이며 pleos 빌드에서는 영어 대체 안내를 표시한다. 언어를 추가할 때 화면 코드를 바꿀 필요가 없다.
- `content/locales/country-locales.json`: 50개 지역의 개발 후보 매핑이며 방문 순위나 지원 완료 목록이 아니다.
- `scripts/prepare_content.py`: 개발용 초안을 다시 만드는 도구. 검수 콘텐츠를 등록한 이후에는 백업 없이 실행하지 않는다.

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

## 시연 순서

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
