# 사용자 지정 Pleos 시각화 출처

2026-11-14. 사용자가 정확히 지정한 기준은 `output/qa/carcue-pleos-sdk.mp4`의 왼쪽 차량 패널이다. 안전벨트와 은색 차량의 원본 렌더 장면을 앱 내부 이미지로 사용한다. 이후 추가했던 실차 사진이나 외부 3D 모델과 구분한다.

| 항목 | 기록 |
| --- | --- |
| 입력 | `output/qa/carcue-pleos-sdk.mp4` · 2560×1440 · 약 23.387초 |
| SHA256 | `3657b7a2a8105066980b1f27ee3b78bb1e4dac57caa3383a01770cf446fa8a6e` |
| 차량 | 19.00~20.00초 · 0.05초 간격 21장 · crop x=130, y=520, w=635, h=405 |
| 안전벨트 | 4초 · crop x=250, y=70, w=370, h=185 |
| 출력 | `content/illustrations/pleos-reference/car/frame-000.png`~`frame-020.png`, `seatbelt.png` |
| 원본 보존 | 입력 MP4는 변경하지 않음. PNG 해시·좌표·시각은 동봉 manifest에 기록 |

## SDK와의 구분

확인한 Vehicle SDK 2.3.2에는 위 시각화를 앱에 넣는 공개 UI/3D 위젯이 없다. 앱은 기존 SDK의 문 Capability·GET·변경 Listener를 데이터 입력으로 사용하고, 시각화는 위 영상에서 얻은 미리 렌더된 이미지 프레임으로 구현한다. SDK의 실제 3D 엔진이나 모델 파일을 앱에 이식한 것이 아니다. 안전벨트 상태 API는 새로 연결하지 않았다.

원본 영상의 렌더된 화면만 자르며 SDK APK·이미지 패키지의 그래픽 리소스를 추출하거나 역컴파일하지 않았다. 로컬 SDK 이미지 manifest의 라이선스 3.4에 복제·변경·재배포·역컴파일 제한이 있으므로 SDK 자체의 자산을 재사용할 권한이 확인된 것으로 취급하지 않는다.

## 사용 범위 기록

이번 PNG는 사용자가 지정한 녹화를 바탕으로 요청한 **로컬 개발·검토용 참조 시각화**다. Pleos 그래픽을 CC0 또는 별도 공개 라이선스 자산이라고 표시하지 않는다. 외부 배포·공모전 제출을 위한 그래픽 재배포 권한은 확인되지 않았다. 이 작업에서는 외부 게시나 저장소 push를 수행하지 않는다. 음악의 CC BY 4.0과 이전 사진의 CC0는 이 그래픽에 적용되지 않는다.

## 재현

```bash
xcrun swiftc -suppress-warnings -module-cache-path .tooling/swift-module-cache scripts/extract_pleos_reference.swift -o .tooling/extract-pleos-reference
.tooling/extract-pleos-reference output/qa/carcue-pleos-sdk.mp4 content/illustrations/pleos-reference
python3 scripts/validate_pleos_reference.py
```

검증기는 원본 MP4와 PNG 해시, 크기, 개폐 프레임 차이 및 안전벨트 미연결 표기를 검사한다. `--apk`를 반복 지정하면 APK 내부 파일이 동일한지도 대조한다. 해당 영상은 로컬 원본이므로 Git에 동봉하지 않으며 PNG·추출 코드·manifest로 변경 경위를 남긴다.
