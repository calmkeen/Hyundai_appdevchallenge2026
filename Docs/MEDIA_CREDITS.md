# 영상·앱 미디어 출처

2026-11-13 확인. 기계가 만든 배경음악은 현재 소개 영상에서 사용하지 않는다. 상세 다운로드 URL·파일 해시는 `media-sources.json`과 앱의 `illustrations/vehicles.json`에서 관리한다.

## 배경음악

**A Kind Of Hope — Scott Buckley**, 원작자 공개 라이브러리의 무료 다운로드를 사용한다. [곡 페이지](https://www.scottbuckley.com.au/library/a-kind-of-hope/), [원작자의 사용 조건](https://www.scottbuckley.com.au/library/using-this-music/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

원작자는 출처 표기를 조건으로 상업 프로젝트를 포함한 사용을 허용한다. 영상에는 곡명·작곡가·라이선스·사이트를 표시한다. 유튜브에 게시할 때는 원작자 안내에 따라 **영상 설명란에도** 다음 표기를 넣는다. 복사 가능한 텍스트는 `output/qa/carcue-app-intro-credits.txt`에 저장한다.

> 'A Kind Of Hope' by Scott Buckley - released under CC-BY 4.0. www.scottbuckley.com.au

소개 영상에서는 원곡 12초 지점부터 영상 길이(현재 34초)만큼을 사용하고, 음량 조정과 시작·끝 페이드를 적용한다. 원본 MP3는 로컬 `.tooling/media/`에서만 편집 입력으로 보관하며 Git·APK에 넣지 않는다. 음악을 단독 배포하거나 오디오 지문 서비스에 등록하지 않는다.

## 실차 사진

| 앱 프로필 | 사진·촬영자 | 라이선스·표시 |
| --- | --- | --- |
| IONIQ 5 | [Hyundai Ioniq 5 (front).jpg](https://commons.wikimedia.org/wiki/File:Hyundai_Ioniq_5_(front).jpg), crash71100, 2021-07-04 | CC0 1.0. 원본 JPEG 그대로 보관하고 UI에서 아래쪽 기준으로 표시 |
| IONIQ 5 N | [Hyundai ioniq 5 N.jpg](https://commons.wikimedia.org/wiki/File:Hyundai_ioniq_5_N.jpg), Calreyn88, 2025-06-28 | CC0 1.0. 원본 JPEG 그대로 보관하고 UI에서 전체 비율 유지 |

두 원본 페이지에서 CC0 공개를 확인했다. 앱 사진 아래에 촬영자와 CC0를 표시하고, 원본 주소와 해시를 함께 보관한다. 사진은 해당 차종의 외관 참고용이며 선택한 차량의 정확한 연식·시장·옵션이나 현재 문 상태를 증명하지 않는다. 프로필별 파일을 분리하고 언어를 바꿔도 사진·판매지역이 유지되도록 한다.

## 3D 모델과 이전 이미지

현재 기본 3D는 `scripts/build_ioniq5_model.py`로 직접 제작한 IONIQ 5 스타일 메시다. 차체와 경첩 문을 분리한 GLB·네이티브 메시·제작 소스를 저장소에 보관한다. 다운로드한 외부 모델·현대 공식 CAD·스캔 데이터가 아니며 특정 연식/트림 일치를 검증하지 않았다. 비율·외형은 [현대 브로슈어](https://ioniq5.hyundai.co.in/ioniq-5-brochure.pdf)를 참고했고 브로슈어 이미지나 CAD를 추출해 포함하지 않았다. 상세 출처·해시는 `content/models/ioniq5-articulated.json`을 따른다.

이전 일반 Canvas 차량과 사진 중심 시작 카드는 Git 이력과 이전 산출물로 보존했다. 현재 시작 카드는 실제 APK의 3D 뷰를 캡처한 이미지이며 모든 기능 장면도 같은 앱의 실행 화면이다. 실차 사진은 보조 탭에서만 사용한다.

충전 가이드 사진은 사용자가 제공한 인계 ZIP의 `assets/ui/guide.svg` 내장 PNG다. 외부 원작자·별도 사용권은 인계 자료에서 확인되지 않았다. 기존 개발 Mock 예시로 유지하며 실제 게시용 검수 완료로 표시하지 않는다.
