# CarCue 공식 제출 준비

2026-11-15 KST. 앱명은 **CarCue(카큐)**, 확정 팀명은 **calmkeen**이다. 자료 준비·검증과 실제 메일 발송·접수·동의·서명을 구분한다.

| 자료 | 위치와 상태 |
| --- | --- |
| 공식 기획서 | `output/submission-official/20261115/CarCue-application-proposal-filled.docx`. 참가정보 포함본은 로컬 전용이며 Git에 넣지 않는다. 공개 원고는 `OFFICIAL_SUBMISSION_PROPOSAL.md` |
| Pleos release APK | `apk/calmkeen_CarCue_release.apk`, 0.1.1-rc1/code2, 32,560,321bytes. 별도 release 서명, DEBUG/IS_MOCK=false |
| 소개 영상 | 같은 로컬 제출 폴더의 `CarCue-intro-KO-EN-JA.mp4`, 기존34초 SDK debug 시연과 byte-identical. 새 release와 다른 바이너리의 기록 |
| 출처 | 같은 로컬 폴더의 `CREDITS.txt`. 원래 음악과 차량·벨트 시각 자료의 확인된 이용 범위 보존 |
| GitHub | `release/0.1.1-first-submission` 후보. 최종 URL·커밋은 로컬 제출 폴더의 `GITHUB.txt`로 제공 |
| README | SDK 앱 설치, 별도 서버/무료 AI, Mock, 재빌드, Pleos Connect2.1.0/API34/2560×1440과 SDK2.3.2/Service2.3.22 명시 |

## 빌드와 자료 일치

APK 빌드 소스는 `7d492c1aa3daf4d2dcf436b4dd89222835094bd2`다. 최종 통합과 이 소스 사이의 `android/`, `content/`, `backend/app`, 고정 의존성, `contracts/` 차이를 검사한다. 파일명 변경은 APK 바이트와 서명에 영향을 주지 않았다.

APK SHA256은 `b5060db99072ae67af28a161304cc27e8e202ee282d11aa96803dbb977ff377f`, 인증서 SHA256은 `c945dc5eed5903ddd06efd51455c0d96239af5f11bc329fcd6b5381c99bf95e3`다. 148개 JVM·lint 오류0/경고16·설정 거절4개와 공개 manifest는 `SUBMISSION_RELEASE_APK.md`, `../apk/SUBMISSION_RELEASE_MANIFEST.json`을 따른다. 서명키·비밀번호·참가자 연락처는 공개하지 않는다.

CI에 APK의 실제 서명·해시·release 속성·SDK 클래스·동봉 콘텐츠를 키 없이 검사하는 단계를 추가했다. Demo JVM/Mock APK 검사와 구분하며 설치나 SDK callback 수신으로 표시하지 않는다. 이후 콘텐츠 변경 시에는 APK를 갱신하거나 고정 제출 소스에서 기존 APK를 검사해야 한다.

## 실제 연동과 남은 시험

- 이전 Pleos AVD에서 문 GET/callback, 차량 프레임 변경·복귀, Car UX Drive/Park, 문 안내·정상 종료를 검증했다. 실차·VIN 자동 인증은 아니다.
- 새 release 설치·AVD 재시험은 미실시다. 새9개 안내의 화면·원문 왕복·실제 무료 모델 선택, 진행 중 언어 변경/Drive/종료,429 화면 시험이 남아 있다.
- 새9개는 센서 미연결 수동 안내다. 전체12개는4주제×한국어·영어·일본어이며 실제 HTTP 안내9개/저장 번역36건과 모델·SDK 시험을 구분한다.
- AI에는 별도 서버와 무료 로컬 Ollama가 필요하다. 주소는 `http://10.0.2.2:8001`, 공급자 기본값은 DISABLED다. 유료 AI·자유 QUESTION 생성 번역은 보류다.
- Mock은 별도 demo flavor와 CI 대역·합성 시험이다. 제출 APK는 pleos flavor다. 차량은 사전 렌더 프레임, 벨트는 센서 미연결 이미지다.

## 본인이 마무리할 항목

이메일·미확정 역할·작성일을 확인하고 동의 여부, 본인 서명·서명일을 직접 작성한다. 소속은 선택이다. 로컬 초안은 일반 부문 1인 팀 기준이며 실제 인원이 다르면 구성원과 서명란을 보완한다. 공개 Docs/소스에는 실명·전화번호·이메일을 넣지 않는다.

접수는 **2026-11-15 23:59 KST**, `appdevchallenge@hyundai-partners.com` 이메일이다. 제목은 `[차량용 앱 개발 공모전] calmkeen_대표자명`이며 실제 대표자명은 로컬 양식에서 확인한다. 추가 팀원은 모두 CC한다. 기획서는 필수, 영상·소스와 release APK는 선택 가산점 자료다. 메일에 저장소 URL과 심사 기준 최종 커밋을 적는다.

공식 근거: [제출 안내](https://appdevchallenge.auto-hmg.io/guide/submission), [FAQ](https://appdevchallenge.auto-hmg.io/faq), [공식 DOCX](https://appdevchallenge.auto-hmg.io/downloads/contest-application-consent.docx). 기존 `release/0.1-first-draft`, 원본 APK·영상·PDF·ZIP과 strict 구 묶음 도구는 보존한다. 기존 ZIP이 새 공식 접수 묶음으로 자동 대체되지는 않는다.
