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

`feature/ci-runner-context`에서 `CARCUE_DB`를 백엔드 테스트 **step의 env**로 옮겼다. [GitHub 공식 context 표](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability)에 따르면 step env에서는 runner를 사용할 수 있다. 읽기 전용 권한과 MOCK/비어 있는 AI 키 설정은 유지한다. 원격 수정 실행 결과는 작업 기록/검증 보고서에서 로컬 검사와 구분한다.
