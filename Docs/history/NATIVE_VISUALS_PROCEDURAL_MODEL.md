# 앱 내부 IONIQ 5 스타일 3D

2026-11-13. 최신 요청에 따라 사진 중심 화면을 실제로 렌더링하는 3D 모델로 바꿨다. 홈·상태·문 상세의 기본은 3D이며, 기존 실차 사진은 보조 탭으로 보존했다.

## 모델과 동작

`build_ioniq5_model.py`가 저장소 자체 메시를 생성한다. IONIQ 5의 비율(길이 4.635m, 폭 1.890m, 높이 1.605m, 휠베이스 3m), 각진 차체, 픽셀 램프, 긴 실내, 휠 아치·스포크·유리·미러·좌석을 참고했다. 차체와 앞좌석 왼쪽 문은 별도 노드다. 문 외판·유리·내장재·미러가 경첩 축을 따라 0→62도로 함께 회전한다. 약 0.72초의 부드러운 개폐와 가로·세로 드래그 회전을 제공한다. 위에서 내려다보는 각도에서는 관찰 거리를 늘려 화면 여백을 확보한다. 전체 14,734삼각형이다.

외부에서 내려받은 모델이나 현대 공식 CAD가 아니다. 자체 제작 외형 참고 모델이며 정확한 연식·트림·옵션·실내의 일치를 검증하지 않았다. N 프로필에서도 일반 IONIQ 5 스타일 참고 모델임을 표시하며 N 전용 메시라고 주장하지 않는다. 원본 모델·축·치수·파일 해시는 `content/models/ioniq5-articulated.json`, 편집·검토 가능한 일반 형식은 같은 폴더의 GLB다.

`ArticulatedVehicleView.kt`는 Android TextureView와 OpenGL ES 2.0으로 실제 깊이 버퍼·표면 조명·멀티샘플을 사용한다. 멀티샘플이 없는 기기는 기본 설정으로 대체한다. Compose Canvas의 다각형 겹치기나 사진 교체 애니메이션이 아니다. `VehicleVisual.kt`가 같은 Reading과 언어 자원을 연결한다. 애니메이션과 드래그가 멈추면 프레임 요청도 멈추고, 화면 제거 시 EGL 자원을 해제한다.

## 데이터 의미

신선한 SUPPORTED / VALUE / OPEN·CLOSED만 개폐 자세를 결정한다. 미수신·미지원·오류·오래된 값은 ‘상태 미확인’과 회색 문/22도 설명 자세를 사용한다. 이 자세는 실제 부분 열림 값이 아니다. 물리적 왼쪽을 판매지역에 따라 운전석으로 치환하지 않는다.

demo의 문 열림·닫힘 버튼은 MOCK 데이터를 바꾸는 실제 앱 버튼이다. 차량 제어 SDK SET은 호출하지 않는다. UX 제한이 알려지지 않았거나 적용된 경우 회전·시연 버튼은 비활성화한다. pleos는 기존 SDK 수신을 같은 렌더러에 연결하지만 이번 변경에서 실차나 공식 Pleos AVD 수신을 다시 시험한 것은 아니다.

## 보존한 사진과 가이드

CC0 IONIQ 5/IONIQ 5 N 사진과 출처는 보조 ‘실차 사진’ 탭에 유지한다. 기본 3D 대신 사진을 보여주는 흐름은 제거했다. Mock 가이드의 차량 자리에도 같은 3D를 사용하고, 충전 사진 단계는 사용자 인계 이미지로 유지한다. 인계 이미지의 외부 배포 이용 조건은 미검수이며 실제 조작 매뉴얼로 게시하지 않는다. 사진 출처는 `MEDIA_CREDITS.md`를 따른다.

한국어·영어·일본어 자원은 공통 JSON에서 관리한다. 3D/사진/UI 기능은 실제 코드이며 차량 데이터와 미연결 AI를 실제 연동으로 소개하지 않는다.

## 재현과 검증

```bash
python3 scripts/build_ioniq5_model.py
python3 scripts/validate_3d_model.py
python3 scripts/record_native_showcase.py
python3 scripts/render_app_intro.py
```

촬영에는 부팅된 전용 `CarCue_UI35` / emulator-5582와 최신 demo·기기 테스트 APK가 필요하다. 설치 base.apk와 전달 APK 해시를 대조한 뒤 한 번의 실제 실행을 녹화한다. 문 개폐와 회전도 동일 APK에서 동작한다. 원본은 `output/qa/carcue-native-run.mp4`, 소개 영상 구성은 `APP_INTRO_VIDEO.md`, 최신 시험 결과는 `VALIDATION_REPORT.md`를 따른다.

기술 참고: [Android OpenGL 환경](https://developer.android.com/develop/ui/views/graphics/opengl/environment), [TextureView](https://developer.android.com/reference/android/view/TextureView). 외형 참고 치수: [현대 IONIQ 5 브로슈어](https://ioniq5.hyundai.co.in/ioniq-5-brochure.pdf). 브로슈어의 이미지나 CAD 데이터를 추출해 모델에 포함하지 않았다.
