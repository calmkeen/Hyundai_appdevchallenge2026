# 소개 영상 전환 결함 수정

2026-11-15. 사용자 지적 후 전체 영상을 다시 디코딩해 전환 중 초록색 변색과 검은 플래시를 확인했다. 기존 선별 스틸 검수는 짧은 전환 프레임을 놓쳤다. 앱·APK·기획서·SDK 동작은 변경하지 않았다.

## 변경과 검증

기존 `render_sdk_intro.swift`와 원본/검증 결과를 그대로 두고 독립 `render_sdk_intro_clean.swift`를 추가했다. 투명 레이어/매 컷 opacity fade/움직이는 하단 막대를 사용하지 않고, 초기화한 불투명 BGRA 프레임에 실제 녹화 화면과 기존 안내 디자인을 합성한다. 출력은 H.264·1920×1080·30fps·34초다.

원래 시작/끝3초,14기능 각2초,한국어·영어·일본어,모든 source window/crop/문구/차량·벨트 이미지가 같다. 실제 원본 PTS의 이전 프레임을 유지하며 새 UI·차량 포즈나 프레임 보간을 생성하지 않는다. 기존 영상의 AAC를 passthrough로 복사한다.

| 검사 | 수정 전 | 수정 후 |
| --- | --- | --- |
| 전체 실제 디코딩 | 1020프레임·정상 종료 | 1020프레임·정상 종료 |
| 프레임 간격 | 1/30초 | 1/30초·누락/역행0 |
| 초록 변색 후보와 전환 시각 검토 | 70프레임/28구간 | 0구간 |
| 화면 밖 deck 검은 플래시 | 14프레임 | 0프레임 |
| 음원 PCM | 5,997,600bytes | byte-identical |
| 시각 검수 | 전환 결함 재현 | 경계 시트5개·전체5fps 시트6개·원해상도631프레임 독립 검토 통과 |

초록 후보는 stride4 RGB 표본에서 `G>R+10 && G>B+8 && G>35`, outside-app 비율0.001 이상을 찾는 보조 검사다. 실제 경계 시트를 함께 열어 변색을 확인했다. 검은 플래시는 deck corner 최대RGB<2 보조 검사와 시각 대조를 사용한다. 앱의 의도된 검은 letterbox는 제거 대상이 아니다.

새 MP4 SHA256은 `22399ce4af059b25c85e102e15cdedefd5fd27254aef8ba0910b279835da156c`, 크기는5,880,682bytes다. 공개본은 `media/intro/carcue-sdk-intro.mp4`, 전달용은 `output/video/CarCue-intro-fixed.mp4`다. 음원 PCM SHA256은 전후 모두 `cc2131ac9a83db8a4b1cd8e539e78c40d75fa1e648e9d93539bdafa67b5b96ba`다.

원본34초 MP4 `638c1f54…e18d`와 기존 SDK 원본·원래 렌더러·APK·ZIP은 보존했다. 기존 ZIP에는 이전 영상이 있으므로 메일 제출 시 새 영상으로 교체한다. README의 기존 영상 URL은 수정본을 제공한다. 무료 음악과 기존 출처/권리 범위는 그대로다.

## 재현과 증거

```bash
xcrun swiftc -parse-as-library -O scripts/render_sdk_intro_clean.swift -o /tmp/carcue-render-clean
xcrun swiftc -parse-as-library -O scripts/analyze_intro_video.swift -o /tmp/carcue-analyze-intro
# PLAN은 기존 resolved-plan.json의 출력 경로만 새 경로로 바꾼 JSON이다.
# WORK는 기존 파일이 없는 빈 디렉터리여야 한다.
/tmp/carcue-render-clean render-clean PLAN WORK ORIGINAL_FINAL_MP4
/tmp/carcue-analyze-intro NEW_VIDEO NEW_QA_DIRECTORY --full-frame-at 21.033333
/tmp/carcue-render-clean pcm ORIGINAL_FINAL_MP4 BEFORE_PCM
/tmp/carcue-render-clean pcm NEW_VIDEO AFTER_PCM
```

이번 실행은 `output/qa/video-cleanup-20261115/`의 `validation.json`, before/after `analysis.json`, 컨택트시트, `render-01/render-plan.json`, `render-01/work/source-frame-map.json`, PCM에 남겼다. macOS AVFoundation 디코더는 샌드박스에서 -12911 오류가 발생해 승인된 OS 접근으로 재시도했다. 세 프레임 smoke mux와 실제 AVAssetReader 표본 디코딩을 확인했으며, AVAssetImageGenerator 임의 시각 프리뷰가 검은 이미지를 반환한 경우는 실제 샘플 디코딩과 구분했다.

원본 SDK 녹화는 약4.45fps VFR이므로 정지·반복 프레임과 실제 움직임의 단계는 남아 있다. 이를 새로운30fps 촬영이나 모든 움직임의 보간 완료로 표현하지 않는다. 이번 수정은 편집 전환 결함 제거이며 새 SDK/실차/모델/유료AI/AVD 시험이 아니다.
