# 2024 한국 판매 아이오닉 5 공식 자료 검토

검토일: 2026-11-14. 이 작업은 Mock 문구 제작이 아니라 공식 자료를 등록하고 실제 SDK 상태에 연결하는 제품 개발 단계다. 아래 검토는 CarCue 내부의 AI 보조 원문 대조와 독립된 두 번째 AI 작업의 의미 검토다. 현대자동차 승인, 인간 자동차 전문가·원어민 인증 검수를 뜻하지 않는다.

## 대상과 판본

| 항목 | 확인한 근거 |
| --- | --- |
| 모델 | 현대자동차 공식 2024 한국어 모델 카탈로그의 `modelId/projCode=NE1`, `langModelName=아이오닉 5` |
| 연식·시장·언어 | 공식 포털의 `year=2024`, `countryCode=A99`, `langCode=ko_KR` 조회와 반환된 NE1/2024/ko_KR HTML/PDF |
| HTML 문서 | `D202406100040`, 최초 게시 2024-06-10, 최종 게시 2024-07-22 |
| PDF 문서 | `D202406100039`, 포털 게시 2024-06-10, 601쪽 |
| PDF 파일 메타데이터 | 생성/수정 2024-01-11 15:44:06+09:00. 포털 게시일과 구분 |
| 내부 판본 키 | `NE1-2024-KR-ko_KR-D202406100040-20240722` |
| PDF SHA-256 | `fd7e08cf0f3ed06a8e47ddee38fcaa463f32fa375b5a7d76c0aee4e0025a6248` |

공식 공개 조회:

- [2024 모델 목록](https://ownersmanual.hyundai.com/api/v2/hmc/models?countryCode=A99&langCode=ko_KR&year=2024)
- [해당 연식의 매뉴얼 메타데이터](https://ownersmanual.hyundai.com/api/v2/hmc/model/owners-manuals?projectCode=NE1&year=2024&langCode=ko_KR&countryCode=A99)
- [한국어 HTML 매뉴얼](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/index.html)
- [한국어 PDF 매뉴얼](https://ownersmanual.hyundai.com/full_pdf/NE1/2024/ko_KR)

HTML의 공통 `rev=1.1` DITA 속성을 공식 매뉴얼 제1.1판이라고 해석하지 않았다. 모델 이미지가 최신 연식을 재사용할 수 있으므로 사진 모양을 연식 근거로 쓰지 않았다. 출처 메타데이터와 검토한 두 절의 해시는 `content/manuals/ioniq5-ne1-2024-kr.json`에 보존한다.

## 검토한 절과 안내 범위

| 공식 절 | 인쇄 / PDF 쪽 | 앱에 반영한 내용 |
| --- | --- | --- |
| [도어/테일게이트/유리창을 열고 닫을 때 조심](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id0d6d99a8d21.html) | 2-7 / 85 | 문이 움직이기 전 손·머리 등 신체의 끼임·충돌 위험 확인 |
| [클러스터 표시창 정보 > 도어, 후드, 테일게이트 열림](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/idff13cd5359c.html) | 4-21 / 167 | 모든 도어·후드·테일게이트 완전 닫힘과 계기판 경고문 AND 열림 표시 해제 확인 |

한국어 HTML 원문과 해당 PDF의 렌더링을 대조해 절 제목·경고·인쇄 쪽수를 확인했다. 인쇄 5-30 / PDF 204의 도어 경고도 보조 확인했으며, 앱의 이번 두 단계 안내에는 위 두 절만 출처로 등록했다. 원본 PDF/HTML과 매뉴얼 그림은 Git/APK에 넣지 않는다. 앱에는 CarCue가 작성한 짧은 요약과 공식 URL을 제공한다.

가이드 `ioniq5-door-open-check`는 ‘닫기 전 끼임 위험 확인 → 완전 닫힘 및 차량 경고/열림 표시 확인’ 두 단계다. 한국어 원문을 기준으로 영어·일본어 자체 요약의 부위, 부정문, 순서, 모든 문/후드/테일게이트와 두 표시의 해제를 독립 대조했다. 첫 초안의 ‘완전히’와 ‘경고문·열림 표시 모두’ 표현을 명시적으로 보강했다. 미국/일본 판매사양으로 바꾼 자료가 아니며, UI 언어 변경은 한국 판매사양을 유지한다.

본문이 단계보다 먼저 화면에 표시되는 점도 검토해, 본문 첫 문장부터 ‘신체 확인 → 닫기’ 순서로 보강했다. 검토 당시 DRAFT/UNREVIEWED였던 파일 해시와 최종 결과는 `output/qa/official-manual-review/20261114T063135Z/independent-body-order-review.json`에 있다. 앞선 `independent-final-review.json`과 이전 후보·초기 미커밋 import도 QA 폴더에 보존했다. 실제 서비스 시작/첫 콘텐츠 커밋 전에 최종 검토 파일을 CLI로 등록했다. 원문 응답·해시·조회 시각·렌더링도 같은 폴더에 보관했다. 이 증거는 원문 대조 결과이며 SDK 데이터 수신 증거와는 별개다.

## 프로필과 연결 경계

- 프로필: `ioniq5-ne1-2024-kr`, 매뉴얼 세트: `hyundai-ioniq5-ne1-2024-kr`.
- VERIFIED는 위 연식·시장·매뉴얼과 해당 안내 범위를 확인했다는 뜻이다. 사용자 선택 프로필이며 SDK가 실차 모델/VIN/장착 옵션을 자동 인증했다는 뜻은 아니다.
- 기존 `demo-ioniq5-2024-kr`, `demo-ioniq5n-2025-gb`는 UNVERIFIED 상태로 보존한다. IONIQ 5 N이나 다른 연식·시장에 이번 안내를 연결하지 않는다.
- 상태 규칙은 실제 Pleos `door.position / ROW_1_LEFT / OPEN`에만 등록한다. Capability·VALUE·수신 시각·UX 허용과 프로필/매뉴얼/언어를 앱 정책에서 다시 확인한다.
- CLOSED는 앞좌석 왼쪽 문에서 수신한 값이다. 잠금, 다른 문·후드·테일게이트, 고장 여부나 운행 안전을 판정하지 않는다. 그 항목들은 차량의 표시와 상태를 직접 확인하도록 안내한다.

등록은 `scripts/import_guides.py`의 검사와 원자적 import로 수행했다. `content/state-guide-rules.json`은 스키마·프로필/판본·게시된 언어별 안내의 관련 property까지 검사한다. 언어 카탈로그의 `guide_status=PARTIAL`은 이 프로필의 door 주제 하나만 세 언어로 제공한다는 뜻이다. 48개 후보 언어 전체 또는 다른 가이드 주제의 검수 완료를 뜻하지 않는다.

`scripts/prepare_content.py`는 이제 VERIFIED 프로필이나 PUBLISHED 문서가 있으면 쓰기 전에 중단한다. 개발 초기 데이터 생성으로 이번 검토 자료가 덮어써지는 것을 막는다.

SDK/가이드 전체 흐름 시험 결과는 `SDK_OFFICIAL_GUIDE_VALIDATION.md`와 `VALIDATION_REPORT.md`에서 기록한다.
