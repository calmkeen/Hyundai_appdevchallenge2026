# 같은 SDK 앱의 전체 기능·세 언어 촬영

2026-11-14. 모든 기능 장면을 동일한 `pleos` debug APK와 동일 앱 프로세스에서 새로 촬영했다. demo APK 장면을 섞지 않는다. 첫 문구는 **“언제, 어디서든, 평소와 같은 경험을.”**이며 34초·기능별 2초·기존 음악을 유지한다.

| 항목 | 결과 |
| --- | --- |
| APK / 패키지 | `output/apk/carcue-pleos-showcase-debug.apk` / `com.carcue.app` |
| SHA256 | `57f767c6850501c6dddd6eac0fab90106c7ef8f840adc97dadfb18066b73edf0` · 설치 base.apk와 일치 |
| 환경 | 공식 CarCue_Pleos21 AVD, API 34, 사용자 10, SDK 2.3.2 / Service 2.3.22 |
| 동일 프로세스 | PID 27585 · 녹화 시작과 종료 직전 동일함을 호스트에서 확인 |
| 실제 촬영 시험 | `PleosShowcaseTest` 1개, 79.742초, `OK (1 test)` |
| 장면 | 차량 선택·세 언어 선택·홈·문 상태/상세·안전벨트·가이드 목록/단계·질문·영어/일본어·종료, 총 20개 |
| 문 상태 | 실제 GET 0, 한국어 callback 1→0, 영어 callback 1, 일본어 callback 0 |
| 이미지 | 닫힘→열림의 실제 차량 이미지 차이, 다시 닫힘에서 최초 픽셀·PNG 해시와 정확히 일치 |
| 언어/사양 | ko-KR→en→ja-JP, KR 시장 유지, 세 언어 모두 같은 SDK 수신 상태 사용 |
| 종료 | 프로필·문 값·세션 삭제, 동일 Listener 해제 및 SDK release 반환 |
| 문자열 | 148개 UI 자원, 세 언어 누락·치환 변수 계약 검사 통과 |

전체 20개 장면의 `source=PLEOS`, 언어·페이지·문 값과 기기 단조 시각을 기록한다. 프로필/최초 언어 선택 전에는 문 값을 아직 요청하지 않으며, 한국어를 선택한 뒤 실제 GET/Listener 연결을 시작하고 영어·일본어 전환 중에도 같은 연결을 유지한다. 값은 시험 코드가 ViewModel에 넣지 않는다. 공식 Virtual Console의 가상 입력만 호스트가 바꾸고 앱은 SDK로 읽기·구독한다. 앱의 SDK SET은 추가하지 않았다.

## 가이드와 AI 표시

SDK debug 앱에서도 기존 가이드 화면 예시를 열 수 있게 했다. `BuildConfig.DEBUG`에서만 예시 카드를 노출하며 원본 차량 매뉴얼을 게시한 것으로 취급하지 않는다. SDK 쪽 예시 문구는 세 언어로 ‘검수된 차량 안내 준비 중’과 ‘이미지 예시’를 표시한다. 실제 SDK 저장소·문 수신은 그대로이며 Mock 차량 공급자로 바꾸지 않는다. AI 질문 화면은 실제 앱 UI이고 외부 AI 호출은 하지 않는다. 안전벨트도 센서 미연결 안내 이미지다.

## 증거와 재현

`output/qa/pleos-full-showcase/`에 다음을 저장한다.

- `carcue-pleos-native-run.mp4/json`: 한 APK의 무편집 연속 녹화·설치/영상 해시·20개 장면·프로세스 ID.
- `instrumentation.txt`, `sdk-events.txt`, `console-events.json`, `showcase-result.json`: 전체 촬영 시험, 실제 GET·4회 변경 callback·해제, 예시/AI 연결 범위.
- `ko-closed.png`, `ko-open.png`, `ko-restored.png`, `en-home/status.png`, `ja-home/status.png`: 같은 SDK 앱의 언어/문 상태 캡처.
- `car-initial-closed.png`, `car-open.png`, `car-restored-closed.png`: 앱 안 차량 이미지의 직접 비교.
- `intro-video-check.txt`, `intro-frames/`, `intro-audio-check.json`: 최종 소개 검수.

부팅된 전용 AVD와 JDK/SDK 환경에서 다음을 사용한다.

```bash
android/gradlew -p android :app:assemblePleosDebug :app:assemblePleosDebugAndroidTest
cp android/app/build/outputs/apk/pleos/debug/app-pleos-debug.apk output/apk/carcue-pleos-showcase-debug.apk
python3 scripts/record_pleos_showcase.py
python3 scripts/render_app_intro.py
```

호스트가 동일 SDK APK/테스트 APK 설치, 전경 사용자와 설치 APK 해시 확인, 공식 콘솔 heartbeat와 Park 입력, 준비/시작/끝 파일 동기화, 장면별 2초 유지, 한국어·영어·일본어의 네 번 문 변경, 녹화 종료 후 세션 해제를 검증한다. 실제 SDK 흐름은 `GET 0 → callback 1 → callback 0 → callback 1 → callback 0 → unregister → release` 순서까지 검사한다. 기기/호스트 시각대는 다르므로 앱 단조 시각의 장면 마커로 편집한다.

이 결과는 공식 전용 AVD의 실제 SDK 경로 검증이다. 실차·안전벨트 센서·외부 AI·검수 매뉴얼을 새로 검증한 결과는 아니다. 시각화는 기존 원본 렌더 프레임 전환 방식이며 실시간 SDK 3D 위젯 이식은 아니다. 원본 그래픽 사용 범위는 `PLEOS_VISUAL_SOURCE.md`를 따른다.
