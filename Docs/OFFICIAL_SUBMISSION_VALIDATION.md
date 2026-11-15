# 공식 제출 DOCX 작성과 검증

2026-11-15. 공식 접수양식에 CarCue(카큐)의 프로젝트 소개를 작성했다. 참가자 정보와 동의·서명은 작성하지 않았으며 실제 접수·이메일 전송은 수행하지 않았다.

## 산출물과 근거

- 편집 원고: `Docs/OFFICIAL_SUBMISSION_PROPOSAL.md`
- 재현 빌더: `scripts/build_official_submission_docx.py`
- 생성물: `output/submission-official/20261115/CarCue-application-proposal.docx` (Git 제외)
- 생성물 SHA256: `d085b73e129e4fe6746b059d6509f49a610fa24871df51bcdfb272c1919ba27e`
- 공식 원본: <https://appdevchallenge.auto-hmg.io/downloads/contest-application-consent.docx>
- 원본 SHA256: `07be893d58b0e96ab7788f0d189d6829f0e59a2cee4bc18cb90ec37eeda2f5fd`

공식 원본은 작업용 `.tooling/official-form/`에 그대로 보관했다. 배포 권리를 확장해 가정하거나 원본·내부 PDF·페이지 PNG를 저장소에 추가하지 않았다. 사용자가 요청한 최종 문서 형식은 DOCX이며 PDF와 PNG는 내부 QA다. 문서 생성 전 artifact authoring marker는 1회 실행했다.

기획서의 현재 범위는 개발 소스 `825076f`의 안내 확장 기록과 아키텍처, 기존 SDK 세션 검증을 바탕으로 작성했다. 문 포함4주제·3언어12개와 신규9개의 API·저장 번역·컴파일 검증을 과거 실제 SDK·Ollama 문 안내 검증과 구분한다. 신규9개의 AVD·실제 모델 시험, 진행 중 요청 경계·429 기기 시험은 미완료로 표기했다. 실차·VIN 인증·추가 센서 연결·OEM 승인·전문가/원어민 인증, MAU·유지율 실측값과 제휴 실적을 주장하지 않는다. 최신 APK와34초 과거 debug 영상이 다른 빌드임을 명시한다.

## 양식 보존 검사

원본을 빈 문서로 재작성하지 않고 ZIP 안의 허용 부분만 패치했다. 원본 양식의 SDT alias가 실제 항목 제목과 어긋나므로 화면의 실제1~8항목을 기준으로 매핑했다. 예를 들어 `vehicle_scenario`는 실제3번 주요 기능이며 `reference_files`는 실제6번 기대효과다.

- `word/document.xml`: 프로젝트 응답7개와 세 앱명란만 작성하고, 선택 숏폼은 공란으로 유지했다. 이미 multiLine인4개 입력란의 개행을 같은 원본 run 안의 `w:br`로 표현했다. SDT ID·태그·별칭·plain-text 속성, 문단·run 속성과 바깥 박스를 보존했다. 6번의 노란 빈칸 강조만 `none`으로 바꿨다.
- `word/settings.xml`: Word에서 기본 PAGE 필드를 갱신하도록 `updateFields=true`만 추가했다. 원본 푸터와 PAGE 캐시를 재작성하지 않았다.
- 위 두 part 외 모든 ZIP part와 관계는 바이트 단위 동일하다. 문서 XML의 허용 편집을 역변환하면 원본 XML과 바이트 단위 동일하다.
- 03개인정보 동의서부터04서명 표와 이후 노드는 마지막 페이지의 알려진 앱명란을 제외하고 모두 동일하다. 마지막 앱명란에는 확정된 CarCue(카큐)만 채웠으며 해당 값·밑줄 외 라벨과 서식은 보존했다. 동의/미동의 체크박스·본인 서명·서명일은 모두 원본의 미선택 공란이다. 01참가 영역도 앱명 외에는 동일하다.
- 섹션1개, A4 세로, 여백·표 폭·테두리·최소 행 높이·원본 글꼴·제목·번호·푸터를 보존했다. 원본의 행 높이는 exact가 아니므로 본문에 맞춰 자연스럽게 늘어난다.
- 원본 SHA를 생성 전후 재대조했다. 기존 APK·영상·PDF·ZIP 파일에는 쓰지 않았다.

## 렌더와 시각 검토

workspace dependency loader가 반환한 번들 Python과 번들 LibreOffice를 사용했다. 시스템 LibreOffice는 사용하지 않았다. 이 환경의 기본 Fontconfig에서는 맑은 고딕이 없어 한글이 누락됐으므로, task-local `FONTCONFIG_FILE`에서 설치된 `/System/Library/Fonts/Supplemental/AppleGothic.ttf`로 매핑했다. DOCX 안의 원본 글꼴 지정은 변경하지 않았다. 사용자 Word의 글꼴 환경에 따라 페이지 수는 달라질 수 있다.

`render_and_diff.py`의4차 렌더 최종6쪽 전체를 PNG로 열어 검토했다. 1쪽은 참가정보, 2~4쪽은 프로젝트 소개, 5쪽은 원본 개인정보 동의서, 6쪽은 원본 서명란이다. 한글과 기호, 전체 표 경계, 앱명 라벨, 줄바꿈, 제목/응답 동반 배치, 푸터 간격, 페이지 번호1~6, 공란·미선택 체크박스를 확인했다. 잘림·겹침·누락 글리프가 없다. 4쪽 하단 여백은 다음 개인정보 동의서의 원본 pageBreakBefore를 유지한 결과다.

최종 section/style/SDT/field/heading audit도 수행했다. 직접 run서식145개·문단서식129개는 원본과 같으며 원본의 스타일 사용 특성도 유지했다. PAGE 필드는1개다. 근거와 페이지 이미지는 작업 디렉터리 `.tooling/official-form/template-fidelity-diff-04/`에 있고, 공유 QA 경로 `output/qa/official-form-20261115/`에도 최종 검사 기록과 이미지를 보존했다.

## 재현

작업 루트에서 공식 DOCX를 별도 내려받고 workspace dependency loader가 반환한 Python 경로를 `CARCUE_DOC_PYTHON`에 지정한 뒤 실행한다. 원본 SHA가 바뀌면 빌더가 중단하므로 새 양식을 먼저 확인해야 한다.

```bash
"$CARCUE_DOC_PYTHON" scripts/build_official_submission_docx.py \
  --template .tooling/official-form/contest-application-consent.docx \
  --source Docs/OFFICIAL_SUBMISSION_PROPOSAL.md \
  --output output/submission-official/20261115/CarCue-application-proposal.docx \
  --evidence-dir output/qa/official-form-NEXT/build
```

빌더는 원본·출력 구분,8개 SDT의 위치·유형, 필수 응답, 법률·서명 보존, 참가 영역 보존, 앱명 라벨, 페이지 구조, 허용 part 외 보존과 원본 해시를 검사한다. 재생성 후에는 documents skill의 번들 `render_docx.py` 또는 `render_and_diff.py`로 새 QA 경로에 렌더하고 모든 페이지를 다시 확인한다.

## 사용자가 작성할 항목

참가 단위·부문, 팀명 또는 개인 성명, 대표자 성명·역할·이메일·휴대폰, 참가 인원, 작성일, 대표자를 포함한 구성원, 각자의 동의·서명·서명일이 남아 있다. 소속은 공식 양식상 선택 사항이다. 운영사 접수번호와 게시하지 않은 선택 숏폼 링크는 공란이다. 참가자 정보를 받더라도 동의 체크·본인 서명·서명일을 임의로 대신 만들지 않는다.

문서의7번은 새 `release/0.1.1-first-submission` 저장소와 `apk/CarCue_release.apk`를 참조한다. 정확한 최종 소스·APK 해시와 공개 여부는 최종 배포 기록으로 확인하며, 이 문서 작성 자체가 원격 release 생성이나 제출 완료의 증거는 아니다.

이후 사용자가 팀명을 확정해 공개 원고의 APK 경로는 `apk/calmkeen_CarCue_release.apk`로 변경했다. 위 해시는 개인정보 입력 전 검수본 이력이다. 참가정보를 작성한 후속 `CarCue-application-proposal-filled.docx`와 렌더/해시는 로컬 `output/qa/official-form-filled-20261115/`에서만 관리한다. 동의 체크·서명·서명일은 공란이며 공개 Docs/빌더에는 연락정보를 넣지 않는다.
