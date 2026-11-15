# 1차 제출 묶음과 실행 범위

2026-11-15. 오늘 밤 메일 제출을 위한 **검토 초안**이다. 사용자가 저녁에 전달 방식과 최종 위치를 알려주기로 했다. 이 작업은 메일 발송·업로드·공모전 제출을 수행하지 않는다.

## 네 가지 제출물

| 제출물 | 기준 |
| --- | --- |
| APK | `output/apk/carcue-pleos-session-boundaries-debug.apk`, SHA256 `5ef560ba1a24e3ce206aeeb6f4f336018b6e8a182bec7214aabc5dd4a261479f` |
| 소개 영상 | `output/qa/sdk-live-intro/live-sdk-intro-20261115-03/carcue-sdk-live-intro.mp4`, SHA256 `638c1f54d3e29ddba3212154c118267bcfc8be21a3dda0ad004066f3e600e18d` |
| GitHub | 검증 APK와 동일한 제품 코드인 고정 커밋. 새 개발 기능이 들어간 develop과 구분 |
| 기획서 | `FIRST_SUBMISSION_PLAN.md`의 검토 PDF. 과거 `07-product-plan.md`와 `reference/` 문서는 결정 이력으로 보존 |

영상은 같은 APK/프로세스의 SDK showcase03 연속 녹화에서 편집한 34초다. 첫 문구는 ‘언제, 어디서든, 평소와 같은 경험을.’이며 한국어·영어·일본어 전환, 14기능 각2초, 기존 무료 음악을 유지한다. 촬영/음악/픽셀 검증과 알려진 한계는 `SDK_LIVE_INTRO.md`를 따른다.

## 실제 연동과 실행 조건

- **실제 연결:** Pleos 전용 AVD의 SDK2.3.2 문 GET/개폐 callback, 앱 차량 그림 변경·복귀, 실제 CarUxRestrictions Drive/Park, 공식 2024 한국시장 아이오닉5 문 안내 연결. 실차나 VIN 자동 인증은 검증하지 않았다.
- **실제 무료 AI:** 서버의 Ollama/qwen3:4b가 검토된 공식 자료 단위를 선택한다. 서버가 주의문과 출처를 조립한다. ANSWER/GUIDE는 저장 번역이며 추가 생성 호출이 없다. 유료 AI·자동 전환·생성 QUESTION 번역은 보류다.
- **시각 자료:** 차량은 SDK 상태에 따라 사전 렌더 프레임을 전환한다. 안전벨트는 안내 이미지이며 센서와 연결하지 않았다. 원본 자산·음악 출처를 함께 제공한다.
- **Mock:** demo APK의 차량 값, CI의 HTTP 대역과 합성 JVM 시험. 제출 후보의 pleos APK 및 실제 SDK 녹화와 구분한다.

검증 APK는 Pleos 개발용 debug 빌드다. 일반 Android 폰에는 Vehicle Service가 없으므로 동일한 차량 연동을 재현할 수 없다. 시연 APK의 서버 주소는 `http://10.0.2.2:8001`이며, 무료 AI에는 별도 Mac 서버와 로컬 Ollama가 필요하다. SDK·모델·키·세션 DB는 배포 묶음에 포함하지 않는다. 구체적인 설정은 `RUNBOOK.md`, `LOCAL_AI_INTEGRATION.md`를 따른다.

## 재현 가능한 묶음

`scripts/package_submission.py`는 `SUBMISSION_CANDIDATE.json`에 명시된 네 파일(APK·영상·PDF·출처)만 해시 대조 후 복사한다. 원본 SDK 시연·독립 검토·영상 편집/검토·PDF 전체 페이지 검토 보고서도 서로 연결해 검사한다. 합격 보고서가 없거나 파일이 바뀌면 출력 전에 거절한다. 원시 QA·개인 질문·세션 DB를 묶음에 복사하지 않는다.

```bash
python3 scripts/package_submission.py check
python3 scripts/package_submission.py build \
  --source-ref release/0.1-first-draft \
  --output-dir output/submission-drafts/20261115/CarCue-first-draft-01
```

출력은 새 디렉터리와 같은 이름의 ZIP이다. `MANIFEST.json`, `SHA256SUMS.txt`, 한국어 실행 안내, 고정 GitHub 링크를 함께 생성한다. 기존 경로/ZIP은 덮어쓰지 않는다. ZIP은 이미 압축된 APK/영상에 불필요한 재압축을 하지 않으며 파일별 해시와 CRC를 확인한다. 네트워크·메일·설치·SDK·모델 호출은 없다.

기본 소스 기준은 `07edb2ae408f8b0d6051fa49cf90af1d29c97108`이다. 선택한 release 커밋과 이 기준 사이에 Android 빌드 입력, 콘텐츠, 서버 앱/의존성, 계약 차이가 있으면 검증 APK의 소스로 표시하지 않는다. 이 검사는 새 APK의 빌드/설치 검증을 대신하지 않는다.

## 남은 양과 제출 판단

오늘 준비는 **개발 잔여 처리(429 대기) / 네 파일의 검토 묶음 / 최신 기획서**의 세 작업으로 나눈다. 새 429 기능의 CI APK와 검증된 시연 APK를 혼합하지 않는다. APK·영상·기획서의 내용 일치와 체크섬을 확인한 뒤 최종 전달 방식만 사용자 지시를 기다린다.

실제 기기 시험은 **AI 처리 중 언어 변경·Drive 전환·이용 종료의 세 경계**가 남아 있다. 사용자가 AVD 재시험을 뒤로 미뤘으므로 이번 제출 준비 중 실행하지 않는다. 정상 시연의 종료 DB0과 부분 시험을 이 세 시험의 전체 성공으로 계산하지 않는다.

제품 전체로는 충전·좌석/거울·화면/표시등의 **3주제×3언어=9개 안내** 검토/게시, 추가 차량 상태/차종·시장, 모바일 QR 진입, RTL/접근성·실차 UX 시험이 남아 있다. 지원 후보48언어/50지역 구조는 번역 완료 수가 아니다. 1차 제출은 현재 확인한 문 상태 중심 시제품으로 범위를 명시하며, 전체 제품 완성을 뜻하지 않는다.
