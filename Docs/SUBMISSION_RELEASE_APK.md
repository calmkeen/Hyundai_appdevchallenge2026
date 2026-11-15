# 제출용 signed Pleos release APK

2026-11-15. 새 제출 APK는 `:app:assemblePleosRelease`, package `com.carcue.app`, versionCode **2**, versionName **0.1.1-rc1**로 빌드한다. 실제 Vehicle SDK 2.3.2와 `IS_MOCK=false`를 사용하며 `debuggable=false`다. 이전 debug APK와 소개 영상은 보존한다. 새 APK의 서명·동봉 안내·버전은 이전 영상에서 검증된 바이너리와 다르다.

공식 제출 파일은 `apk/CarCue_release.apk`로 준비한다. **CarCue는 프로젝트명인 임시 파일명이며 팀명·개인 참가자명이 확정되면 공식 `팀명_앱이름_release.apk` 규칙에 맞춰 바꿔야 한다.** 실제 파일 해시·빌드 소스 커밋·검사 결과는 같은 디렉터리의 `SUBMISSION_RELEASE_MANIFEST.json`을 따른다. 이 문서만으로 기기 시험 통과를 뜻하지 않는다.

## 키와 재빌드

개인키와 비밀번호는 Git/APK에 넣지 않는다. `CARCUE_RELEASE_SIGNING_PROPERTIES`가 가리키는 비공개 Java properties 파일에 `storeFile`, `storePassword`, `keyAlias`, `keyPassword`를 보관하거나 `CARCUE_RELEASE_STORE_FILE`, `CARCUE_RELEASE_STORE_PASSWORD`, `CARCUE_RELEASE_KEY_ALIAS`, `CARCUE_RELEASE_KEY_PASSWORD` 네 환경변수로 제공한다. 환경변수가 properties보다 우선한다. 키가 없으면 release 작업은 실패하며 debug 키·unsigned APK로 대체하지 않는다.

처음 한 번만 프로젝트 전용키를 만든다. 이 명령은 키 생성 후 종료하고 빌드/설치하지 않는다. 기존 키·properties가 모두 있으면 보존하며, 한 파일만 있으면 중단한다. 비밀번호는 무작위 생성하고 출력하지 않으며 두 파일 권한은 0600이다. 예시 경로는 Git에서 제외된다.

```bash
python3 scripts/build_submission_release.py --init-signing
```

JDK17, Android SDK35/Build Tools35.0.0, 캐시된 Gradle8.10.2와 Pleos 의존성이 필요하다. 기본 도구 경로는 저장소의 `.tooling/`이며 `--java-home`, `--android-sdk` 또는 `JAVA_HOME`, `ANDROID_HOME`으로 바꿀 수 있다. `GRADLE_USER_HOME`도 표준 Gradle 환경변수다. 최초 의존성 다운로드가 필요하면 `--online`을 명시한다(기본 offline). 아래 명령은 최대 heap768MB·worker1·offline으로 빌드와 release JVM/lint 검사를 수행한다. AVD·서버·모델은 시작하지 않는다.

```bash
python3 scripts/build_submission_release.py \
  --signing-properties .tooling/signing/carcue-release.properties \
  --submission-avd --server-url http://10.0.2.2:8001 --checks
```

결과는 `android/app/build/outputs/apk/pleos/release/app-pleos-release.apk`다. 키/비밀번호는 따로 안전하게 백업해야 같은 인증서로 다음 버전을 서명할 수 있다. 원시 Gradle 실행도 `CARCUE_RELEASE_SIGNING_PROPERTIES`와 `-PcarcueSubmissionAvd=true -PcarcueServerUrl=http://10.0.2.2:8001`을 사용한다. 일반 release는 제출 AVD 프로필을 명시하지 않으면 HTTPS URL을 반드시 지정해야 한다. 키 없이 debug 빌드·코드 검토는 가능하다.

## 검토 서버와 HTTPS 경계

이 제출 APK는 명시적 `--submission-avd`/`-PcarcueSubmissionAvd=true` 프로필로 빌드해 독립 로컬 서버 `http://10.0.2.2:8001`로 연결한다. 일반 release 기본값은 이 프로필이 꺼져 있으며 명시적 HTTPS URL이 필요하다. `10.0.2.2`는 Android 에뮬레이터의 호스트 접근 주소다. 공개 운영 서버를 배포하지 않았고 HTTPS 주소를 만들어 넣지 않았다. 서버 없이도 동봉 검수 안내12개를 사용할 수 있으나 API/AI 응답에는 별도 서버가 필요하며 AI 공급자 기본값은 DISABLED다.

main manifest의 `usesCleartextTraffic=false`를 유지하고 **release에만** Network Security Configuration을 붙였다. 일반 release는 모든 HTTP를 거절하는 strict XML을 선택하고, 제출 AVD 프로필만 다음 호스트 예외 XML을 선택한다. `base-config`는 cleartext를 거절하고 정확한 호스트 `10.0.2.2`에만 허용한다. Android의 domain 예외는 포트별 제한이 아니므로 해당 호스트의 모든 포트에 적용되며, APK의 실제 backend URL은8001이다. 다른 LAN/공개 호스트의 HTTP는 허용하지 않으며 release 빌드 URL 검사도 해당 호스트 외에는 HTTPS를 요구한다. 인증서 우회·사용자 CA 신뢰·전역 HTTP 허용은 추가하지 않았다. 일반 배포는 별도 검증된 HTTPS backend로 재빌드해야 한다.

검토용 서버는 저장소 루트에서 별도 신규 DB로 시작한다. 기존 서버·DB와 구 제출 APK의 고정 backend/content를 재사용하지 않는다.

```bash
CARCUE_MODE=LIVE CARCUE_AI_PROVIDER=DISABLED \
CARCUE_DB=output/qa/submission-release-review.sqlite3 \
.venv/bin/python -m uvicorn app.main:app --app-dir backend \
  --host 127.0.0.1 --port 8001 --no-access-log
```

이 명령은 사용자가 검토 실행 시 사용하는 예시다. APK 빌드 중 서버·AVD·Ollama·유료 AI를 실행하지 않았다. 무료 로컬 AI 선택은 별도 `LOCAL_AI_INTEGRATION.md` 절차이며 이번 새 APK의 실제 모델·화면 시험으로 계산하지 않는다.

## 설치와 검증 범위

새 release 인증서는 기존 Android debug 인증서와 다르므로 기존 동일 패키지의 debug 설치 위에 `adb install -r`로 갱신할 수 없다. 이번 작업은 기존 앱/AVD 사용자 데이터를 삭제하거나 설치를 시도하지 않았다. 추후 새 전용 Pleos AVD에서 package/user/SDK 환경을 확인하고 설치·실행 검증해야 한다. 기존 userdata를 유지하면서 release로 전환하는 방법을 임의로 수행하지 않는다.

일반 HTTPS `ACTION_VIEW`로 공식 원문/지원 페이지를 연다. 제출 AVD 프로필은 `ALLOW_STOCK_AVD_BROWSER=true`로 기존 API34 Pleos Browser2 대체 경로도 허용한다. 일반 release 기본값은 false다. 대체 경로는 실제 SDK flavor·API34·ranchu와 정확한 component에 한정하고, 시스템 앱·exported/enabled·별도 permission 없음·`/product/app/Browser2/` 설치 경로를 모두 검사한다. 새 브라우저를 설치하지 않는다. 표준 브라우저 처리기가 없으면 앱의 실패 안내가 남는다. 새 release에서 실제 원문 왕복은 미시험이다.

빌드 검사와 APK 내부 검사는 실제 기기 검증과 구분한다. 유료 AI, AVD 재시험, in-flight 언어 변경/Drive/이용 종료 세 경계,429 기기 화면과 신규 세 주제의 실제 센서·무료 모델 시험은 보류 상태다. `scripts/package_submission.py`의 기존 SDK영상·APK 일치 검사를 완화하지 않았으며 기존 묶음 도구는 새 release를 검증된 구 영상과 동일 바이너리로 묶지 않는다.

## 실제 생성·검사 결과

최종 APK 빌드 소스는 **`7d492c1aa3daf4d2dcf436b4dd89222835094bd2`**이며, clean 상태로 빌드를 시작했다. 소스/설정 커밋을 먼저 만들고 APK·해시/검사 기록은 후속 커밋에 추가했다. Gradle의 worktree VCS metadata는 `NO_SUPPORTED_VCS_FOUND`여서 APK 내부에 소스 SHA가 있다고 주장하지 않으며 외부 manifest로 고정한다. 후속 문서/아티팩트 커밋과 이 빌드 소스 사이의 제품 입력 차이를 별도로 확인한다.

| 항목 | 실제 결과 |
| --- | --- |
| 파일 | `apk/CarCue_release.apk`, **32,560,321bytes** |
| APK SHA256 | `b5060db99072ae67af28a161304cc27e8e202ee282d11aa96803dbb977ff377f` |
| 서명 인증서 SHA256 | `c945dc5eed5903ddd06efd51455c0d96239af5f11bc329fcd6b5381c99bf95e3`, 프로젝트 전용 release 인증서·Android Debug 아님 |
| 빌드 | 최종 offline `assemblePleosRelease` 성공, heap768MB·worker1 |
| JVM | **148 passed**, 실패/오류/건너뜀0. manifest 중복 선언 수정 전 실제 수행했고 JVM 입력이 같은 최종 빌드에서는 UP-TO-DATE 재사용 |
| lint | release 전체 **오류0·경고16**. 중복 debug 선언을 제거해 수정했으며 lint suppression을 추가하지 않음 |
| 설정 거절 | 서명 없음, 제출 AVD 프로필 없는 HTTP, 다른 HTTP 호스트 모두 거절. 일반 release의 HTTPS URL 설정 검사 통과(실제 서버 접속 없음) |
| APK 내부 | 실제 Vehicle class 정의·release/DEBUG=false/IS_MOCK=false·API28/35·선택한 NSC·검수 안내12개와 소스 JSON byte 일치·비공개 key/DB/config 파일 부재 확인 |

첫 offline 시도는 캐시에 없는 `lint-gradle:31.8.2` 때문에 중단했고 `--online`으로 의존성만 내려받았다. 첫 전체 lint의 중복 manifest debug 선언 오류는 새 소스 커밋에서 수정한 뒤 최종 offline 빌드로 통과했다. 중간 APK를 제출 파일로 사용하지 않았다. 현지 증거 로그는 `output/apk/submission-release-20261115/`, 공개 검사 결과는 `apk/APK_VERIFICATION.json`, `apk/CONFIGURATION_GUARD_CHECKS.json`에 있다.

```bash
# 키·설치·AVD·모델 없이 현재 제출 APK의 실제 바이트/서명을 검사한다.
python3 scripts/verify_submission_apk.py \
  --apk apk/CarCue_release.apk \
  --manifest apk/SUBMISSION_RELEASE_MANIFEST.json
```

검사기는 공개 Android Build Tools의 `apksigner`, `aapt2`, `dexdump`와 JDK가 필요하다. `--build-tools`, `--java-home`으로 위치를 지정할 수 있다. 동봉 가이드는 현재 checkout의 `content/guides`와 비교하므로 향후 콘텐츠 개발 시에는 고정 빌드 소스로 checkout해 검사하거나 새 APK를 명시적으로 갱신해야 한다. 이 검사는 고정 소스 커밋 이름만 읽고 소스 일치를 증명하는 기능을 대신하지 않는다.

기존 APK `5ef560ba…1479f`와 기존 영상 `638c1f54…e18d`를 실제 재해시해 두 SHA가 그대로임을 확인했다. 새 release를 기존 영상에 나온 동일 바이너리라고 표시하지 않는다. 새 APK의 기기 실행/원문 왕복/무료 모델 검증은 여전히 미실시다.

## 공식 근거

2026-11-15 Firecrawl 로컬로 읽은 Android 공식 [앱 서명](https://developer.android.com/studio/publish/app-signing)은 비공개 properties 분리와 인증서 일치가 필요한 업데이트 조건을 설명한다. [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config)은 base/domain별 cleartext 정책과 manifest 연결을 설명한다. 이 문서의 특정 호스트 예외는 해당 기능을 이번 로컬 검토 환경에 적용한 선택이다.
