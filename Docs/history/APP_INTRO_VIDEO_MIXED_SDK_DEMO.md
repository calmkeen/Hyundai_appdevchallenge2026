# 실제 SDK 문 상태를 담은 CarCue 소개 영상

2026-11-14. 최신 소개 영상은 `output/qa/carcue-sdk-app-intro.mp4`다. 실제 Pleos SDK에서 받은 문 GET·열림 콜백·닫힘 콜백으로 앱 안의 차량 이미지가 바뀌는 장면을 기존 소개에 반영했다. 한국어·영어·일본어 선택/전환과 기능별 약 2초 구성, Scott Buckley의 무료 음악 A Kind Of Hope를 유지한다.

34초·1920×1080·30fps다. 두 실제 앱 녹화의 출처를 장면별로 구분한다. SDK 장면은 공식 Pleos AVD의 `pleos` APK, 나머지 언어·기능 장면은 `demo` APK다. 시작 카드의 차량·안전벨트도 두 APK에 동일하게 동봉한 원본 PNG다.

| 시간 | 구성 | 앱/수신 출처 |
| --- | --- | --- |
| 0–3초 | CarCue 시작 · 원본 차량·안전벨트 | 동봉 PNG |
| 3–7초 | 차량 선택·한국어/영어/일본어 선택 | demo APK · Mock |
| 7–9초 | SDK 최초 닫힘 상태 | pleos APK · 실제 SDK GET 0 |
| 9–11초 | 문 열림에 따라 차량 시각화 전환 | pleos APK · 실제 SDK callback 1 |
| 11–13초 | 문 닫힘에 따라 원래 차량 표시로 복귀 | pleos APK · 실제 SDK callback 0 |
| 13–15초 | 안전벨트 원본 안내 이미지 | pleos APK · 착용 상태 미연결 |
| 15–19초 | 이미지가 있는 가이드 목록·충전 단계 | demo APK · Mock 가이드 |
| 19–21초 | 질문 화면 · AI 답변 연결 준비 중 | demo APK · 실제 AI 호출 없음 |
| 21–29초 | 영어 선택·홈, 일본어 선택·홈 | demo APK · Mock |
| 29–31초 | 이용 종료 확인 | demo APK |
| 31–34초 | CarCue 마무리 | SDK 문 상태와 Mock 기능 구분 |

## 실제 녹화와 편집

`Docs/app-intro.json`의 schema version 2는 `sources.demo`, `sources.sdk`와 각 장면의 `source`를 명시한다. SDK 화면에는 ‘실제 APK 실행 화면 · Pleos SDK 수신 · 전용 AVD’, demo 화면에는 ‘MOCK 데이터’를 표시한다. 실제 SDK라는 표현은 전용 AVD의 서비스/API 호출을 뜻하며 실차 센서 시험을 뜻하지 않는다.

SDK 입력은 `output/qa/pleos-sdk-retest/carcue-pleos-sdk-visual-check.mp4`, 검증 증거는 같은 폴더의 `result.json`이다. 원본 2560×1440에서 CarCue 앱 영역 x=854, y=90, w=1682, h=1051.25를 잘라 소개 화면 안에 확대한다. SDK 기본 차량 패널·상단 바·하단 공조 패널은 포함하지 않는다. 앱 내부 상태·차량 이미지·출처 표시는 원래 녹화 그대로다. 원본의 0.05–2.05초, 1.8–3.8초, 5.8–7.8초, 7.9–9.9초를 각각 사용한다. 개폐 중간 동작과 양 끝 자세가 포함됨을 프레임으로 확인한다.

demo 입력은 `carcue-native-run.mp4`와 같은 이름의 JSON이다. 이전에 통과한 실제 앱 연속 촬영에서 언어 변경·가이드·종료 화면을 가져오며 기기 시각의 장면 마커로 편집 위치를 정렬한다. 화면을 새로 그리거나 차량 상태를 후처리로 합성하지 않는다. 두 APK·입력 MP4·검증 JSON·동봉 이미지의 해시를 렌더 전 확인한다.

차량 시각화는 원본 렌더 프레임을 수신값에 맞춰 전환하는 앱 코드다. 공개 SDK 3D 위젯 이식은 아니다. 안전벨트 센서는 미연결이며 AI 실제 호출도 없다. 시각화의 출처·사용 범위는 `PLEOS_VISUAL_SOURCE.md`, SDK 수신 증거는 `SDK_VISUAL_RETEST.md`를 따른다.

## 음악과 재현

기존 외부 음원 파일의 SHA256, 원곡 12초부터 34초 사용, gain 0.32와 시작/끝 페이드를 유지했다. 최종 AAC를 PCM으로 디코딩해 이전 소개 영상의 음악과 샘플이 정확히 일치함을 확인했다. 곡명·작곡가·CC BY 4.0 크레딧을 영상과 별도 TXT에 유지한다. `MEDIA_CREDITS.md`를 따른다.

```bash
python3 scripts/render_app_intro.py
```

기존의 검증된 두 입력 녹화와 APK·증거 파일·음원이 있으면 재촬영 없이 재현한다. 새 SDK 검증이 필요하면 `scripts/validate_pleos.py --record`, 새 demo 촬영은 `scripts/record_native_showcase.py`를 사용한다. 검증 입력 해시가 달라지면 기존 자료로 렌더하지 않고 중단한다.

SDK 포함 소개 영상은 `carcue-sdk-app-intro.mp4`, 출처/편집 정보는 같은 이름의 JSON, 음악·그래픽 출처는 `carcue-sdk-app-intro-credits.txt`다. 기본 `carcue-app-intro.mp4`와 `carcue-pleos-visual-intro.mp4`도 검수 후 같은 최신 파일로 갱신한다. 기존 `carcue-mock-flow.mp4`는 이전 Mock 소개 그대로 유지한다. 이전 전체 Mock 소개와 JSON·크레딧은 `output/qa/archive-before-sdk-intro/`, 문서는 `history/APP_INTRO_VIDEO_PLEOS_REFERENCE_MOCK.md`에 보존한다. 원본 `carcue-pleos-sdk.mp4`와 SDK 시험 원본도 변경하지 않는다.
