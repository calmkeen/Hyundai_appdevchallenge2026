# CarCue 데이터와 API 계약

이 문서의 `/v1` 경로, 내부 모델, 상태 enum은 CarCue가 구현할 애플리케이션 계약이다. Pleos가 제공하는 API 경로나 이미 실행 중인 서버를 뜻하지 않는다. `contracts/`의 JSON Schema는 데이터 검증용이며 서버 코드를 대신하지 않는다.

## 1 설계 원칙

차량 원시값은 차량 앱에서 읽는다. 서버는 등록된 차량 프로필과 공식 자료를 관리하고 AI 질문·번역을 처리한다. 서버가 SDK 값을 직접 읽거나 휴대폰이 Vehicle SDK를 호출하는 구조로 만들지 않는다.

모든 시각은 ISO 8601 UTC를 사용하고 화면에서는 사용자 언어·시간대로 표시한다. 언어는 BCP 47, 판매지역은 ISO 3166 국가 코드 등 일관된 코드로 관리한다. 식별자는 불투명한 문자열로 사용하고 VIN을 ID에 포함하지 않는다.

## 2 주요 모델

### VehicleProfile

| 필드 | 의미 |
| --- | --- |
| profile_id | 운영자가 등록한 프로필 ID |
| manufacturer, model_code, display_name | 제조사, 정확한 모델 코드와 사용자 이름 |
| model_year, market_code | 연식과 판매지역 |
| powertrain | BEV, ICE, HEV 등 명시한 동력 종류 |
| option_codes | 확인된 옵션 목록 |
| steering_position | LEFT, RIGHT, UNKNOWN. SDK 영역을 운전석으로 오해하지 않기 위한 사양 |
| manual_set_id, manual_version | 적용할 공식 자료 묶음과 버전 |
| verification_status | UNVERIFIED 또는 VERIFIED |
| support_contacts | 해당 사양·시장에 등록된 공식 지원 정보 |

확인되지 않은 기본 프로필을 실제 차량 프로필로 게시하지 않는다. 언어는 이 모델에 고정하지 않는다. 지원 연락처가 없으면 임의 번호 대신 등록된 공식 사이트만 표시하거나 비활성화한다.

### VehicleReading

한 API의 한 영역에 대한 상태다. 배터리 전체 상태와 특정 문 상태를 같은 원시 구조로 억지로 표현하지 말고 정규화된 값과 raw 값을 구분한다.

| 필드 | 의미 |
| --- | --- |
| property_id | 앱 내부 속성 이름. 예 `door.position`, `ev.battery_soc`, `fuel.percent`, `tire.low_pressure`, `safety.telltales` |
| area_id, area_label | 실제 지원되는 물리 영역과 표시 이름. 영역이 없으면 null |
| capability_status | UNKNOWN, SUPPORTED, UNSUPPORTED, CHECK_FAILED |
| read_status | NOT_REQUESTED, LOADING, VALUE, UNAVAILABLE, ERROR, STALE |
| value | 검증된 정규화 값. 없으면 null |
| unit | 검증된 값 단위. 없거나 불명확하면 null |
| raw_value | 디버그·어댑터 검증용 값. 기본적으로 AI에 보내지 않음 |
| received_at | 마지막 성공 수신 시각. 없으면 null |
| vehicle_sampled_at | SDK가 별도로 제공하는 실제 측정 시각. 없으면 null |
| checked_at | 마지막 조회를 시도한 시각 |
| error_code | 실패 정보. 사용자 문구와 분리 |
| source | PLEOS 또는 MOCK |

`VALUE`는 값이 실제로 있고 확인된 범위·단위로 정규화됐을 때만 사용한다. `UNAVAILABLE` 값은 null이다. bool의 false와 값이 없다는 뜻의 null을 혼동하지 않는다. 정규화에 실패한 코드는 임의 정상값으로 바꾸지 않는다.

현재 상태의 `read_status`가 VALUE가 아닌 경우 이 계약의 `value`는 null로 둔다. 현재 상태와 이전 성공값을 둘 다 표시해야 하면 이전 성공값은 별도 필드나 이력으로 둔다. 현재 상태의 value에 오래된 값을 넣고 VALUE라고 표시하지 않는다.

### VehicleSnapshot

`profile_id`, `source`, `created_at`, `readings[]`를 가진다. 한 카드가 성공해도 다른 카드의 값이 정상이라는 뜻이 아니다. 프로필 변경 시 기존 스냅샷을 무효화한다.

서버 전송용 스냅샷은 질문에 필요한 속성·영역·정규화 값·수신 시각만 추린다. 원시값, VIN, 위치, 사용자 식별자와 디버그 오류 전문은 기본 전송하지 않는다.

### Guide와 GuideStep

Guide에는 ID, 프로필 적용 범위, 주제, 제목, 본문, 언어, 원문 언어, 단계, 출처와 페이지·절, 버전, 번역 검수 상태가 필요하다. ‘판매지역이 같음’만으로 연식·옵션이 다른 자료를 섞지 않는다.

GuideStep에는 단계 ID, 순서, 짧은 제목과 설명, 필요한 이미지, 공식 주의 문구, 관련 상태 속성, 허용된 다음 동작이 들어간다. 출처 위치를 기록하지 못한 조작 절차는 검수 완료로 게시하지 않는다.

원본과 번역은 `guide_id + source_version + locale + glossary_version`으로 구분한다. 원본 버전이 바뀌면 번역의 재검토 여부를 표시한다. 이미지의 원 출처와 사용 조건도 콘텐츠 레코드에 남긴다.

### GuidanceRule

규칙은 `rule_id`, 적용 프로필, 속성, 물리 영역, 검증된 조건, 연결할 가이드·단계, 표시 문구와 공식 심각도 정보를 가진다. 조건 판정과 심각도는 서버의 생성 답변이 아니라 검수된 설정으로 관리한다.

예시 구조는 다음과 같다. `OPEN`은 앱의 정규화 값이며 SDK가 이 문자열을 돌려준다는 뜻이 아니다.

```json
{
  "rule_id": "door_open_front_left",
  "profile_id": "demo_profile",
  "property_id": "door.position",
  "area_id": "ROW_1_LEFT",
  "operator": "EQ",
  "expected_value": "OPEN",
  "guide_id": "registered_door_guide",
  "step_id": "check_door_location"
}
```

### LocaleEntry

`locale`, 표시 이름, native name, RTL 여부, UI 문자열 상태, 가이드 번역 상태를 관리한다. 국가별 언어 매핑은 별도 목록이다. 계약의 예제 언어가 전체 지원 언어 목록은 아니다.

### Session

임시 `session_id`, 서버용 불투명 token, 프로필, 선택 언어, 생성·만료 시각과 종료 상태를 관리한다. token에는 차량 SDK 접근권이나 차량 제어권이 없다. 서버의 세션과 앱의 SDK 연결 생명주기를 분리한다.

## 3 API 공통 규칙

- HTTPS를 기본으로 하고 개발용 로컬 HTTP는 debug 환경에서만 허용한다.
- AI·번역·대화 API는 세션 소유를 검사한다. 프로필 ID만 알면 다른 대화를 읽을 수 있게 하지 않는다.
- `X-Request-Id`를 사용하고 질문 중복 처리는 세션과 요청 ID 기준으로 한다.
- 지원하지 않는 언어·프로필은 명확히 거부하거나 대체 선택을 요청한다.
- 외부 API 키, 프롬프트 전문, 내부 예외를 클라이언트 오류에 노출하지 않는다.
- 질문·번역 길이, 출력 길이, 세션별·전체 요청 한도와 제한된 재시도를 설정한다.
- 로컬 개발의 무인증 Mock 서버와 실제 서버의 인증 경로를 구분한다. 배포 시 debug 우회가 남아 있으면 완료가 아니다.

## 4 엔드포인트

| 메서드 | 경로 | 용도 |
| --- | --- | --- |
| GET | `/health` | 프로세스 상태 확인. provider 세부 비밀정보 제외 |
| GET | `/v1/vehicle-profiles` | 공개 가능한 프로필 목록 |
| GET | `/v1/vehicle-profiles/{profile_id}` | 정확한 프로필과 문서 버전 |
| GET | `/v1/locales` | UI·콘텐츠별 지원 상태 포함 언어 목록 |
| GET | `/v1/guides?profile_id=&locale=&topic=&q=` | 해당 차량의 가이드 목록·검색 |
| GET | `/v1/guides/{guide_id}?profile_id=&locale=` | 원문·단계·출처·번역 상태 포함 상세 |
| POST | `/v1/sessions` | 익명 이용 세션과 만료 시각 발급 |
| POST | `/v1/ask` | 차종 자료를 검색한 후 질문에 답변 |
| POST | `/v1/translate` | 텍스트 번역과 원문·검토 상태 반환 |
| DELETE | `/v1/sessions/{session_id}` | 해당 세션의 대화·번역 임시 내용 삭제 |

QR 딥링크는 초기에는 `carcue://guide?profile_id=<등록된 ID>`처럼 안내 프로필만 지정한다. public 웹 App Link 도메인은 실제 도메인이 결정된 뒤 별도로 설정한다. 예제 스킴은 프로젝트 설계안이다. 임의 URL을 서버가 다운로드하도록 만들지 않는다.

## 5 질문 요청

```json
{
  "request_id": "client-generated-uuid",
  "session_id": "opaque-session-id",
  "profile_id": "registered-profile-id",
  "locale": "ko-KR",
  "question": "왼쪽 앞문이 열려 있다고 나와요. 어디서 확인하나요?",
  "guide_context": {"guide_id": null, "step_id": null},
  "vehicle_context": [
    {
      "property_id": "door.position",
      "area_id": "ROW_1_LEFT",
      "value": "OPEN",
      "read_status": "VALUE",
      "received_at": "2026-11-13T00:00:00Z",
      "source": "MOCK"
    }
  ]
}
```

위 시간과 값은 계약을 설명하기 위한 Mock 데이터다. 운영 요청에는 앱이 받은 실제 값과 실제 수신 시각을 넣는다. 서버는 세션의 프로필과 요청의 프로필이 다르면 거부한다. 다른 차량 자료로 답하기 위해 프로필을 몰래 변경하지 않는다.

`vehicle_context`는 참고 정보이며 센서 자체의 무결성을 보증하는 값이 아니다. 최종 조치 문구는 해당 차량의 검수된 자료에서 가져온다. Mock 출처 요청은 실제 연동 응답으로 보고하지 않는다.

## 6 질문 응답

다음은 자료가 없을 때의 응답이다. 모든 질문에 답을 만들어내지 않는다.

```json
{
  "request_id": "client-generated-uuid",
  "status": "NO_RELIABLE_SOURCE",
  "locale": "ko-KR",
  "answer": "이 차량에 맞는 설명을 아직 확인하지 못했어요. 차량 정보를 다시 확인하거나 공식 매뉴얼을 살펴봐 주세요.",
  "citations": [],
  "follow_up_question": null,
  "actions": [{"kind": "SELECT_PROFILE", "target_id": null}],
  "mode": "MOCK"
}
```

응답 상태는 다음과 같다.

- `ANSWERED`: 해당 차량의 자료로 설명할 수 있고 서버가 출처를 확인했다.
- `NEED_MORE_INFO`: 차량이나 질문의 정보가 부족해 사용자 확인이 필요하다.
- `NO_RELIABLE_SOURCE`: 해당 차량에 맞는 자료가 없다.
- `TEMPORARILY_UNAVAILABLE`: 연결·provider·서버 문제로 지금 처리할 수 없다.

`ANSWERED`이면 citations가 하나 이상 있어야 하고, 각 출처의 profile/manual/source version이 이번 검색 결과와 일치해야 한다. citations의 이름·URL·절 정보는 모델이 임의로 채우는 대신 서버의 자료 레코드에서 구성한다.

허용하는 actions는 `OPEN_GUIDE`, `OPEN_MANUAL`, `REFRESH_STATUS`, `OPEN_SUPPORT`, `SELECT_PROFILE`다. 각각 등록된 가이드·매뉴얼·상태·지원 정보만 가리킬 수 있다. 임의 URL, 코드 실행, `SET_DOOR` 같은 제어 행동은 허용하지 않는다.

`mode=LIVE`는 실제 서버 처리 경로라는 뜻이며 차량 상태까지 실제 수신됐다는 보증이 아니다. 실제 차량 상태의 출처는 각 VehicleReading의 `source`로 별도 판정한다.

모델 출력과 최종 서버 응답을 구분한다. 요청 ID, 모드, 실제 출처 메타데이터와 허용 행동은 서버에서 확인·조립한다. JSON Schema 통과 후에도 의미와 출처를 검증해야 한다.

## 7 번역 요청과 응답

요청은 `request_id`, `session_id`, `profile_id`, `source_locale` 또는 자동 감지, `target_locale`, `text`, `content_kind`, 선택적 `guide_id`를 가진다. `content_kind`는 QUESTION, ANSWER, GUIDE 등이다.

응답은 원문, 감지 또는 확정 언어, 대상 언어, 번역문, 적용 용어집 버전, 검토 상태와 모드를 반환한다. 정적 가이드는 저장된 검수 번역을 우선한다. 새 생성 번역은 검수 완료로 반환하지 않는다.

단위·부정·금지·조작 순서가 바뀌는지 점검하고 실패하면 번역을 ‘정확함’으로 표시하지 않는다. 재번역 또는 원문·다른 언어 선택으로 안내한다. 역번역만 통과했다고 안전한 조작 번역으로 확정하지 않는다.

## 8 오류와 오프라인

| 상황 | 처리 |
| --- | --- |
| 400/422 입력 오류 | 잘못된 필드를 수정하도록 요청. provider 재시도 금지 |
| 401/403 세션 오류 | 세션 재시작 또는 권한 확인. 다른 세션으로 자동 대체 금지 |
| 404 프로필·가이드 없음 | 차량 다시 선택 또는 등록된 원문 안내 |
| 409 프로필·버전 충돌 | 최신 프로필·가이드 확인 후 사용자 맥락 유지 |
| 429 요청 한도 | 재시도 가능 시간 표시. 무한 재전송 금지 |
| 502/503/504 AI 처리 실패 | 현재 실패 표시와 저장 가이드 제공. 제한된 재시도 |
| SDK 미수신 | 인터넷 실패와 별도로 표시. 정상·0으로 대체 금지 |

AI 답변이 진행 중일 때 세션이 끝나면 취소하거나 결과를 버린다. 네트워크가 복구돼도 종료한 세션의 이전 질문을 자동 재전송하지 않는다.

## 9 저장과 캐시

정적 가이드는 프로필·버전·언어별로 저장하고 원본 변경 시 갱신한다. 초기에는 검수한 기본 가이드 묶음을 앱과 함께 제공할 수 있다. 원문 URL을 열어야만 안내를 볼 수 있게 만들지 않는다.

AI 답변 캐시는 질문·차량 프로필·매뉴얼 버전·언어가 같아야 재사용한다. 차량 상태가 포함된 답변을 다른 상태나 다른 이용 세션에 그대로 보여주지 않는다. 초기에는 개인 질문 답변 캐시를 생략하고 정적 번역 캐시만 구현해도 된다.

대화의 기본 보관 시간은 짧게 설정하고 서버와 앱에서 공유한다. 구현 기본안으로 세션 만료 120분을 제안하며, 제품 정책이 달라지면 설정과 사용자 설명을 함께 바꾼다. 이 값은 Pleos 규정이나 확정된 보관 정책이 아니다.

## 10 제공한 계약 파일

`contracts/vehicle-snapshot.schema.json`, `ask-response.schema.json`, `guide.schema.json`은 필드 구조를 고정하기 위한 출발점이다. OpenAI Structured Outputs로 그대로 보내기 전에 사용할 모델이 지원하는 Schema 범위를 확인하고 모델용 출력 Schema를 별도로 만든다. 앱·서버 계약을 단순화하려고 검증 조건을 삭제하지 않는다.

`vehicle-snapshot.mock.json`은 Mock 출처를 명시한 상태 예제이고 `ask-response.mock.json`은 자료 부족 응답 예제다. `guide.template.json`은 검수 전 템플릿이며 실제 조작 가이드로 노출하면 안 된다.
