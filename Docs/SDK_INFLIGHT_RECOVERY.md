# 실제 SDK in-flight 시험 복구

작성 기준: 2026-11-15, `feature/sdk-inflight-recovery`.

## 기준선과 잔여 범위

선행 네 기능 브랜치와 `develop`은 통합 작업에서 실제 원격 SHA 일치와 CI 다섯 건 성공을 확인했다. 이는 기존 구현·검증의 기준선이며, 새 복구 브랜치의 실제 in-flight 시험이 완료됐다는 뜻은 아니다.

| 브랜치 | 확인된 기준 SHA |
| --- | --- |
| `feature/question-deferral-cache-boundary` | `d6be7412883672daa7a93cce0869cc8181d7eee5` |
| `feature/multilingual-assistant-boundaries` | `78bd7675ec6bd232679deb918452328fa7469eea` |
| `feature/sdk-session-validation` | `6c5274208d33c3991cbcf9ff5bab63374ce24712` |
| `feature/sdk-intro-refresh` | `5bdc5c1790880b711dc1a182a04d8bb991e17213` |
| `develop` | `736dc95fe300996137043ca5c78437b8516352fc` |

기존 showcase03의 실제 앱·SDK·무료 AI·저장 번역 검증과 소개 영상 결과는 보존한다. 추가로 필요한 것은 **실제 무료 로컬 모델 요청이 진행 중일 때 언어 변경·실제 UX 주행 제한·이용 종료를 각각 실행하는 세 경계**의 통과 증거다. 기존 실패·미완료 기록을 성공으로 바꾸지 않는다. 유료 AI 및 자유 질문 번역의 기본 보류 정책도 유지한다.

## 근거 1: AVD keyguard 서비스 상태

late07은 instrumentation 시작 전 `KEYGUARD_NOT_READY`로 거절됐다. 당시 Android 사용자는 10이었으나 keyguard policy에는 `showing=true`, `currentUser=-10000`이 남았고 물리 캡처는 검은 화면이었다. 모델 호출과 시험 DB 기록은 0개였다. 근거는 `output/qa/multilingual-session-20261115/sdk-session-late-20261115-07/validation.json` 및 `software03-keyguard-probe.json`이다.

Android 14의 `KeyguardServiceDelegate`는 초기화·reset 때 showing/secure를 true, 사용자를 `UserHandle.USER_NULL`로 둔다. 실제 서비스 연결 해제 때도 이 상태로 reset하고 lock screen 표시를 요청한다. 따라서 이 조합을 사용자 PIN 필요나 앱 오류의 증거로 해석할 수 없다. 이전 `output/qa/official-links-20261114/avd-keyguard-diagnostic.json`에는 keyguard binding DEAD와 CarService/OEM 앱 초기화 실패도 있었다. 이것이 최신 부팅의 동일 원인이라는 결론까지 내리지는 않는다. [Android 14 공식 소스](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-14.0.0_r1/services/core/java/com/android/server/policy/keyguard/KeyguardServiceDelegate.java)

host와 software 부팅 모두 ColorBuffer 오류가 있었고, 첫 host 부팅은 해당 오류 이후에도 showcase03을 통과했다. GPU 단독 원인은 확정되지 않았다. 원래 `config.ini`는 host이며 software 시험의 실제 실행 override와 생성된 `hardware-qemu.ini`는 lavapipe/swangle 계열을 사용했다. 설정 파일과 실행 시 선택된 backend를 구분한다.

복구는 동일 system image·동일 userdata를 유지하며 **host + `-feature -Vulkan` 실행 override와 snapshot load/save 금지**를 사용하는 별도 시도로 기록한다. 공식 문서는 Apple Silicon의 Vulkan 호환 문제에 software 렌더링 또는 GLES 앱의 Vulkan 비활성화를 안내하지만, 이 옵션이 Pleos keyguard 초기화 문제를 해결한다는 보장은 없다. `-gpu software` 자동 선택과 명시적 `swiftshader`도 서로 같은 설정으로 취급하지 않는다. [공식 그래픽 옵션](https://developer.android.com/studio/run/emulator-acceleration#command-gpu), [공식 문제 해결](https://developer.android.com/studio/run/emulator-troubleshooting)

`-no-snapshot`은 snapshot load/save를 모두 금지하며 userdata 초기화와 다르다. 완전 종료 후 `.qcow2`·암호화 키를 포함한 AVD 전체를 보존하고, `-wipe-data`, 앱 데이터 삭제, 보안 설정 약화, 시스템 앱 임의 disable·서비스 kill을 사용하지 않는다. software 렌더링의 snapshot은 공식적으로 신뢰성 제한이 있다. headless system user0는 일반 사용자 화면 계정으로 취급하지 않는다. [공식 실행 옵션](https://developer.android.com/studio/run/emulator-commandline#startup-options), [snapshot 제한](https://developer.android.com/studio/run/emulator-snapshots#quickboot-troubleshooting), [Automotive 사용자 모델](https://source.android.com/docs/automotive/users_accounts/multi_user)

## 근거 2: Activity getter의 idle 대기

이 문제는 AVD 복구와 별개의 **테스트 관측 경계**다. 기존 `vm` getter는 접근할 때마다 `ViewModelProvider(rule.activity)`를 호출했다. 로컬에 설치된 Compose test 1.6.6과 AndroidX Test core 1.6.1의 바이트코드를 읽어 Activity provider가 `ActivityScenario.onActivity()`를 사용하고, 이 메서드가 계측 스레드에서는 `Instrumentation.waitForIdleSync()` 후 main-thread 작업을 수행하는 것을 확인했다. 따라서 단순한 `vm.state.value` 관측도 매번 idle 대기를 다시 거칠 수 있었다.

보완은 `prepare()`에서 원래 Activity와 ViewModel을 요청 시작 전에 한 번 확보하고 이후 상태·focus 관측에 그 참조를 사용하는 test-only 변경이다. 초기 관측기는 navigation handler를 main thread에서 실행한 뒤 영어 선택·종료 확인에 실제 UI 버튼을 사용했다. 후속 처리 중 경계 시험은 아래처럼 생산 handler 통합 검증으로 분리했다. SDK·UX·서버·모델 값을 주입하거나 모델 응답을 인위적으로 지연하지 않는다.

이는 반복 getter에 idle barrier가 존재한다는 구현 근거에 대한 수정이다. 과거 모든 지연의 단독 원인이나 세 실제 경계 시험의 성공을 입증한 것은 아니다. Activity 재생성이 발생하면 기존 참조를 새 Activity로 가장하지 않고 시험 실패로 다뤄야 한다. 실제 테스트 APK 해시와 후속 실행 결과는 아래에 별도로 기록한다.

## 복구 후 run01~03 기록

이 절의 run01~03은 앞 절의 기존 `sdk-session-late-*` 시도와 다르다. 새 증거 루트는 `output/qa/sdk-inflight-recovery-20261115/`이며, 세 실행 모두 전체 결과는 **FAIL**이다. 실제 설치 앱 SHA256은 계속 `5ef560ba1a24e3ce206aeeb6f4f336018b6e8a182bec7214aabc5dd4a261479f`이고, 이후 보완은 테스트 APK·호스트 관측기에만 적용했다.

| 실행 | 관측된 경계와 실패 구분 | 종료 시 DB sessions/results/history |
| --- | --- | --- |
| `sdk-inflight-20261115-01` | 언어 변경은 실제 처리 중임을 증명했다. Drive의 실제 UX callback은 02:45:31.174Z로 모델 HTTP 완료 02:45:28Z보다 늦었다. 완료 후 결과를 in-flight 억제로 간주하지 않고 native assertion 실패로 거절했다. End는 미실행. | `0/0/0` |
| `sdk-inflight-20261115-02` | 실제 Drive UX callback은 02:51:55.737Z였고 VM은 취소 후 빈 상태였으나, semantic assertion 뒤 기록한 boundary가 02:51:57.376Z로 늦었다. 호스트는 `INFLIGHT_NOT_EXERCISED`로 중단했다. 관측 시점 문제와 제품의 늦은 응답 재표시를 같은 실패로 단정하지 않는다. End는 미실행. | 중단 직후 `1/2/2`; 별도 정상 앱 삭제 복구 후 `0/0/0` |
| `sdk-inflight-20261115-03` | 언어 변경과 Drive의 보수적 타이밍 증명 및 실제 서버 완료 뒤 2초 결과 억제 검사는 통과했다. 이어지는 Drive 물리 화면 캡처에서 API34 `UiAutomation.takeScreenshot()` 내부 null hardware buffer의 `asBitmap()` NPE가 발생해 전체 실패했다. `checked-drive` 기록 전 중단됐고 End는 미실행. | `0/0/0` |

각 원본은 위 루트의 해당 run 디렉터리 `validation.json`과 `instrumentation.txt`다. run01의 순서 판정은 `run01-timing-review.json`, run02의 실제 callback/marker 비교는 `late02-scoped-timing.json`을 참조한다. run03은 `late_boundaries`의 locale/drive 타이밍 증명과 `instrumentation.txt`의 `image()` 예외 위치를 함께 읽어 부분 통과 범위를 판단한다.

run02의 남은 DB를 수동 SQL 삭제나 성공 결과로 숨기지 않았다. `normalAppDeletionRecovery`의 실제 정상 앱 삭제 복구 후 0건을 확인했으며 근거는 `after-run02-normal-app-deletion-recovery.json`이다. 각 실행은 Park/0/CLOSED로 복구했다. 세 실패 실행의 `SCOPED_SDK_LOGS` cleanup 오류도 원본대로 유지하며, 완결된 SDK lifecycle 검증을 통과했다고 보고하지 않는다.

## run04~08과 AVD 복구 후보

아래 다섯 실행도 **전체 FAIL**이다. 증거 경로는 같은 루트의 `sdk-inflight-20261115-04`~`08` 디렉터리다. 이전 실행의 부분 증명을 합쳐 세 경계가 모두 통과했다고 집계하지 않는다.

| 실행 | 실패와 검증 범위 | 종료 시 DB sessions/results/history |
| --- | --- | --- |
| run04 | 언어·Drive 타이밍 증명과 완료 후 2초 억제를 다시 확인했다. 같은 APK/PID에서 locale 물리 캡처는 성공했으나 Drive는 5초 기한의 실제 display 재시도 4회 모두 null buffer NPE여서 실패했다. Compose의 실제 앱 root PNG는 보존됐고 End는 미실행이다. | `0/0/0` |
| run05 | 언어 선택 UI 클릭/idle 관측이 실제 모델 처리 20.649초보다 늦어 `INFLIGHT_NOT_EXERCISED`로 거절했다. | 중단 직후 `1/1/1`; 정상 앱 삭제 복구 후 `0/0/0` |
| run06 | 생산 언어 handler의 native boundary는 03:14:42.904Z였으나, 호스트가 heartbeat 14회 실패 뒤 `wait_ready`에 머무는 동안 모델이 완료돼 엄격한 관측 판정을 충족하지 못했다. 모델 duration은 27.224초이며 전체 성공으로 세지 않는다. | 중단 직후 `1/1/1`; 정상 앱 삭제 복구 후 `0/0/0` |
| run07 | 명시적 SwiftShader 후보에서 `ACTUAL_PENDING_SDK_CONTEXT_REQUIRED`로 거절했다. 실제 pending SDK/UX 전제의 불일치를 우회하지 않았다. 앱 종료 timeout 및 SDK 로그 cleanup 오류도 남겼다. | `1/1/1`; 이후 host03의 정상 앱 복구에서 `0/0/0` 확인 |
| run08 | host03에서 ADB 관측이 시간 초과되고 에뮬레이터 프로세스가 watchdog 경로의 exit139로 종료됐다. 모델 호출 0회·DB0이지만 fixture 복구와 lease 종료도 실패했으므로 전체 실패다. | `0/0/0` |

run05/06 삭제 복구는 `after-run05-normal-app-deletion-recovery.json`, `after-run06-normal-app-deletion-recovery.json`에 각각 기록했다. run07 후의 DB0과 keyguard 준비 회복은 `host03-readiness-and-app-recovery.json`에, 실제 정상 앱 시작 확인은 별도 `host03-normal-app-start-confirmation.json`에 기록했다. run08의 `RESTORE_FIXTURES`·`CLOSE_LEASE` 및 다른 cleanup 오류는 원본 `validation.json`에서 실패로 유지한다.

AVD 원본을 초기화하지 않았다. 에뮬레이터 정상 exit0 후 22개 파일을 APFS clone으로 보존했고, userdata QCOW2·암호화 키/오버레이·config의 SHA 일치를 확인했다. 근거는 `avd-preserved-before-swiftshader.json`이다. 동일 userdata의 명시적 SwiftShader + Vulkan 비활성화 후보는 boot 완료만으로 준비됐다고 간주하지 않았다. `swiftshader-boot-readiness-02.json`과 `swiftshader-keyguard-service-probe.json`에는 user10·Awake·CarService 존재와 별개로 keyguard의 `currentUser=-10000`이 남았으며, run07은 실제 SDK 문맥 검사에서 실패했다. 이후 host03에서 기존 keyguard 준비 기준을 다시 만족했다.

host03/run08은 단순 앱 Java crash와 다르다. 직전 H264 `no frame`·ColorBuffer 오류에 이어 QEMU main/CPU 스레드의 약 15초 무응답을 watchdog이 감지했고 `CrashReporter::GenerateDumpAndDie` 경로로 종료됐다. 개인 정보가 없는 fault 요약은 `emulator139-sanitized-crash.json`, 추가 대기 프레임의 **symbol/image 이름만**은 `emulator139-audio-wait-frames.json`에 보존했다.

추가 스택에서는 guest CPU가 `virtio_snd_stream_prepare0_locked`에서 CoreAudio의 `AudioDeviceStart`/`StartAndWaitForState`를 기다리고, CoreAudio 출력 callback도 mutex를 기다렸다. QEMU main loop·다른 CPU·ADB vsock·WiFi 스레드는 `qemu_mutex_lock_iothread`에서 대기했다. 이는 오디오 시작/콜백 교착의 후보 근거이며, lock 소유자나 최초 원인까지 확정한 것은 아니다. H264 로그만으로 영상 디코더를 원인으로 단정하지 않는다.

현재 runtime04 후보는 같은 AVD·이미지·userdata와 host + `-feature -Vulkan`에 **`-no-audio`만 추가**한다. 설치 에뮬레이터 help와 공식 문서에서 지원을 확인한 실행 옵션이며, 시스템 앱 disable·보안 설정 변경이 아니다. 영상 `HardwareDecoder`는 이번 후보에서 끄지 않았다. `noaudio04-readiness-and-app-start.json`은 기존 keyguard 기준·정상 앱 시작·DB0을 확인하지만 세 in-flight 경계 통과 증거는 아직 아니다. 최종 후속 시험 결과는 아래에 통합 담당자가 기록한다. [공식 오디오 실행 옵션](https://developer.android.com/studio/run/emulator-commandline#startup-options)

run08 기준 실제 설치 앱은 앞서 명시한 `5ef560…` 그대로이며, handler 시험 APK는 `2540d3f37c9d23fee6eb8d8357f4e8307fcc9dcb55f3debd85d2579ee6fa4ca6`, 호스트 스크립트는 `480c7d2395cdc5f9e6d9caeab2367daa5cd58f1e5d4d7b698cd9de2791b05afb`이다. `run08-artifact-runtime-pins.json`에 원문 해시와 runtime override를 기록했으며 생산 앱 코드는 바꾸지 않았다.

## run09와 후속 실행 준비

runtime04의 `-no-audio`에서 run09는 언어 경계의 실제 처리 중 타이밍·완료 후 억제·실제 화면 캡처까지 확인했다. 하지만 ASK에서 SDK 값이 60초를 넘긴 뒤, 시험 helper가 새 GET 전에 기존 값의 신선도를 요구해 60초 대기 후 실패했다. 실제 SDK는 STALE/value null을 정상 표시했고 이 상태를 VALUE로 가장하지 않았다. `instrumentation.txt`의 `refresh → reading` timeout과 `late09-progress-probe-02.json`의 수신 시각·STALE을 함께 보존한다. 전체 run09는 FAIL이며 DB는 `0/0/0`이다.

이후 `refresh()`는 **실제 GET → GET 횟수/수신 시각 변경 → 기존 PLEOS/SUPPORTED/VALUE/CLOSED·60초 신선도·UX 검사**로 순서를 고쳤다. 장시간 답변 뒤·Park 복귀도 같은 순서이며 초기 세션과 새 이용자의 최초 수신 검사는 유지한다. late 송신은 입력·동의 준비 뒤 새 GET을 수행하고 동의가 유지되는지도 검사한다. 신선도 제한이나 실제 SDK 출처 조건을 줄이지 않았다. 새 시험 APK는 `43c4bc146e0e0cc09584a4d40b74120fa116a3e5b9ca244e8020375aebfdb8ec`이고 기능 APK는 계속 같다.

runtime04는 시험 정리 뒤 별도의 host SIGSEGV/exit139도 보였다. 새 fault는 `gfxstream → cleanupProcGLObjects → eglDestroyContext → EglContext` 소멸 경로였으며 앞선 CoreAudio watchdog과 같은 충돌로 단정하지 않는다. 정제된 근거는 `emulator-noaudio139-gl-cleanup-frames.json`이다. `-no-audio`가 무시됐다는 증거도 아니다.

후속 후보는 원본 설정/데이터를 유지한 `SwiftShader + -no-audio + -skin 1280x720 + -cores 4` 실행 override다. framebuffer/CPU 지원 형식은 설치된 emulator help로 확인했다. 이전 충돌 보고 동의 창이 부팅을 막아, 게스트 미연결 상태의 소유 프로세스에 SIGTERM을 요청한 뒤 응답하지 않아 종료했다. 해당 사전 부팅 종료와 중복 실행 거절도 QA에 보존한다. 이후 공식 `-crash-report-mode never -no-metrics`로 외부 전송 없이 시작하며 로컬 충돌 증거·SDK/UX 검사·hang 검출을 감추지 않는다. 이 준비 작업을 실제 세 경계 통과로 집계하지 않는다.

## run10~11과 화면 동기화 보완

run10은 위 1280×720/4-core 후보에서 부팅·user10·CarService·keyguard 및 설치 APK 해시를 확인한 뒤 시작했다. 이후 CarService가 사라져 `REGISTERED_CAR_SERVICE_REQUIRED` 전제 검사에서 거절됐으며 실제 생성 호출 0회·DB `0/0/0`이다. 직전 모델 load-only는 빈 응답의 모델 적재이며 생성 성공으로 세지 않는다. 플랫폼 exit-info에는 CarService의 Java crash와 SystemUI ANR이 있었다. CarService의 정제된 예외는 `CarServiceHelperWrapper.waitForCarServiceHelper → sendInitialUser → CarUserService` 초기 사용자 경로의 `IllegalStateException`이다. 모델 적재와의 시간적 근접만으로 메모리 부족이나 인과를 확정하지 않는다. 근거는 `runtime-preflight-20261115-01/platform-exit-summary-before-reboot.json`, `car-7945-filtered-cause.json`이다.

같은 AVD를 정상 `adb reboot`하고 모델을 적재하지 않은 상태에서 실제 CarService/keyguard 준비를 두 번 확인한 뒤 run11을 실행했다. 실제 언어 handler의 처리 중 타이밍은 통과했다(provider 25,958ms, pending 하한→완료 관측 약 18,964.85ms). 이후 VM의 답변·번역은 비어 있었지만 `assistant_answer` 노드 부재 검사에서 Compose idle 대기가 끝나지 않아 native 224.065초에 실패했다. Drive·End는 진입하지 않았고 전체 FAIL, DB `0/0/0`, Park/0/CLOSED·lease 복구를 기록했다. SDK lifecycle의 미완료 callback 검사도 통과로 바꾸지 않는다. `sdk-inflight-20261115-11/` 원본과 `runtime-preflight-20261115-01/run11-runtime-summary.json`이 근거다.

후속 계측은 실제 boundary marker **뒤에만** 공개 Compose test `mainClock`을 수동 진행한다. 실제 벽시계에 맞춰 프레임을 계속 진행하고, 기존 상태 및 실제 UI 노드 부재 검사·모델 완료 대기·완료 후 2초 반복 검사·실제 화면 캡처를 유지한다. SDK·HTTP·모델·SystemClock 시간은 바꾸지 않는다. 각 케이스의 완료 및 checked marker 뒤에만 ASK를 벗어나 TextField를 unmount하고 원래 clock 설정을 복원한다. 실패 정리에서도 생산 종료 handler와 프레임 반영 뒤 clock을 복원한다. 이는 테스트 렌더 동기화 보완이며 앱 안정성 문제의 단독 원인을 확정한 결론이나 세 경계 통과 증거가 아니다.

run12는 이 보완의 테스트 APK `4ae3ce5b1fbb36656b42301f4e80d1f198d834eb0c5ed2193ee31bd36da00feb`로 실행했다. 언어 경계의 실제 provider 21,409ms·pending 하한→완료 관측 약 20,782.34ms 및 모델 완료 후 2초의 VM/실제 semantic 노드 부재 검사는 통과했다. 이어 `image()`의 원래 Activity window focus 15초 대기에서 시간 초과해 native 136.880초에 전체 FAIL했다. 실패 캡처에서는 약 6초 뒤 같은 PID의 실제 화면을 얻었지만 이를 원래 경계의 캡처 성공으로 대체하지 않았다. Drive·End 미실행, DB `0/0/0`·Park/0/CLOSED·lease 복구이며 원본은 `sdk-inflight-20261115-12/`에 보존한다.

후속 focus 대기는 late/manual 모드에서만 45초 실제 deadline의 polling 안에서도 프레임을 진행한다. 같은 원래 Activity의 실제 focus·생존을 요구하고, 캡처 뒤 빈 결과/실제 노드 부재를 다시 검사한다. 호스트도 네 캡처의 focus·Activity·수동 clock·진행 프레임을 확인한다. focus를 직접 설정하거나 Activity를 재실행하지 않는다. 45초는 polling 기한이며 개별 플랫폼 호출까지의 절대 상한은 아니다. host의 최종 600초 거절 기준을 유지한다. 일반 autoAdvance/showcase의 기존 15초 대기는 바꾸지 않았다.

run12 뒤에는 ADB shell 지연과 실제 CarService 미등록도 관측했다. `adb reboot`의 ACK가 시간 초과됐고 이후 uptime도 유지돼 즉시 재부팅 완료로 보고하지 않았다. 따라서 run12의 초점 실패를 테스트 프레임 정지 하나의 원인으로 확정하지 않는다. 소유 emulator의 정상 종료 ACK·launcher exit0·ADB 장치 부재 후 동일 데이터를 보존한 headless(`-no-window`) 실행을 후속 후보로 분리했다. 새 이미지·runtime 다운로드나 데이터 초기화 없이 실제 가상 display의 UI/물리 캡처·SDK/UX 준비 조건을 그대로 요구한다.

## run13과 별도 Stable runtime 비교

37.2.13 headless 부팅은 CarService/SystemUI 네 PID가 61초간 유지됐고, keyguard false/user10·`CarUserService`의 User0Unlocked/initial user10 및 Console DDS 준비를 확인했다. 그러나 run13은 최초 문 상태의 실제 GET을 받지 못해 `reading()`의 60초 기한에서 native 96.033초 FAIL했다. 모델 호출0, DB `0/0/0`·Park/0/CLOSED·lease 복구이며 새 clock 경계 구간에 진입하지 않았다. 같은 원래 Activity의 진단용 실제 캡처는 성공했지만 이를 기능 성공으로 대체하지 않는다. 원본은 `sdk-inflight-20261115-13/`, 최소 서비스 진단은 `build-focus-frames-13/run13-minimal-sdk-service-diagnosis.json`이다.

초기 성공 로그 whitelist에는 `READ_TIMEOUT`이 없어 메인 Handler 정지처럼 보일 수 있었다. 별도 PID11881의 시각 로그에는 실제 12초 타이머 및 후속 READ_TIMEOUT 3회가 있었다. SDK2.3.2 jar의 GET은 one-way Binder 요청(code4/flags1/reply null) 뒤 callback을 받는 구조다. 두 근거는 60초 메인 스레드 차단 가설을 지지하지 않으며, 생산 SDK 코드를 추측으로 변경하지 않았다. 후속 관측기는 명시적 안전 실패 코드도 `sdk_failure_events`에 보존한다. 임의 로그 본문·질문을 추가 기록하지 않는다.

비교 runtime은 [Google 공식 아카이브](https://developer.android.com/studio/emulator_archive)의 **37.2.12 Stable/build16428233/mac ARM64**다. ZIP은 416,112,708bytes, 공식 SHA256 `f4c4a142bda54fcec064bdb32b51f19e25bae0a45ad019197ef968bf7a48979b`와 일치하고 전체 CRC를 확인했다. `.tooling/emulator-runtimes/37.2.12/emulator/`에 404개 파일의 전체 패키지를 분리 추출했으며 기존 SDK를 덮어쓰거나 서로 다른 버전의 라이브러리를 혼합하지 않았다. 근거는 `emulator-37.2.12-archive-verified.json`, `emulator-37.2.12-runtime-prepared.json`이다.

샌드박스 안의 버전 probe는 Qt의 NEON 기능 검사에서 SIGABRT였으나, 실제 Mac 환경의 읽기 전용 `-version`은 exit0/37.2.12/build16428233을 확인했다. 하드웨어 미지원이나 AVD crash로 단정하지 않으며 서명 재작성·보안 설정 변경도 하지 않았다. 기존 headless runtime의 정상 exit0·ADB 장치 부재 후 **binary/full package 버전만** 바꿔 같은 이미지·userdata·headless/SwiftShader/noaudio/1280×720/4cores·snapshot 금지 조건으로 비교한다. 이는 호환·문제 해결이 이미 검증됐다는 뜻이 아니다.

37.2.12의 첫 준비는 13:50:24 KST에 통과했지만, 후속 재확인에서는 ADB/CarService가 응답하지 않고 Console active도 false였다. 이 사이 host 벽시계와 worker monotonic의 경과 차이가 나타났다. `pmset`의 최소 이벤트 확인 결과 **13:50:26에 Clamshell Sleep**, 이후 DarkWake/Maintenance Sleep 반복과 14:06:10 Wake가 있었다. 현재 덮개 열림(`AppleClamshellState=No`)과 기존 caffeinate의 idle display/system sleep 억제는 별도로 확인했다. 이 잠자기 교란 뒤의 재확인을 버전 호환 불가 증거로 쓰지 않고, 동일 runtime을 정상 종료/재시작한 뒤 다시 검사한다. OS 수면·잠금·보안 설정은 바꾸지 않았다. 근거는 `host-sleep-wake-events.json`, `host-current-lid-state.json`, `host-sleep-assertions.json`이다. 수집은 관련 시각/허용된 원인 태그/자체 assertion만 보존하며 전체 사용자 로그를 저장하지 않는다.

## 처리 중 handler 검증과 일반 UI 검증의 구분

처리 중 세 케이스는 **실제 SDK·실제 무료 provider와 생산 handler의 통합 검증**이다. 언어는 main thread에서 `language()`를 실행한 뒤 현재 action scope로 `chooseLanguage("en", scope)`를 호출한다. 종료는 Settings 화면 이동이 먼저 요청을 취소하지 않도록 pending 상태에서 `endSession()` 자체를 호출해 epoch 증가와 실제 DELETE 경계를 검사한다. Drive는 실제 플랫폼 UX callback을 그대로 사용한다. 상태를 직접 쓰거나 handler의 세션·scope·UX 검사를 생략하지 않는다.

호스트는 세 명시적 route와 pending의 실제 PLEOS/CLOSED·UX 허용·60초 신선도를 확인하고, 종료에서는 epoch 증가·PROFILE·profile/value null을 추가 검사한다. handler 뒤 실제 렌더링·UI 숨김·완료 후 2초 결과 억제·새 이용자·DB 삭제·SDK/fixture 정리를 그대로 검사한다. 마지막 정상 종료의 UI 버튼 경로도 유지한다. handler가 거절되거나 경계가 늦으면 전체 실패이며 모델 지연·가짜 차량 값·자동 재호출로 기회를 만들지 않는다.

정상 언어 선택·종료 확인 버튼은 같은 앱의 showcase03 성공 증거에 연결한다. 이전 실제 클릭의 locale 부분 증명과 Drive 부분 증명도 보존한다. 그러나 새 handler 시험 결과를 **busy 중 전체 물리 gesture/Compose 클릭 경로를 검증한 결과로 보고하지 않는다.**

## 후속 관측기 보완

1. **실제 경계 직후 marker:** Drive는 실제 StateFlow의 UX known·restricted 및 생산 callback이 만든 `busy=false`를 직접 polling한 직후 marker를 기록한다. 반복 Activity getter·Compose idle/semantic 대기를 이 관측 앞에 넣지 않는다. 언어 변경·종료도 실제 상태 변경 직후 marker를 남기고, 화면 숨김과 늦은 결과 부재 등 기존 UI assertion은 유지한다. warmup의 실제 Drive↔Park 왕복도 대역 없이 확인한다.
2. **독립 audit 관측:** ADB 작업이 끝난 main-loop 시각 대신 별도 thread가 실제 audit 파일을 약 20ms 간격으로 읽어 요청별 최초 관측 시각을 보존한다. 이 값은 실제 완료 시각의 상한이며, 20ms는 스케줄링 지연의 최대치를 보장하지 않는다. `U=최초 audit 관측`, `L=pending 관측 하한`, `D=provider duration_ms`일 때 `(U-L)*1000 < D-1`을 요구한다. 1ms는 duration의 반올림 오차에 대한 보수적 여유다. 경계 전 audit 부재와 `U >= 호스트 boundary 관측 시각`도 그대로 요구한다. observer의 읽기 오류·종료 실패는 전체 통과를 막는다. 모델 호출이나 실제 응답 시점을 변경하지 않는다.
3. **실제 물리 화면 캡처의 범위:** run04까지 API34의 null buffer NPE/null 캡처에 5초 재시도 기한을 적용했으나 실제 Drive display를 얻지 못해 전체 실패했다. 이후 Drive만 실제 Compose root PNG와 `physical_unavailable` 메타데이터를 보존하고, 실제 Park 복귀·UX 허용·SDK 신선도를 재확인한 뒤 별도 이름/시각의 물리 캡처를 저장하도록 분리했다. 이것은 Drive physical의 대체 이미지가 아니다. 원래 window focus·Compose·기존 UI/SDK assertion의 실패는 계속 실패다. 다른 경계의 실제 물리 캡처 요구도 유지한다. NPE를 의도된 보안 차단으로 해석하지 않으며 Compose bitmap·이전 PNG·생성 이미지를 physical 파일로 만들지 않는다.
4. **Console 관측과 외부 쓰기의 분리:** while 상단은 heartbeat 오류 때 독립 worker가 살아 있는지 확인하고 recovery count를 기록하며, 관측 전에 30초 readiness 대기로 막지 않는다. 이때 worker alive를 Console 준비 완료로 해석하지 않는다. INITIAL/RESTORED와 모든 fixture 쓰기 직전 `wait_ready`, 실제 요청 전후 heartbeat 검사와 최종 복구·close는 유지한다. 별도 audit 관측과 SDK/UX 타이밍 증명도 그대로다. 실패 횟수를 숨기거나 전 구간 heartbeat가 무중단이었다고 보고하지 않는다.

## 유지하는 통과 기준

- API34·지정 AVD·user10·부팅·Awake·실제 keyguard 준비·동일 설치 APK 해시를 확인한다. CarService/실제 UX known·허용 상태와 신선한 `Source.PLEOS` SDK 값을 확인한 후 시작한다.
- 독립 Console heartbeat를 유지한다. 시뮬레이터 입력은 호스트 Console fixture이며 앱은 실제 SDK GET/callback만 사용한다. 실제 주행 제한·해제 조건을 완화하지 않는다.
- 세 요청 각각 실제 UUID·busy 상태·완료 전 audit 부재를 관측하고, 실제 UI/UX/종료 경계 후에도 audit가 아직 없어야 한다. 완료 audit와 실제 provider 처리시간을 보수적으로 대조해 시작·경계·완료의 순서를 증명한다. 타이밍을 충족하지 못하면 `INFLIGHT_NOT_EXERCISED`로 거절한다.
- 실제 무료 `OLLAMA_LOCAL`/`qwen3:4b` audit 세 개의 요청 hash·model·HTTP200·structured 검증·양수 token/duration·응답 digest를 일대일로 확인한다. 취소 후 모델 완료까지 기다리고 추가 관측 동안 답변·번역·출처·action이 다시 표시되지 않는지 확인한다.
- 종료 후 새 이용자에게 이전 결과가 없어야 한다. 세션 DB 삭제, SDK listener 해제/release, Park/0/CLOSED 복구와 lease 종료를 확인한다. 실패·cleanup 오류·추가 요청을 숨기지 않으며 일부 통과를 전체 통과로 집계하지 않는다.

## 최종 실행 명령

최종 통과 실행의 run ID·정확한 명령·설치 APK/test APK 해시·증거 경로는 아래 결과와 함께 기록한다. 각 실패 실행의 실제 명령·설치 해시는 해당 `command.json`/`validation.json` 및 runtime pin 파일에 보존한다. 독립 검토자는 소스만 읽었으며 실제 빌드·런타임·모델 호출은 통합 실행 기록과 구분한다.

## 최종 결과

**미완료 — run01~13은 전체 FAIL이며 세 실제 in-flight handler 경계의 전체 통과 증거 대기.** 언어·Drive의 부분 증명과 진단용 캡처를 합쳐 최종 성공으로 취급하지 않는다. 별도 공식 37.2.12 runtime의 실제 SDK 회신·준비 및 후속 시험 결과를 확인한 뒤 갱신한다. 기존 실패·복구·삭제 원본은 보존한다. 작업 브랜치의 checkpoint `02947ed` 원격/CI success와 현재 후속 소스의 실제 기기 검증 상태도 구분한다.
