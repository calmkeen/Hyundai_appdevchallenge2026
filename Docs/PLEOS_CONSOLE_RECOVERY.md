# Pleos Console 503 복구와 최신 APK 재시험

2026-11-14. 작업 브랜치 `feature/pleos-console-readiness`, 구현 커밋 `aa7e8e3`. 앱·SDK 어댑터·공식 콘텐츠·기기 테스트의 검증 조건은 변경하지 않았다. 기존 최신 APK `e9ab702d…`를 다시 설치하거나 교체하지 않고 실제 설치 파일의 해시를 대조해 시험했다.

## 확인한 원인과 수정

Console의 HTTP 응답과 차량 DDS 준비는 별개다. 전용 AVD 콜드 부팅 후 첫 heartbeat가 성공했어도 문/속도 `emulator_active`와 DDS, 기어 `bridge_ready`는 처음에는 false였고, heartbeat를 유지한 뒤 true로 전환됐다. 기존 드라이버는 heartbeat POST 직후 준비 확인 없이 PUT을 시도했다. 또한 ADB·HTTP·녹화/프로세스 대기와 같은 동기 루프에서만 heartbeat를 보내 연결 유지에 공백이 생길 수 있었다.

로컬 공식 Console HTML은 초기 POST 뒤 별도의 1초 `setInterval`로 heartbeat를 보내며 종료 시 `closing=1`을 보낸다. 이 흐름을 시험 도구에도 반영했다. `scripts/pleos_console.py`가 독립 heartbeat를 유지하고 다음을 제한 시간 내 모두 확인한다.

- 문: `emulator_active=true`, `dds_ready.door_position=true`.
- 속도/페달: `emulator_active=true`, `dds_ready.speed/accelerator/brake=true`.
- 기어: `bridge_ready=true`.

`--console-ready-timeout` 기본값은 60초다. 준비되지 않으면 fixture 조작과 instrumentation을 시작하지 않는다. heartbeat 성공만으로 준비 완료로 판정하지 않으며 오류·만료를 숨기지 않는다. SDK 수신/UI의 기존 timeout과 assertion은 유지한다. 녹화·ADB 로그 수집이 실패해도 외부 상태 복구를 시도하고, 그 오류는 전체 성공을 거부하는 근거로 남긴다. 최종 Park/0/CLOSED를 확인한 뒤 heartbeat thread와 lease를 종료한다. 진단은 필요한 flag·오류 유형으로 제한한다.

실제 Console 회귀에서도 **비활성 상태의 속도/페달0 PUT은 503**, 독립 heartbeat와 준비 확인 후 같은 요청은 **200**이었다. 주 작업을 6초 멈춘 동안 heartbeat 7회가 수행됐고 모든 준비 flag와 200 응답을 유지했다. 원시 차량값을 대신 생성하거나 DDS를 우회한 수정이 아니다.

공식 설정의 Cold boot 요구를 따랐으며, 이전 시도에 Cold boot가 없었다고 원인을 단정하지 않는다. 임의 서비스 강제 시작·HVAC 전환·권한/무결성 검증 우회·데이터 초기화는 하지 않았다.

- [공식 Cold boot 설정](https://document.pleos.ai/en/docs/connect/guide/getting-started/application-development/configure-pleos-connect-emulator#cold-boot-settings): Quick boot에서는 VHAL을 사용할 수 없다고 안내한다.
- [공식 Console 연결·문제 해결](https://document.pleos.ai/en/docs/connect/guide/getting-started/application-development/use-vehicle-emulator#troubleshooting): 지원 AVD·ADB·8088 포워딩·호스트 포트·브라우저 연결을 확인한다. 구체적인 503 내부 판정은 공개 문서가 아닌 이번 AVD 관측으로 구분한다.

## 최신 APK 전체 흐름 결과

전용 `CarCue_Pleos21`/API34/사용자10, SDK2.3.2/Vehicle Service2.3.22, 실제 LIVE 가이드 서버8001에서 run `official-guide-20261114-sdk-e2e-05`가 **19.188초, OK (1 test)**로 통과했다.

| 검증 대상 | 확인 결과 |
| --- | --- |
| 설치 바이너리 | 앱 `e9ab702dc191294372d9e7a8dce9216394f3b440825cbf892ffea5867a66ee97`, 테스트 `2cc2ef14e0681aa33c196298a28b615c947c237691e5438d11cdac0a64ad5a33`; 실제 base APK를 pull해 입력과 일치 확인 |
| 문/차량 표시 | 실제 Capability·GET CLOSED → callback OPEN → callback CLOSED. 차량 열림 PNG는 달라지고 닫힘 복귀 PNG는 최초와 SHA256이 정확히 일치 |
| 공식 가이드 | OPEN에서 관련 가이드 진입, 정확한 프로필·매뉴얼 세트/판본·두 공식 URL 확인. 닫힘 callback 반영 및 명시 재조회 GET CLOSED |
| 주행 제한 | Drive/속도20의 실제 UX callback `requires=true, flags=80`에서 안내 차단·제한 중 진입 거절. Park 복귀 callback `false/0` 확인 |
| 종료/복구 | 동일 Listener unregister·SDK release, Console Park/속도0/앞좌석 왼쪽 문 CLOSED 복구. cleanup 오류 없음, heartbeat 종료·closing 오류 없음 |
| 표시 증거 | 정상 런처의 실제 디스플레이 캡처에서 CarCue 표시 확인. 실행 직후 전환 화면과 전환 완료 캡처를 구분. 기기 테스트 PNG는 앱 Window 캡처이며 새 소개 영상은 제작하지 않음 |

공식 프로필은 사용자가 선택한 2024 한국시장 범위다. 이 시험은 전용 AVD가 제공하는 **실제 Pleos SDK 값 수신**이며 실차·SDK 차종 자동 인증 시험은 아니다. 외부 Console만 시험 조건을 조작하고 앱은 SDK SET을 호출하지 않는다. 새 Mock 시나리오·실제 AI 호출·안전벨트 센서 연결은 추가하지 않았다.

## 증거와 재현

- `output/qa/pleos-console-recovery/20261114T0818Z/`: `lease-readiness-probe.json`, `real-console-regression.json`, `installed-app.json`, `normal-launch-smoke.json`, `physical-normal-launch-settled.png`, `e2e-driver.txt`.
- `output/qa/pleos-official-guide/official-guide-20261114-sdk-e2e-05/`: `validation-result.json`, `instrumentation.txt`, `sdk-events.txt`, `run-status.json`, `console-readiness.json`, `console-session-final.json`와 가이드/UX/차량 PNG.
- 로컬 HTTP 회귀 7개, 전체 서버/도구 회귀 **140개 통과**. 기존 AnyIO deprecation warning 1개. 모의 HTTP 서버를 사용하는 도구 단위 시험과 위 실제 Console/SDK 기기 시험은 별도다.

```bash
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python scripts/validate_pleos_official_guide.py \
  --apk output/apk/carcue-pleos-official-guide-debug.apk \
  --test-apk output/qa/pleos-official-guide/validated-harness-20261114-01/core-test-from-device-2cc.apk \
  --normal-launch-evidence output/qa/pleos-console-recovery/20261114T0818Z/normal-launch-smoke.json \
  --run-id <new-unique-run-id>
```

이 명령은 이미 설치된 APK의 해시를 확인한다. 다른 빌드의 시험에는 해당 app/test APK를 빌드·설치하고 정상 실행 증거도 다시 확보한다. 이전 run01/02/04 실패와 run03 성공은 이력으로 보존한다. 새 run05 결과로 최신 APK의 전체 재시험 미완료 항목을 해소했다.

시험과 상태 복구 후 전용 AVD는 정상 종료했다. 종료 명령 성공·호스트 emulator 프로세스 종료·ADB 목록 제거를 확인했으며, 데이터와 스냅샷 파일은 유지했다. `output/qa/pleos-console-recovery/20261114T0818Z/vm-cleanup.json`에 남겼다.
