# 실제 SDK 문 상태와 앱 차량 시각화 재시험

2026-11-14. **통과**. Mock 수신값을 사용하지 않고 공식 Pleos 전용 AVD의 실제 Vehicle SDK에서 문 GET과 두 방향 변경 콜백을 받았다. 같은 앱 안의 차량 이미지가 닫힘 → 열림 → 닫힘으로 바뀌는 것을 픽셀 비교와 연속 녹화로 확인했다.

| 항목 | 확인 |
| --- | --- |
| 환경 | CarCue_Pleos21, API 34, 2560×1440, 전경 Android 사용자 10 |
| SDK / Service | Vehicle SDK 2.3.2 / Vehicle Service 2.3.22 (versionCode 74) |
| 앱 | `pleos` flavor, `BuildConfig.IS_MOCK=false`, 모든 검사 시 `source=PLEOS` |
| Capability | ROW_1_LEFT, min=0 / max=1, READ_WRITE |
| 최초 값 | 실제 GET 0 → CLOSED, 닫힌 차량 이미지 |
| 열림 변경 | 공식 Virtual Console `door_fl=1` → 실제 SDK callback 1 → OPEN, 열린 차량 이미지 |
| 닫힘 복귀 | 공식 Virtual Console `door_fl=0` → 실제 SDK callback 0 → CLOSED, 최초 이미지와 정확히 일치 |
| 픽셀 | 차량 이미지 139,020픽셀 중 8,083픽셀(약 5.81%)이 열림에서 변경됨 |
| 종료 | 동일 Listener 해제와 SDK release 반환, 앱의 세션·문 값 삭제 확인 |
| 시험 결과 | `PleosSdkTest` 1개, 16.747초, `OK (1 test)` |

닫힘 이미지 SHA256은 최초·복귀 모두 `d8a42beba03f5370c57acc84e5d5a657b239209aa60b770a497cf5893e8d593d`다. 열림은 `edccfcf2c5b795cc2f2889e629e1a6d2f105d2393ada9a47c82f9e8b147d5e6c`다. 텍스트나 접근성 설명만 비교하지 않고 차량 `Image` 노드를 실제로 캡처해 검사했다. 안전벨트는 착용 상태 미연결 안내 이미지로 유지하며 Mock 개폐 버튼이 없는 것도 검사했다.

## 증거

폴더는 `output/qa/pleos-sdk-retest/`다.

- `pleos-instrumentation.txt`: 실제 기기 시험 결과.
- `pleos-sdk-events.txt`: Capability·GET·callback 1·callback 0·unregister·release.
- `pleos-console-events.json`: 외부 시험 도구의 공식 콘솔 시뮬레이션 입력 1 → 0.
- `pleos-initial-get.png`, `pleos-changed-callback.png`, `pleos-restored-callback.png`: CarCue 앱 내부 전체 캡처.
- `sdk-car-initial-closed.png`, `sdk-car-open.png`, `sdk-car-restored-closed.png`: 차량 이미지 노드만의 캡처.
- `sdk-visual-result.json`, `result.json`: 픽셀 차이·복귀 해시, 설치 APK와 빌드 APK 일치, 파일 해시.
- `carcue-pleos-sdk-visual-check.mp4`: 약 10.002초·2560×1440, 실제 전용 AVD 화면의 연속 녹화. 왼쪽은 Pleos 기본 패널, 오른쪽 CarCue 안에 추가한 차량 이미지도 함께 바뀐다. 후처리로 다른 차량 프레임을 영상 위에 삽입하지 않았다.
- `video-check.txt`, `video-frames/`: 닫힘·열림·복귀 영상 프레임 디코딩 및 육안 확인.

검증한 APK는 `output/apk/carcue-pleos-sdk-verified-debug.apk`이며 SHA256은 `556847802b8a4046a3fa445491bc2ba08069bdcd7da6d62e30da2874c4ce6151`다. 설치 base.apk와 동일함을 확인했다. 기존 Mock APK와 전체 Mock 소개는 보존한다. 최신 34초 소개에는 이 검증 영상의 SDK 개폐·안전벨트 장면을 반영하고 나머지 Mock 장면과 구분한다(`APP_INTRO_VIDEO.md`). 원본 시각화 기준 영상 `carcue-pleos-sdk.mp4`도 변경하지 않았다.

## 재현과 범위

최신 `assemblePleosDebug`, `assemblePleosDebugAndroidTest`를 빌드해 부팅된 전용 AVD의 실제 전경 사용자에 설치한 뒤 실행한다.

```bash
.venv/bin/python scripts/validate_pleos.py --record
```

도구는 전용 emulator·부팅 완료·전경 사용자를 확인하고 같은 APK가 설치됐는지 대조한다. instrumentation 실행 사용자와 `run-as <package> --user <id>` 파일 수집 사용자를 일치시킨다. 각 SDK 수신 후 원본 프레임 애니메이션이 끝나도록 실제 시간 동안 Compose 시험 프레임을 진행한다. 단계별 캡처 신호 후 콘솔 값을 변경하며, 마지막 장면 녹화가 끝난 뒤 종료·해제를 확인한다. ADB/전체 시험에 제한 시간을 둔다.

앞선 `Process crashed` 시도는 `output/qa/pleos-reference-sdk-attempt/`에 보존한다. 이번에는 부팅 후 사용자 10의 정상 앱 기동을 확인하고 설치·시험·파일 수집 사용자를 명시해 통과했다. 이전 종료의 단일 원인을 확정한 것은 아니다. 이번 시험 crash 버퍼는 비어 있으며, instrumentation 완료 후 정상 프로세스 종료는 앞선 실행 전 실패와 구분한다.

이는 **실제 SDK/서비스 경로를 사용한 에뮬레이터 검증**이다. 문 상태를 바꾼 주체는 호스트의 공식 Virtual Console 시험 도구이며 앱에는 SDK SET을 추가하지 않았다. 물리 차량 센서·다른 문 영역·다른 값 범위·안전벨트 센서·실제 AI 호출을 검증한 결과가 아니다. 앱 시각화는 원본 렌더 프레임 전환 방식이며 실시간 SDK 3D 위젯으로 바뀐 것은 아니다. 호스트 UTC 이벤트 시각과 AVD 시간대의 앱/logcat 표시는 다르므로 기기 단조 시각과 단계 순서를 함께 기록한다.
