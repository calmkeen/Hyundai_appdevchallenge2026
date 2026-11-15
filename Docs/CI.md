# 기본 CI와 작업별 검증

2026-11-14. `.github/workflows/basic-ci.yml`는 develop/main/release 대상 PR과 feature/develop/release/hotfix/main push, 수동 실행에서 계약·UI 자원·백엔드 회귀를 확인하도록 구성한다. Python 3.10과 기존 `backend/requirements.lock.txt`를 사용한다. 환경은 MOCK이며 외부 AI 키/모델을 주입하지 않는다.

GitHub의 [Python 빌드·테스트 공식 문서](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)에 따라 checkout/setup-python으로 환경을 준비하고 로컬과 같은 명령을 실행한다. 워크플로 권한은 저장소 읽기이며 앱 배포·업로드는 수행하지 않는다.

```bash
python -m pip install -r backend/requirements.lock.txt
python scripts/check_contracts.py
python scripts/import_guides.py check
python -m pytest backend/tests -q
```

2026-11-14 로컬에서 계약 3종·148개 UI 자원의 세 언어/치환 변수 검사와 백엔드 26개 회귀가 통과했다. 로그는 `output/qa/git-flow/contracts.txt`, `backend-tests.txt`다. AnyIO의 기존 deprecation warning 1개가 있고 실패는 없다. YAML 구문과 실행 명령도 로컬에서 확인한다. GitHub에서 실행된 결과는 아직 없으며 원격 push/실행 결과와 구분한다.

## 이 CI의 범위

이 기본 CI만으로 Android 빌드·실제 SDK 수신·실제 AI 호출이 통과한 것은 아니다. 해당 변경은 JDK 17/Android 환경의 빌드·단위 시험과 필요 시 전용 AVD 시험을 별도로 실행해 PR에 기록한다. SDK/AVD와 로컬 APK·영상은 CI 입력으로 Git에 넣지 않는다. 실제 SDK 증거는 `SDK_FULL_APP_SHOWCASE.md`, 앱/서버 전체 검증 이력은 `VALIDATION_REPORT.md`를 따른다.

GitHub의 브랜치 보호나 필수 상태 검사는 이 YAML만으로 설정되지 않는다. 원격 운영을 구성할 때 실제 저장소 설정을 확인해 별도로 적용한다.

검수 가이드 등록 feature부터 게시 메타데이터 카탈로그 검사와 등록·게시 정책/API 테스트도 같은 CI에서 실행한다. 기본 DRAFT가 검사에 통과해도 게시 가능한 실제 매뉴얼이 있다는 뜻은 아니다. 절차는 `GUIDE_CONTENT_WORKFLOW.md`를 따른다.

## 최초 원격 실행과 수정

develop `4b8b65b`를 실제 push한 뒤 [첫 실행](https://github.com/calmkeen/Hyundai_appdevchallenge2026/actions/runs/43565452391)은 job 생성 전 실패했다(jobs 0개). 로컬 YAML 파싱은 통과했지만 GitHub context 사용 가능 범위까지 검사하지 못했다. `jobs.<job_id>.env`에 쓴 `runner.temp`는 해당 위치에서 지원되지 않는 설정이었다.

`feature/ci-runner-context`에서 `CARCUE_DB`를 백엔드 테스트 **step의 env**로 옮겼다. [GitHub 공식 context 표](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability)에 따르면 step env에서는 runner를 사용할 수 있다. 읽기 전용 권한과 MOCK/비어 있는 AI 키 설정은 유지한다.

수정 통합본 develop `bfb548b`의 [실제 원격 실행](https://github.com/calmkeen/Hyundai_appdevchallenge2026/actions/runs/43566021842)은 성공했다. 계약/UI 자원, 가이드 카탈로그, 백엔드 회귀의 세 단계가 모두 success임을 Jobs API에서도 확인했다. 첫 실행의 실패 이력은 보존한다. 이 결과는 Android/SDK/AI 실제 기기·외부 서비스 시험을 포함하지 않는다.

공식 문 안내 등록부터 계약 검사에 상태-가이드 규칙의 JSON Schema 및 실제 게시 콘텐츠 참조 검사를 포함한다. 백엔드 회귀에는 등록한 3언어 문 안내의 LIVE API 조회·다른 프로필/언어 차단·검수 콘텐츠의 초기화 방지 시험을 포함한다. 네트워크로 현대자동차 원문을 매 CI마다 가져오지는 않으며 원문 검토 증거와 해시는 별도로 보존한다.

공식 콘텐츠 develop `25bb1c7`의 [원격 실행](https://github.com/calmkeen/Hyundai_appdevchallenge2026/actions/runs/43569403093)도 성공했다. SDK 전용 AVD 시험은 이 GitHub runner에서 수행하지 않았으며 별도 기기 증거로 관리한다.

SDK 연결 develop `547da78`의 [원격 실행](https://github.com/calmkeen/Hyundai_appdevchallenge2026/actions/runs/43574314346)은 성공했다. 후속 Console 수정부터 백엔드 회귀에 로컬 HTTP 서버를 이용한 독립 heartbeat/준비 대기/종료 시험7개가 포함된다. 실제 Console503 재현과 최신 APK의 전체 SDK run05는 로컬 전용 AVD 증거이며 CI의 HTTP 대역 시험과 구분한다.

## 무료 로컬 AI 단계 · 2026-11-14

현재 CI는 같은 계약/카탈로그/백엔드 명령을 사용하며, 실제 Ollama 실행·Android 빌드·전용 AVD 시험은 포함하지 않는다. 로컬 전체 backend370개, UI168 문구·가이드4레코드·상태규칙1개, Android JVM52개를 확인했다. 실제 모델/앱/SDK 증거는 `LOCAL_AI_INTEGRATION.md`, `LOCAL_AI_APP_VALIDATION.md`에 분리했다. 기본 환경은 MOCK/DISABLED이고 유료 API 자동전환은 없다.

최신 기능의 원격 CI는 해당 develop push 후 별도 확인한다. 이전 develop `eac1986` 실행43576062421의 성공을 이번 코드의 실행으로 확대하지 않는다.

오프라인·종료 복구 단계는 UI177 자원/콘텐츠·서버370 회귀를 같은 CI에서 검사한다. Android JVM84·실제 AVD16단계·기본앱SDK8단계는 로컬 별도 실행이며 GitHub runner에서 SDK/모델을 실행하지 않는다. `OFFLINE_SESSION_VALIDATION.md` 참조.

## Android 재현 빌드 · 2026-11-15

`.github/workflows/android-ci.yml`을 기존 Basic validation과 별도로 추가했다. 기존 계약·콘텐츠·백엔드 워크플로와 의존성은 변경하지 않는다. Android workflow도 같은 PR/push 대상과 수동 실행을 사용하며 저장소 읽기 권한만 요청한다.

| 작업 | 실행 조건 | 검증 범위 | 산출물 |
|---|---|---|---|
| Demo JVM tests and MOCK APK | PR/push/수동 실행 | `testDemoDebugUnitTest`와 `assembleDemoDebug` | `carcue-demo-MOCK-<commit>` 및 JVM XML/HTML 보고서 |
| Pleos APK compile only | 수동 실행에서 `compile_pleos=true` | 공개 Maven의 Vehicle 2.3.2로 `assemblePleosDebug` | `carcue-pleos-COMPILE_ONLY-<commit>` |

기본 자동 CI의 Android 범위는 **Demo-only**다. Pleos Maven의 인증 없는 접근은 이번 로컬 환경에서 DNS 확인에 실패해 검증하지 못했다. 따라서 Pleos compile-only는 기본 비활성인 명시적 수동 작업으로 제공한다. 키나 계정·GitHub secret을 추가하지 않는다. 접근 실패 또는 컴파일 오류가 발생하면 해당 작업은 실패하며 `continue-on-error`로 숨기지 않는다. 수동 작업이 실제 성공하기 전에는 Pleos 컴파일 통과로 보고하지 않는다.

환경은 `ubuntu-24.04`, Temurin Java 17, 저장소 Gradle wrapper **8.10.2**, Android **API 35 / build-tools 35.0.0**이다. 저장소의 AGP 8.8.2/Kotlin 2.0.0/앱·SDK 의존성은 유지한다. `setup-gradle`의 wrapper 검증과 Gradle 캐시를 사용하며 `setup-java`의 별도 Gradle 캐시는 중복 사용하지 않는다. SDK/AVD 이미지·개인 Gradle 캐시·유료 AI 키·Ollama 모델은 CI 입력이 아니다.

```bash
# GitHub runner에서 실행. 호스트 부하 때문에 이번 로컬 작업에서는 실행하지 않았다.
cd android
./gradlew --no-daemon --max-workers=2 \
  -PcarcueServerUrl=http://10.0.2.2:8000 \
  :app:testDemoDebugUnitTest :app:assembleDemoDebug

# 명시적으로 선택한 수동 Pleos compile-only 작업
./gradlew --no-daemon --max-workers=2 \
  -PpleosSdkVersion=2.3.2 -PcarcueServerUrl=http://10.0.2.2:8000 \
  :app:assemblePleosDebug
```

`scripts/package_android_ci.py`는 runner의 aapt2로 실제 APK package/version/compile·target SDK를 검사한 뒤 이름을 붙인다. Demo는 `com.carcue.app.demo`와 `-mock` 버전명, Pleos는 `com.carcue.app`를 요구한다. 산출물에는 APK, `artifact.json`, `SHA256SUMS.txt`가 포함되며 commit/run ID와 검증 범위를 기록한다. artifact 이름에는 재실행 attempt도 붙여 충돌을 피한다. 보존 기간은 7일이다. JVM 실패 시에도 만들어진 테스트 보고서는 업로드한다. APK는 runner의 일회성 debug 서명이며 배포용 서명키를 사용하지 않는다.

**MOCK APK는 차량 데이터가 Mock인 demo flavor이며, AI 실행까지 검증했다는 뜻이 아니다.** APK의 서버 URL은 기존 기본 개발 주소 `http://10.0.2.2:8000`이고 CI가 서버나 AI를 기동하지 않는다. Pleos COMPILE_ONLY APK도 실제 SDK 수신·문 상태 변화·Car UX·실제 모델·실차 시험 통과를 뜻하지 않는다. 설치 APK를 이용한 실제 AVD 증거와 세 응답 경계 미완료 상태는 별도 문서대로 유지한다.

이번 변경은 로컬 YAML 구조/AST 검사, 메타데이터 합격·거절 7개 확인과 기존 Pleos APK의 aapt2 정적 메타데이터 읽기를 통과했다. 로컬 Gradle·AVD·모델은 실행하지 않았다. 새 원격 실행의 실제 JVM 개수·빌드/업로드 성공 여부는 해당 commit의 Actions 결과를 확인해 기록해야 하며, 이전 로컬 JVM127/백엔드475 또는 과거 CI 성공을 새 작업의 성공으로 확대하지 않는다.

공식 근거: [setup-java v5](https://github.com/actions/setup-java/tree/v5), [Gradle actions v5](https://github.com/gradle/actions/releases/tag/v5.0.0), [setup-gradle 문서](https://github.com/gradle/actions/blob/v5/docs/setup-gradle.md), [upload-artifact v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2), [Ubuntu 24.04 Android 도구](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md#android), [sdkmanager](https://developer.android.com/tools/sdkmanager), [Gradle 8.10.2 Java 호환성](https://docs.gradle.org/8.10.2/userguide/compatibility.html). Java/Gradle action v5는 호환성을 확인해 선택한 버전이며 최신 major라는 뜻은 아니다.

공식 문서 조회는 사용자 설정의 로컬 Firecrawl을 먼저 확인했다. 로컬 스택이 꺼져 있어 서비스를 추가 기동하지 않고 내장 웹 도구로 위 공식 문서만 확인했으며 Cloud Firecrawl은 사용하지 않았다.
