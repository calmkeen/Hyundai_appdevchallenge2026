# 영상·앱 미디어 출처

2026-11-13 확인. 기계가 만든 배경음악은 현재 소개 영상에서 사용하지 않는다. 상세 다운로드 URL·파일 해시는 `media-sources.json`과 앱의 `illustrations/vehicles.json`에서 관리한다.

## 배경음악

**A Kind Of Hope — Scott Buckley**, 원작자 공개 라이브러리의 무료 다운로드를 사용한다. [곡 페이지](https://www.scottbuckley.com.au/library/a-kind-of-hope/), [원작자의 사용 조건](https://www.scottbuckley.com.au/library/using-this-music/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

원작자는 출처 표기를 조건으로 상업 프로젝트를 포함한 사용을 허용한다. 영상에는 곡명·작곡가·라이선스·사이트를 표시한다. 유튜브에 게시할 때는 원작자 안내에 따라 **영상 설명란에도** 다음 표기를 넣는다. 복사 가능한 텍스트는 `output/qa/carcue-app-intro-credits.txt`에 저장한다.

> 'A Kind Of Hope' by Scott Buckley - released under CC-BY 4.0. www.scottbuckley.com.au

소개 영상에서는 원곡 12초 지점부터 영상 길이(현재 32초)만큼을 사용하고, 음량 조정과 시작·끝 페이드를 적용한다. 원본 MP3는 로컬 `.tooling/media/`에서만 편집 입력으로 보관하며 Git·APK에 넣지 않는다. 음악을 단독 배포하거나 오디오 지문 서비스에 등록하지 않는다.

## 실차 사진

| 앱 프로필 | 사진·촬영자 | 라이선스·표시 |
| --- | --- | --- |
| IONIQ 5 | [Hyundai Ioniq 5 (front).jpg](https://commons.wikimedia.org/wiki/File:Hyundai_Ioniq_5_(front).jpg), crash71100, 2021-07-04 | CC0 1.0. 원본 JPEG 그대로 보관하고 UI에서 아래쪽 기준으로 표시 |
| IONIQ 5 N | [Hyundai ioniq 5 N.jpg](https://commons.wikimedia.org/wiki/File:Hyundai_ioniq_5_N.jpg), Calreyn88, 2025-06-28 | CC0 1.0. 원본 JPEG 그대로 보관하고 UI에서 전체 비율 유지 |

두 원본 페이지에서 CC0 공개를 확인했다. 앱 사진 아래에 촬영자와 CC0를 표시하고, 원본 주소와 해시를 함께 보관한다. 사진은 해당 차종의 외관 참고용이며 선택한 차량의 정확한 연식·시장·옵션이나 현재 문 상태를 증명하지 않는다. 프로필별 파일을 분리하고 언어를 바꿔도 사진·판매지역이 유지되도록 한다.

## IONIQ 5 전용 3D 모델

보조 탭의 모델은 [vevalabs/openx-assets](https://github.com/vevalabs/openx-assets/tree/main/src/vehicles/hyundai_ioniq_5_2022)의 **Hyundai Ioniq 5 2022**다. 원작자 andikapratamaw(2022), 후속 가공 Dogan Ulus(2026). [저작권·라이선스 기록](https://github.com/vevalabs/openx-assets/blob/1a63f13b5cfee3e01207a84b13b40fc172d92a95/src/REUSE.toml)은 MPL-2.0 AND CC-BY-4.0을 명시한다.

원본 GLB는 [20261015 릴리스](https://github.com/vevalabs/openx-assets/releases/tag/20261015), 편집 가능한 Blend는 고정 커밋 `1a63f13b5cfee3e01207a84b13b40fc172d92a95`에서 받았다. Blend 파일의 SHA256을 LFS 포인터와 대조했다. 출처·해시는 `content/models/ioniq5-articulated.json`에 기록한다. 변경은 좌표 변환, 원본 앞좌석 왼쪽 문 그룹/경첩 유지, 개폐 애니메이션, 앱용 메시 스트림과 접지 그림자다. 원본 곡면 법선·30재질을 보존한다.

앱 설정과 3D가 나오는 영상에 다음 저작자/라이선스/변경 사실을 표시하고, 별도 게시용 텍스트에 원작자·저장소·라이선스 링크를 넣는다.

> 3D: andikapratamaw (2022), Dogan Ulus (2026) · MPL-2.0 + CC BY 4.0 · adapted

APK의 `assets/models/source/`와 저장소 `content/models/source/`에 원본 Blend/GLB, 변환 소스, 원본 저작권 기록, [MPL 2.0](https://www.mozilla.org/MPL/2.0/)·[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 전문을 포함한다. 변환된 모델과 개폐 클립도 일반 GLB로 제공한다. 모델은 현대 공식 CAD·공식 지원 또는 특정 연식·트림 일치를 뜻하지 않는다.

기존 자체 제작의 각진 모형과 사진 중심 영상은 Git 이력과 이전 산출물로 보존했다. 최신 소개 영상은 사진 중심으로 복원했다. 기능 장면은 실제 APK 녹화이며 시작 카드 사진도 APK에 동봉한 JPEG와 동일하다. 3D는 최신 소개 영상에 사용하지 않는다.

충전 가이드 사진은 사용자가 제공한 인계 ZIP의 `assets/ui/guide.svg` 내장 PNG다. 외부 원작자·별도 사용권은 인계 자료에서 확인되지 않았다. 기존 개발 Mock 예시로 유지하며 실제 게시용 검수 완료로 표시하지 않는다.
