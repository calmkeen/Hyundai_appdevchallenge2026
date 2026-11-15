# CarCue(카큐) · Hyundai App Development Challenge 2026

**낯선 차량의 상태와 사용법을 자신의 언어로 확인하는 Pleos 차량 앱입니다.**

차량 매뉴얼 범위 선택 → 한국어·영어·일본어 선택 → 현재 상태 확인 → 관련 사용 안내 → 질문·저장 번역 → 이용 종료로 이어집니다. 국내외 외국인 차량 이용자를 대상으로 하며 렌터카·관광객에 한정하지 않습니다. Kotlin/Compose 앱, FastAPI 서버, 검토된 안내 데이터로 구성한 시제품입니다.

## 제출 APK와 기획서

- **서명 Release APK:** [apk/CarCue_release.apk](apk/CarCue_release.apk) — 실제 Pleos SDK를 사용하는 `pleos` 빌드입니다. APK의 해시·서명·빌드 소스와 재빌드 절차는 [Release APK 기록](Docs/SUBMISSION_RELEASE_APK.md)을 따릅니다.
- **기획서 원문:** [현재 시제품과 후속 계획](Docs/FIRST_SUBMISSION_PLAN.md)
- **이전 검토 묶음:** [기존 APK·영상·PDF·ZIP과 실행 조건](Docs/FIRST_SUBMISSION_PACKAGE.md). 기존 34초 영상은 이전 debug APK의 검증 기록이며, 위 Release APK나 새 안내 9개의 기기 실행 증거가 아닙니다.

공식 [제출 안내](https://appdevchallenge.auto-hmg.io/guide/submission)는 GitHub 소스, `apk/`의 서명된 실행 가능 Release APK, README의 실행 방법·환경·Pleos Connect 버전·화면 크기·APK 위치를 요구합니다. 최종 APK 파일명은 `팀명_앱이름_release.apk` 형식이며, 현재 `CarCue_release.apk`는 팀명 확정 전 임시 이름입니다. 메일에는 저장소 URL과 최종 커밋 해시를 기재합니다. 공개 범위와 11월 16~23일 저장소 접근 조건, 소스·APK ZIP 대체 제출은 [공식 FAQ](https://appdevchallenge.auto-hmg.io/faq)를 따릅니다.

## 실행 환경

| 구분 | 확인한 환경·설정 |
| --- | --- |
| Pleos 에뮬레이터 | **Pleos Connect 2.1.0**, Android 14 / API 34, ARM64, 사용자 10 |
| 디스플레이 | **2560 × 1440 px**, 가로 화면 — 실제 SDK 시연 원본 해상도 |
| 차량 연동 | Vehicle SDK **2.3.2**, Vehicle Service **2.3.22** |
| Android 빌드 | JDK **17**, Gradle Wrapper **8.10.2**, Platform / target API **35**, Build Tools **35.0.0**, minSdk **28** |
| 서버 | Python **3.10 이상**, [고정 의존성](backend/requirements.lock.txt), FastAPI / SQLite |
| 제출 APK 서버 주소 | `http://10.0.2.2:8001` — Android 에뮬레이터에서 호스트의 로컬 서버에 접근 |
| 선택형 무료 AI | 호스트의 Ollama / `qwen3:4b`; 앱과 별도로 실행 |

위 Pleos 환경에서 이전 debug APK의 SDK·차량 UX를 검증했습니다. 새 Release APK의 설치·실행 재시험과 새 안내의 AVD 시험은 아직 수행하지 않았습니다. 일반 Android 폰·일반 AVD에는 같은 Vehicle Service가 없으므로 아래 Pleos 연동을 그대로 재현할 수 없습니다. 상세 근거는 [SDK 환경과 수신 기록](Docs/SDK_CAPABILITY_REPORT.md), [기존 실제 SDK 시연](Docs/SDK_SESSION_VALIDATION.md)을 참고합니다.

## 제출용 Pleos 앱 실행

아래 명령은 저장소 루트에서 실행합니다. Pleos Connect 에뮬레이터는 공식 개발 환경에 맞게 설치·부팅하고, `adb`가 PATH에 있어야 합니다. APK에는 백엔드·모델·Pleos 시스템 이미지가 포함되지 않습니다.

### 1. 소스와 로컬 서버 준비

```bash
git clone --branch release/0.1.1-first-submission \
  https://github.com/calmkeen/Hyundai_appdevchallenge2026.git
cd Hyundai_appdevchallenge2026
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock.txt
mkdir -p output/submission-local
CARCUE_MODE=LIVE CARCUE_AI_PROVIDER=DISABLED \
CARCUE_DB=output/submission-local/sessions.sqlite3 \
.venv/bin/python -m uvicorn app.main:app --app-dir backend \
  --host 127.0.0.1 --port 8001 --no-access-log
```

다른 터미널에서 `curl http://127.0.0.1:8001/health`로 `status: ok`, `mode: LIVE`를 확인합니다. 이 설정은 공식 안내 조회와 저장된 안내 번역용이며 AI 모델을 호출하지 않습니다. `.env` 파일은 자동으로 읽지 않습니다. 기존 8001 서버가 있으면 먼저 해당 서버의 용도와 소스를 확인하고, 구 APK용 서버와 혼용하지 않습니다.

### 2. Release APK 설치·실행

`adb devices`로 전용 Pleos 에뮬레이터의 serial을 확인한 뒤 아래 예시 값을 바꿉니다. 기존 앱(이전 debug APK 포함)과 서명이 다르면 업데이트 설치가 거절될 수 있으므로 기존 데이터를 보존할 새 전용 AVD/테스트 프로필을 사용합니다.

```bash
adb devices
export CARCUE_SERIAL=emulator-5554
adb -s "$CARCUE_SERIAL" shell am get-current-user
adb -s "$CARCUE_SERIAL" install --user 10 -r apk/CarCue_release.apk
adb -s "$CARCUE_SERIAL" shell am start --user 10 \
  -n com.carcue.app/com.carcue.app.MainActivity
```

확인한 시험 환경의 사용자는 10입니다. 다른 구성이라면 현재 활성 사용자를 확인해 `--user` 값을 맞춥니다. 앱에서 **2024 한국시장 아이오닉 5** 매뉴얼 프로필과 언어를 선택하고 Park 상태에서 사용 안내를 엽니다. 프로필 선택은 문서 범위 선택이며 VIN·실제 차종 자동 인증이 아닙니다. 문 상태는 SDK가 유효한 값을 제공할 때만 표시하며, SDK/차량 UX 확인 불가 또는 주행 제한 상태에서는 입력과 긴 안내를 제한합니다. 문 개폐 재현에는 공식 Virtual Console 설정이 필요하며 [SDK 실행 절차](Docs/RUNBOOK.md#현재-실제-개발-흐름-sdk-문-상태와-공식-가이드)를 따릅니다. 앱은 차량 제어 API를 호출하지 않습니다.

### 3. 무료 로컬 AI 선택

질문 응답을 사용하려면 호스트에 Ollama와 `qwen3:4b`를 별도로 준비합니다. [로컬 AI 실행 안내](Docs/LOCAL_AI_INTEGRATION.md#실행과-재검증)의 런타임·모델·라이선스를 확인한 뒤, 앞의 AI 비활성 서버를 종료하고 다음 전용 launcher로 8001 서버를 실행합니다. 아래 명령은 모델을 다운로드하거나 Ollama를 자동으로 시작하지 않습니다. `NEW_RUN`은 아직 없는 새 실행명으로 바꿉니다.

```bash
.venv/bin/python scripts/run_local_ai_backend.py \
  --model qwen3:4b --ollama-url http://127.0.0.1:11434 --port 8001 \
  --evidence-dir output/qa/NEW_RUN/server
```

모델은 검토된 완전한 안내 단위의 ID를 선택하고 서버가 본문·주의문·출처를 반환합니다. `ANSWER`/`GUIDE` 번역은 같은 판본의 저장 문자열로 제공해 모델을 추가 호출하지 않습니다. **유료 AI와 생성 `QUESTION` 번역은 보류**하며 유료 자동 전환은 없습니다. 새 충전·좌석/거울·화면/표시등 안내의 실제 모델 선택 시험은 수행하지 않았습니다.

## 소스 빌드

`JAVA_HOME`을 JDK 17 경로로, `ANDROID_HOME`을 Android SDK 경로로 설정합니다. 실제 Pleos 빌드는 공식 Maven 저장소에서 Vehicle SDK 2.3.2를 받을 수 있어야 합니다. 접근 권한이 필요한 경우 개인 개발 환경에만 설정하고 자격정보를 커밋하지 않습니다.

첫 명령은 로컬 서명 키를 생성하거나 기존 키를 재사용하고 종료합니다. 두 번째 명령으로 제출용 Pleos AVD의 로컬 서버에 연결하는 Release를 빌드·검사합니다. 첫 의존성 다운로드에는 `--online`을 사용하며, 캐시가 있는 재빌드에서는 이 옵션을 빼면 오프라인으로 실행합니다. 서명 키·비밀번호는 개인 경로에만 보관하며, 상세 설정은 [Release APK 기록](Docs/SUBMISSION_RELEASE_APK.md)을 따릅니다.

```bash
python3 scripts/build_submission_release.py --init-signing
python3 scripts/build_submission_release.py \
  --signing-properties .tooling/signing/carcue-release.properties \
  --submission-avd --server-url http://10.0.2.2:8001 --online --checks
```

`--submission-avd`는 이 제출용 에뮬레이터 구성을 명시하는 옵션입니다. 일반 Release는 HTTPS 서버 주소가 필요합니다. debug 빌드와 개발용 시험 명령은 [전체 실행 안내](Docs/RUNBOOK.md)를 참고합니다.

## 별도 Mock 데모

Pleos SDK 없이 UI 흐름만 확인하는 개발용 구성입니다. 위 1단계의 소스·가상환경·의존성을 준비한 뒤, 서버와 앱을 각각 실행하고 일반 Android AVD를 사용합니다. 제출용 앱·실제 SDK 검증과 구분합니다.

```bash
# 저장소 루트, 별도 터미널
mkdir -p output/submission-local
CARCUE_MODE=MOCK CARCUE_AI_PROVIDER=DISABLED \
CARCUE_DB=output/submission-local/mock.sqlite3 \
.venv/bin/python -m uvicorn app.main:app --app-dir backend \
  --host 127.0.0.1 --port 8000 --no-access-log
```

```bash
android/gradlew -p android :app:assembleDemoDebug \
  -PcarcueServerUrl=http://10.0.2.2:8000
export CARCUE_DEMO_SERIAL=emulator-5556
adb -s "$CARCUE_DEMO_SERIAL" install -r \
  android/app/build/outputs/apk/demo/debug/app-demo-debug.apk
adb -s "$CARCUE_DEMO_SERIAL" shell am start \
  -n com.carcue.app.demo/com.carcue.app.MainActivity
```

Mock 차량 값과 미검수 시연 프로필이 표시됩니다. 외부 AI는 호출하지 않으며 실제 SDK 수신 성공을 뜻하지 않습니다.

## 현재 범위와 검증 상태

| 기능 | 구현·확인 범위 |
| --- | --- |
| 차량 상태·차량 UX | 이전 Pleos AVD에서 실제 문 GET/개폐 callback, 차량 이미지 변경·복귀, CarUxRestrictions Drive/Park 확인. 실차 시험 없음 |
| 사용 안내 | 2024 한국시장 아이오닉 5의 문·AC 완속 충전·좌석/일반 미러·클러스터 **4주제 × 3언어 = 12개 게시**. 문만 SDK 상태와 연결; 새 세 주제는 센서 미연결 수동 안내 |
| 무료 AI·저장 번역 | 기존 문 안내에서 실제 Ollama 선택 확인. 새 안내 9개는 실제 HTTP 조회·저장 번역 36건 확인; 해당 새 안내의 실제 모델 선택·AVD 화면 시험은 미실시 |
| 남은 기기 시험 | 진행 중 요청의 언어 변경·Drive·이용 종료 3경계, 신규 429 화면, 새 안내의 화면·언어·원문 왕복. AVD 재시험은 보류 |

자체 안내는 공식 원문 대조와 AI 보조 의미 검토를 거친 요약이며 OEM 승인·자동차 전문가·원어민 인증을 뜻하지 않습니다. 48언어/50지역은 확장 후보 데이터이며 지원 완료 수가 아닙니다. 안전벨트는 센서와 연결하지 않은 안내 이미지입니다. 사용자 지정 Pleos 녹화 프레임의 외부 재배포 권한은 미확인입니다. 시각 자산·음원의 출처와 확인된 이용 범위는 [미디어 크레딧](Docs/MEDIA_CREDITS.md), [Pleos 시각 자료 출처](Docs/PLEOS_VISUAL_SOURCE.md)를 따릅니다.

기존 `release/0.1-first-draft`의 APK·영상·기획서·ZIP은 당시 스냅샷으로 보존합니다. **구 APK는 해당 고정 release의 backend/content와 짝으로 재현**하며 최신 서버와 혼용하지 않습니다. 새 Release의 빌드·서명 검사는 이전 debug APK의 기기 시험을 대체하지 않습니다.

## 문서와 구조

`android/`는 Compose 앱, `backend/`는 서버, `content/`는 프로필·언어·안내 데이터, `Docs/`는 기획·실행·검증 기록입니다. 인증정보·서명 키·SDK 바이너리·모델·사용자 세션 DB는 저장소에 올리지 않습니다.

- [전체 실행 안내](Docs/RUNBOOK.md) · [아키텍처](Docs/ARCHITECTURE.md) · [API 계약](Docs/DATA_API_SPEC.md)
- [공식 안내 9개 확장·검증](Docs/GUIDE_EXPANSION_VALIDATION.md) · [콘텐츠 등록 절차](Docs/GUIDE_CONTENT_WORKFLOW.md) · [공식 매뉴얼 검토](Docs/MANUAL_REVIEW_IONIQ5_2024_KR.md)
- [실제 SDK·공식 안내 연결](Docs/SDK_OFFICIAL_GUIDE_VALIDATION.md) · [오프라인 안내·종료 복구](Docs/OFFLINE_SESSION_VALIDATION.md)
- [무료 AI 구성](Docs/LOCAL_AI_INTEGRATION.md) · [기존 실제 앱 AI 검증](Docs/LOCAL_AI_APP_VALIDATION.md)
- [CI와 검증 범위](Docs/CI.md) · [개발 순서](Docs/DEVELOPMENT_ORDER.md) · [작업 기록](Docs/DEVELOPMENT_LOG.md)
- [초기 통합 기획안](Docs/07-product-plan.md) · [기획 개요](Docs/01-product-concept.md) · [MVP·기술 설계](Docs/02-mvp-and-architecture.md) · [초기 SDK 검증](Docs/03-sdk-verification.md) · [개발 기준](Docs/04-development-plan.md) · [Git Flow](Docs/05-git-flow.md) · [근거·결정 이력](Docs/06-evidence-and-decisions.md)
