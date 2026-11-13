# 실제 앱의 차량·가이드 시각 요소

2026-11-13. 사용자 요청은 실제 APK 안에서 차량 그림·가이드 이미지·3D가 동작하는 화면을 녹화하는 것이다.

## 기본 실차 사진

홈·상태·상세는 선택 차종별 CC0 실차 사진을 기본으로 표시한다. IONIQ 5는 crash71100, IONIQ 5 N은 Calreyn88의 공개 사진이다. 앱에 촬영자·CC0와 외관 참고용 안내를 표시하며, 사진에서 현재 상태나 정확한 연식·옵션을 판정하지 않는다. 원본·라이선스·해시는 `MEDIA_CREDITS.md`, `media-sources.json`, `content/illustrations/vehicles.json`에서 관리한다. 사진은 해당 APK 안에서 직접 로드한다.

3D 위치 모형은 ‘3D 위치 예시’ 보조 탭에서 선택한다. 이는 실제 차종의 정밀 3D 모델이 아니다. 안내 단계의 차량 그림 자리도 실차 참고사진으로 바꿨다.

## 3D 보조 모형과 가이드 구현

- `VehicleVisual.kt`가 앱 내부에서 절차적으로 만든 3D 메시를 원근 투영해 Compose Canvas로 그린다. 드래그로 관찰 각도를 바꾸며 실제 화면 상태에 따라 앞좌석 왼쪽 문을 표시한다. 외부 3D 영상이나 Pleos 시스템 UI를 붙이지 않는다.
- 모형은 차체·유리·바퀴·문으로 이루어진 일반적인 차량 위치 예시다. 선택 차종의 정확한 외형이나 스캔 모델을 뜻하지 않는다. 해당 설명을 한국어·영어·일본어로 표시한다.
- 신선한 `SUPPORTED / VALUE / OPEN 또는 CLOSED`만 모형의 문 상태로 연결한다. 미수신·오류·오래된 값·미지원은 상태 미확인으로 표시한다. 물리적 왼쪽을 운전석으로 바꾸지 않는다.
- 홈·차량 상태·문 상세에서 모형을 표시한다. 차량 상태의 Mock 열림·닫힘 버튼은 demo에서만 제공하며 실제 차량 제어를 호출하지 않는다. UX 제한이 알려지지 않았거나 적용된 경우 회전·Mock 버튼을 비활성화한다.
- `content/illustrations/charging-preview.png`는 첨부된 `assets/ui/guide.svg`의 내장 PNG를 그대로 추출한 것이다. 가이드 목록과 Mock 단계 화면의 실제 Image 컴포넌트로 로드한다. 사진 사용권의 외부 배포 검수 상태는 인계 원본과 같다. 현재는 개발 시연 자산이며, 실제 차종별 조작 절차의 검수 완료를 뜻하지 않는다.
- 세 언어의 UI 문구는 136개다. 시각 요소 문구도 공통 JSON 자원으로 관리한다. 사진은 Mock 가이드 예시에만 연결하며 실제 게시 가이드 데이터와 섞지 않는다.

## 실제 연동과 Mock

3D 렌더링·드래그·사진 표시·버튼·언어 변경은 실제 앱 기능이다. demo의 차량값과 열림·닫힘 시연은 MOCK이다. pleos는 기존 SDK 수신 결과를 같은 시각 컴포넌트에 연결하지만, 이번 변경에서 실차나 SDK를 재시험하지 않았다. 실제 OpenAI 호출도 추가하지 않았다.

## 촬영

`NativeShowcaseTest`가 실제 Compose 버튼과 터치로 하나의 앱 실행을 진행한다. 각 기능을 2초 유지하며, 호스트는 앱이 준비된 뒤 Android `screenrecord`를 시작한다. 테스트 종료로 런처가 나타나기 전에 녹화를 멈추도록 파일 신호로 동기화한다.

```bash
python3 scripts/record_native_showcase.py
```

부팅된 `CarCue_UI35` / emulator-5582와 demo·기기 테스트 APK가 필요하다. 스크립트는 지정한 테스트 AVD만 사용하고 해당 demo 앱의 데이터를 초기화한다. 원본 APK와 설치된 base.apk의 SHA256을 비교한 뒤 녹화한다. 결과는 `output/qa/carcue-native-run.mp4`, APK·영상 해시와 장면 시각은 같은 이름의 JSON, 기기 실행 결과는 `native-showcase-instrumentation.txt`다.

이 영상은 하나의 APK 실행 화면을 연속 녹화한다. 사진·3D·가이드 화면도 해당 APK 안에서 그려진다. 영상 후처리로 이미지·다른 앱 화면을 삽입하지 않는다. 이전 편집본들은 이 실행 증거와 별도로 보존한다.

## 기술 참고

[Compose 제스처 처리](https://developer.android.com/develop/ui/compose/touch-input/pointer-input/understand-gestures)를 참고했다. 외부 3D 라이브러리를 추가하지 않았으며, 기존 Compose/Android 의존성으로 빌드한다.
