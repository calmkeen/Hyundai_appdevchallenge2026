# 최신 SDK·공식 안내·무료 로컬 AI 소개 영상

이 문서는 새 촬영/편집 준비 단계다. 실제 원본 녹화·렌더·시각 검토가 아직 완료되지 않았으며, 이전 소개 영상의 성공을 최신 APK 결과로 재사용하지 않는다.

정적 준비 검증은 구성 검사·Python AST/JSON 파싱·합성 파일/메타데이터/언어전환 회귀35개·전용 Swift 컴파일이 통과했다. 합성 파일은 실제 MP4/APK가 아니며 기기·SDK·모델·실제 영상 렌더 검증으로 계산하지 않는다.

`sdk-intro-live.json`은 34초를 유지한다. 시작과 마무리 각 3초, 기능 14개는 각각 2초다. 첫 문구는 “언제, 어디서든, 평소와 같은 경험을.”이다. 기존 영상/설정/촬영 스크립트는 변경하지 않는다.

| 순서 | scene_id | 화면 |
| --- | --- | --- |
| 1–2 | `profile`, `language-ko` | 차량 확인, 한국어 선택 |
| 3–5 | `door-closed`, `door-open`, `door-restored` | 실제 SDK GET·열림/닫힘 알림과 앱 차량 시각화 |
| 6–7 | `seatbelt`, `official-guide-step2` | 센서 미연결 안전벨트 이미지, 한국시장 공식 문 안내 |
| 8–9 | `ask-ko`, `translation-en` | 실제 무료 Ollama 답변 선택, 검수된 저장 ANSWER 번역 |
| 10–12 | `language-en`, `ask-en`, `ask-ja` | 영어 전환과 영어·일본어 실제 답변 |
| 13–14 | `drive-restricted`, `end-session` | 실제 플랫폼 UX 제한, 기록 정리와 초기화 |

모든 기능 장면은 같은 최신 `com.carcue.app` APK/프로세스의 한 연속 `screenrecord`에서 가져온다. 정지 이미지로 기능 화면을 대체하거나 다른 APK·이전 영상의 장면을 섞지 않는다. 시작 카드의 차량/벨트 이미지는 해당 APK와 같은 사용자 지정 참고 PNG다.

촬영 담당의 `showcase-manifest.json` 계약은 `schema_version:1`, `type:UNEDITED_REAL_PLEOS_APK_SCREENRECORD`, `test_pass:true`, `single_apk/single_process:true`, 원본 영상/설치 APK SHA, `app_pid`, `source:PLEOS`, `recording_started_device_ms`를 포함한다. scene에는 `scene_id/device_ms/hold_end_device_ms/hold_seconds`, 언어·페이지·차량/UX·AI 출처, Compose/physical PNG 경로가 들어간다. `device_ms`는 편집할 2초 구간의 시작이다. 일반 기능은 안정된 결과를 유지한다. 실제 ASK3의 요청 해시와 Ollama audit3을 대조한다. 세션 토큰은 기록하지 않는다.

`language-en`만 `scene_kind:LANGUAGE_TRANSITION`으로 구분한다. 구간 시작 뒤 실제 English 선택 시각 `selection_clicked_device_ms`, 홈 전환 완료 시각 `transition_completed_device_ms`를 기록하며 두 시각 모두 해당2초 컷 안에 있어야 한다. 끝 스냅샷은 `selected_locale/locale:en`, `page:HOME`이다. 이 장면을 안정된 정지 화면으로 잘못 검증하지 않는다.

원본은 해당 AVD 도구가 지원하는 최대360초 안의 한 연속 녹화다. 원본 길이·해상도는 AVFoundation으로 직접 읽고 모든 선택 구간이 실제 길이 안에 있는지 확인한다. 모델 대기 시간은 원본에 남기고 소개 편집에서 안정된 결과2초만 사용한다.

기본 crop은 2560×1440 원본의 전체 CarCue 패널 `[854,90,1682,1210]`이다. 이전 1051.25 높이 crop은 긴 번역의 마지막 주의문을 자를 수 있어 쓰지 않는다. 전체 패널을 영상 안에 비율 유지해 배치하며, 실제 촬영 PNG와 최종 프레임을 별도로 대조한다.

음악은 기존 `.tooling/media/scott-buckley-a-kind-of-hope.mp3`만 사용한다. SHA256은 `d0dc554c0db9ea208b4f59e4f0c1b4446aa7ef622c7bfeffca278130a46c51f1`, 시작 12초·gain 0.32·fade-in 0.8초/fade-out 1.4초다. 다운로드/생성은 하지 않는다. 이전 34초 영상과 디코딩 PCM을 정확히 비교하며, 원곡과 출처 표기는 `MEDIA_CREDITS.md`/`media-sources.json`을 따른다.

```bash
# 녹화/런타임 없이 구성만 검증한다.
python3 scripts/render_sdk_intro.py --check-plan

# 실제 촬영 완료 후 원본/설치/장면/모델 근거를 읽기만으로 검사한다.
python3 scripts/render_sdk_intro.py --workspace-root /Users/younsung/hyundai \
  --manifest /Users/younsung/hyundai/output/qa/NEW_RECORDING/showcase-manifest.json --check-only

# 검증된 새 원본으로만 새 ignored QA 출력 디렉터리를 만든다.
python3 scripts/render_sdk_intro.py --workspace-root /Users/younsung/hyundai \
  --manifest /Users/younsung/hyundai/output/qa/NEW_RECORDING/showcase-manifest.json \
  --output-dir /Users/younsung/hyundai/output/qa/sdk-live-intro --run-id NEW_RENDER
```

`--plan`으로 이 새 설정의 위치를 지정할 수 있다. `--audio-reference`의 기본값은 보존한 `output/qa/carcue-full-sdk-intro.mp4`다. 렌더러는 기존 출력 디렉터리를 거절하고 새 MP4·resolved plan·검증 JSON·크레딧·1920×1080 프레임16개·비교 PCM만 새 run 디렉터리에 저장한다. 원본 manifest와 기존 plan은 수정하지 않는다.

렌더 검증 성공 뒤에도 `visual_review_status=PENDING_INDEPENDENT_REVIEW`다. 원해상도 프레임16개와 원본 physical 캡처를 직접 열어 실제 CarCue 전면 표시, 두 주의문/출처/언어·검수 표기, 문 변화/주행 제한/종료 장면과 레이아웃을 확인해야 최종 시연 완료로 기록한다.

실제 SDK는 전용 AVD의 값이며 실차/차종/VIN 인증이 아니다. AI는 무료 로컬 Ollama/qwen3:4b가 검수된 전체 안내 단위를 선택하고 서버가 기존 본문·단계·주의문을 조립한다. 저장 번역은 추가 모델 호출0이다. 유료 AI와 생성 QUESTION 번역은 사용하지 않는다. 벨트 센서는 미연결이며 차량 그림은 앱 안의 사전 렌더 프레임이다. Pleos 그래픽의 외부 재배포 권한이나 OEM·인간 전문가 인증을 주장하지 않는다.
