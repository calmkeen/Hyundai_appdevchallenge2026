# 앱 내부 IONIQ 5 전용 3D 모델

2026-11-14. 사용자가 기존 자체 모형의 각진 외형을 수정해 달라고 요청해, 실제 IONIQ 5를 모델링한 외부 자산으로 교체했다. 모델의 원본 차체·곡면 법선·재질·문 부품을 사용한다.

## 출처와 이용 조건

[OpenX Assets](https://github.com/vevalabs/openx-assets)의 `hyundai_ioniq_5_2022`를 사용한다. 원작자는 andikapratamaw(2022), 후속 가공은 Dogan Ulus(2026)다. 저장소 `src/REUSE.toml`과 모델 XOMA는 **MPL-2.0 AND CC-BY-4.0**을 명시한다. 원본 Blend SHA256은 LFS 포인터와 대조했다. 원본 GLB는 `20261015` 릴리스에서 내려받았다. 원본·커밋·다운로드 출처·변경 사항·해시는 `content/models/ioniq5-articulated.json`과 `MEDIA_CREDITS.md`를 따른다.

원본은 2022 IONIQ 5 모델이며 현대 공식 CAD·실차 스캔이라고 주장하지 않는다. 앱의 개발 프로필 2024/N 2025와 정확한 연식·트림·시장·옵션의 일치를 검증하지 않았다. N 프로필에서도 일반 IONIQ 5 참고 모델임을 표시하며 N 전용 모델로 소개하지 않는다.

앱 설정에 원작자·저장소·라이선스·변경 사실을 표시한다. 원본 Blend/GLB, 변환 Python 소스, 라이선스 전문과 저작권 기록을 APK의 `assets/models/source/`에도 동봉한다. APK를 ZIP으로 열어 원본·소스를 얻을 수 있다. 같은 파일을 저장소에도 보관한다. 소개 영상과 게시용 크레딧 텍스트에도 모델 출처를 표시한다.

## 모델 변환과 개폐 유지

`build_ioniq5_model.py`는 원본 GLB의 37,350개 삼각형·30개 재질·44개 메시를 읽는다. 형상을 새로 그리거나 기존 각진 모형을 매끈하게 처리하는 방식이 아니다. 원본의 `Grp_Door_Left_0` 하위 문·유리·미러·방향지시등을 하나의 움직이는 그룹으로 유지한다. 원본 경첩을 앱 좌표로 변환한 위치는 (-0.939586, 0.914294, -0.954437)m다. 실제 앱에서 0→62도, 약 0.72초로 부드럽게 개폐한다.

좌표는 +Y 위, -Z 앞, -X 물리적 왼쪽이다. 원본 차체·법선·재질을 보존하고 좌표 변환, 개폐 애니메이션, 접지 그림자만 추가했다. 그림자는 1,248삼각형이며 전체 런타임은 38,598삼각형이다. 변환한 GLB에도 문 개폐 클립을 넣어 일반 3D 도구에서 확인할 수 있다.

## 앱 렌더링

`ArticulatedVehicleView.kt`는 TextureView/OpenGL ES 2.0의 깊이 버퍼와 멀티샘플을 사용한다. 수입한 부드러운 정점 법선을 그대로 보간하고, 금속도·거칠기·투명도에 따라 표면을 구분한다. 간단한 GGX 조명과 절차적 스튜디오 하늘 반사, 톤 매핑을 적용한다. 외부 HDRI나 자동차 사진을 렌더링 입력으로 사용하지 않는다. 유리는 불투명 차체 뒤의 별도 블렌딩 패스로 그린다. 복잡한 투명체의 완전한 광선 추적을 구현한 것은 아니다.

문·유리·미러는 같은 경첩을 공유한다. 가로·세로 드래그로 회전하며 높은 관찰 각도에서는 거리를 늘린다. 움직임이 끝나면 프레임 요청을 멈추고, 화면 제거 시 EGL 자원을 해제한다. 홈·상태·문 상세·Mock 가이드의 차량 자리에 같은 모델을 쓴다. 기존 CC0 사진은 보조 탭으로 보존한다.

## 데이터 구분

신선한 SUPPORTED/VALUE의 OPEN·CLOSED만 개폐 자세를 결정한다. 미수신·미지원·오류·오래된 값은 미확인 표시와 회색 문/22도 설명 자세를 쓴다. 이 자세는 실제 부분 열림 값이 아니다. 물리적 왼쪽을 운전석으로 바꾸지 않는다.

3D 렌더링·개폐·회전·언어 전환은 실제 앱 기능이다. demo의 문 상태와 시연 버튼은 MOCK이며 차량 제어 SDK SET을 호출하지 않는다. UX 제한이 알려지지 않았거나 적용되면 회전·시연 버튼을 비활성화한다. pleos는 기존 SDK 수신을 같은 렌더러에 연결한다. 이번 교체에서 실차·공식 Pleos AVD 수신을 다시 시험하거나 실제 OpenAI를 호출한 것은 아니다.

충전 가이드 사진은 기존 사용자 인계 이미지로 유지했다. 이는 개발 Mock 화면 예시이며 실제 조작 절차나 외부 배포 이용 조건의 검수 완료를 뜻하지 않는다.

## 재현과 검증

```bash
python3 scripts/build_ioniq5_model.py
python3 scripts/validate_3d_model.py
python3 scripts/record_native_showcase.py
python3 scripts/render_app_intro.py
```

기존 각진 모형·APK·영상은 Git 이력과 `output/qa/archive-before-real-model/`, `output/apk/*-before-real-model.apk`로 보존했다. 최신 검증 결과는 `VALIDATION_REPORT.md`, 영상 구성은 `APP_INTRO_VIDEO.md`에서 관리한다. 카탈로그는 한국어·영어·일본어 138개 UI 자원을 포함한다.

기술 근거: [glTF 2.0 변환·재질·애니메이션 명세](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html), [Android TextureView](https://developer.android.com/reference/android/view/TextureView).
