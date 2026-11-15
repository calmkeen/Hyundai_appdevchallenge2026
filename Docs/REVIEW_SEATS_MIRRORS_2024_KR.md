# 2024 KR IONIQ 5 좌석·미러 안내 검토

작성일: 2026-11-15. **PUBLISHED / 독립 AI 보조 의미 검토 통과**. 이 문서는 CarCue 자체 요약과 번역 초안의 원문 대조 기록이다. 현대자동차 승인이나 인간 자동차 전문가·원어민 인증 검수를 뜻하지 않는다. 기존 도어 가이드·출시 APK·영상·기획서·제출 ZIP은 변경하지 않는다.

## 대상과 판본

- 프로필: `ioniq5-ne1-2024-kr` (사용자 선택, 실차/VIN 자동 인증 아님).
- 매뉴얼 세트: `hyundai-ioniq5-ne1-2024-kr`.
- 판본: `NE1-2024-KR-ko_KR-D202406100040-20240722`.
- 공식 HTML 문서 `D202406100040`, 최종 게시 2024-07-22. 공식 포털 메타데이터를 이번 조사에서도 조회했다.
- 기존 공식 한국어 PDF: 601쪽, SHA256 `fd7e08cf0f3ed06a8e47ddee38fcaa463f32fa375b5a7d76c0aee4e0025a6248`.
- 영어·일본어는 한국 판매사양의 한국어 원문을 요약한 CarCue 번역이다. 미국/일본 판매사양으로 바꾸지 않으며 L=운전석, R=동승석의 원문 관계를 유지한다.

## 출처와 수집 경로

로컬 Firecrawl을 기본으로 조사했다. 이 작업자에게는 로컬 MCP 도구가 노출되지 않았고 직접 readiness `127.0.0.1:3002` 접속은 거절됐다. 부모 작업이 실제 `firecrawl_local` MCP로 공식 본문을 HTTP 200 수집해 공유했다. Cloud 플러그인은 호출하지 않았다. 내장 웹의 직접 URL 읽기도 실패했으며 이를 수집 성공으로 기록하지 않는다.

공식 HTML 본문과 같은 판본 PDF의 경고·그림·인쇄 쪽수를 대조한다. 원본 HTML/PDF와 그림은 가이드 JSON이나 APK에 포함하지 않는다. 가이드에는 자체 요약과 공식 절 URL만 등록한다.

| 공식 절 | 인쇄 / PDF 쪽 | 연결하는 내용 |
|---|---|---|
| [올바른 운전 자세](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/idb26b9ae7995.html) | 2-3 / 81 | 브레이크 끝까지 밟을 때 무릎, 스티어링 휠과 손목, 귀 상단과 헤드레스트 기준 |
| [좌석](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id81db5616e14.html) | 3-2~3-5 / 92~95 | 사양 차이, 주행 중 조절 금지, 고정·끼임·페달 방해·탑승자·벨트와 등받이 자세 |
| [앞좌석](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/idf49da880ae1.html) | 3-6~3-13 / 96~103 | 수동·전동 전후/등받이 조절, 스위치·배터리 주의, 헤드레스트 위치와 끼임·간섭 |
| [실내 미러](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id38ef2ccc415.html) | 5-43 / 217 | 뒤 유리 시야, 시야 방해·개조 금지, 주야 전환/ECM의 조건부 차이 |
| [실외 미러](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id754c73d5e23.html) | 5-44~5-45 / 218~219 | 볼록거울 거리, ACC/ON·L/R·스위치, 주행 중 조절/접기 금지, 빙결·모터·접이 주의 |

[좌석, 스티어링 휠, 미러 조정](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id3914bac8fab.html)도 인쇄 2-3/PDF81에서 보조 대조했다. 같은 PDF 쪽의 ‘올바른 운전 자세’와 서로 다른 HTML 절이므로 무릎·손목 문장을 이 절 URL에 잘못 귀속시키지 않는다. 가이드의 출처 5개 한도를 유지하기 위해 주행 중 금지는 좌석/실외 미러 절로도 지지한다.

조사 증거는 저장소 루트의 `output/qa/guide-expansion-20261115/research/`에 있다. `seat-adjustment`, `seats`, `front-seats`, `inside-mirror`, `outside-mirror`의 JSON은 raw HTML·수집 메타데이터, MD는 TOC를 제외한 본문이다. 자세 절은 로컬 MCP Transport closed 및 내장 웹 실패 후, 부모 작업의 certifi 인증서 검증 직접 HTTPS GET 200으로 수집했다(`driving-posture-direct.html` / `driving-posture-direct.json`). 원본 PDF와 PNG의 SHA는 `output/qa/guide-expansion-20261115/seats-mirrors/pdf-pages/manifest.json`에 보존한다.

## 안내의 범위

가이드 ID는 `ioniq5-seat-mirror-before-driving`, 주제는 `seats_mirrors`다. 주행 전 안전한 곳에 정차한 상태에서 운전석 기본 자세와 일반 실내/실외 미러를 확인하는 다섯 단계다.

1. 정차하고 좌석 이동 범위·발 주변·뒷좌석 탑승자 확인.
2. 실제 장착된 수동/전동 장치로 앞뒤·등받이를 조절하고 고정 확인.
3. 운전 자세·헤드레스트·벨트 위치 확인.
4. 일반 실내 미러 시야와 주야 전환식/ECM의 조건부 차이 확인.
5. 일반 실외 미러의 각도·접이 버튼·실거리 차이 확인.

실차의 옵션을 SDK로 식별하지 않는다. DSM·DCM, 메모리·릴렉션 컴포트·전좌석 메모리·후진 자동 각도, 뒷좌석/다리받침대/열선·통풍, 청소·가죽 관리, 헤드레스트 분리·재장착은 이번 기본 조작 설명에 포함하지 않는다. 해당 기능이 있으면 전용 원문을 확인하도록 명시한다. 일반 미러 조작을 DSM/DCM에 그대로 적용하지 않는다. 높낮이·허리 지지대 등 추가 조절의 상세 스위치 동작도 원문을 우선한다.

주차 브레이크 해제, 스티어링 휠 조절, 출발·차선 변경의 전체 절차를 가르치는 안내가 아니다. 앱은 좌석 고정·미러 위치·사각지대 센서를 읽지 않으며 안전/정상 판정이나 차량 조작을 하지 않는다. 이 제품 한계는 본문에 두고 ‘공식 주의문’에 임의의 센서 주장을 섞지 않는다.

## 주의문 보존 확인표

| 구분 | 초안에 보존한 의미 |
|---|---|
| 조작 시점 | 주행 중 좌석/미러 조절 및 미러 접기 금지. 정차 → 조절 순서 |
| 손·발·주변 사람 | 좌석 밑/가동부의 손 끼임, 레일/고정장치 접촉, 뒷좌석과 어린이, 헤드레스트 폴 가이드 손가락 끼임 |
| 물건·페달·화재 | 바닥/발 주변 물건의 페달 방해와 이동 상해, 기계장치 틈에 손 넣기 금지, 라이터 가스·화재 |
| 고정·모터 | 수동 레버 복귀·좌석/등받이 고정, 전동 과도한 힘/동시 조작 금지·조절 뒤 손 떼기·시동 OFF 배터리, 허리 지지대 한계 |
| 자세·벨트·에어백 | 똑바로 깊숙이 앉기, 어깨띠/골반띠, 과도한 젖힘/접힌 좌석/방석 미끄러짐 위험, 조작 가능한 범위의 에어백 거리 |
| 헤드레스트 | 귀 상단 기준·머리와 거리, 제거한 채 주행/주행 중 조절 금지·액세서리 금지, 앞쪽 좌석/등받이와 선바이저 등 간섭 |
| 실내 시야 | 높게 쌓인 물건·앞으로 튐, 개조/와이드 미러/임의 탈착 금지, 야간 위치 선명도 저하, ECM 센서 차단 금지 |
| 실외 거리·조절 | 볼록거울의 물체는 보이는 것보다 훨씬 가까움, 실내 미러로 뒤차 실제 거리 확인, L/R·ACC/ON·손조절 금지 |
| 빙결·접이 | 얼음 긁기/억지조작 금지·해빙 방법, 최대각도 이후 모터 작동, 접이 버튼 사용·손접기 금지·과도한 OFF 접이의 배터리 |

다섯 단계의 모든 본문과 21개 주의문을 하나의 등록 단위로 검토한다. 영어 길이를 줄일 때 중복 금지문 한 항목을 다른 단계의 같은 명시적 금지문으로 합쳤고, 나머지 주의 의미를 삭제하지 않았다. 독립된 두 번째 작업자의 최종 의미 대조를 통과했다.

## 초안 상태와 검증 경계

신규 파일은 `content/drafts/ioniq5-seat-mirror-before-driving/{ko-KR,en,ja-JP}.json`이다. 대조 원본은 `lifecycle=DRAFT`, 한국어 `translation_review_status=NOT_APPLICABLE`, 영어/일본어 `UNREVIEWED`로 보존한다. 독립 대조를 통과한 별도 사본만 PUBLISHED 및 번역 REVIEWED 상태로 등록했다. source 5개는 실제 HTML/PDF 근거 대조에 따라 VERIFIED로 기록했으며, 이는 번역의 독립 검토·게시 승인과 별개다.

- `related_properties=[]`: 좌석·미러 센서가 연결됐다고 표시하지 않는다.
- action은 등록된 공식 절의 `OPEN_MANUAL`뿐이며 SDK 읽기/SET/시나리오를 추가하지 않았다.
- source는 같은 한국어 판본·공식 HTTPS 도메인 5개다.
- 전체 body + 모든 단계 title/body/cautions를 공백 정규화해 연결한 글자 수: KO 2374, EN 2837, JA 2158 (최종 리뷰 수정 시 재계산).
- 본문/주의 일부를 뺀 AI 단위는 만들지 않는다. 전체 bundle이 API 길이를 넘으면 축약을 가장해 주의문을 삭제하지 않고 보수적으로 거절한다.
- 모델 호출, 유료 AI, AVD/실차 시험은 수행하지 않았다. Schema 검사도 의미 검토나 실제 기기 시험을 대신하지 않는다.

기존 공식 매뉴얼 검토의 범위·한계는 `MANUAL_REVIEW_IONIQ5_2024_KR.md`에 보존한다.

## 원문 HTML SHA256

아래는 같은 판본의 실제 수집 HTML 바이트(로컬 MCP 응답의 HTML 문자열 UTF-8, 직접 GET은 저장 원본)의 해시다.

| 절 | SHA256 |
|---|---|
| 올바른 운전 자세 | `f08cd68ab647962143ad6fd9a1a62aeba8fd6a354d89c9b49d98356482d0b893` |
| 좌석 | `1b376e03ec1906e690cfae46d38a7de20c37e172de9210f06b2d5e6c6fff47b2` |
| 앞좌석 | `12f8dec71afccc1b6363fdd888dc79cd50cf6edb7a60cb51002d40a85626d9ba` |
| 실내 미러 | `ece7c05b6169bb48024f271bf7bf5c6cfed46fe56c87797d684b70085cb4701f` |
| 실외 미러 | `2fdf46c821a8045a404cdad395250e55c3c4fb3b47b1e5608b3fe819a600f058` |

## 독립 검토 반영 후보

두 번째 작업자의 원문/KO·EN·JA 대조에서 전동 동시 스위치의 `two or more` 임계값, 방석 일반의 마찰 감소 위험(미끄러운 방석만으로 한정하지 않음), 과도한 등받이 기울임의 복부·목 벨트 조임 기전을 보강했다. 단계 3은 별도 자세 절 `idb26b9ae7995.html`의 source ID를 직접 참조한다. 21개 주의문 수는 유지하며 이 변경이 반영된 최종 3개 원본 해시를 독립 재검토하여 PASS로 고정한 뒤 별도 사본을 등록했다. 영어 2837자는 2800자 목표보다 길지만 3000자 API 상한 이내이며, 주의 의미를 더 줄이지 않는다.

## 게시 결과

독립 검토: `output/qa/guide-expansion-20261115/seats-independent-review.json`, SHA256 `0a5a43b47a6b781f3ef7fc8476669ec5c3f020cbf27d05874fab382850709cfd`, `passed=true`. 이는 위에서 설명한 두 번째 AI 작업의 원문·번역 대조이며 OEM/인간 인증이 아니다.

검토 DRAFT 원본은 덮어쓰기 없이 `output/qa/guide-expansion-20261115/prepared-guides/seats_mirrors/`에 복사했다. 게시 사본은 `published-candidates/seats_mirrors/`에서 lifecycle/번역 검토 상태와 EN/JA 용어 버전 메타데이터만 바꿨다. 본문·모든 단계·21개 주의문·출처는 독립 검토 해시의 내용 그대로다. 원본 DRAFT는 작업트리와 QA에만 보존하고 APK/영구 커밋의 입력으로 포함하지 않는다.

EN/JA `glossary_version=carcue-ioniq5-seat-mirror-v1`는 이번 검토에서 대조한 다음 용어·조건을 식별한다. 공통 glossary catalog나 다른 주제의 용어 파일을 변경하지 않았다.

| KO | EN | JA |
|---|---|---|
| 운전석 / 동승석 | driver / passenger | 運転席 / 助手席 |
| 헤드레스트 | head restraint | ヘッドレスト |
| 실내 / 실외 미러 | interior / exterior mirror | ルームミラー / ドアミラー |
| 볼록거울 / 보이는 것보다 훨씬 가까움 | convex / much closer than they appear | 凸面鏡 / 見える位置よりはるかに近い |
| 두 개 이상 동시 조작 금지 | do not use two or more at once | 二つ以上を同時に操作しない |
| 복부·목 조임 | abdomen/neck compression | 腹部・首が締め付けられる |

`import_guides.py check`의 게시 조건 검사 3개가 VALID였고, `import --content-root <좌석 작업트리>/content`의 원자적 신규 등록 3개가 IMPORTED였다. 기존 파일을 덮어쓰지 않았다.

| 언어 | 검토 DRAFT SHA256 | 게시 record / SHA256 |
|---|---|---|
| ko-KR | `7ba88103796484711832320173abe1cfd16d69a1e11ebba88b186859630964e9` | `content/guides/guide-384ef4bceadb0c5cf252dc4b549b262730da43d163f8628e0693b8662a03a370.json` / `f2ff2bec2b88202177d87791b83717b1c804208f057808d3cd3b7fa5df3a87e6` |
| ja-JP | `ecd04bd5227208a2635201fccd5767244dd7d5558991952c9cf4eea3410b5da6` | `content/guides/guide-3e66eb24f512f3df06f7e4bc6e58132096b6ef478ebf17736e363492cb1c40b2.json` / `8efc7b02edd0d0b686b2f9eb36b6fc3af2eea22d3570bbbc190ad7c3bcd1011b` |
| en | `1865dfa24039ce9e808092c85862889186156a07ec473ebbd235b5ab8c4426e6` | `content/guides/guide-89366d0a0a2f03202f9b9bd74f97450a87bbf01571ca58ab585d7d20ed62df27.json` / `65986588f06e807297ceded3cd4baa484f565d013e7f057adb553204c5f7b101` |

게시 후의 실제 SDK/AI 시험이나 사용자 효과 측정을 수행했다는 뜻은 아니다. 좌석·미러 센서 미연결 및 주행 전 직접 확인 범위는 그대로다. 기존 제출 고정 산출물도 변경하지 않았다.
