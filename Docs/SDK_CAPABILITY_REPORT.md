# SDK 지원 조사와 실제 수신 기록

기준일: 2026-11-13. 실차 시험이 아닌 **공식 Pleos 전용 AVD의 실제 SDK 호출**과 Mock을 구분한다.

## 환경과 보존

- 기존 `feature/docs-tourism-concept` / `d302fc6`의 문서·LICENSE·브랜치를 보존했다. 시작 시 미커밋 변경 없음.
- 작업 브랜치 `feature/carcue-mvp`. 원격 push·병합·배포·제출 없음.
- 인계 ZIP의 SHA-256 전 항목 검증 후 최신 명세는 `Docs/`, 원본 시작 지시문은 `Docs/handoff/`에 보관했다.
- Gradle 8.10.2, AGP 8.8.2, Kotlin/Compose compiler 2.0.0, compile/target SDK 35, min SDK 28.
- 최종 JDK: Temurin 17.0.21+9 ARM64. 초기 설치 JDK 18에서는 테스트 의존성 DNS 조회 실패가 발생했으며 JDK 17 전환 후 다운로드·빌드를 통과했다.
- 빌드 SDK, JDK, 새 AVD는 프로젝트 `.tooling/`에 격리했다. 기존 사용자 Android Studio/AVD를 변경하지 않았다.

## 실제 검증 버전

| 구성 | 확인 |
| --- | --- |
| Vehicle SDK | 공식 Maven 2.3.2 AAR 취득·실제 컴파일 성공. 빌드 기본값 2.3.2 |
| Vehicle Service | AVD의 `ai.pleos.playground.service.vehicle`, versionName 2.3.22, versionCode 74 |
| 전용 AVD | Pleos Connect 2.1.0, Android 14 / API 34, ARM64, 2560×1440, RAM 4GB |
| 이미지 | 공식 `crp-arm64-sys-img.xml`과 SHA-1 `24d28eb2f18eba5e87c861a7eb2bdccebb049419` 일치 |
| Mock UI 시험 | 별도 일반 Google APIs API 35, 1280×800 |

온라인 SDK 소개의 Service 2.3.21, 인계서의 2.3.22, 공식 샘플 main의 SDK 2.3.1에는 차이가 있었다. 실제 설치·검증한 조합은 위 표의 2.3.2 / 2.3.22다. 초기 Maven DNS 실패는 재시도 후 해소됐다.

## 속성별 상태

| 항목 | API / 권한 | 실제 결과 |
| --- | --- | --- |
| 앞좌석 왼쪽 문 | checkDoorPositionCapabilities / getCurrentDoorPosition / registerDoorPosition / unregisterDoorPosition, `pleos.car.permission.CAR_DOORS` | Capability 수신: ROW_1_LEFT, min 0 / max 1, READ_WRITE. GET 0 수신, 실제 콜백 0→1과 UI 갱신 확인 |
| SOC | check/get/register/unregisterEvBatteryStateOfCharge, CAR_ENERGY | 구조만 준비, 앱 호출 미연결 |
| 연료 | check/get/register/unregisterFuelPercent, CAR_ENERGY | BEV에서 임의 수치 생성 안 함, 앱 호출 미연결 |
| 타이어 저압 | checkLowTirePressureCapabilities / checkWheelAreaCapabilities / getLowTirePressure | 앱 호출 미연결. PSI 등 숫자 제공으로 해석하지 않음 |
| 경고등 | checkTelltalesCapabilities / getTelltalesInfo / registerTelltales / unregisterTelltales | 앱 호출 미연결. 미수신을 정상으로 표시하지 않음 |
| CarUxRestrictions | 표준 android.car API로 구현, API 35 선언·컴파일 확인 | 초기 실제 GET requires=false / flags=0. 공식 콘솔의 주행 조건에서 실제 callback requires=true / flags=80, 주차 복귀 callback false / 0 확인 |

`ROW_1_LEFT`는 물리적 앞좌석 왼쪽이며 운전석으로 바꾸지 않는다. 공식 Virtual Console의 Front left / Close·Open과 실제 0·1 수신을 대조했다. **시험한 영역과 min 0 / max 1일 때만** CLOSED/OPEN으로 정규화하며 다른 영역·값 범위는 의미를 추측하지 않는다. 이는 실차 전체 사양 검증이 아니다.

## 수신 검증 방법과 증거

1. 공식 전용 AVD 부팅, Vehicle Service 버전 확인.
2. 차량 속성 권한 CAR_DOORS와 SDK 바인딩·네트워크 권한만 포함한 `pleos` APK 설치. CONTROL_* 권한은 없음.
3. SDK initialize → Capability → 최초 GET → Listener 등록.
4. 공식 Virtual Console의 browser heartbeat를 유지한 상태에서 `door_fl=0`을 읽고, `door_fl=1`로 시뮬레이션 변경.
5. 실제 SDK `onPositionUpdated` 콜백, 변경된 화면, 수신 시각 확인.
6. 세션 종료 시 같은 Listener·영역의 unregister와 release 호출·반환 확인. 최종 결과는 검증 보고서를 따른다.

실행 도구는 `scripts/validate_pleos.py`다. emulator serial과 `ro.kernel.qemu=1`을 확인해 실기기에서는 실행을 거부한다. **시뮬레이션 변경은 테스트 도구가 공식 Virtual Console에 요청하며 앱은 GET/구독만 수행한다.** 앱에 SET이나 문 제어 기능을 넣지 않았다.

증거 경로: `output/qa/pleos-instrumentation.txt`, `pleos-sdk-events.txt`, `pleos-console-events.json`, 전용 AVD 화면 캡처. Logcat 시간대와 콘솔 이벤트의 UTC ISO 8601을 구분한다. 차량 측 측정 시각을 알 수 없어 앱 수신 시각으로 표시한다.

## UX 라이브러리 차이와 한계

공식 이미지에는 `ai.pleos.playground.car`와 `car-frameworks-service`가 있지만 표준 `android.car` 공유 라이브러리는 등록되어 있지 않다. 필수 선언 시 APK 설치가 거부되는 것을 실제 확인했다. 표준 라이브러리를 선택적으로 선언하고, 클래스가 없으면 `UxState(known=false, restricted=true)`로 처리한다. 속도나 기어로 제한 상태를 대체하지 않는다.

공유 라이브러리 등록 유무와 런타임 클래스 제공 여부는 달랐다. 선택 선언으로 설치한 후 이 이미지에서는 표준 Car 클래스와 실제 UX API 호출이 정상 동작했다. `UX:GET:requires=false:flags=0` → 주행 조건의 `UX:CALLBACK:requires=true:flags=80` → 주차 복귀 `UX:CALLBACK:requires=false:flags=0`을 기록했다. 증거는 `output/qa/pleos-ux-events.txt`와 `pleos-driving-restriction.png`다.

다른 환경에서 클래스/제한 값을 확인하지 못할 때만 입력·긴 안내를 보수적으로 막고 차종을 확정하지 않은 읽기 전용 상태 보기를 허용한다. 이번 전용 AVD는 실제 초기 조회·변경·주차 복귀를 확인했다. Mock의 PARKED/RESTRICTED는 별도 UI 회귀이며 실차·다른 지역 정책 검증은 남아 있다.

## 공식 출처

- [Vehicle SDK 개요](https://document.pleos.ai/en/docs/pleos-only/connect-sdk-pleos/Vehicle/intro)
- [공식 샘플](https://github.com/Pleos-Playground/pleos-sample-vehicle-app)
- [전용 AVD 설치](https://document.pleos.ai/en/docs/connect/guide/getting-started/application-development/setup-connect-sdk-emulator)
- [Virtual Console](https://document.pleos.ai/en/docs/connect/guide/getting-started/application-development/use-vehicle-emulator)
- [주행 제한 개발 가이드](https://document.pleos.ai/en/docs/pleos-only/vehicle-app-developer-guide/driving-restriction-development-guide)
