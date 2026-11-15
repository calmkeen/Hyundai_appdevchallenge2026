# 2024 한국시장 아이오닉5 화면·표시등 안내 대조

2026-11-15. `ioniq5-cluster-display-check`의 한국어·영어·일본어 3개를 원문·독립 의미 검토한 뒤 소유 worktree의 게시 카탈로그에 등록했다. 공식 원문을 대조한 자체 요약이며 현대자동차 승인이나 인간 전문가·원어민 인증 검수는 아니다. 신규 주제 보호 정책과 전체 답변 bundle 핀은 통합 작업에서 함께 반영한다.

## 판본과 범위

- 프로필: `ioniq5-ne1-2024-kr`, 매뉴얼 세트: `hyundai-ioniq5-ne1-2024-kr`.
- 판본: `NE1-2024-KR-ko_KR-D202406100040-20240722`, 2024 한국 판매사양의 한국어 원문. EN/JA도 한국시장 내용을 요약하며 미국·일본 판매사양으로 바꾸지 않는다.
- 안내 범위: 주차 중 클러스터 밝기 설정, READY·서비스 경고등 구분, 파워다운 표시의 세 단계다. 전 경고등 목록·고장 진단·운행 안전 판정은 제공하지 않는다.
- CarCue는 이 항목의 SDK 센서를 연결하거나 밝기를 제어하지 않는다. 모든 `related_properties`는 빈 배열이며 행동은 해당 공식 원문 열기만 등록한다. 문 상태 재조회나 충전 제어는 없다.

## 대조한 공식 자료

| 공식 절 | 인쇄 / PDF 쪽 | 확인한 내용 |
| --- | --- | --- |
| [클러스터 조명 밝기 조절](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id4d773b8d07c.html) | 4-3 / 149 | ON 상태, 설정 > 디스플레이 > 화면 밝기, 수동/주간·야간 자동, 클러스터·인포테인먼트 동시 변경, 미등 점등 시 스위치 조명 동시 조절 |
| [클러스터 경고등 및 표시등](https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id44e0749ede7.html) 중 READY·서비스·파워다운 | 0-48 / 54 | READY의 켜짐/꺼짐/깜빡임, 서비스 ON 3초, 두 경고의 점검 조건, 출력 제한·급가속 금지·언덕 밀림 |

Root가 로컬 Firecrawl로 위 HTML 두 절을 HTTP200으로 수집했다. 담당자는 수집 본문을 읽고 기존 공식 601쪽 PDF의 해당 두 쪽을 Poppler로 PNG 렌더한 뒤 실제 이미지를 열어 제목·그림·주의 구획·본문·인쇄 쪽수를 대조했다. PDF SHA256은 `fd7e08cf0f3ed06a8e47ddee38fcaa463f32fa375b5a7d76c0aee4e0025a6248`이다. 원문 PDF·HTML·매뉴얼 그림은 Git이나 앱에 넣지 않는다.

원본 수집·읽기 전용 렌더 증거는 저장소 루트의 `output/qa/guide-expansion-20261115/research/` 아래 `cluster-brightness.json`, `ev-indicators.json`, `display-page-4-3-pdf149.png`, `display-page-0-48-pdf54.png`다. HTML은 공통 목차를 포함한 원본, `.md`는 본문 대조용이며 출처 절의 범위를 확대하지 않는다.

## 세 언어 의미 대조 항목

| 항목 | 세 언어에 보존한 조건·주의 |
| --- | --- |
| 밝기 | 차량 ON에서 실제 차량 화면의 메뉴 사용. 수동/자동 선택, 두 화면 동시 변경과 미등 상태의 스위치 조명. 주차 중 확인은 CarCue의 사용 경계로 본문에 표시 |
| READY | 시동 후 주행 준비 완료 시 켜짐. 꺼짐은 정상 주행 불가, 깜빡임은 비상 운전 상태. 꺼짐/깜빡임이면 현대 하이테크센터 또는 Bluehands 점검·정비 |
| 서비스 | ON 시 점등 후 `3초 / 3 seconds / 3秒` 뒤 소등. 주행 중 점등 또는 시동 후 꺼지지 않는 조건에서 점검·정비 |
| 파워다운 | 매우 적은 고전압 배터리 잔량·낮아지는 전압·높은 구동계 온도와 고전력 부품 보호를 위한 출력 제한. 단독 점등을 고장으로 설명하지 않는다는 원문 범위 유지 |
| 파워다운 주의 | 서비스 경고와 동시 점등이면 점검. 급가속·급출발 금지. 언덕 오르기 어려움·언덕길 밀림 가능성을 모두 유지 |

`official_cautions`는 원문의 경고·주의 요약이다. 두 화면과 스위치 조명이 함께 바뀐다는 정상 설명은 1단계 본문에 두고 그 단계의 주의 배열은 비운다. 임의의 안전 보장이나 조작 제어를 추가하지 않는다. 시동 ON 상태의 밝기 메뉴와 READY/서비스의 시동 후 조건을 합쳐 차량을 주차 상태에서 출발시키라는 절차로 바꾸지 않았다. 서비스 경고를 단순 일시 표시로 무조건 무시하거나 파워다운 단독 점등을 안전 판정으로 해석하지 않는다.

용어 버전 `carcue-ioniq5-display-v1`은 이 자체 요약에서 `클러스터 / cluster / メーター`, `서비스 경고등 / service warning / サービス警告灯`, `파워다운 / power-down / 出力制限表示`를 대응한다. 번역 UI 메뉴명은 한국어 공식 메뉴의 설명용 번역이며 영어·일본어 차량 UI를 별도로 검증했다는 뜻이 아니다.

## 초안 검사와 게시 등록

작성 당시 KO는 DRAFT/NOT_APPLICABLE, EN·JA는 DRAFT/UNREVIEWED였다. 세 파일은 기존 guide Schema, 단계1~3 순서, 출처 참조, 센서/재조회 미연결, OPEN_MANUAL 행동만 사용함을 검사했다. 본문·세 단계 제목/본문·모든 주의를 함께 이어도 EN 1,723자, KO826자, JA814자로 2,800자 목표와 기존 3,000자 상한 이하다.

Root의 독립 원문·3언어 의미 대조가 통과한 뒤 lifecycle을 PUBLISHED, EN·JA의 translation_review_status를 REVIEWED로 승격했다. KO는 NOT_APPLICABLE을 유지한다. 독립 기록은 `output/qa/guide-expansion-20261115/display-independent-review.json`, 담당자 원문 대조는 `display-author-review.json`, 등록 결과는 `display-publication.json`에 있다. 마지막 두 파일도 같은 QA 디렉터리에 있다.

기존 `scripts/import_guides.py import`에 이 worktree의 절대 `--content-root`를 지정해 3개를 새 파일로 등록했고, `check`는 기존 문 안내3개·신규3개·기존DRAFT1개인 7레코드를 VALID로 판정했다. 최초 승격 후보는 원본 초안에서 lifecycle/translation_review_status만 바꿨다.

이어 Root의 분류 검토에 따라 아직 커밋하지 않은 신규3개에 한 번의 구조 교정을 적용했다. 1단계의 정상 설명 문장을 글자 그대로 본문 끝으로 옮기고 `official_cautions=[]`로 바꿨다. 설명이나 실제 경고의 내용·순서·문자 수는 보존했다. 새로운 공통 보호 정책은 경고가 있는 2·3단계의 주의를 필수로 검사하며 빈 배열을 채우려고 정상 설명을 경고로 만들지 않는다. 기존 문 가이드와 원본 QA는 변경하지 않았다. 아래 해시는 이 구조 교정 후의 게시 레코드다.

| 언어 | 게시 레코드 | SHA256 |
| --- | --- | --- |
| ko-KR | `content/guides/guide-6acea0b6d1fafc32ffd9b4777fec9b28e2264f0fbdb30604f5c2f9295dc7c115.json` | `37b92b1033efc743b15b1acd7157b2bbc725fdad2dc06b1a36f4931ba3997270` |
| en | `content/guides/guide-6b891982d447e71265fcda6157e1fc38dfc0d84449d3f6dd5be835f643fc6642.json` | `4f3259b04a299517a66b5374c4e0f2e236ab5c55aa35cc3c2712cd3956e3489c` |
| ja-JP | `content/guides/guide-b023fdd43211cfd27acc968f50ad70fc472dd9ae1a1896dcc459d9cb7dc145c4.json` | `06f0e7bac7cd4d87cabfd44d8c3f588df1216f023015b7d7196221915ea06c3c` |

미게시 초안은 공유 QA의 `prepared-guides/display_indicators/`와 worktree의 Git 제외 경로 `.tooling/review-drafts/ioniq5-cluster-display-check/`에 원본 그대로 보존했다. `content/drafts`에는 남기지 않아 Android 자산이나 영구 커밋에 섞이지 않는다. 최초 승격 후보는 공유 QA의 `published-candidates/display_indicators/`, 구조 교정본은 `published-candidates/display_indicators-structural-followup/`에 별도로 보존한다.

전체 답변 bundle 핀·새 주제 보호 정책과 실제 HTTP/API·Android 빌드 검증은 통합 담당자가 수행한다. 등록 검사만으로 SDK 수신·기기 화면·실제 모델 검증을 통과했다고 하지 않는다. AVD·Ollama·유료 AI를 실행하지 않았고 기존 제출용 APK·영상·PDF·ZIP과 release는 변경하지 않았다.
