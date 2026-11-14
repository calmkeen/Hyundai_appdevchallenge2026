# 기본 CI와 작업별 검증

2026-11-14. `.github/workflows/basic-ci.yml`는 develop/main/release 대상 PR과 feature/develop/release/hotfix/main push, 수동 실행에서 계약·UI 자원·백엔드 회귀를 확인하도록 구성한다. Python 3.10과 기존 `backend/requirements.lock.txt`를 사용한다. 환경은 MOCK이며 외부 AI 키/모델을 주입하지 않는다.

GitHub의 [Python 빌드·테스트 공식 문서](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)에 따라 checkout/setup-python으로 환경을 준비하고 로컬과 같은 명령을 실행한다. 워크플로 권한은 저장소 읽기이며 앱 배포·업로드는 수행하지 않는다.

```bash
python -m pip install -r backend/requirements.lock.txt
python scripts/check_contracts.py
python -m pytest backend/tests -q
```

2026-11-14 로컬에서 계약 3종·148개 UI 자원의 세 언어/치환 변수 검사와 백엔드 26개 회귀가 통과했다. 로그는 `output/qa/git-flow/contracts.txt`, `backend-tests.txt`다. AnyIO의 기존 deprecation warning 1개가 있고 실패는 없다. YAML 구문과 실행 명령도 로컬에서 확인한다. GitHub에서 실행된 결과는 아직 없으며 원격 push/실행 결과와 구분한다.

## 이 CI의 범위

이 기본 CI만으로 Android 빌드·실제 SDK 수신·실제 AI 호출이 통과한 것은 아니다. 해당 변경은 JDK 17/Android 환경의 빌드·단위 시험과 필요 시 전용 AVD 시험을 별도로 실행해 PR에 기록한다. SDK/AVD와 로컬 APK·영상은 CI 입력으로 Git에 넣지 않는다. 실제 SDK 증거는 `SDK_FULL_APP_SHOWCASE.md`, 앱/서버 전체 검증 이력은 `VALIDATION_REPORT.md`를 따른다.

GitHub의 브랜치 보호나 필수 상태 검사는 이 YAML만으로 설정되지 않는다. 원격 운영을 구성할 때 실제 저장소 설정을 확인해 별도로 적용한다.
