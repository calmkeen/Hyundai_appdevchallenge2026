# 모든 기능을 같은 SDK 앱에서 촬영한 CarCue 소개

이 문서는 공식 문 안내 등록 이전 MVP APK의 소개 영상 기록이다. 원본 영상·음악·해당 APK는 보존한다. 후속 실제 SDK/공식 매뉴얼 연결 앱은 `SDK_OFFICIAL_GUIDE_VALIDATION.md`를 따르며, 이 영상의 가이드 예시를 새 공식 안내의 실행 증거로 사용하지 않는다.

2026-11-14. 최신 소개 영상은 `output/qa/carcue-full-sdk-intro.mp4`다. 한국어·영어·일본어 전환과 가이드·질문·이용 종료까지 **동일 Pleos SDK 연결 APK/프로세스**에서 새로 촬영했다. demo APK 화면은 사용하지 않는다. 첫 문구는 사용자 방향에 맞춰 “언제, 어디서든, 평소와 같은 경험을.”로 바꿨다.

영상은 34초·1920×1080·30fps다. 기능 화면 14개는 각각 2초이며 시작/마무리는 3초다. Scott Buckley의 기존 무료 음악 A Kind Of Hope, 같은 12초 시작 구간·gain 0.32·페이드를 유지한다. 디코딩된 음악 PCM도 이전 34초 영상과 정확히 일치한다.

| 시간 | 화면 · 모두 같은 SDK 앱 |
| --- | --- |
| 0–3초 | “언제, 어디서든, 평소와 같은 경험을.” 시작 카드 |
| 3–7초 | 차량 선택·한국어/영어/일본어 선택 |
| 7–9초 | 실제 SDK 최초 문 닫힘 |
| 9–11초 | 실제 SDK 열림 콜백과 앱 차량 개폐 전환 |
| 11–13초 | 실제 SDK 닫힘 콜백과 차량 이미지 복귀 |
| 13–15초 | 안전벨트 원본 안내 · 센서 미연결 표시 |
| 15–19초 | SDK 개발 앱의 가이드 목록·충전 이미지 단계 예시 |
| 19–21초 | 같은 앱의 질문 화면 · AI 답변 연결 준비 중 |
| 21–29초 | 영어 선택·홈, 일본어 선택·홈 |
| 29–31초 | 같은 SDK 앱의 이용 종료 확인 |
| 31–34초 | “익숙한 경험을, 어디서나.” 마무리 |

## 한 APK 원본과 출처 확인

원본은 `output/qa/pleos-full-showcase/carcue-pleos-native-run.mp4`, 증거는 같은 이름의 JSON이다. 앱은 `com.carcue.app`, APK는 `output/apk/carcue-pleos-showcase-debug.apk`다. 설치 base.apk와 전달 APK SHA256을 대조하고, 한 프로세스에서 20개 장면을 연속 녹화했다. 모든 장면의 수신 출처·언어·페이지·문 값과 기기 단조 시각을 기록한다. 한국어에서 닫힘→열림→닫힘, 영어에서 열림, 일본어에서 닫힘의 실제 SDK 콜백을 받아 언어를 바꿔도 같은 연결이 동작함을 검사했다. 상세 시험은 `SDK_FULL_APP_SHOWCASE.md`를 따른다.

`app-intro.json`은 `sources.sdk` 하나만 사용한다. 렌더러는 다른 APK 입력이 섞이면 중단한다. 원본 2560×1440의 CarCue 영역 x=854, y=90, w=1682, h=1051.25를 동일하게 crop/확대하므로 모든 기능 화면의 크기·앱 메뉴·차량 프로필이 일관된다. 장면별 파일 마커 시각으로 2초 컷을 정렬하고 문 개폐 시작 직전도 포함한다. 왼쪽 Pleos 시스템 차량 패널은 넣지 않는다. 시작 카드의 차량/안전벨트는 이 APK에 동봉한 원본 PNG다.

하단에는 ‘실제 Pleos SDK 연결 앱 · 전용 AVD’를 표시한다. 차량 데이터는 실제 SDK 경로지만 가이드 콘텐츠는 debug 화면 예시, 안전벨트 센서는 미연결, AI 실제 호출은 없음이라는 구분을 앱/설명에 유지한다. 검수된 매뉴얼이나 실제 3D SDK 위젯이 연결된 것으로 소개하지 않는다. 출처·사용 범위는 `PLEOS_VISUAL_SOURCE.md`, 음악은 `MEDIA_CREDITS.md`를 따른다.

```bash
python3 scripts/record_pleos_showcase.py
python3 scripts/render_app_intro.py
```

촬영 원본과 APK·검증 JSON·음원 해시가 일치해야 재현된다. `carcue-full-sdk-intro.json`에 단일 입력·설치 APK·음악·편집 구간·SDK 증거를 기록하며 복사 가능한 출처는 `carcue-full-sdk-intro-credits.txt`다. 기본 `carcue-app-intro.mp4`, `carcue-sdk-app-intro.mp4`, `carcue-pleos-visual-intro.mp4`는 최종 검수 후 같은 새 영상으로 갱신한다. `carcue-mock-flow.mp4`는 이전 Mock 버전 그대로 보존한다.

이전 SDK/demo 혼합 영상·메타데이터·크레딧은 `output/qa/archive-before-full-sdk-intro/`, 문서는 `history/APP_INTRO_VIDEO_MIXED_SDK_DEMO.md`에 보존한다. 원본 기준 `carcue-pleos-sdk.mp4`, 이전 단일 SDK 시험 녹화와 기존 Mock 원본도 변경하지 않는다.
