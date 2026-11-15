# 공식 사용 안내 9개 확장과 검증

2026-11-15. `DEVELOPMENT_ORDER.md`의 기본 사용 안내 확장 순서에 따라 충전·좌석/거울·화면/표시등을 각각 한국어·영어·일본어로 게시했다. 기존 문 안내3개를 포함해 **4주제·3언어=12개 PUBLISHED**, 기존 DRAFT 템플릿1개로 총13개 레코드다. 다른 차종·시장·옵션·48언어 전체의 완료 수가 아니다.

## 안내 범위와 공식 근거

| 주제·가이드 ID | 실제 구현 | 검토 문서 |
| --- | --- | --- |
| 충전 `ioniq5-ac-charging-check` | AC 완속 충전 전 조건과 연결 직후 시작 확인. 3단계·10개 주의문. DC/ICCB/V2L·충전 종료·비상 분리는 범위 밖 | [충전 검토](REVIEW_AC_CHARGING_2024_KR.md) |
| 좌석/거울 `ioniq5-seat-mirror-before-driving` | 주행 전 앞좌석·자세/헤드레스트·일반 실내외 미러. 5단계·21개 주의문. DSM/DCM·메모리/릴렉션·통풍/열선·헤드레스트 분리는 범위 밖 | [좌석/거울 검토](REVIEW_SEATS_MIRRORS_2024_KR.md) |
| 화면/표시등 `ioniq5-cluster-display-check` | 밝기 설정과 READY·서비스·파워다운. 3단계, 정상 밝기 설명은 본문·실제 주의는2/3단계. 다른 경고등의 진단은 범위 밖 | [화면/표시등 검토](REVIEW_CLUSTER_DISPLAY_2024_KR.md) |

공식 한국시장 NE1/2024 HTML과 같은 판본의 PDF를 대조했다. 포털을 재조회해 HTML문서 `D202406100040`·최종게시20240722, PDF문서 `D202406100039`를 확인했다. 내부 판본 키 `NE1-2024-KR-ko_KR-D202406100040-20240722`를 유지한다. 영어·일본어는 한국시장 원문의 자체 요약이며 미국/일본 판매사양으로 바꾸지 않는다. 원문 PDF/HTML/그림은 새로 Git/APK에 넣지 않는다.

내부 검토는 **공식 원문 대조와 독립 두 번째 AI의 의미 검토**다. OEM 승인·인간 자동차 전문가/원어민 인증을 뜻하지 않는다. 초안·수정 요청·최종 의미 대조·게시 사본·출처/레코드 해시는 `output/qa/guide-expansion-20261115/`와 `content/manuals/ioniq5-ne1-2024-kr.json`의 새 review 블록에 기록했다. 기존 문 안내와 기존 metadata의 검토 이력은 보존했다.

## 앱과 AI 경계

Android의 `Guide`에 topic/relatedProperties를 보존하고 게시 가이드라는 이유만으로 문 상태를 붙이던 경로를 제거했다. 검증된 프로필·판본·door.position·실제 문 규칙이 맞는 기존 문 안내에서만 문 상태/GET를 표시한다. 새 세 안내는 관련 property가 비어 있고 수동 공식 안내와 원문 열기를 제공한다. **충전·좌석/미러·표시등 센서 수신, 차량 조작, 밝기 제어를 새로 연결하지 않았다.**

AI 검색은 선택된 다른 가이드의 문맥을 임의의 타 주제 질문에 빌려 쓰지 않는다. 명시적 주제·짧은 문맥 후속 질문을 구분하며 혼합 주제·확인된 범위 밖 하위 주제를 거절한다. 이 유한한 경계 검사가 임의 질문의 의미 적합성을 보증하지는 않는다.

새 `:manual-bundle:v1`은 body와 모든 단계 제목/본문·명시 주의문을 한 단위로 조립한다. 필수 주의가 있는 단계와 전체 payload/text SHA를 고정해 일부 주의 삭제·과거 부분 답변 캐시를 거절한다. 최대3000자·최대5출처를 유지하며 초과분을 잘라 답하지 않는다. 기존 문 `:closing-bundle:v1`의 규칙·문자열·게시3파일은 바꾸지 않았다. 현재 최장 영어는 좌석/거울2837자다. ANSWER/GUIDE 저장 번역은 같은 프로필·판본·가이드만 대응한다.

## 실제 수행 결과

| 검사 | 결과 | 실제/대역 구분 |
| --- | --- | --- |
| 원문·3언어 의미 검토 | 신규9개 독립 대조 통과, 게시 검사13개 VALID | 실제 공식 문서 대조. 전문가 인증 아님 |
| 전체 backend | **606 passed**, 기존 AnyIO deprecation warning1 | 실제 데이터 회귀+합성 catalog/provider·HTTP 대역. 실제 모델/SDK 호출0 |
| 계약/카탈로그 | **UI194** 세 언어·4개 완전답변 정책/12핀·기존 상태 규칙1 통과 | 구조·게시 조건·해시 검사 |
| 순수 Android 정책 | 선택한 Kotlin/JVM **28개** 통과 | topic 보존·문 binding 경계의 합성 정책. 전체 앱/기기 시험과 구분 |
| 실제 로컬 HTTP | 가이드 **9개**, 저장 번역 **36건**(3주제×6방향×ANSWER/GUIDE), 범위 밖 질문 **9건** 통과 | 실제 FastAPI/SQLite/TCP. 공급자는 DISABLED, 저장 번역은 STORED_GUIDE·모델0 |
| 정리 | 생성 세션 삭제 확인, sessions/results/history **0/0/0**, 소유 서버 정상 shutdown 확인 | 자기 신규 DB/프로세스만 사용. 기존 서버·DB 재시작/삭제0 |

회귀 로그는 `integration-final-02/`, 실제 HTTP는 `http-live-01/validation.json`에 보존했다. Uvicorn0.34가 정상 종료 후 SIGTERM을 다시 보내는 동작을 설치 소스에서 확인했으며, 종료 코드는 그대로 기록하고 실제 `Application shutdown complete.` 로그와 DB0을 함께 요구한다. 원격 Android CI는 Demo JVM/Mock APK 컴파일이며 실제 SDK/AVD·모델 시험을 포함하지 않는다. push/최종 CI는 정확한 원격SHA/실행 ID로 별도 기록한다.

```bash
# backend 의존성이 있는 Python. 매번 새 evidence 경로를 사용한다.
.venv/bin/python scripts/validate_manual_guides.py \
  --output-dir output/qa/guide-expansion-NEXT/http-live-01
```

이 도구는 자체 loopback 소켓을 자식 서버에 전달하고 공급자DISABLED·빈 유료 키·신규 DB로 기동한다. 기존 포트·서버·DB를 재사용하지 않으며 토큰은 메모리에만 둔다. 새 가이드와 저장 번역을 확인한 뒤 세션을 삭제하고 자기 서버만 종료한다. AVD·Ollama·유료 AI는 기동하지 않는다.

## 기존 제출물과 남은 시험

기존 제출용 APK5ef…·영상638…·PDF3a9…·ZIP79a…의 **네 SHA256이 모두 그대로**임을 재대조했다. 고정 `release/0.1-first-draft`와 main은 이동하지 않는다. 이번9개는 최신 개발본이며 기존 제출 APK/영상에 반영했다고 쓰지 않는다.

**구 제출 APK는 고정 release의 backend/content와 짝으로 재현한다.** 구 APK는 topic을 읽지 않아 새 서버의 비문 가이드에 문 패널을 표시할 수 있으므로 새 서버와 혼용하지 않는다. 기존 `validate_local_ai.py` 등 door-only 도구도 해당 고정 버전의 검증 범위다. 새 도구의 실제 HTTP는 별도 신규 서버/DB를 사용해 기존 제출 환경과 격리했다. 업데이트 설치의 기존 가이드 캐시에는 이전 문 안내만 있을 수 있어 새 안내를 받으려면 온라인 동기화가 필요하다.

사용자 지시대로 AVD 재시험과 유료 AI는 보류했다. **새9개의 실제 Pleos 앱 화면·언어/주행 제한·원문 왕복과 새 세 주제의 실제 무료 모델 선택 시험은 미실시**다. 기존 진행 중 언어 변경·Drive·이용 종료3경계와 신규429 기기 화면 검증도 남아 있다. 이번 원문·API/저장 번역·빌드 검증을 그 시험의 성공으로 계산하지 않는다.
