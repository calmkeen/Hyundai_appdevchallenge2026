# 최신 SDK·공식 안내·무료 로컬 AI 소개 영상

최종 기능 촬영 `sdk-session-showcase-20261115-03`은 native 194.754초와 host 검증이 통과했다. 같은 최신 APK/프로세스의 단일 원본으로 새 소개 영상을 편집한다. 최종 편집 `live-sdk-intro-20261115-03`도 34초/1920×1080/30fps·음악 PCM exact와 원해상도 대표16장+세부13장 검토를 통과했다. 이전 영상의 성공을 최신 결과로 재사용하지 않는다.

최종 로컬 영상은 `output/qa/sdk-live-intro/live-sdk-intro-20261115-03/carcue-sdk-live-intro.mp4`, SHA256 `638c1f54d3e29ddba3212154c118267bcfc8be21a3dda0ad004066f3e600e18d`다. 별도 `visual-review.json` SHA256은 `35a6ea072c40f4ed01cf892284458cac2285d8f4a99c67afec861f57306c6b4f`이며 원본/renderer의 PENDING 기록은 수정하지 않았다.

`sdk-intro-live.json`은 34초 구성이다. 시작과 마무리 각 3초, 기능 14개는 각각 2초다. 첫 문구는 “언제, 어디서든, 평소와 같은 경험을.”이다. 기존 영상/설정/촬영 스크립트와 음악은 보존했다.

| 순서 | scene_id | 화면 |
| --- | --- | --- |
| 1–2 | `profile`, `language-ko` | 차량 확인, 한국어 선택 |
| 3–5 | `door-closed`, `door-open`, `door-restored` | 실제 SDK GET·열림/닫힘 callback과 앱 차량 시각화 |
| 6–7 | `seatbelt`, `official-guide-step2` | 센서 미연결 안전벨트 이미지, 한국시장 공식 문 안내 |
| 8–9 | `ask-ko`, `translation-en` | 실제 무료 Ollama 답변 선택, 검수된 저장 ANSWER 번역 |
| 10–12 | `language-en`, `ask-en`, `ask-ja` | 실제 영어 선택과 영어·일본어 답변 |
| 13–14 | `drive-restricted`, `end-session` | 실제 플랫폼 UX 제한, 기록 정리와 초기화 |

모든 기능 장면은 같은 `com.carcue.app` APK/프로세스의 한 연속 `screenrecord`에서 가져온다. 정지 이미지로 기능 화면을 대체하거나 다른 APK·이전 영상의 장면을 섞지 않는다. 시작 카드의 차량/벨트 이미지는 해당 APK와 같은 사용자 지정 참고 PNG다.

촬영03의 앱 SHA는 `5ef560ba1a24e3ce206aeeb6f4f336018b6e8a182bec7214aabc5dd4a261479f`, 설치 후 pull SHA도 같다. test APK는 `82409ca5409eebdd7ead1a02a5da4ffb768804089a84e303ec9814c2bb92b884`, PID는 `12463`이다. 원본 SHA는 `fd836b2fcc2185472fe575efbaf23c06c53717d561c4b2bbada2c4c12994e10b`다.

원본은 2560×1440, 199.981초의 실제 가변 프레임 녹화다(평균 약4.45fps). 최종 30fps는 기록된 프레임을 반복/샘플링한 편집이며 생성한 차량 포즈나 보간 움직임을 추가하지 않는다. 원본 길이·해상도를 AVFoundation으로 읽고 모든2초 구간이 원본 안에 있는지 검사한다. 모델 대기는 원본에 남긴다.

`showcase-manifest.json`의 원본/설치/장면 해시, 단일 APK·프로세스, PLEOS, 실제 ASK3의 요청 해시와 Ollama audit3을 대조했다. Ollama `0.40.16`/`qwen3:4b`의 실제3회 선택이며, 저장 ANSWER 번역3회는 `STORED_GUIDE`/model null/추가 모델 호출0이다. 생성 QUESTION 번역과 유료 AI는 호출하지 않았다. 종료 후 DB sessions/results/history 모두0, fixture Park/0/CLOSED 복구와 cleanup 오류0도 확인됐다.

원본 PNG39개 중 동일 픽셀 alias4개를 제외한35개를 원해상도로 실제 열었다. 3ASK+3저장 번역은 게시된 body→1단계/주의→2단계/주의의 전체 단위와 exact 일치한다. 닫기 전 신체 확인, 끼인 상태에서 닫지 말기, 출발 전 모든 문·후드·테일게이트 완전 닫힘, 계기판 경고문과 열림 표시 둘 다 해제를 유지한다. KO/EN/JA 선택과 원문/검수 번역 표기, KR 매뉴얼 범위, 두 공식 출처도 대조했다. 이 검토는 선택된 예시에 대한 독립 AI 보조 검토이며 OEM·인간 전문가·원어민 인증이 아니다.

`language-en`은 실제 Japanese UI 언어 메뉴→English 선택→English HOME 전환이다. 원본과 편집의 구간 내0.05/0.25/0.8/1.8초를 별도로 열어 확인했다. 편집 시작0.05초는 기존 fade로 어둡고0.25/0.8초 메뉴,1.8초 영어 HOME이 보인다. native 선택/완료 시각도 해당2초 안에 있는지 검사하며 정지 화면으로 취급하지 않는다.

문2컷은 `--source-window-review`에 고정한 실제 callback 전환을 사용한다. 원본의 OPEN21.16–23.16초, CLOSED24.8–26.8초를 선택했다. callback 시각 환산은 `device_ms − (recorded_at − received_at)`을 사용하지만 영상 프레임과 정확히 일치한다고 단정하지 않는다. 원해상도 원본 픽셀을 직접 열어 문 각도 변화를 확인한 것이 편집 구간의 근거다. renderer는 두 문만 허용하고 callback 추정±2초·2초 길이·최소3개 고유 시각의 전체 프레임 해시·컷 순서/비겹침을 검사한다.

같은 검토 파일의 `verified_scene_windows`는 안전벨트 STATUS 한 장면만 선택적으로 허용한다. marker±3초/2초 길이/실제 전체 프레임3개 이상과 해시를 요구하며, 선택 구간은 원본28.9–30.9초다. 다른11개 컷은 native manifest의2초 구간과 정확히 같다. 이 검토 파일은 원본 manifest를 고치지 않는다.

전체 CarCue 패널 crop은 `[854,90,1682,1210]`이며 영상 안에 비율을 유지해 letterbox로 배치한다. 기존1051.25 높이는 긴 번역 마지막 주의문을 잘라 쓰지 않는다. 긴 결과를 담기 위해 스크롤한 장면에서는 상단 화면 제목 일부가 viewport 밖이지만 결과·주의문은 모두 보인다. 기능당2초는 소개용으로 전체 주의문을 읽을 충분한 시간은 아니다.

음악은 기존 `.tooling/media/scott-buckley-a-kind-of-hope.mp3`만 사용한다. SHA256 `d0dc554c0db9ea208b4f59e4f0c1b4446aa7ef622c7bfeffca278130a46c51f1`, 시작12초/gain0.32/fade-in0.8초/fade-out1.4초를 유지했다. 이전34초 영상과 디코딩 PCM5,997,600바이트가 exact 일치하며 SHA는 `cc2131ac9a83db8a4b1cd8e539e78c40d75fa1e648e9d93539bdafa67b5b96ba`다. 출처/CC BY4.0 표기는 `MEDIA_CREDITS.md`/`media-sources.json`과 새 영상 크레딧을 따른다.

```bash
python3 scripts/render_sdk_intro.py --check-plan

# 실제 수행 명령. 다시 실행할 때는 기존 폴더 보존을 위해 새 run-id를 쓴다.
python3 scripts/render_sdk_intro.py --workspace-root /Users/younsung/hyundai \
  --manifest /Users/younsung/hyundai/output/qa/multilingual-session-20261115/sdk-session-showcase-20261115-03/showcase-manifest.json \
  --source-window-review /Users/younsung/hyundai/output/qa/sdk-live-intro/source-review-20261115-01/source-window-review-v3.json \
  --output-dir /Users/younsung/hyundai/output/qa/sdk-live-intro --run-id live-sdk-intro-20261115-03 \
  --audio-reference /Users/younsung/hyundai/output/qa/carcue-full-sdk-intro.mp4
```

`--check-only`는 실제 미디어를 디코딩하지 않고 파일/설치/장면/AI/선정 프레임 해시와 메타데이터를 검사한다. 실제 render는 새 ignored QA 폴더만 만들며 Swift 전용 binary·MP4·resolved plan·검증 JSON·크레딧·프레임16개·PCM을 저장한다. macOS 디코더는 기본 sandbox에서 `Cannot Decode(-11821/-12911)`가 발생했고 승인된 OS 접근 재시도에서 성공했다.

정적 준비35개와 새 전환/장면 메타데이터 회귀22개,3개 컷 변경/11개 동일 대조, Python AST·JSON·Swift 컴파일을 검증했다. 이는 실제 SDK/모델 재시험 수로 계산하지 않는다. 원본과 renderer의 `PENDING_INDEPENDENT_REVIEW` 상태는 불변으로 두고 별도 `visual-semantic-review.json`/`visual-review.json`에 독립 관측과 한계를 남긴다.

로컬 ignored QA 경로는 다음과 같다. 원본 JSON·이미지·실패 이력은 Git에 넣거나 덮어쓰지 않는다.

- `output/qa/multilingual-session-20261115/sdk-session-showcase-20261115-03`: 원본·native/host/audit·독립 의미/시각 검토.
- `output/qa/sdk-live-intro/source-review-20261115-01`: 원본 시각별 프레임·선정 근거v1/v2/v3·메타데이터 회귀.
- `output/qa/sdk-live-intro/live-sdk-intro-20261115-03`: 최종 편집·16개 대표/별도 세부 프레임·PCM·독립 검토.
- 촬영01의 애니메이션 캡처 실패와02의 고정 sidebar scroll 실패는 보존했다. 앱 코드 변경 없이 test만 보완한 촬영03이 성공했다.
- 편집01은 안전벨트 컷에 다음 가이드 화면이 섞여 시각 검토 실패,02는 열림 움직임이 fade에 가려 시작 시점을 보강했다. 두 결과의 format/PCM 성공과 전체 시각 승인 여부를 구분해 보존했다.

실제 SDK는 전용 AVD의 값이며 실차/차종/VIN 인증이 아니다. AI는 검수된 전체 안내 단위를 선택하고 서버가 기존 본문·단계·주의문을 조립한다. 벨트 센서는 미연결이고 차량 그림은 앱 안의 사전 렌더 프레임이다. Pleos 그래픽 외부 재배포 권한, 범용 AI 품질 완료, OEM·인간 전문가 인증을 주장하지 않는다.
