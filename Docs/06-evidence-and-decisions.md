# 근거 및 결정 기록

## 2026-11-12
- 외국인 렌터카 안내에서 차량과 함께 제공하는 다국어 경험까지 논의 범위를 확장.
- OEM 출고 사전 탑재는 장기 경로, 초기 고객과 적용 차량은 가설.
- 사용자가 QR 연결, 차종 안내, 차량 AI 채팅, 관광 추천과 방문 목록 기반 동선을 제안.
- 수동 관광 목록→내비 전달과 차량 안내를 우선 검증하는 안을 제시. 아직 최종 확정 아님.
- Gleo의 기존 매뉴얼 안내 및 내비 기능과 중복되므로 최초·유일 주장 금지.
- SDK 실물 선언은 확인했으나 런타임 성공 미검증.
- 사용자 기존 프로젝트 파일은 없었으며 LICENSE만 있던 원격을 clone. 원격 인증은 미완료.

## 공식 근거
- [심사 기준](https://appdevchallenge.auto-hmg.io/guide/judging-awards): 차량 특화성·창의성·기술 활용성·사업성. 배점 미공개.
- [제출 안내](https://appdevchallenge.auto-hmg.io/guide/submission): 필수 접수양식과 선택 산출물 구분.
- [Vehicle SDK](https://document.pleos.ai/en/docs/pleos-only/connect-sdk-pleos/Vehicle/intro)
- [Vehicle 권한](https://document.pleos.ai/en/docs/pleos-only/connect-sdk-pleos/Vehicle/vehicle-permission)
- [공식 샘플](https://github.com/Pleos-Playground/pleos-sample-vehicle-app)
- [경유지 경로 요청](https://document.pleos.ai/en/docs/pleos-only/connect-sdk-pleos/NaviHelper/route-with-waypoints)
- [SDK 신청 상태](https://document.pleos.ai/docs/pleos-only/create-my-project)
- [주행 UX 제한](https://document.pleos.ai/en/docs/pleos-only/vehicle-app-developer-guide/driving-restriction-development-guide)
- [사전 설치 앱·CCP](https://document.pleos.ai/en/docs/pleos-only/vehicle-app-developer-guide/ccp-rotary-controller-development)
- [Gleo 공식 발표](https://www.hyundai.com/worldwide/en/newsroom/detail/0000001168)
- [TourAPI 공식 포털](https://api.visitkorea.or.kr/): 외국어 데이터 이용 후보. 엔드포인트·키·약관·캐시·호출 제한은 별도 검증.

자료의 존재가 앱의 실제 동작, 데이터 이용권 확보, 제휴 또는 제품 효과 검증을 뜻하지 않는다.

## 기획 기준안 보강
- 관광 목록과 다국어 차량 안내를 하나의 첫 탑승 경험으로 연결하는 [통합 기획안](07-product-plan.md)을 추가했다.
- QR 안내 링크와 인증 페어링, 수동 목록 정렬과 최적화, SDK 선언과 실행 증거를 명시적으로 분리했다.
- 3~5명 비교 과제는 앞으로 수행할 검증 계획이며 참가자 확보·테스트 결과가 아니다.
- 사용자 설치 작업은 건드리지 않았으며 SDK 실행 상태의 새로운 성공 기록은 없다.

## 사용자 방향 전환: 차량 이용 가이드 중심
- 최신 지시에 따라 여행 중심 표현을 수정했다. 첫 일회 안내 뒤 필요할 때 자신의 언어로 상태별 확인하고 현지 직원 도움으로 이어지는 흐름이 중심이다.
- 관광·일정은 부가 기능으로 낮췄다. 직원 반복 설명 시간 절감은 검증 전 가설이다.
- [신규 공식 공지](https://appdevchallenge.auto-hmg.io/notice/c0a1a000-2026-4923-8000-000000000008)의 공개 TTS/STT/FusedLocation 개발 시험 가능, LLM SDK·Gleo interface 미제공, 차량 마이크 외부 STT 금지를 반영했다. 실행 성공을 뜻하지 않는다.
- 앞선 관광 중심 기록은 당시 검토 이력이며 현재 우선순위는 이 항목과 최신 제품 기획안을 따른다.
