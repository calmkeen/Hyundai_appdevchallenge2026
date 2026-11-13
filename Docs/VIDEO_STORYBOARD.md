# CarCue 영상 구성

최신 소개는 `output/qa/carcue-sdk-app-intro.mp4`다. 34초·1920×1080·30fps, 기능별 약 2초와 한·영·일 전환을 유지한다. 자세한 시간표와 출처는 `APP_INTRO_VIDEO.md`, 편집 구간은 `app-intro.json`에서 관리한다.

7–15초는 실제 Pleos AVD SDK 수신 검증 녹화를 사용한다. SDK GET 닫힘 → 열림 callback → 닫힘 callback과 앱 내부 차량 변화가 각 2초이며, 이어 2초는 원본 안전벨트 안내다. SDK 기본 패널을 제외하고 CarCue 앱 영역만 자른다. 해당 장면은 ‘Pleos SDK 수신 · 전용 AVD’, 다른 demo APK 기능·언어 장면은 ‘MOCK’으로 표시한다. 두 APK와 두 녹화의 해시·출처는 결과 JSON에 기록한다. 배경음악은 이전과 동일한 외부 무료 음원을 유지한다.

SDK 개폐 증거는 `SDK_VISUAL_RETEST.md`와 `output/qa/pleos-sdk-retest/`다. 기존 Mock 소개·원본 녹화도 아래와 같이 보존한다.

## 보존한 demo APK 실행 원본

2026-11-14. 사용자가 지정한 Pleos 영상의 안전벨트·은색 차량 렌더 장면을 APK 내부에 넣었다. 문 상태에 따라 원본 프레임이 전환된다. 기능 화면 위에 Pleos 기본 패널이나 다른 차량 화면을 후처리로 붙이지 않는다. 시작 카드만 같은 동봉 PNG로 구성한다.

| 순서 | 실제 앱 화면·동작 |
| --- | --- |
| 1 | 차량 선택 |
| 2 | 한국어·영어·일본어 선택 |
| 3 | 홈 · 원본 차량과 안전벨트 |
| 4 | 문 열림 수신 상태 |
| 5 | Mock 닫힘 버튼 · 원본 차량 닫힘 전환 |
| 6 | Mock 열림 버튼 · 원본 차량 다시 열림 전환 |
| 7 | 원본 안전벨트 안내 · 착용 상태 미연결 |
| 8 | 문 상세 · 원본 차량 |
| 9 | 가이드 목록 · 기존 안내 이미지 |
| 10 | 가이드 1단계 · 원본 차량 |
| 11 | 가이드 2단계 · 충전 이미지 |
| 12 | 단계의 AI 질문 화면 |
| 13–15 | 영어 선택·홈·상태 |
| 16–18 | 일본어 선택·홈·상태 |
| 19 | 이용 종료 확인 |
| 20 | 초기화된 차량 선택 화면 |

원본은 `carcue-native-run.mp4`, 증거는 같은 이름의 JSON과 `native-showcase-instrumentation.txt`다. 설치/전달 APK·이미지 바이트·해시와 20개 장면의 시각을 기록한다. 최신 소개 편집은 이 원본 중 차량/언어 선택·가이드·질문·종료 장면만 사용하며, 문 개폐·안전벨트 장면은 SDK 입력으로 교체했다. 데이터는 demo의 MOCK이며 안전벨트 센서는 미연결, 실제 AI 호출은 없다. 실시간 SDK 3D 위젯으로 소개하지 않는다.

```bash
python3 scripts/record_native_showcase.py
python3 scripts/render_app_intro.py
```

이전 사진·3D 중심 편집본은 원래 파일 또는 아카이브로 보존한다. 사용자가 지정한 `carcue-pleos-sdk.mp4` 자체도 변경하지 않는다. 시각화 출처·사용 범위는 `PLEOS_VISUAL_SOURCE.md`를 따른다.
