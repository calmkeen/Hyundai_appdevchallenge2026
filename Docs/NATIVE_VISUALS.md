# Pleos 원본 차량·안전벨트 시각화

2026-11-14. 사용자 지정 영상 `output/qa/carcue-pleos-sdk.mp4`의 왼쪽 Pleos 패널에 있던 은색 차량과 파란 안전벨트 그림을 CarCue 앱 내부에 표시한다. 다른 실차 사진이나 OpenX 모델로 대체하지 않는다. 원본 파일은 변경하지 않았다.

## 앱에서의 표시

`VehicleSceneCard`는 Compose `Image`로 안전벨트 안내와 원본 차량을 함께 표시한다. 홈·현재 상태·문 상세에서 사용하며, Mock 가이드의 차량 이미지 자리도 같은 차량을 쓴다. 안전벨트에는 세 언어로 ‘안내 이미지 예시 · 착용 상태 미연결’을 표시한다. 실제 착용 여부나 경고를 판정하지 않는다.

차량은 원본 영상 19~20초에서 잘라낸 21개 프레임을 약 720ms 동안 전환한다. 신선한 `SUPPORTED/VALUE`의 `OPEN`/`CLOSED`만 개폐 자세에 연결한다. 취소·반전 시 현재 프레임에서 이어간다. 미수신·실패·미지원·오래된 값은 흐린 위치 참고 이미지와 ‘미확인’을 표시하며 닫힘으로 안내하지 않는다. 같은 PNG 해시의 비트맵은 공유한다.

이는 **원본 렌더 프레임을 사용하는 앱 내부 이미지 애니메이션**이다. SDK가 공개한 3D 위젯이나 실시간 3D 메시 렌더링으로 소개하지 않는다. 시점 회전은 제공하지 않는다. demo의 개폐 버튼은 Mock 수신값만 바꾸며 차량 제어 SET을 호출하지 않는다. pleos flavor는 기존 실제 SDK GET/Listener 수신값을 같은 표시기에 연결한다.

## 자산과 이전 구현 보존

원본 PNG·좌표·시각·해시는 `content/illustrations/pleos-reference/manifest.json`, 추출 코드는 `scripts/extract_pleos_reference.swift`다. 원본 영상과 모든 PNG 및 두 APK의 바이트 일치를 `scripts/validate_pleos_reference.py`로 검사한다. SDK APK나 SDK 원본 그래픽 자산을 추출·역컴파일하지 않았다. 출처와 사용 범위는 `PLEOS_VISUAL_SOURCE.md`를 따른다.

기존 CC0 사진과 OpenX 모델·OpenGL 코드·원본/라이선스는 저장소와 APK에 보존한다. 현재 주 화면과 소개 영상에서는 사용하지 않으며, 이전 ‘사진 / 3D 모델’ 선택 탭을 노출하지 않는다. 사진 중심 설명은 `history/NATIVE_VISUALS_PHOTO_RETURN.md`, 이전 모델 구현은 `history/NATIVE_VISUALS_REAL_MODEL_PRIMARY.md`에 남겼다. 충전 가이드의 기존 인계 이미지도 보존한다.

## 실행과 검증

```bash
python3 scripts/validate_pleos_reference.py --apk output/apk/carcue-demo-debug.apk --apk output/apk/carcue-pleos-debug.apk
python3 scripts/record_native_showcase.py
python3 scripts/render_app_intro.py
```

최신 소개 영상의 모든 문 상태·안전벨트·언어·가이드·질문·종료 장면은 같은 pleos APK/프로세스의 실제 연속 녹화를 사용한다. SDK debug 앱에서 가이드 UI 예시도 표시하되 안전벨트 센서 미연결·실제 외부 AI 호출 없음은 유지한다. 실제 SDK 수신 시험 및 최종 결과는 `VALIDATION_REPORT.md`를 따른다.

2026-11-14 실제 SDK 재시험도 완료했다. 전용 AVD의 GET 0 → callback 1 → callback 0으로 같은 차량 이미지의 개폐·복귀를 확인했고, 열림 8,083픽셀 변경과 닫힘의 정확한 복귀를 비교했다. SDK 해제까지 통과했으며 `SDK_VISUAL_RETEST.md`에 별도 실제 SDK 영상과 증거를 기록한다. 이후 전체 촬영을 `PleosShowcaseTest`로 확장해 언어·기타 기능까지 같은 SDK 앱으로 통일했다. `SDK_FULL_APP_SHOWCASE.md`를 따른다.
