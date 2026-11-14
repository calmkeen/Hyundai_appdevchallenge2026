# UX 서비스 연결 복구

2026-11-14. `feature/ux-service-recovery`. 차량 데이터 SDK와 UX 제한 서비스 연결은 독립이다. 이 변경은 실제 플랫폼의 UX boolean/flags 판정과 unknown의 차단 동작을 유지하면서 연결 소유권과 제한된 재연결만 보완한다.

## 실제 관측과 구현 경계

`output/qa/official-links-20261114/official-resources-20261114-05/events.jsonl`에는 등록 원문·지원 링크의 한국어/영어/일본어 6회 왕복 뒤 SDK GET 수가 1→7로 늘고 가이드 단계 1이 보존된 기록이 있다. 후반 AI 화면에서 Activity는 `RESUMED`인데 UX는 unknown으로 바뀌어 다음 동작이 차단됐다. 당시 실제 `UX:DISCONNECTED` 로그가 관측됐다. 서비스 자체의 끊김과 이전 연결 콜백의 지연 중 어느 것이 근본 원인인지는 확정하지 않는다. 이 실패를 성공으로 바꾸지 않는다.

기존 어댑터는 모든 foreground 연결이 같은 `ServiceConnection`과 listener, 가변 Car/manager 필드를 공유했다. 이제 각 attempt가 별도의 Car·manager·ServiceConnection·listener를 소유한다. 순수 `UxConnectionGate`가 foreground epoch와 attempt token을 검사해 이전 attempt의 늦은 known/unknown 이벤트를 버린다.

- `start`: 이전 소유권·timer를 정리하고 새 epoch를 시작한다. 첫 값은 unknown이다.
- 연결 완료: 해당 attempt의 manager를 얻고 listener를 등록한 뒤 현재 UX를 실제 GET한다. 이 GET이 완료되기 전 callback으로 known을 만들지 않는다.
- 연결 예외·manager/GET 값 없음·실제 disconnect·15초 초기 연결 timeout: 먼저 해당 token을 무효화하고 unknown을 보고한다. 그다음 그 attempt의 listener/Car만 unregister/disconnect한다.
- 활성 foreground에서는 1초·3초·10초 간격으로 최대 3번 추가 연결한다. 매번 새 Car/manager/listener를 사용한다. 성공 GET은 같은 foreground의 retry 예산을 다시 채우지 않는다. 예산 소진 뒤에는 unknown으로 유지한다.
- `stop`: 먼저 epoch를 무효화하고 report를 제거하며 retry/timeout을 취소한다. 같은 소유자 객체만 한 번 정리한다. 종료 뒤 timer나 이전 연결 callback은 새 연결·UI 갱신을 만들지 못한다.

어댑터의 lifecycle 진입과 timer/manager 이벤트는 main looper에서 직렬 처리한다. 기존 ViewModel은 Activity lifecycle에서 start/stop을 main으로 호출한다. timeout은 main queue의 제한된 재시도 경계이며, 진행 중인 동기 Binder 호출을 강제로 중단하는 장치가 아니다.

실제 제한 판정은 기존과 같다: `requiresDistractionOptimization=true` 또는 `activeRestrictions != UX_RESTRICTIONS_BASELINE`이면 차단한다. 기어·속도나 마지막 허용값으로 대체하지 않는다. SDK GET/callback/TTL, 차량 제어 범위, 유료 AI·자유 질문 번역 보류는 변경하지 않는다. 새 Mock 차량/UX 값을 앱에 추가하지 않는다.

## API 확인과 수집 근거

로컬 compileSDK35의 `platforms/android-35/optional/android.car.jar`를 `javap`로 확인했다. 사용한 API는 기존 `Car.createCar(Context, ServiceConnection)`·`connect`·`disconnect`, `CarUxRestrictionsManager.registerListener`·`unregisterListener`·`getCurrentCarUxRestrictions`다. 새 hidden API나 reflection을 사용하지 않는다.

Android 14 AOSP 원문도 확인했다.

- [Car.java](https://android.googlesource.com/platform/packages/services/Car/+/refs/tags/android-14.0.0_r1/car-lib/src/android/car/Car.java): ServiceConnection listener는 main thread에서 실행되고, disconnect 뒤 기존 manager는 무효화된다. 연결/해제 소유자를 분리해야 하는 근거다.
- [CarUxRestrictionsManager.java](https://android.googlesource.com/platform/packages/services/Car/+/refs/tags/android-14.0.0_r1/car-lib/src/android/car/drivingstate/CarUxRestrictionsManager.java): 기존 listener가 있으면 먼저 해제해야 하며, 현재 UX GET은 null일 수 있다.

로컬 Firecrawl MCP의 첫 소스 조회는 60초 timeout, 기본 Python 원문 요청도 연결 오류였다. 이후 프로젝트 HTTP 클라이언트의 정상 TLS 검증으로 같은 공식 AOSP `?format=TEXT` 원문을 HTTP 200 수집했다. `output/qa/ux-service-recovery-20261114/Car-android14-02.java`, `CarUxRestrictionsManager-android14-02.java`, `aosp-source-fetch-01.json`, `aosp-source-fetch-02.json`에 성공/실패와 실제 수집시각·SHA를 함께 보존했다. Cloud 도구·유료 API는 사용하지 않았다. AOSP 참조 소스가 Pleos OEM 런타임의 모든 내부 구현과 동일하다고 단정하지 않는다.

공개 compile API에는 UX timestamp getter가 없다. 따라서 같은 attempt에서 GET 전 생성된 callback이 나중에 전달되는 경우까지 timestamp로 정렬한다고 주장하지 않는다. 이번 범위는 attempt/epoch 격리와 새 GET 뒤의 소유권 검증이다.

## 검증

`UxConnectionGateTest`는 synthetic 상태 정책 시험이다. 첫 GET 이전 callback 차단, 실패/종료 후 늦은 known 차단, 이전 disconnect가 새 연결을 무효화하지 않음, stop 뒤 retry 0회, ticket 중복 소비 방지, 정확한 finite backoff·성공 GET 후에도 유한한 예산, 새 foreground epoch에서만 예산 복구를 검증한다. 실제 Car service나 UX 값을 대역으로 앱에 주입하는 시험은 아니다.

검증 결과: JVM **94개 통과**(신규 gate 10개 포함, 실패·오류·건너뜀 0), Pleos Debug APK 빌드 통과(54초). 이후 attempt 번호 진단 로그까지 반영한 최종 증분 APK 빌드도 통과했다(3초). 로그는 `output/qa/ux-service-recovery-20261114/android-validation-02.log`, `android-validation-03.log`, 테스트 합계와 APK SHA는 `build-result-01.json`이다. 초기 sandbox의 Gradle 캐시 lock 접근 실패도 `android-validation-01.log`에 보존했다. 지정 JDK17/SDK35·Vehicle SDK2.3.2·offline·max-workers2, 서버 주소8001로 빌드했으며 실제 서버를 호출하지 않았다.

실제 서비스 강제 종료·AVD 조작·실차 시험은 이 작업에서 수행하지 않았다. 재연결 뒤 실제 UX GET과 기존 제한/해제 흐름의 기기 검증은 root의 통합 APK에서 별도로 확인한다.
