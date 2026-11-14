# 검수 가이드 등록과 조회

2026-11-14. `feature/reviewed-guide-import`에서 추가한 도구다. 실제 차량 매뉴얼을 확보하거나 내용 검수를 완료한 작업은 아니다. 현재 기본 프로필은 UNVERIFIED이며 기본 가이드는 DRAFT다.

## 검사와 등록

저장소 루트에서 서버 의존성이 설치된 Python을 사용한다.

```bash
# 현재 content/guides 전체 검사 (DRAFT도 구조를 검사)
.venv/bin/python scripts/import_guides.py check

# 편집자가 준비한 파일을 쓰기 없이 검사
.venv/bin/python scripts/import_guides.py check /absolute/path/reviewed-guide.json --json

# 기존 파일을 덮어쓰지 않고 단일 레코드 등록
.venv/bin/python scripts/import_guides.py import /absolute/path/reviewed-guide.json
```

`--content-root /absolute/path/content`로 별도 카탈로그를 지정할 수 있다. 그 아래 `profiles/catalog.json`, `locales/catalog.json`이 필요하며 저장 대상은 `guides/`다. JSON 결과에는 status와 file/code/path/message 진단이 들어간다. path는 JSON Pointer다. 종료 코드는 성공 0, 정책/중복/내용 충돌 1, 입력/카탈로그/쓰기 오류 2다. 카탈로그에 이미 문제가 있으면 가져오기 전에 수정해야 한다.

등록 파일명은 레코드 식별자의 SHA-256으로 결정한다. 입력 파일명이나 guide_id를 경로로 사용하지 않는다. 같은 식별자와 같은 JSON 내용의 재등록은 `UNCHANGED`, 같은 식별자의 다른 내용은 `RECORD_CONFLICT`다. 원문 버전·번역을 구분하는 식별자는 다음 조합이다.

```text
(guide_id, locale, manual_set_id, source_version)
```

guide_id가 같아도 언어/매뉴얼 버전이 다르면 별도 레코드다. 현 API에는 같은 조합의 번역 교정판을 구분하는 revision 필드가 없으므로 이를 몰래 덮어쓰지 않는다. 교정판 관리가 필요하면 계약 확장을 별도 feature로 진행한다. 기존 자료의 철회/교체는 검토한 콘텐츠 변경 커밋으로 수행한다.

파일을 같은 디렉터리의 임시 파일에 기록·fsync한 뒤 hard link로 완성된 파일을 한 번에 공개한다. 기존 경로를 덮어쓰지 않으며 실패 시 임시 파일을 정리한다. 이 방식이 지원되지 않는 파일시스템에서는 쓰기 오류로 끝난다. 실행 중인 서버 Catalog는 시작할 때 파일을 읽으므로 콘텐츠 반영 후 개발 서버를 재시작해야 한다. 실서비스 자동 배포/재시작은 이번 기능에 포함하지 않는다.

## 게시 기준

모든 파일은 JSON Schema를 통과해야 한다. PLANNED/DRAFT/REVIEWED는 구조가 맞아도 앱에 게시되지 않는다. PUBLISHED에는 다음을 추가로 요구한다.

- 등록된 VERIFIED 프로필, 정확히 일치하는 매뉴얼 세트와 버전.
- 등록된 표시 언어와 원문 언어, 비어 있지 않은 제목·본문·주제·식별자.
- VERIFIED 출처와 일치하는 버전/절, 정상 HTTPS 호스트. URL 안의 계정·비밀번호, 제어 문자, 잘못된 포트는 거절.
- 번역은 REVIEWED와 glossary_version 필수. 원문도 UNREVIEWED 상태이면 게시 불가.
- 출처/단계 식별자 중복 금지, 단계는 배열 순서대로 1부터 연속. 존재하는 단계는 유효한 출처를 하나 이상 참조해야 함.
- 동일한 게시 레코드 식별자가 두 개 이상이면 조회에서 모두 제외.

단계가 없는 본문형 안내는 현재 계약대로 허용한다. URL 형식 검사와 VERIFIED 표시는 공식 발행자·저작권·차량 적합성·번역 의미를 외부에서 확인했다는 뜻이 아니다. 담당자가 원문, 차종·연식·시장·옵션, 이용 조건, 표현·부정·숫자·단위를 실제로 검수해야 한다. CLI는 이러한 상태를 자동 변경하지 않고 URL도 내려받지 않는다.

등록 시와 서버 조회 시 같은 `backend/app/guide_policy.py`를 사용한다. 잘못된 게시 자료는 `/v1/guides`와 개별 조회에서 제외되며 내부 `Catalog.publication_issues`로 원인을 확인할 수 있다. 검증 오류를 공개 앱 응답에 문서 원문과 함께 유출하는 관리 API는 추가하지 않았다.

## 검증 자료와 실제 자료 구분

테스트의 VERIFIED 프로필·`example.test` 출처·본문은 임시 디렉터리와 테스트 메모리에만 존재한다. 실차 매뉴얼·공식 출처의 진위를 보증하지 않으며 기본 `content/`에 등록하지 않는다. 기본 카탈로그 검사 통과는 미검수 DRAFT 구조가 맞다는 뜻이며 게시 가능한 가이드가 있다는 뜻은 아니다.

후속 순서는 `ARCHITECTURE.md`와 `DEVELOPMENT_ORDER.md`를 따른다. 실제 문 상태에 맞춘 안내 규칙은 검수된 해당 차량 자료가 들어온 후 연결한다.
