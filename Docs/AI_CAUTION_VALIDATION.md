# AI 답변 주의문 보완 검증

2026-11-14~15 (KST). 작업은 `feature/ai-complete-caution-answers`(정책/회귀)와 `feature/ai-caution-validation`(실제 호출/앱 검증/Docs)로 나눴다. 유료 AI와 자동 전환, 생성 QUESTION 번역의 기본 보류를 유지한다. 구현 정책은 [AI_CAUTION_POLICY.md](AI_CAUTION_POLICY.md)를 따른다.

## 문제와 보완

이전 원문 연결 run06에서 ‘문을 닫기 전에 무엇을 확인해야 하나요?’를 두 번째 가이드 단계에서 질문하면, 모델이 닫힘 표시 확인 단계만 선택해 앞 단계의 끼임 주의를 생략했다. 당시 실패 해석과 원본 출력은 그대로 보존했다.

현재 등록된 문 안내는 본문 → 신체 확인 단계 → 그 단계의 모든 주의문 → 닫힘/계기판 확인 단계 → 그 단계의 모든 주의문을 하나의 `closing-bundle:v1` 답변으로 반환한다. 모델은 등록 단위를 선택하고 서버가 검토된 문자열과 출처를 조립한다. 새 경고를 자유 생성하는 방식은 아니다. 규칙/판본/해시/주의문/출처가 맞지 않으면 부분 답변으로 돌아가지 않고 거절한다. 과거 부분 ASK/ANSWER 번역 캐시도 현재 정책으로 재검사한다.

기존 게시된 한국어·영어·일본어 가이드 JSON 3개는 기준선 `7852159` 대비 바이트를 보존했다. 프로필 `ioniq5-ne1-2024-kr`, 매뉴얼 `hyundai-ioniq5-ne1-2024-kr`, 판본 `NE1-2024-KR-ko_KR-D202406100040-20240722`에만 적용한다.

## 공식 매뉴얼 대조

`firecrawl_local` MCP로 아래 두 공식 페이지를 fresh 요청(`maxAge=0`)해 HTTP 200 본문을 다시 읽었다. 로컬 연결의 최초 권한 실패도 기록했으며 Firecrawl Cloud는 사용하지 않았다.

- [도어·후드·테일게이트 열림 경고](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/idff13cd5359c.html)
- [도어·테일게이트·유리창 개폐 주의](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id0d6d99a8d21.html)

한국어 원문과 세 언어 출력에서 다음을 각각 확인했다. 문을 닫기 전 손·머리 등 신체를 확인하고, 신체가 개구부에 있으면 닫지 않으며, 확인 후 닫는 순서를 유지한다. 출발 전에는 모든 문·후드·테일게이트의 완전 닫힘과 계기판의 **경고문 및 열린 부분 표시 모두**의 해제를 직접 확인한다. 앞좌석 왼쪽 문 CLOSED 값 하나로 잠금·전체 닫힘·출발 가능을 단정하지 않는다.

‘신체가 문틈에 있으면 닫지 마세요’는 공식 원문에서 도출한 CarCue의 명시적 주의 요약이며 OEM 금지문의 직접 인용이 아니다. 이번 검토는 공식 한국시장 2024 NE1 매뉴얼 두 절을 근거로 한 AI 보조 원문/의미 검토다. OEM 승인·인간 전문가·원어민 인증이나 다른 차종/주제의 검수 완료를 뜻하지 않는다.

근거: `output/qa/answer-cautions-20261114/manual-review/manual-review.json`, `semantic-checklist.md`. API 출력 9개와 ANSWER 번역 6개를 별도 에이전트가 실제로 읽은 기록은 `api-cautions-20261114-03/semantic-review.json`이다.

## 실제 무료 모델 API

`api-cautions-20261114-03`은 Mac의 Ollama 0.40.16 / `qwen3:4b`와 LIVE FastAPI/SQLite를 실제 호출했다. 모델 digest는 `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`이다.

| 항목 | 결과 |
| --- | --- |
| ASK | 한국어·영어·일본어 × 첫 단계/두 번째 단계/가이드 문맥 없음 = **9개 통과**, 실제 모델 9회 |
| 완전성 | 매번 본문+두 단계+모든 주의문 5조각의 정확한 내용/순서, 출처 2개와 프로필/판본 일치 |
| 중복 재생 | 동일 요청 9개 재생, 추가 모델 호출 0회 |
| ANSWER 저장 번역 | 3언어 사이 6방향 모두 전체 bundle 일치, 추가 모델 호출 0회 |
| GUIDE 저장 번역 | raw body 3개 기존 동작 보존, 추가 모델 호출 0회 |
| 과거 불완전 ANSWER | body/step1/step2 × 3언어 = 9개 거절, 번역 null·NOT_CALLED |
| 기본 보류 | QUESTION 3언어 요청 거절, 추가 모델 호출 0회 |
| 범위 밖 질문 | 충전/브레이크 등 3개 출처 없음으로 거절, 추가 모델 호출 0회 |
| 종료 | 생성 세션 모두 DELETE, sessions/results/history 각각 0건 |

이 API 시험은 `vehicle_context=[]`이며 SDK 수신 시험으로 계산하지 않는다. 모델 audit의 요청 hash·HTTP 200·STRUCTURED_VALIDATED·토큰/응답 digest를 9개 요청과 1:1 대조했다. 실제 결과는 `output/qa/answer-cautions-20261114/api-cautions-20261114-03/validation-result.json`이다.

초기 도구 run01은 세션 생성 상태 코드를 200으로 잘못 기대했고, run02는 실제 `token` 필드 대신 다른 필드명을 기대해 실패했다. 모델 호출은 모두 0회였다. 검증 도구를 실제 API 계약에 맞게 고친 뒤 별도 run03으로 실행했다. 앞선 각 실행이 만든 빈 QA 세션 한 개만 소유권/내용을 확인해 제거했으며 실패 로그와 삭제 증거를 보존했다. 실패를 성공 기록으로 수정하지 않았다.

## 실제 SDK 앱

기존 userdata를 보존한 공식 Pleos API34 AVD `CarCue_Pleos21_LocalAI`/user10에서 `PleosCautionAnswersTest`를 실행했다. 최종 `app-cautions-20261114-02`는 **73.640초 / 1개 통과**다.

| UI 경로 | 실제 ASK | 저장 ANSWER 번역 |
| --- | --- | --- |
| 첫 번째 가이드 단계 | 한국어 완전 답변 | 영어 REVIEWED |
| 두 번째 가이드 단계 | 영어 완전 답변 | 일본어 REVIEWED |
| HOME, 가이드 문맥 없음 | 일본어 완전 답변 | 한국어 NOT_APPLICABLE·원문 안내 |

앱 시험은 **3개 문맥 경로/3회 실제 모델 호출/3회 저장 번역**이며 API의 9개 조합 전체를 기기에서 실행한 것은 아니다. 문맥은 실제 UI 진입 경로로 기록하며 독립 네트워크 패킷 캡처를 뜻하지 않는다. 매 단계 실제 PLEOS·SUPPORTED/VALUE·CLOSED·TTL 60초 이내 값, 알려진 UX 허용 상태와 새 GET을 확인했다(GET 횟수 3/4/6/7/9/10). 앱 동의·송신·응답·전체 주의문 표시·두 출처·번역 제목·이용 종료/삭제 대기 해제를 실제 화면에서 검사했다. 저장 번역은 추가 모델 호출 0회다.

6개 Compose 캡처와 대응하는 focused Activity 물리 디스플레이 캡처 6개, 일반 런처 캡처 1개를 별도 에이전트가 원해상도로 읽었다. 핵심 6개 답변/번역 화면은 주의문 잘림·겹침 없이 일치했다. 일반 런처 초기 사진은 좁은 CarCue 프로필 영역과 지도가 나뉘어 일부 프로필 설명이 잘려 보인다. 이 사진을 전체 폭 레이아웃 완료의 근거로 확대하지 않는다. 테스트의 `KEEP_SCREEN_ON`은 시험 동안만 설정하고 복구한다. SDK 서비스·렌더러·보안 설정은 바꾸지 않는다. AVD 시스템 패널과 CarCue 내부 이미지를 구분한다.

최종 앱은 `output/apk/carcue-pleos-caution-answers-debug.apk`, SHA256 `8e4ff19f1ed6b01136b9a36b9335e1fc2e59df04dda02fcfcad7f60a9070ed12`다. 실제 설치본을 pull해 일치시켰다. native02 당시 테스트 APK는 `output/apk/carcue-pleos-caution-answers-validated-test.apk`, SHA256 `0d3aa103f0dd3938dfd757b0e8cfb15b30e50345b0888d0489961f5c0d5c72ac`로 보존한다. 기능 APK는 후속 검증 도구 정리에도 바꾸지 않는다.

앞선 native01은 **77.999초 PASS**로 동일한 3답변/3저장 번역을 확인했다. 다만 비동기 일반 런처 직후 찍힌 전체 사진은 내비게이션 화면이어서 CarCue 물리 표시 근거로 쓰지 않았다. 원본은 그대로 보존하고, 플랫폼 `am start -W`와 Activity focus 확인·단계별 물리 캡처를 추가한 별도 native02에서 다시 확인했다. 원 validation의 독립 검토 대기 표시는 보존하고, 별도 `visual-semantic-review.json`에 검토 결과를 남겼다.

두 native 실행 모두 세션 종료 뒤 서버 DB 세 테이블이 0건이다. 전체 실제 모델 호출은 API 9 + native01 3 + native02 3 = 15회로 audit와 일치한다. 마지막 host fixture는 Park/0/CLOSED, Console 자체 lease와 독립 bootstrap heartbeat의 close HTTP 200/ACK·종료 코드 0을 확인했다. 전용 AVD도 `emu kill` 후 실행 프로세스 종료와 빈 `adb devices`를 확인했으며 userdata·캐시·snapshot을 삭제하지 않았다. 무료 서버와 Ollama는 유지한다.

## 자동 회귀와 경계

backend **462개**, Android JVM **110개**, 계약·게시 bundle 해시/출처/185개 세 언어 UI 자원 검사와 Pleos Debug 앱/테스트 빌드를 통과했다. backend 최종 재확인은 12.77초이며 최초 샌드박스 실행의 loopback 서버 bind 오류 9개를 보존하고 정상 로컬 소켓 환경에서 별도로 재실행했다. 이는 제품 실패를 무시하거나 테스트를 제외한 것이 아니다.

최종 읽기 리뷰 뒤 API audit 검사를 강화하고 저장된 실제 API03 이벤트 9개를 새 검사 함수로 오프라인 재검사해 통과했다(추가 모델 호출 0). 기존 `PleosLocalAiFlowTest`도 보호 가이드의 부분 단위를 허용하지 않도록 바꾸고 테스트 APK 컴파일 13초 통과를 확인했다. 이 보조 helper 자체를 추가 기기 실행한 결과로 계산하지 않는다. native02에서 사용한 테스트 APK는 위 별칭/hash로 그대로 보존하고, 후속 compile-only 테스트 APK hash는 `final-build-artifacts.json`에 따로 기록했다. 기능 앱과 신규 strict 시험 본체는 변경하지 않았다.

- 실제 연동: Mac 무료 Ollama, HTTP/FastAPI/SQLite, 공식 AVD의 Vehicle SDK 2.3.2/Service 2.3.22·AndroidCarUX, 네이티브 앱 응답/번역 화면.
- 생성과 저장의 구분: ASK는 실제 모델의 등록 단위 선택 후 서버 조립이다. ANSWER/GUIDE 번역은 검토된 저장 문자열이며 실시간 생성 번역이 아니다.
- 대역: 서버 회귀의 provider/HTTP fixture, 기존 demo flavor와 MOCK 서버. 이번 실제 실행에는 차량/모델 대역을 넣지 않았다. Console 입력 자체는 전용 AVD의 시뮬레이션이다.
- 미검증/보류: 실차·다른 차종/판본/주제, 모든 자유 질문의 관련성, 생성 QUESTION 번역 품질, 유료 AI. 이전 문 개폐/주행 제한 전체 회귀는 기존 별도 기록이며 이번 73.640초 시험으로 새 전체 회귀를 주장하지 않는다.

## 재현

기존 전용 AVD 데이터와 캐시를 보존하고, 무료 서버는 다음 명령으로 별도 실행한다. 모델 설치/시작과 서버 환경은 [LOCAL_AI_INTEGRATION.md](LOCAL_AI_INTEGRATION.md)를 따른다.

```bash
.venv/bin/python scripts/run_local_ai_backend.py --model qwen3:4b --port 8001 --evidence-dir output/qa/answer-cautions-20261114/live-server
.venv/bin/python scripts/validate_caution_answers.py --run-id UNIQUE_API_RUN --audit-file output/qa/answer-cautions-20261114/live-server/provider-events.jsonl --database output/qa/answer-cautions-20261114/live-server/sessions.sqlite3
.venv/bin/python scripts/validate_caution_app.py --apk output/apk/carcue-pleos-caution-answers-debug.apk --test-apk output/apk/carcue-pleos-caution-answers-validated-test.apk --audit-file output/qa/answer-cautions-20261114/live-server/provider-events.jsonl --run-id UNIQUE_APP_RUN
```

실행 ID는 새 값이어야 한다. 앱 도구는 APK를 설치하지 않고 설치된 두 APK의 실제 바이트 hash를 입력 파일과 대조한다. Console host fixture는 격리 AVD에서 Park/0/CLOSED로 설정하고 finally에서 복구·lease 해제한다. 앱의 SDK SET은 없다. 모델 audit 구간이 겹치지 않도록 API/앱 도구는 순서대로 실행한다.
