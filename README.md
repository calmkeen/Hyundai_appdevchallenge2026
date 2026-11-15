# CarCue · Hyundai App Development Challenge 2026

Pleos 차량용 앱 기획·개발 작업 저장소입니다.

CarCue는 낯선 차량의 상태와 사용법을 자신의 언어로 확인하는 Pleos 차량 앱입니다. 현재 Kotlin/Compose 앱과 FastAPI 서버를 개발 중이며, Mock과 실제 연동의 검증 상태를 별도로 관리합니다.

2026-11-13 인계 패키지의 최신 범위는 **차량 확인 → 언어 선택 → 현재 상태 → 관련 가이드 → AI 질문·번역 → 이용 종료**입니다. 대상은 국내외 외국인 차량 이용자이며 렌터카·관광객에 한정하지 않습니다. 이전 번호 문서는 결정 이력으로 보존했습니다.

## 실행과 현황

- [공식 사용 안내 9개 확장·검증](Docs/GUIDE_EXPANSION_VALIDATION.md) · 충전/좌석·거울/화면·표시등 각3언어, 기존 문 안내 포함12개 게시
- [1차 제출 검토용 기획서](Docs/FIRST_SUBMISSION_PLAN.md) · [제출 묶음·실행 조건·남은 범위](Docs/FIRST_SUBMISSION_PACKAGE.md)
- [실행 방법](Docs/RUNBOOK.md)
- [구현 상태 및 Mock 구분](Docs/IMPLEMENTATION_STATUS.md)
- [SDK 지원 조사](Docs/SDK_CAPABILITY_REPORT.md)
- [검증 결과](Docs/VALIDATION_REPORT.md)
- [최신 개발 순서](Docs/DEVELOPMENT_ORDER.md)
- [Git Flow 작업 규칙](Docs/05-git-flow.md) · [작업별 개발 기록](Docs/DEVELOPMENT_LOG.md)
- [백엔드·Android CI와 검증 범위](Docs/CI.md)
- [아키텍처와 점진적 개발 구조](Docs/ARCHITECTURE.md)
- [검수 가이드 등록·조회 절차](Docs/GUIDE_CONTENT_WORKFLOW.md)
- [2024 한국 아이오닉 5 공식 매뉴얼 검토](Docs/MANUAL_REVIEW_IONIQ5_2024_KR.md)
- [실제 SDK 문 상태와 공식 가이드 연결·검증](Docs/SDK_OFFICIAL_GUIDE_VALIDATION.md)
- [Console 503 복구·최신 APK 전체 재시험](Docs/PLEOS_CONSOLE_RECOVERY.md)
- [오프라인 검수 안내·종료 복구 검증](Docs/OFFLINE_SESSION_VALIDATION.md)
- [무료 로컬 AI 구성·실제 호출](Docs/LOCAL_AI_INTEGRATION.md) · [Pleos 앱 AI 연결 검증](Docs/LOCAL_AI_APP_VALIDATION.md)
- [화면 명세](Docs/SCREEN_SPEC.md) · [API 계약](Docs/DATA_API_SPEC.md) · [완료 기준](Docs/ACCEPTANCE.md)

`android/`는 네이티브 Compose 앱, `backend/`는 서버, `content/`는 프로필·언어·가이드 데이터입니다. 공식 2024 한국시장 아이오닉5 문·AC 완속 충전·좌석/일반미러·클러스터 안내를 각3언어로 게시했습니다. 문 상태만 실제 Pleos AVD SDK와 연결했으며 새 세 주제는 수동 공식 안내입니다. 유료 AI와 생성 질문 번역은 보류하고, 답변은 완전한 검토 단위 선택·번역은 저장된 검토 문자열을 사용합니다. 새9개의 실제 모델 선택과 기기 화면 시험은 미실시입니다. 기존 미검수 프로필/템플릿은 비게시로 보존합니다.

기존 제출 APK·영상·기획서·ZIP은 고정 release의 스냅샷으로 보존합니다. 구 APK는 해당 release의 backend/content와 짝으로 사용하며 최신 개발 서버와 혼용하지 않습니다. 새 가이드의 실제 HTTP 검증은 별도 서버/DB에서 수행합니다.

## 문서

- [현재 시제품과 후속 계획](Docs/FIRST_SUBMISSION_PLAN.md) · 실제 SDK·무료 AI·저장 번역과 남은 기기 시험
- [초기 통합 제품 기획안](Docs/07-product-plan.md) · 당시 사용자 시나리오, 기능 경계, 검증 계획 이력
- [기획 개요](Docs/01-product-concept.md)
- [MVP 및 기술 설계](Docs/02-mvp-and-architecture.md)
- [SDK 검증 기록](Docs/03-sdk-verification.md)
- [개발 계획과 검증 기준](Docs/04-development-plan.md)
- [Git Flow](Docs/05-git-flow.md)
- [근거와 결정 기록](Docs/06-evidence-and-decisions.md)

현재 구현·설치 상태와 제한은 SDK 검증 기록을 참고합니다. 인증 정보, SDK 바이너리, 사용자 데이터는 이 저장소에 올리지 않습니다.
