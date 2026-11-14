# 공식 원문·지원 링크 카탈로그

2026-11-14. 이 문서는 등록 자료·서버 action의 검증 범위다. 외부 브라우저 실제 실행과 Pleos handler 동작은 Android 기기 검증 결과로 별도 기록한다.

## 등록 범위와 출처

사용자가 선택한 `ioniq5-ne1-2024-kr`의 판매지역 `KR`에 현대자동차의 한국 공식 **WEBSITE** 한 개를 등록했다. 영어·일본어 UI에서도 이 시장은 바뀌지 않는다. 이 프로필은 SDK 차종·VIN 자동 인증 결과가 아니다.

| 필드 | 등록 값 |
| --- | --- |
| id | `hyundai-kr-customer-support` |
| kind | `WEBSITE` |
| title | 현대자동차 고객 문의 |
| url / evidence_url | [현대자동차 한국 고객 문의](https://www.hyundai.com/kr/ko/e/customer/center) |
| market_code / source_locale | `KR` / `ko-KR` |
| verification_status | `VERIFIED` |
| reviewed_at | `2026-11-14T12:45:09.962773Z` |

로컬 Firecrawl MCP를 직접 실행해 공식 도메인 검색과 해당 페이지의 본문을 수집했다. 페이지 제목·한국어 메타데이터·차량 구입/정비 서비스 문의·FAQ·ARS 상담 안내를 확인했다. 앱에는 전화번호·영업시간을 복제하거나 발신 동작을 등록하지 않는다. 링크의 최신 안내는 공식 사이트에서 확인한다. `VERIFIED`는 수집한 출처와 적용 시장을 대조했다는 콘텐츠 상태이며 OEM 승인·인간 전문가 인증이나 실시간 접속 성공 보증이 아니다.

수집 근거는 저장소의 ignored QA 산출물 `output/qa/official-links-20261114/catalog/`에 보존한다.

- `support-search-01.json`: `firecrawl_search`의 공식 URL 검색 결과.
- `customer-center-01.json`, `customer-center-01.md`: 선택 페이지의 실제 응답·수집시각·본문. HTTP 200.
- `support-landing-01.json`, `support-landing-01.md`: 기존 고객지원 landing 후보의 응답. HTTP 200과 제목은 확인됐으나 추출 본문이 탐색 요소뿐이어서 지원 설명의 본문 근거로 채택하지 않았다.
- `mcp-verification.stderr.log`: 이 작업 전용 로컬 MCP stderr. 다른 작업의 로그 경로를 사용하지 않았다.

연결은 `/bin/bash /Users/younsung/Dev_Personal/Sendbird/firecrawl-local/mcp.sh`의 stdio MCP이며 Cloud Firecrawl 도구·유료 AI를 사용하지 않았다. 이 로컬 MCP의 tools/list에는 feedback 도구가 없어 feedback 호출은 생략했다. 웹 본문은 출처 자료로만 취급했다.

## 계약과 실행 경계

`support_contacts`는 프로필에 포함된 등록 레코드다. `contracts/support-contact.schema.json`과 `backend/app/official_links.py`가 ID·WEBSITE·검증 상태·동일 판매지역·등록 언어·출처·UTC 검토시각을 확인한다. 모호하거나 잘못된 레코드가 있으면 해당 지원 목록은 노출하지 않는다. 두 기존 개발용 프로필은 미검수 상태와 빈 지원 목록을 보존한다.

서버가 반환하는 `OPEN_SUPPORT.target_id`는 등록 contact ID다. `OPEN_MANUAL.target_id`는 검증된 citation의 `source_id`다. 모델은 URL/action을 생성하지 않는다. 서버는 현재 검색·게시 범위와 출처 메타데이터를 다시 대조한 뒤 action을 조립한다. 같은 호스트에 있다는 이유만으로 다른 차량·시장 URL을 허용하지 않는다.

기존 게시 계약의 source ID는 action 대상보다 넓은 문자열을 허용한다. resolver는 응답 계약의 ASCII ID 형식·최대 128자를 다시 검사해 실행 대상에 부적합한 ID를 차단한다. 기존 원문·citation을 고치거나 다른 링크로 대체하지 않는다. 현재 등록된 3언어 source ID는 이 경계를 통과한다.

- `ANSWERED`: 기존 관련 가이드/상태 재조회와 함께, 실제 인용한 등록 출처 및 프로필의 공식 지원을 제공한다.
- `NO_RELIABLE_SOURCE` / `NEED_MORE_INFO`: 등록 지원만 추가한다. 관계없는 문 안내를 질문의 근거로 만들지 않는다.
- `TEMPORARILY_UNAVAILABLE`: 기존 오류 동작과 빈 action을 유지한다.

기존 게시 가이드 단계의 `OPEN_MANUAL.target_id`에는 raw URL이 남아 있다. 원문·검토 해시 보존을 위해 이 게시 파일을 변경하지 않는다. 이 필드는 legacy이며 URL 실행 권한으로 해석하지 않는다. 앱은 현재 등록된 출처 ID/지원 ID로만 외부 대상을 결정해야 한다.

Android 실행부는 누른 순간의 세션·프로필/판본·등록 대상·실제 UX 허용을 재확인하고, handler 부재나 실행 거부를 사용자 오류로 처리해야 한다. 기존 SDK GET/callback/TTL·종료 정리·철회 정책을 바꾸지 않는다. 유료 AI 및 자유 질문 번역의 기본 보류도 유지한다.

## 검증 범위

`backend/tests/test_official_links.py`는 실제 등록 카탈로그와 명시적 provider 대역으로 다음을 검증한다: 3언어에서 동일 KR 대상 유지, canonical citation ID/action, 미지원 질문의 모델 무호출 지원 경로, 잘못된 시장/검증 상태/언어/URL/검토시각·중복 식별자 차단, raw URL target 거절, 판본·프로필 불일치와 변경된 citation 거절, 게시 legacy 보존. 외부 사이트·차량·모델을 호출하는 시험은 아니다.

검증 결과: `scripts/check_contracts.py` 통과(지원 WEBSITE 1개·기존 상태 규칙 1개·기준선 UI 177자원). `python -m pytest backend/tests -q`는 신규 40개를 포함한 **410개 통과 / 29.56초**다. 실제 전체 출력은 ignored QA의 `catalog/backend-tests-01.txt`에 보존했다. 앱의 정상 외부 실행·실제 Pleos UX 차단·복귀는 이 문서의 서버 대역 시험만으로 완료라고 계산하지 않는다.

독립 리뷰 뒤 action ID 형식 경계를 보완했다. 관련 회귀 **46개 통과**, 전체 **416개 통과 / 6.17초**, 계약 재검사 통과다. 게시 자체에는 유효한 공백·URL·129자·중간/끝 개행 source ID로도 응답이 action 계약을 지키며, 현재 3언어 공식 자료의 대상은 유지됨을 검증했다. 후속 전체 출력은 `catalog/backend-tests-02.txt`다. 초기 결과와 원본 수집 자료는 보존한다.
