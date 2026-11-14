# 생성 질문 번역 보류와 과거 캐시

2026-11-15 (KST). `feature/question-deferral-cache-boundary`. 다국어·이용 종료 검증 과정에서 기존 개발 opt-in 번역 결과가 같은 DB에 남았을 때의 경계를 보완한다.

## 문제와 처리

생성 QUESTION 번역은 기본 보류지만 기존 구현은 provider 설정을 확인하기 전에 동일 request ID의 저장 성공 결과를 반환했다. 따라서 개발 옵션을 켠 서버에서 만든 UNREVIEWED 번역을 같은 DB의 보류 서버가 다시 보여줄 수 있었다. 신규 요청의 무호출 검사만으로는 잡히지 않는 경계다.

이제 캐시 재생도 현재 모드와 `enable_draft_question_translation`을 검사한다. 현재 생성이 허용되지 않으면 원문과 요청 fingerprint를 보존하고 `TEMPORARILY_UNAVAILABLE`, `translated_text=null`, `NOT_CALLED`, model 없음의 결과로 교체한다. 현재 요청에서 모델을 호출하지 않으며 다른 내용으로 같은 ID를 재사용하면 기존 409를 유지한다. LIVE 기본 보류와 MOCK 전환 모두 적용한다.

ANSWER/GUIDE 저장 번역과 완전한 문 주의문 정책, 유료 provider 보류, 세션 소유 검사·만료·종료 삭제는 유지한다. 명시적 개발 opt-in 자체의 의미 품질을 완료하거나 자동 활성화한 작업이 아니다.

## 검증

실제 SQLite 임시 DB와 FastAPI TestClient에서 개발 opt-in 결과를 만든 뒤 서버를 닫고 같은 DB를 새 보류 서버로 다시 열었다. 한국어→영어, 영어→일본어, 일본어→한국어 × LIVE/MOCK 6개에서 과거 번역 2회 반복 차단, 원문/fingerprint 보존, 입력 변경 409와 종료 후 sessions/results/history 0건을 확인한다. provider HTTP는 `httpx.MockTransport` 대역이므로 실제 모델 호출 증거로 계산하지 않는다. 과거 결과 생성은 대역 1회, 보류 재생은 0회다.

전체 backend 결과는 루트 검증 기록 `output/qa/multilingual-session-20261115/backend-cache-boundary-tests.log`를 따른다. 실제 SDK 앱·무료 모델 재시험은 별도 통합 검증에서 기록한다.
