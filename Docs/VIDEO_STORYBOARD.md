# Mock 짧은 영상 구성

2026-11-13. 사용자 요청: 이전 이미지 요소 포함, 기능당 약 2초, 한국어·영어·일본어 전환 유지.

최신 파일은 `output/qa/carcue-mock-short.mp4`이며 1280×800, 30fps, 28초다. 실제 demo APK 녹화 구간과 기기 테스트 캡처에, 인계 패키지 `assets/ui/guide.svg`에 포함된 충전 사진을 더한 **편집본**이다. 충전 사진은 영상용 참고 장면으로 삽입했고 별도 자막으로 구분한다. 검수된 차량 조작 안내나 실제 AI 답변 생성의 증거로 사용하지 않는다.

| 시간 | 장면 | 원본 |
| --- | --- | --- |
| 0–2초 | 차량 선택 | 실제 APK 녹화 |
| 2–4초 | 한국어·영어·일본어 목록 | 실제 APK 녹화 |
| 4–6초 | 한국어 홈 | 실제 APK 녹화 |
| 6–8초 | 한국어 차량 상태 | 실제 APK 녹화, MOCK 값 |
| 8–10초 | 충전 가이드 이미지 예시 | 인계 SVG의 내장 사진, 별도 자막 |
| 10–12초 | 단계별 가이드 | 실제 APK 기기 테스트 캡처 |
| 12–14초 | AI 질문 / 자료 부족 응답 | 실제 APK 기기 테스트 캡처, MOCK 서버 |
| 14–16초 | 영어 선택·전환 | 실제 APK 녹화 |
| 16–18초 | 영어 홈 | 실제 APK 녹화 |
| 18–20초 | 영어 차량 상태 | 실제 APK 녹화, MOCK 값 |
| 20–22초 | 일본어 선택·전환 | 실제 APK 녹화 |
| 22–24초 | 일본어 홈 | 실제 APK 녹화 |
| 24–26초 | 일본어 차량 상태 | 실제 APK 녹화, MOCK 값 |
| 26–28초 | 이용 종료 후 초기 화면 | 실제 APK 기기 테스트 캡처 |

앱 코드와 APK를 바꾸는 작업은 수행하지 않았다. 무편집 녹화는 `carcue-mock-languages.mp4`로 보존한다. 편집본의 입력 파일·종류·구간·SHA256은 `carcue-mock-short.json`에 기록한다. 기본 `carcue-mock-flow.mp4`도 짧은 편집본으로 갱신한다.

## 재현

기존 녹화·기기 테스트 캡처가 `output/qa/`에 있는 macOS/Xcode 환경에서 실행한다.

```bash
python3 scripts/render_mock_short.py
```

`Docs/video-short.json`이 편집 구성을 관리한다. `scripts/edit_mock_showcase.swift`는 AVFoundation으로 영상 구간을 자르고, 사진·캡처를 2초 영상으로 만든 뒤 30fps MP4로 내보낸다. 음성·배경음악은 추가하지 않았다. 기술 참고: [Apple의 시간 구간 삽입 API](https://developer.apple.com/documentation/avfoundation/avmutablecomposition/inserttimerange(_:of:at:)), [프레임 쓰기 API](https://developer.apple.com/documentation/avfoundation/avassetwriterinputpixelbufferadaptor/append(_:withpresentationtime:)).
