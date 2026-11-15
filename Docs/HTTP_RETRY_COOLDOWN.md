# HTTP 429 재시도 대기

2026-11-15. `DATA_API_SPEC.md`의 429 재시도 가능 시간 표시를 구현한다. 차량 SDK, 실제 모델, 유료 AI 정책, 게시 가이드는 변경하지 않는다.

## 동작

- `CarCueApi`는 HTTP 429의 `Retry-After`를 오류 본문 파싱과 별도로 읽어 `ApiFailure.retryAfterMillis`에 보존한다. 다른 HTTP 상태는 기존 처리를 유지한다.
- 음수가 아닌 초 또는 `RFC_1123_DATE_TIME`으로 해석 가능한 HTTP 날짜를 사용한다. 날짜는 응답 헤더를 읽은 시각에 한 번만 기간으로 변환한다. 지난 날짜/0초는 추가 대기가 없고, 미래 날짜의 밀리초 미만은 올림하여 먼저 풀리지 않게 한다.
- 헤더 누락·빈 값·잘못된 형식·음수·단일 comma-list는 60초 대기다. 여러 헤더는 해석한 대기 중 최댓값을 사용한다. 유효한 긴 대기를 한 시간 등으로 줄이지 않으며, 표현 범위를 넘는 숫자는 `Long.MAX_VALUE` 밀리초로 포화한다.
- `AssistantCooldown`은 주입한 단조 시계의 시작 시각과 경과 시간으로 계산한다. 앱에서는 `SystemClock.elapsedRealtime()`을 사용한다. 벽시계·시간대 변경은 이미 시작한 대기를 앞당기지 않는다. 대기 중 자동 재전송은 없다.
- `UiState.assistantCooldownSeconds`와 `ai_retry_cooldown`에 한국어·영어·일본어 남은 초를 표시한다. 429는 일반 연결 실패와 구분한 요청 한도 안내와 `serverConnection=HTTP_429`로 남긴다. 전송과 재시도 버튼을 함께 비활성화하며, `ViewModel.send()`도 직접 재검사해 오래된 버튼 이벤트/직접 호출이 대기를 우회하지 못한다.
- 대기 범위는 세션 epoch·프로필·선택 언어다. 실제 언어 변경과 프로필/세션 변경·이용 종료에서 타이머와 대기를 정리한다. 같은 언어 재선택, 화면 이동·요청 취소·백그라운드 전환만으로 현재 대기를 지우지 않는다. 서버의 실제 할당량은 이 UI 범위와 별개로 계속 적용된다.
- 대기가 끝난 뒤 사용자 재시도는 기존 `AssistantRequests`의 `RESEND` 규칙을 따른다. 동일 요청의 ID·본문·최초 SDK 수신 시각을 다시 생성하지 않는다. 새 입력/맥락은 기존 정책대로 새 요청이다. 대기 만료가 서버 요청 성공을 보장하지 않으며 서버가 다시 429를 보내면 새 대기를 적용한다.

대기는 메모리에만 둔다. 앱 프로세스 재시작 후에는 서버가 한도를 다시 판정한다. 새 이용자에게 이전 대화나 이전 세션 타이머를 넘기지 않는다.

## 검증과 남은 조건

호스트 부하 때문에 전체 로컬 Gradle 빌드·AVD·실제 모델 호출은 수행하지 않았다. 다음은 실행한 가벼운 검증이다.

1. 기존 캐시의 Kotlin 2.0.0 CLI/JDK 17, `-Xmx256m -XX:ActiveProcessorCount=1`로 순수 정책·모델과 JUnit을 컴파일했다. 변경하지 않은 공식 자원 모델 타입은 기존 루트 빌드의 클래스에서 참조했다. Android 앱 전체 컴파일을 대신하는 결과가 아니다.
2. `AssistantCooldownTest` 14개와 `AssistantRequestPolicyTest` 11개, 합계 **25개 통과**, 실패 0개. 헤더 0/과거/미래·공백·중복·오버플로, 24시간 보존, 시간 경계·시계 변경·범위 분리·정리, 대기 후 동일 요청 재전송을 검사했다. 실제 HTTP/SDK/AI 호출 시험은 아니다.
3. `scripts/check_contracts.py` 통과. UI 자원 **193개**의 세 언어와 치환 변수, 기존 공식 자료·번들·지원·상태 규칙을 확인했다.
4. 기존 `backend/tests/test_api.py::test_quota_limits_provider_cost` **1개 통과**. 서버가 한도에서 `429 / Retry-After: 60`을 반환하는 HTTP 테스트 대역 회귀다. 기존 AnyIO deprecation warning 1개가 남는다. 서버 소스는 바꾸지 않았다.

로그는 `output/qa/http-retry-cooldown-20261115/policy-unit-01/`의 `compile.log`, `junit.log`, `result.json`, `contracts-final.log`, `server-quota.log`, `lightweight-checks.json`에 보존한다. 전체 Android JVM·앱/flavor 빌드는 통합 후 원격 CI에서 별도로 확인해야 한다. 새 APK의 429 표시·버튼 대기 실제 화면은 아직 검증하지 않았으며, 기존 SDK 시연 APK/영상의 통과를 이번 변경의 기기 시험으로 계산하지 않는다.
