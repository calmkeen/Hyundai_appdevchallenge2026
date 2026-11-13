# Mock 짧은 영상 구성

2026-11-13. 사용자 요청: 이전 이미지 요소 포함, 기능당 약 2초, 한국어·영어·일본어 전환 유지.

최신 파일은 `output/qa/carcue-mock-visuals-3d.mp4`이며 1280×800, 30fps, 32초다. 실제 demo APK 녹화 구간·기기 테스트 캡처, 인계 가이드의 충전 사진, 기존 Pleos 전용 에뮬레이터 녹화의 3D 차량 장면을 합친 **편집본**이다. 모든 장면은 2초다.

3D 차량은 **Pleos 에뮬레이터의 시스템 UI**다. 영상에서는 차량 부분을 확대하고 출처 자막을 넣었다. CarCue가 자체 3D 렌더러를 구현했다는 의미가 아니다. 충전 사진도 영상용 참고 장면으로 구분한다. Mock 앱의 상태값, 시스템 3D 화면, 참고 이미지를 각각의 출처로 관리한다.

| 시간 | 장면 | 원본 |
| --- | --- | --- |
| 0–2초 | 3D 차량 · 문 닫힘 | Pleos 에뮬레이터 시스템 UI, 확대·출처 자막 |
| 2–4초 | 차량 선택 | 실제 APK 녹화 |
| 4–6초 | 한국어·영어·일본어 목록 | 실제 APK 녹화 |
| 6–8초 | 한국어 홈 | 실제 APK 녹화 |
| 8–10초 | 한국어 차량 상태 | 실제 APK 녹화, MOCK 값 |
| 10–12초 | 문 열림 3D 표시 | Pleos 에뮬레이터 시스템 UI, 확대·출처 자막 |
| 12–14초 | 충전 가이드 이미지 예시 | 인계 SVG의 내장 사진, 별도 자막 |
| 14–16초 | 단계별 가이드 | 실제 APK 기기 테스트 캡처 |
| 16–18초 | AI 질문 / 자료 부족 응답 | 실제 APK 기기 테스트 캡처, MOCK 서버 |
| 18–20초 | 영어 선택·전환 | 실제 APK 녹화 |
| 20–22초 | 영어 홈 | 실제 APK 녹화 |
| 22–24초 | 영어 차량 상태 | 실제 APK 녹화, MOCK 값 |
| 24–26초 | 일본어 선택·전환 | 실제 APK 녹화 |
| 26–28초 | 일본어 홈 | 실제 APK 녹화 |
| 28–30초 | 일본어 차량 상태 | 실제 APK 녹화, MOCK 값 |
| 30–32초 | 이용 종료 후 초기 화면 | 실제 APK 기기 테스트 캡처 |

앱 코드와 APK를 바꾸는 작업은 수행하지 않았다. 무편집 녹화는 `carcue-mock-languages.mp4`, SDK 녹화는 `carcue-pleos-sdk.mp4`로 보존한다. 이전 28초 편집본은 `carcue-mock-short.mp4`에 남긴다. 최신 편집본의 입력 파일·종류·확대 영역·구간·SHA256은 `carcue-mock-visuals-3d.json`에 기록한다. 기본 `carcue-mock-flow.mp4`는 새 32초 편집본으로 갱신한다.

## 재현

기존 녹화·기기 테스트 캡처가 `output/qa/`에 있는 macOS/Xcode 환경에서 실행한다.

```bash
python3 scripts/render_mock_short.py
```

`Docs/video-short.json`이 편집 구성을 관리한다. `scripts/edit_mock_showcase.swift`는 AVFoundation으로 영상 구간을 자르고, 사진·캡처를 2초 영상으로 만든 뒤 30fps MP4로 내보낸다. 3D 영상에는 구간별 출처 자막을 합성하며, 나머지 구간에는 표시하지 않는다. 음성·배경음악은 추가하지 않았다. 기술 참고: [Apple의 시간 구간 삽입 API](https://developer.apple.com/documentation/avfoundation/avmutablecomposition/inserttimerange(_:of:at:)), [프레임 쓰기 API](https://developer.apple.com/documentation/avfoundation/avassetwriterinputpixelbufferadaptor/append(_:withpresentationtime:)).
