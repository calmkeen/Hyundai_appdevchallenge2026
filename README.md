# CarCue · Hyundai App Development Challenge 2026

Pleos 차량용 앱 기획·개발 작업 저장소입니다.

CarCue는 낯선 차량의 상태와 사용법을 자신의 언어로 확인하는 Pleos 차량 앱입니다. 현재 Kotlin/Compose 앱과 FastAPI 서버를 개발 중이며, Mock과 실제 연동의 검증 상태를 별도로 관리합니다.

2026-11-13 인계 패키지의 최신 범위는 **차량 확인 → 언어 선택 → 현재 상태 → 관련 가이드 → AI 질문·번역 → 이용 종료**입니다. 대상은 국내외 외국인 차량 이용자이며 렌터카·관광객에 한정하지 않습니다. 이전 번호 문서는 결정 이력으로 보존했습니다.

## 실행과 현황

- [실행 방법](Docs/RUNBOOK.md)
- [구현 상태 및 Mock 구분](Docs/IMPLEMENTATION_STATUS.md)
- [SDK 지원 조사](Docs/SDK_CAPABILITY_REPORT.md)
- [검증 결과](Docs/VALIDATION_REPORT.md)
- [최신 개발 순서](Docs/DEVELOPMENT_ORDER.md)
- [화면 명세](Docs/SCREEN_SPEC.md) · [API 계약](Docs/DATA_API_SPEC.md) · [완료 기준](Docs/ACCEPTANCE.md)

`android/`는 네이티브 Compose 앱, `backend/`는 서버, `content/`는 프로필·언어·가이드 데이터입니다. 기본 카탈로그는 미검수 개발 프로필이며 공개 가능한 차량 매뉴얼은 아직 없습니다. `contracts/guide.template.json`은 게시하지 않습니다. OpenAI 키는 서버 환경변수에만 설정합니다.

## 문서
- [통합 제품 기획안](Docs/07-product-plan.md) · 사용자 시나리오, 기능 경계, 검증 계획
- [기획 개요](Docs/01-product-concept.md)
- [MVP 및 기술 설계](Docs/02-mvp-and-architecture.md)
- [SDK 검증 기록](Docs/03-sdk-verification.md)
- [개발 계획과 검증 기준](Docs/04-development-plan.md)
- [Git Flow](Docs/05-git-flow.md)
- [근거와 결정 기록](Docs/06-evidence-and-decisions.md)

현재 구현·설치 상태와 제한은 SDK 검증 기록을 참고합니다. 인증 정보, SDK 바이너리, 사용자 데이터는 이 저장소에 올리지 않습니다.
