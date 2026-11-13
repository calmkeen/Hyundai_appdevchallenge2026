# 실차 사진 중심 앱 소개 영상

2026-11-14. 사용자가 초기 영상의 실차 이미지가 더 좋고 3D의 완성도가 낮아 보인다고 피드백해, 소개 방향을 사진 중심으로 되돌렸다. 홈·상태·상세와 가이드의 기본 차량 이미지는 실제 IONIQ 5/IONIQ 5 N 사진이다. 3D는 앱의 보조 탭에서 유지하고 소개 영상에 넣지 않는다.

영상은 32초·1920×1080·30fps다. 기능 장면은 약 2초씩 유지하며 한국어·영어·일본어와 실제 언어 선택 장면을 담는다. 이전과 같은 Scott Buckley의 외부 무료 음원 A Kind Of Hope를 사용하고 합성 음악은 만들지 않는다.

| 시간 | 화면 |
| --- | --- |
| 0–3초 | CarCue · 실제 IONIQ 5 사진으로 시작 |
| 3–7초 | 차량·세 언어 선택 |
| 7–11초 | 실차 사진과 문 상태 열림/닫힘 표시 |
| 11–13초 | 실차 참고사진과 수신 상태 분리 |
| 13–17초 | 이미지가 있는 가이드 목록·충전 단계 |
| 17–19초 | 질문 화면 · AI 연결 준비 중 |
| 19–27초 | 영어 선택·홈, 일본어 선택·홈 |
| 27–29초 | 이용 종료 확인 |
| 29–32초 | CarCue 마무리 |

모든 기능 장면은 새 APK의 실제 연속 녹화다. 시작 카드 사진도 APK에 동봉한 원본 JPEG와 바이트가 일치하는지 검사한다. 설치 base.apk와 전달 APK, 원본·소개 영상의 해시를 대조한다. 정지 사진을 실제 문 개폐 영상처럼 소개하지 않는다. 문 상태는 별도 카드의 수신 정보이며 영상의 값은 MOCK이다. 실제 AI 호출은 없다.

사진은 crash71100의 IONIQ 5, Calreyn88의 IONIQ 5 N(CC0)이다. 출처는 `MEDIA_CREDITS.md`, 해시는 `media-sources.json`과 `content/illustrations/vehicles.json`에서 관리한다. 사진의 연식·옵션·현재 상태를 선택 프로필과 일치한다고 주장하지 않는다. 3D의 라이선스와 원본 소스는 앱에 보존한다.

```bash
python3 scripts/record_native_showcase.py
python3 scripts/render_app_intro.py
```

부팅된 CarCue_UI35와 최신 APK를 준비한다. 촬영은 19개 실제 앱 장면을 2초씩 유지하며 시작·끝을 파일 신호로 동기화한다. 편집 도구는 `source_scene`을 실제 기기 시각에 맞춰 자동 정렬한다. 결과는 `output/qa/carcue-app-intro.mp4`이며 `carcue-photo-intro.mp4`, 기본 링크 `carcue-mock-flow.mp4`도 같은 파일이다. 사진 기본 APK 별칭은 `output/apk/carcue-demo-photo-debug.apk`다. 직전 3D 중심 버전·APK는 `archive-before-photo-return/`, `*-before-photo-return.apk`로 보존한다.
