# 앱의 실차 사진과 보조 3D

2026-11-14. 최신 사용자 선호는 사진 중심의 완성도 있는 앱 소개다. 홈·상태·문 상세와 Mock 가이드의 기본 차량 이미지를 실제 IONIQ 5/IONIQ 5 N 사진으로 되돌렸다. 3D 모델·개폐·회전 구현은 ‘3D 모델’ 보조 탭에 보존한다. 소개 영상은 실차 사진·수신 상태·가이드 이미지·언어 전환으로 구성하며 3D 화면을 사용하지 않는다.

## 사진 표시와 출처

`VehicleSceneCard`는 `VehicleRealPhoto`를 기본으로 표시한다. 프로필별 원본 JPEG는 `content/illustrations/vehicles.json`으로 매핑한다. IONIQ 5는 crash71100, IONIQ 5 N은 Calreyn88의 CC0 사진이다. 앱에 촬영자와 외관 참고용 표시를 유지한다. 사진에서 문 상태나 정확한 연식·옵션을 판정하지 않는다. 수신 상태는 사진과 별도 텍스트·카드로 보여준다. 출처·해시는 `MEDIA_CREDITS.md`, `media-sources.json`을 따른다.

가이드의 차량 이미지 자리도 실차 사진이다. 충전 이미지는 사용자 인계 ZIP의 기존 사진이며 개발 Mock 시연으로만 사용한다. 실제 조작 절차나 게시용 이용 조건의 검수 완료를 뜻하지 않는다.

## 보존한 3D 기능

보조 탭의 모델은 OpenX Assets의 Hyundai IONIQ 5 2022다. andikapratamaw(2022), Dogan Ulus(2026), MPL-2.0 AND CC-BY-4.0. 원본 37,350삼각형·30재질·곡면 법선·문/유리/미러와 원래 경첩을 유지한다. OpenGL 렌더러·62도 개폐·드래그 회전·미확인 22도 설명 자세는 변경하지 않았다. 원본·변환 소스·라이선스 전문은 APK의 assets/models/source에 계속 포함한다. 현대 공식 CAD 또는 선택 프로필의 연식·트림 일치로 소개하지 않는다. 상세 교체 이력은 `history/NATIVE_VISUALS_REAL_MODEL_PRIMARY.md`다.

신선한 SUPPORTED/VALUE OPEN·CLOSED만 모델 자세로 연결한다. 오류·미지원·미수신·오래된 값은 회색 문과 미확인 표시다. 물리적 왼쪽을 운전석으로 바꾸지 않는다. UX 제한 시 회전·시연 버튼을 막는다. demo 버튼은 MOCK 값만 바꾸며 차량 제어 SDK SET은 호출하지 않는다.

## 실제 동작과 검증

사진·상태 표시·보조 3D·버튼·언어 전환은 실제 앱 코드다. 소개 영상은 새 demo APK를 연속 녹화한 것이다. 차량값은 MOCK, 실제 OpenAI 호출은 없다. 기존 pleos SDK 수신 어댑터를 같은 UI에 유지하지만 이번 변경에서 새 실제 SDK·실차 검증을 하지 않았다.

```bash
python3 scripts/validate_3d_model.py --apk output/apk/carcue-demo-debug.apk --apk output/apk/carcue-pleos-debug.apk
python3 scripts/record_native_showcase.py
python3 scripts/render_app_intro.py
```

19개 실제 화면을 녹화하고, 설치/전달 APK와 사진 자산의 바이트 일치·해시를 검사한다. 이전 3D 중심 영상과 APK를 보존했다. 최신 시험 결과는 `VALIDATION_REPORT.md`를 따른다.
