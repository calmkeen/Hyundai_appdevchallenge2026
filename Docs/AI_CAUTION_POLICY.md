# AI 답변의 완전한 주의문 단위

2026-11-14. `feature/ai-complete-caution-answers`. 이 정책은 한국시장 2024 IONIQ 5의 등록 문 안내에서 앞 단계의 확인 사항이 빠지는 문제를 서버에서 막는다. 유료 AI 연결과 자유 질문 번역의 기본 보류는 변경하지 않는다.

## 문제와 원문 보존

기존 답변 후보는 가이드 body·각 단계 body/주의문 중 하나였다. 닫힘 표시를 확인하는 두 번째 단계에서 질문하면 그 단계만 선택해도 기존 exact-unit 검증을 통과했으며, 첫 단계의 손·머리 등 신체 확인과 닫지 말아야 하는 조건이 답변에 포함되지 않을 수 있었다. 모델에게 앞 단계를 고르라고 요청하는 것만으로는 이 누락을 막을 수 없다.

현재 작은 2단계 문 안내에는 전체 확인 순서를 하나의 canonical 답변으로 사용한다. 기존 PUBLISHED 3언어 JSON과 출처·검토 해시는 수정하지 않는다. 새 문구나 다른 주제의 경고를 만들어 추가하지 않는다. `official_cautions`는 기존 CarCue의 **명시적 주의 요약**이며, 해당 문장이 OEM 원문 금지문의 직접 인용이라는 뜻은 아니다. 기존 검토는 AI 보조 원문 대조와 의미 검토 범위이며 OEM 승인·인간 전문가 인증이 아니다.

## 정확한 등록 범위

`content/answer-bundles.json`과 `contracts/answer-bundles.schema.json`이 다음을 고정한다.

- profile `ioniq5-ne1-2024-kr`, manual set `hyundai-ioniq5-ne1-2024-kr`.
- source version `NE1-2024-KR-ko_KR-D202406100040-20240722`, guide `ioniq5-door-open-check`, topic `door`.
- locale `ko-KR`, `en`, `ja-JP` 각각의 canonical JSON payload SHA256과 최종 bundle UTF-8 SHA256.
- 순서가 고정된 `check-pinch-area`, `check-closure-display` 두 단계와 각 source reference.
- `hyundai-ne1-2024-kr-door-open-warning`, `hyundai-ne1-2024-kr-door-pinch-caution` 두 출처. 출처 배열 순서는 기존 guide.sources와 같다.

단위 ID는 `<guide_id>:<locale>:<source_version>:closing-bundle:v1`이다. 본문은 다음 문자열 배열을 `\n`으로 연결한 결과와 정확히 같아야 한다.

```text
guide.body
step1.body
step1.official_cautions의 모든 항목
step2.body
step2.official_cautions의 모든 항목
```

원문 조각의 재작성·공백 정리·주의문 제거·단위 환산을 하지 않는다. 현재 길이는 KO 324자, EN 786자, JA 328자다. 답변/저장 번역 계약을 모두 만족하도록 3000자를 넘는 단위는 자르지 않고 거절한다.

등록 규칙, 필수 단계/주의문/출처, scope 또는 SHA가 맞지 않으면 이 guide는 답변 후보가 0개가 된다. 해당 guide ID는 코드에서 보호 대상으로 예약해 규칙 파일 누락·손상·항목 삭제도 기존 body/step 단위로 돌아가지 못하게 한다. 다른 가이드의 기존 body/step 후보와 body-only 계약은 보존한다. 이 정책을 다른 판본·차종에 적용하려면 해당 자료와 정책을 새로 검토해야 한다.

## 서버 조립과 저장 번역

Ollama는 status와 등록 unit ID만 선택한다. 이 문 안내의 schema에는 전체 bundle 하나만 허용되며, 두 번째 단계 context가 앞 단계의 확인이나 주의문을 제거하지 못한다. 모델이 과거 step ID를 반환하면 거절한다. 서버는 선택 ID의 검수 문자열·출처를 조립하고, `validate_answer`도 같은 후보만 허용한다. 다른 provider 대역이 과거 body/step을 반환하거나 주의문 하나만 제거해도 최종 API에서 거절한다.

ANSWER 번역은 전체 bundle 문자열과 source locale을 정확히 확인한 뒤 같은 guide/manual/version·suffix·출처 집합의 목표 언어 bundle을 반환한다. 모델 호출은 0회이고 목표 레코드의 REVIEWED/NOT_APPLICABLE 및 glossary 정보를 유지한다. 과거의 불완전 body/step 답변은 현재 ANSWER 번역으로 승격하지 않는다.

GUIDE 번역은 AI 답변 단위와 분리했다. 등록 가이드의 raw body를 동일 판본의 저장 raw body로 정확히 매핑하는 기존 기능을 유지한다. QUESTION 생성 번역은 기본 보류다.

## 같은 DB의 과거 캐시

새 배포에서도 동일 request ID의 과거 결과가 먼저 반환될 수 있으므로 신규 호출뿐 아니라 캐시를 검사한다.

- cached ASK `ANSWERED`: 현재 검색 scope·완전한 canonical answer·두 출처의 정확한 metadata·현재 서버 action과 대조한다. 불일치하면 기존 fingerprint를 유지하고 고정된 현지화 `NO_RELIABLE_SOURCE`/NOT_CALLED 결과로 교체한다. 원래 부분 답변이나 history를 응답에 첨부하지 않고 숨은 모델 호출도 하지 않는다. 같은 ID의 반복 재생도 모델을 호출하지 않는다.
- cached ANSWER/GUIDE `TRANSLATED`: 현재 저장 매핑과 전체 응답을 다시 대조한다. 과거 부분 ANSWER나 잘못된 번역/검수 metadata는 TEMPORARILY_UNAVAILABLE, translated_text null, NOT_CALLED로 거절한다. 입력 original_text 보존은 기존 계약대로다.

request ID의 다른 입력 재사용은 기존 409이며 fingerprint를 바꾸지 않는다. 기존 session 소유 검사·만료·종료 삭제와 모델 audit의 본문 비노출도 유지한다.

## 검증 범위

서버 회귀는 합성 provider/HTTP 대역과 실제 등록 카탈로그를 사용한다. 각 body/주의 요약 하나라도 제거한 답변, 이전 단독 단위, 두 번째 단계 ID 선택 변조, 한 출처 누락, profile/manual/version/locale·SHA·규칙 손상, 크기 초과, same-DB 캐시 재생 및 foreign citation을 검사한다. 저장 ANSWER 언어 방향·GUIDE raw body·지원되지 않는 질문·중복 요청도 확인한다. 모델에 정확한 ID를 선택하라는 prompt만 검사하고 완료로 판단하지 않는다.

실제 무료 모델·실제 SDK 앱 검증은 root의 별도 실행 결과로 기록한다. 이 구현 작업은 서버8001·Ollama·AVD를 조작하지 않았으며, 대역 시험 통과를 실제 모델·실차·모든 주제의 품질 완료로 계산하지 않는다.

로컬 검증 결과: 관련 회귀 **272개 통과 / 3.63초**, 최종 전체 backend **462개 통과 / 6.79초**. 신규 정책/API/캐시 회귀 82개를 포함한다. 기존 단독 3단위 번역 조합은 새 단일 bundle의 모든 언어 방향·명시/자동 source 선택 조합으로 바꾸고, 과거 3단위는 거절 회귀로 검증한다. `scripts/check_contracts.py`도 통과했다(필수 bundle1개·실제 3언어 payload/text 핀·기존 지원/상태 규칙·UI185자원).

실제 출력은 ignored `output/qa/ai-complete-cautions-tests-02.txt`, `ai-complete-cautions-backend-full-02.txt`에 보존했다. 이전 실패한 개발 단계 출력도 덮어쓰지 않았다. `ai-complete-cautions-policy-01.json`은 정책·최종 단위 SHA와 기준선 대비 게시 3파일 보존 확인 기록이다.

후속 실제 검증은 [AI_CAUTION_VALIDATION.md](AI_CAUTION_VALIDATION.md)에 기록했다. 실제 API9개와 SDK 앱3답변/3저장 번역을 무료 Ollama로 확인했다. 초기 실패와 독립 검토를 별도 보존하며 이 정책의 합성 회귀 결과와 구분한다.
