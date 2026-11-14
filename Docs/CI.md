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
