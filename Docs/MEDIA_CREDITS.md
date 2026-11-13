# 영상·앱 미디어 출처

2026-11-13 확인. 기계가 만든 배경음악은 현재 소개 영상에서 사용하지 않는다. 상세 다운로드 URL·파일 해시는 `media-sources.json`과 앱의 `illustrations/vehicles.json`에서 관리한다.

## 배경음악

**A Kind Of Hope — Scott Buckley**, 원작자 공개 라이브러리의 무료 다운로드를 사용한다. [곡 페이지](https://www.scottbuckley.com.au/library/a-kind-of-hope/), [원작자의 사용 조건](https://www.scottbuckley.com.au/library/using-this-music/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

원작자는 출처 표기를 조건으로 상업 프로젝트를 포함한 사용을 허용한다. 영상에는 곡명·작곡가·라이선스·사이트를 표시한다. 유튜브에 게시할 때는 원작자 안내에 따라 **영상 설명란에도** 다음 표기를 넣는다. 복사 가능한 텍스트는 `output/qa/carcue-app-intro-credits.txt`에 저장한다.

> 'A Kind Of Hope' by Scott Buckley - released under CC-BY 4.0. www.scottbuckley.com.au

소개 영상에서는 원곡 12초 지점부터 32초를 사용하고, 음량 조정과 시작·끝 페이드를 적용한다. 원본 MP3는 로컬 `.tooling/media/`에서만 편집 입력으로 보관하며 Git·APK에 넣지 않는다. 음악을 단독 배포하거나 오디오 지문 서비스에 등록하지 않는다.

## 실차 사진

| 앱 프로필 | 사진·촬영자 | 라이선스·표시 |
| --- | --- | --- |
| IONIQ 5 | [Hyundai Ioniq 5 (front).jpg](https://commons.wikimedia.org/wiki/File:Hyundai_Ioniq_5_(front).jpg), crash71100, 2021-07-04 | CC0 1.0. 원본 JPEG 그대로 보관하고 UI에서 아래쪽 기준으로 표시 |
| IONIQ 5 N | [Hyundai ioniq 5 N.jpg](https://commons.wikimedia.org/wiki/File:Hyundai_ioniq_5_N.jpg), Calreyn88, 2025-06-28 | CC0 1.0. 원본 JPEG 그대로 보관하고 UI에서 전체 비율 유지 |

두 원본 페이지에서 CC0 공개를 확인했다. 앱 사진 아래에 촬영자와 CC0를 표시하고, 원본 주소와 해시를 함께 보관한다. 사진은 해당 차종의 외관 참고용이며 선택한 차량의 정확한 연식·시장·옵션이나 현재 문 상태를 증명하지 않는다. 프로필별 파일을 분리하고 언어를 바꿔도 사진·판매지역이 유지되도록 한다.

## 이전 이미지의 출처

- 각진 3D 차량은 `VehicleVisual.kt`에서 직접 만든 일반적인 위치 설명 모형이다. 외부에서 받은 실제 IONIQ 5 모델이 아니다. 현재는 실차 사진을 기본으로 표시하며 이 모형은 ‘3D 위치 예시’ 보조 탭에서만 제공한다.
- 기존 소개 시작 카드의 자동차 선 그림도 코드로 그린 브랜드 일러스트였다. 현재 시작 카드에는 위 CC0 IONIQ 5 실차 사진을 사용한다.
- 충전 가이드 사진은 사용자가 제공한 인계 ZIP의 `assets/ui/guide.svg` 안에 내장된 PNG를 추출한 것이다. 외부 원작자·별도 사용권은 인계 자료에서 확인되지 않았다. 기존 Mock 가이드 예시로만 유지하며, 실차 외관 사진 두 개와 출처를 구분한다.
