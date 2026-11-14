# CarCue 개발 인계 패키지

외국인이 지금 이용하는 차량의 상태와 사용법을 익숙한 언어로 이해하도록 돕는 Pleos 차량 앱의 개발 작업 지시서입니다. 최신 기획, 화면 동작, 데이터 구조, 구현 순서와 완료 기준을 한곳에 모았습니다.

## 전달 방법

새 개발 채팅에 이 ZIP을 첨부하고 `START_HERE.md`의 지시문으로 작업을 시작하세요. 기존 Git 저장소를 확인한 뒤 문서를 `Docs/`에 보관하고 구현합니다. 이 자료 자체는 실행 가능한 앱이나 실제 연동 성공 증거가 아닙니다.

## 파일 안내

| 경로 | 용도 |
| --- | --- |
| `START_HERE.md` | 새 개발 세션에 전달할 지시문 |
| `Docs/DEVELOPMENT_ORDER.md` | 제품 목표·개발 범위·구조·SDK·AI·다국어·Git·단계별 납품 |
| `Docs/SCREEN_SPEC.md` | 화면 S01~S11의 동작과 예외 상태 |
| `Docs/DATA_API_SPEC.md` | 내부 모델·백엔드 API·출처·세션·오류 계약 |
| `Docs/ACCEPTANCE.md` | 실제 연동과 제품 흐름의 완료 판정 |
| `contracts/` | JSON Schema와 MOCK·검수 전 템플릿 |
| `design-tokens.json` | 흰색·파란색 색상과 디자인 기준 |
| `assets/ui/` | 제안서용 UI SVG. 앱에서는 내용만 네이티브로 재구현 |
| `assets/icons/` | Lucide 아이콘과 사용권 |
| `reference/carcue_vehicle_support.pdf` | 기존 최신 제안서 원본. 이번 작업에서 변경하지 않음 |
| `reference/SOURCES.json` | 제안서·이미지 출처 |
| `SHA256SUMS.txt` | 패키지 파일 무결성 확인 |

차량 제어, 모바일 차량 인증 연결, 여행 추천, 마스코트 확정은 초기 핵심 구현에 포함하지 않습니다. QR은 등록된 안내 프로필을 여는 용도이며 차량 상태 접근권을 부여하지 않습니다.

Schema 통과는 데이터 구조 검증입니다. 실제 SDK 지원, 매뉴얼 출처의 적합성, AI 답변의 정확성을 증명하지 않습니다. JSON의 MOCK 값과 DRAFT 가이드를 실제 차량 정보·검수 완료 콘텐츠로 게시하지 마세요.
