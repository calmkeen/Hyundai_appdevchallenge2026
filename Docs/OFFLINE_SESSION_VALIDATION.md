# 첫 실행 저장 안내와 오프라인 세션 검증

2026-11-14 최종 검증 기록. 문서 11의 ‘첫 실행·연결 실패에도 프로필과 검수된 기본 안내 제공’, ‘AI 실패 시 저장 가이드 연결’을 구현했다. **QA3/run04 전체 통과: 첫 계측 57.131초, 새 프로세스 계측 6.889초, 13+3단계·PNG 16개·실제 로컬 AI 1회**다. 16개 화면의 독립 AI 보조 검토도 해당 기록 범위에서 통과했다. run01·실패 run02/03·별도 진단의 원판정은 보존한다.

## 구현 범위

프로필과 한국어·영어·일본어 검수 안내는 기존 `content`를 APK assets로 동봉한다. 새 안내·차량값·번역을 만들지 않는다. 번들·캐시·API 모두 기존 `GuidePublicationPolicy`를 사용해 등록된 VERIFIED 프로필, 정확한 매뉴얼 세트/판본·언어, PUBLISHED 상태, 검수 번역, 출처·단계를 재검증한다.

| 안내 출처 | 의미 |
|---|---|
| `BUNDLED` | 새 설치에서 허용된 APK 동봉 검수 안내 |
| `CACHE` | 동일 프로필·연식·시장·매뉴얼 세트/판본·언어의 파일 snapshot을 재검증한 안내 |
| `SERVER` | 실제 CarCue HTTP 응답에서 수신하고 게시 조건을 통과한 안내 |
| `NONE` | 표시할 검수 안내 없음 |

이 출처는 차량 데이터의 `PLEOS`/`MOCK`와 별개다. 번들 안내를 표시한다고 SDK 차량 상태가 Mock이 되지 않으며, 서버에서 가이드를 받았다고 실제 자동차종이 인증되는 것도 아니다. 실제 SDK 값과 규제 상태를 확인하지 못하면 기존 보수적 UX 제한을 유지한다.

`ContentRepository.cachedGuides()`는 로컬 snapshot을 먼저 읽고, 허용된 미조회 scope에만 번들을 적용한다. `CarCueViewModel`은 로컬 안내를 먼저 표시한 뒤 비동기 서버 갱신을 수행한다. `refreshGuides()`와 화면의 새로고침을 제공하며 인터넷·서버·SDK 연결 상태는 분리한다. 인터넷 검증 상태만으로 로컬 백엔드 사용을 차단하지 않는다.

AI 연결 실패·일시 불가에는 가짜 답변을 만들지 않고 ‘저장된 안내 보기’를 제공한다. 기존 검수 가이드를 다시 사용하며 AI 답변이나 검수 번역으로 위장하지 않는다. 같은 scope의 서버 철회는 열린 안내에도 적용하고, 다른 UI 언어의 빈 결과를 기존 원문의 철회로 오해하지 않는다. 역순 응답은 기존 요청 gate로 차단한다.

## 첫 설치와 기존 설치 이행

이전 캐시 v1은 서버의 빈 성공 응답을 파일 삭제로 표현했다. 따라서 기존 설치의 ‘파일 없음’만으로 미조회와 철회를 구분할 수 없다. 새 `BundledGuideBootstrap`은 다음처럼 처리한다.

- 저장된 bootstrap 결정이 있으면 이후 재시작·업데이트에도 유지한다.
- 결정이 없는 **새 설치**에서만 `firstInstallTime > 0 && firstInstallTime == lastUpdateTime`를 확인하고 번들 허용 결정을 영속화한다.
- 미표식 업그레이드·알 수 없는 설치 시각·손상된 표식·저장 실패는 보수적으로 번들을 허용하지 않는다. 기존 유효 캐시는 계속 읽을 수 있다.
- 알려진 snapshot이 있으면 그 결과가 번들보다 우선한다. 서버 빈 성공도 `[]`를 원자적으로 저장해 정상 파일시스템에서는 재시작 후 번들이 되살아나지 않는다. 손상·접근 불가·현재 프로세스에서 무효화된 snapshot도 번들로 대체하지 않는다.

디스크가 쓰기를 거부하면 현재 프로세스는 이전 캐시를 차단하지만, 영속화하지 못한 무효화까지 다음 프로세스가 기억한다고 보증하지 않는다. 첫 설치 시각은 오프라인 초기 자료 제공을 결정하는 앱 설치 메타데이터이며 차량 인증 수단이 아니다.

## 빌드·단위 검증

`output/qa/offline-guides-20261114/qa-build-manifest.json`을 읽어 다음 입력을 확인했다. Android JVM 단위 테스트 **84개, 실패/오류/건너뜀 0개**, QA 앱·테스트 APK 빌드 완료다. 이는 실제 SDK 계측 통과를 뜻하지 않는다.

| 빌드 입력 | SHA-256 |
|---|---|
| `output/apk/carcue-pleos-offline-qa-debug.apk` | `f1b276e774dccd7053ff47961230f421db0d253ff202f144469f12166f22fea1` |
| `output/qa/offline-guides-20261114/offline-qa-test.apk` | `8b1634da96ffd861276466639805b8ff31405ff205a3ef4f3967ff187492234f` |

run02·03의 QA2 입력은 `qa2-build-manifest.json`에서 별도로 확인했다. 단위 테스트 84개의 실패/오류/건너뜀은 모두 0이며, run02→03 사이 앱·테스트 APK 코드는 바꾸지 않았다.

| run02·03 QA2 빌드 입력 | SHA-256 |
|---|---|
| `output/apk/carcue-pleos-offline-qa2-debug.apk` | `b649a65fb0896b3157b8791a6961495fe7093890a471f8e5824fbf981de4a48c` |
| `output/qa/offline-guides-20261114/offline-qa2-test.apk` | `9e059119a9719da814814d64dbc3579bada49262e51c1a74ba39a4fc995df635` |

최종 전체 재검증의 새 QA3 입력은 `qa3-build-manifest.json`에서 확인했다. 제품 코드는 QA2와 같고 native의 실제 SDK·UX 준비 확인만 보강했으며 앱 ID를 `com.carcue.app.offlineqa3`로 분리했다.

| run04 QA3 빌드 입력 | SHA-256 |
|---|---|
| `output/apk/carcue-pleos-offline-qa3-debug.apk` | `3ebc39e8cfc9ca44fcfa3720a591a7f1c173af31f9275a4445e0f5c6f36843ff` |
| `output/qa/offline-guides-20261114/offline-qa3-test.apk` | `ce678e98b42c4140234a6eb1f9c3fb00d91687c8c384b9af3176af88ad34fce2` |

QA1·QA2·QA3는 `carcueApplicationId`를 별도로 지정한 동일 제품 소스·실제 Pleos SDK 경로다. 기존 `com.carcue.app`과 앞선 QA 패키지의 데이터·캐시를 지우지 않는다. 최초 설치 시각 두 개와 앱 ID·초기 캐시 비어 있음만 `installation.json`에 남긴다. QA2는 run02에서 처음 설치했고 run03에서 동일 해시·설치 시각·파일을 재사용했다. QA3/run04는 새 설치이며 `firstInstallTime=lastUpdateTime=1794658179377`, `cacheInitiallyEmpty:true`를 확인했다. 설치 후 pull한 앱·테스트 해시도 위 QA3 입력과 일치한다. 재설치·`pm clear`로 상태를 맞추지 않았다.

## 최종 실제 결과와 보존 이력

최종 근거는 `output/qa/offline-guides-20261114/offline-session-20261114-04/validation.json`이다. 기능·전체 host 판정이 모두 true, `cleanup_errors=[]`다. 정상 콘텐츠 동기화와 실제 SDK OPEN/CLOSED, 오프라인 AI 실패 후 저장 안내, 새 이용자 CACHE를 확인한 뒤 앱 데이터 삭제 없이 프로세스를 재시작했다. 같은 SQLite DB의 sessions/results/history가 각각 1에서 0이 됐고 Console fixture는 문 닫힘/Park/속도 0으로 복구됐다. host의 백엔드가 종료되고 heartbeat lease도 닫혔다.

실제 모델 이벤트는 Ollama 0.40.16 / `qwen3:4b`의 `LocalPassageSelection` 1건이며 `LIVE_LOCAL_ASK_KO` 요청 해시와 일치한다. 오프라인 실패에 가짜 답변·출처를 만들지 않았고, 안내 본문을 매번 모델로 생성하거나 번역하지 않았다. 모델 digest는 `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`다.

같은 폴더의 새 `visual-review.json`은 원 metadata에 적힌 artifact 28개 해시를 모두 대조하고 PNG 16개를 직접 확인했다. 3언어 번들·서버 안내와 EN 캐시의 검수 본문/끼임 금지문·두 공식 URL·판본·KR 프로필이 유지됐으며 출처 문구도 BUNDLED/SERVER/CACHE에 맞았다. SDK 열림→닫힘 텍스트, 오류 배너·저장 안내 CTA, 새 이용자와 재시작의 본문 초기화·삭제 대기, 최종 삭제 후 배너/재시도 제거가 메타데이터와 일치했다. 실질적인 의미·표시 문제는 찾지 못했다.

공용 캐시 보존은 세션 종료·새 이용자 전후 파일 해시 동일 assertion과 새 프로세스의 새 ContentRepository에서 EN/CACHE 1건을 읽은 assertion으로 확인했다. `RESTART_CACHE_PRESERVED` 이미지 자체는 프로필 화면이므로 그 사진만으로 파일 보존을 주장하지 않는다. 이미지에는 첫 단계와 전체 요약이 보이며, 전체 단계·주의문·출처의 원문 일치는 별도 native assertion으로 확인했다. 독립 검토는 이 기록의 AI 보조 대조이며 OEM·인간 전문가·원어민 인증이나 일반 제품 품질 보증이 아니다.

기존 `com.carcue.app` 패키지의 최종 앱도 별도 실제 SDK 전체 회귀에서 **20.285초 통과**했다. 근거는 `output/qa/pleos-official-guide/official-guide-offline-session-20261114-01/`의 원 metadata·native 로그다. 앱 SHA-256 `9dea39807f7ecb545784e84da489b81c044fb4a61e92f596cd42fb4870d696ce`, 테스트 `0df63e0c0975ef20ff7b958f628590ee85be4dc68ac7e4603f1d9da3fb2a4432`가 기기 pull 해시와 일치했다. 8단계에서 문 GET/개폐 callback·차량 픽셀 변화/복원·공식 가이드·명시 refresh·실제 Drive UX 차단/Park 복귀·listener 해제/release·fixture 복구를 확인했다. `cleanup_errors=[]`이며 이 회귀의 외부 AI 호출은 0회다. QA3의 오프라인/AI 시험과 패키지·검증 범위를 구분한다.

별도 부트스트랩 보조 `keep-console.py`는 앞선 ADB 8초 timeout 뒤 close HTTP timeout으로 **exit 1**, close 응답 미확인이었다. 이 보조 실패는 보존하며 모든 보조 lease가 graceful close됐다고 주장하지 않는다. run04와 기존 패키지 SDK 회귀의 자체 lease·cleanup 정상 기록은 각각 별도 근거이며 앱 계측 통과 판정도 유지한다.

최종 `output/qa/offline-guides-20261114/environment-cleanup.json`에서 **`adb emu kill`의 OK 응답과 ADB 장치 목록 비움**을 확인했다. 그러나 host emulator launcher는 **exit 137 / SIGKILL**로 반환돼 clean process exit 0이나 전체 정상 프로세스 종료로 확대하지 않는다. 137의 발생 원인은 확정하지 않았다. 기존·QA AVD userdata 디렉터리는 존재하고 wipe·삭제 없이 보존했으며 기본 무료 서버 LIVE와 Ollama 0.40.16의 정상 HTTP 200 상태는 별도로 확인했다.

run01 근거는 `output/qa/offline-guides-20261114/offline-session-20261114-01/`이다. `validation.json`의 기능·전체 host 판정이 모두 true이며 첫 계측 **79.793초**, 새 프로세스 계측 **10.356초**, 13+3단계·PNG 16개·실제 로컬 모델 호출 1회를 확인했다. 앱 데이터 삭제 없이 실제 프로세스를 바꾸고 동일 SQLite DB의 sessions/results/history가 각각 1에서 0이 됐다. `cleanup_errors=[]`와 문 닫힘/Park/속도 0 복구, own backend 종료를 확인했으며 Ollama는 유지한다.

run02(`offline-session-20261114-02`)의 원 `validation.json`은 `passed:false / ConsoleHeartbeatError`, `cleanup_errors=[]`다. 첫 native 로그는 0 bytes, 서버 전환은 0회이고 모델 호출·기능 통과 근거는 없다. 이 실패 판정을 보존한다. host만 기존 deadline 안에서 실제 DDS 준비 flags를 다시 확인하도록 보강했고, 명시적 `--reuse-qa-install`로 동일 QA2 설치를 보존한 run03을 실행했다.

run03(`offline-session-20261114-03`)도 원 판정은 `passed:false / NATIVE_ASSERTIONS_FAILED`, `cleanup_errors=[]`다. 보존된 중간 event는 12개이며 마지막은 `OFFLINE_SESSION_ENDED`다. 다음 캐시 가이드 재진입에서 제목 노드를 찾지 못했다. 실제 UX 연결 해제가 관측됐고 기존 test가 페이지·UX 준비를 기다리지 않던 경계가 확인돼, 같은 45초 내 UX·화면·scope·origin 준비 확인과 실패 직전 상태/화면 보존을 보강했다. ‘단순 recompose’나 ‘캐시 결함’으로 원인을 확정하지 않는다. 앱·SDK·UX 정책이나 기한은 완화하지 않았다.

`cached-reentry-20261114-01/validation.json`의 별도 진단은 **12.625초 통과**다. QA2 앱 해시 `b649a65f…`를 바꾸지 않고 diagnostic 테스트 `a73d71e7ff01f0c4840292780ffd78f164fd408a062bc37663b09091fdb251cf`로 두 번의 실제 SDK CLOSED 수신·UX 허용·EN CACHE 가이드 진입을 확인했다. 진단의 두 단계에서는 삭제 대기를 계속 보존했으며 삭제 완료로 판정하지 않았다. 이 제한된 성공은 run03의 원 실패나 전체 16단계 판정을 바꾸지 않는다.

실패 실행의 별도 정리 근거 `offline-session-20261114-03/failed-run-cleanup.json`은 같은 SQLite DB를 복구하고 정상 launcher foreground 뒤 실제 삭제로 sessions/results/history 0을 확인했다. 앱 데이터는 지우지 않았고 원 실패 리포트도 수정하지 않았다. QA3/run04의 전체 통과는 이 과거 실패 판정을 바꾸지 않는다. 프레임워크 자동 연결 해제의 구체 원인도 확정하지 않았다.

실제 CarCue 백엔드 포트 8001을 닫아 연결 거절을 확인한 뒤 host가 자신의 LIVE 무료 로컬 백엔드만 시작·종료한다. 비행기 모드·전체 인터넷 단절을 검증했다고 확대하지 않는다. 차량 fixture는 전용 Pleos AVD Console에서만 바꾸며 앱 SDK SET·시나리오 주입은 하지 않는다.

| 과정 | run04에서 확인한 근거 |
|---|---|
| 첫 설치 오프라인 | 초기 다운로드 캐시 없음, 설치 시각 일치, 3언어 `BUNDLED`와 정확한 본문·단계·주의문·공식 URL |
| 실제 SDK 연결 | GET CLOSED → OPEN callback과 관련 번들 가이드 → CLOSED callback |
| AI 연결 실패 | 가짜 답변/출처 없음, 저장 가이드 CTA로 동일 검수 안내 열기 |
| 서버 연결 복구 | 3언어 `SERVER`·실제 파일 캐시, 한국어 ASK 실제 로컬 모델 1회 |
| 재오프라인·새 이용자 | 이용 종료 시 본문/언어 초기화·삭제 대기, 공용 캐시 보존, 새 이용자 EN `CACHE` |
| 새 프로세스 | 데이터 삭제 없이 종료/재시작, 삭제 큐·공용 캐시 보존, 같은 SQLite 서버 복구 후 삭제 재시도 |
| 최종 정리 | 서버 sessions/results/history 0, fixture 복구, lease 종료와 own backend 정리 |

최종 run04가 위 13+3단계를 완료했다. 마커와 실제 응답을 맞춰 시험했으며 테스트에서 앱 차량값을 직접 넣지 않았다. run01 성공·QA2/run03 중간 12단계 실패·제한된 재진입 진단·실패 후 정리도 각각 별도 근거로 보존한다. 앱 코드·SDK·UX 보호 정책을 완화해 통과시킨 것으로 설명하지 않는다.

실제 device의 삭제 검증 범위는 정상 생성된 세션 → 서버 OFF 중 이용 종료 → 새 프로세스의 큐 복구 → 같은 SQLite 서버 복귀 → 실제 DELETE `200 / DELETED` → 서버 데이터 0이다. ‘취소 후 늦은 POST 응답’ 경합과 비정상 2xx/202 처리는 현재 순수 coordinator·응답 계약 단위 테스트 11개의 범위이며, 실제 HTTP 지연·202를 기기에 주입해 확인한 것으로 확대하지 않는다.

서버 철회·손상·저장 실패는 캐시 단위 테스트와 게시 정책 검증 범위다. 이번 native 시험 서버는 실제 원본 Catalog의 정상 검수 콘텐츠와 실제 연결 거절만 사용하며 가짜 서버 응답을 넣지 않는다. 정상 콘텐츠 동기화 성공을 철회·손상·모든 저장 실패의 기기 통과로 설명하지 않는다.

전용 AVD·user 10과 모델이 준비되고 포트 8001 및 QA 패키지가 새 설치 조건을 만족할 때 실행하는 host 명령은 다음과 같다. 기존 run 디렉터리를 덮어쓰지 않는다.

```bash
.venv/bin/python scripts/validate_offline_guides.py \
  --package com.carcue.app.offlineqa3 \
  --apk output/apk/carcue-pleos-offline-qa3-debug.apk \
  --test-apk output/qa/offline-guides-20261114/offline-qa3-test.apk \
  --output-dir output/qa/offline-guides-20261114 --run-id NEW_UNIQUE_RUN
```

run03처럼 초기 host 준비 실패 뒤 이미 설치된 동일 QA2를 재사용하는 경우에만 `--reuse-qa-install`을 명시한다. 이 옵션은 새 설치 조건·APK 해시·캐시 없음 검증을 생략하거나 앱 데이터를 지우는 옵션이 아니다.

차량 문서 범위는 `ioniq5-ne1-2024-kr` / `hyundai-ioniq5-ne1-2024-kr` / `NE1-2024-KR-ko_KR-D202406100040-20240722`다. 자유 QUESTION 번역 기본 비활성화와 유료 AI 보류를 유지한다. 이미지는 Compose Window capture이며 실제 물리 디스플레이 가시성·실차 동작·OEM/인간 전문가/원어민 인증의 근거로 사용하지 않는다. 임시 대화·토큰·VIN·전체 차량 payload는 공용 안내 캐시에 넣지 않는다.
