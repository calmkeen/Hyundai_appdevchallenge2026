# Pleos 원본 시각화를 담은 앱 소개 영상

2026-11-14. 최신 사용자 요청에 따라 지정 영상의 안전벨트 그림과 은색 차량 시각화를 CarCue 안에 넣고, 새 APK를 실제 실행해 소개 영상을 다시 촬영한다. 다른 차량 사진·OpenX 모델을 주 시각화로 사용하지 않는다. 이전 사진 중심 구성은 `history/APP_INTRO_VIDEO_PHOTO_RETURN.md`에 보존했다.

영상은 34초·1920×1080·30fps다. 기능 장면은 약 2초씩 보여주며 한국어·영어·일본어와 실제 언어 선택 장면을 포함한다. Scott Buckley의 외부 무료 음악 A Kind Of Hope를 유지하며 합성 음악은 만들지 않는다.

| 시간 | 화면 |
| --- | --- |
| 0–3초 | CarCue · APK와 같은 원본 차량·안전벨트 이미지 |
| 3–7초 | 차량·세 언어 선택 |
| 7–11초 | 원본 차량과 수신 상태 · 문 열림/닫힘 |
| 11–13초 | 앱 내부에서 원본 차량 프레임이 다시 열림으로 전환 |
| 13–15초 | 원본 안전벨트 안내 · 착용 상태 미연결 표시 |
| 15–19초 | 이미지가 있는 가이드 목록·충전 단계 |
| 19–21초 | 질문 화면 · AI 연결 준비 중 |
| 21–29초 | 영어 선택·홈, 일본어 선택·홈 |
| 29–31초 | 이용 종료 확인 |
| 31–34초 | CarCue 마무리 |

모든 기능 장면은 같은 APK의 실제 연속 녹화에서 자른다. Pleos 외부 시스템 패널을 영상 위에 합성하지 않는다. 차량·안전벨트는 APK 내부에 동봉한 이미지이며, 시작 카드도 같은 PNG를 사용한다. 설치 base.apk와 전달 APK, 원본/소개 영상, 이미지 자산의 해시·바이트를 대조한다.

차량은 미리 렌더된 21개 프레임을 수신값에 맞춰 전환하며, 공개 SDK 3D 위젯을 연결한 것은 아니다. 안전벨트 센서는 미연결이다. 소개 영상의 차량 데이터는 MOCK이고 실제 AI 호출은 없다. 실제 SDK 수신 검증은 별도 Pleos AVD 시험으로 구분한다. 출처·사용 범위는 `PLEOS_VISUAL_SOURCE.md`, 음악은 `MEDIA_CREDITS.md`를 따른다.

```bash
python3 scripts/record_native_showcase.py
python3 scripts/render_app_intro.py
```

부팅된 CarCue_UI35와 최신 demo·기기 테스트 APK를 준비한다. 촬영은 20개 실제 화면을 약 2초씩 유지하며 파일 신호로 시작·끝을 동기화한다. `source_scene`과 실제 기기 시각으로 편집 구간을 정렬하고 개폐 전환 시작을 포함한다.

결과는 `output/qa/carcue-app-intro.mp4`, 최신 별칭은 `carcue-pleos-visual-intro.mp4`와 `carcue-mock-flow.mp4`다. 최신 APK 별칭은 `output/apk/carcue-demo-pleos-visual-debug.apk`다. 사진 중심 영상·APK는 `output/qa/archive-before-pleos-reference/`, `output/apk/*-before-pleos-reference.apk`에 보존한다. 원본 기준 영상 `carcue-pleos-sdk.mp4`는 덮어쓰지 않는다.

## 별도 실제 SDK 검증 영상

2026-11-14 실제 문 GET·양방향 콜백과 앱 내부 차량 이미지 개폐/복귀를 확인한 10.002초 전용 AVD 녹화는 `output/qa/pleos-sdk-retest/carcue-pleos-sdk-visual-check.mp4`다. `SDK_VISUAL_RETEST.md`에서 관리한다. 위 34초 소개 영상은 Mock APK 녹화 그대로 보존하며 이 새 SDK 실증과 구분한다.
