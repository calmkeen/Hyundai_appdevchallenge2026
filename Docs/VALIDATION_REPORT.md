# 검증 결과

2026-11-14. 실차, 공식 전용 AVD의 실제 SDK, 일반 AVD의 Mock, 외부 AI 대역을 구분한다.

## 검증 상태

| 구분 | 명령/환경 | 결과 |
| --- | --- | --- |
| 서버 회귀 | `.venv/bin/python -m pytest backend/tests -q` | 이전 26개 통과 (세 언어의 자료 부족 응답 포함), 서버 코드 변경 없음 |
| Android 단위 | `:app:testDemoDebugUnitTest` | 이전 6개 통과, 실패/건너뜀 0 |
| Mock 기기 회귀 | API 35 / 1280×800 / `CarCueFlowTest` | 5개 통과, 원본 개폐 프레임 픽셀 차이·안전벨트 미연결·세 언어·기존 흐름 |
| 실제 APK 연속 촬영 | API 35 / `NativeShowcaseTest` | 1개 통과, 20개 실제 화면·개폐·세 언어 전환 |
| 실제 SDK 기기 회귀 | Pleos 2.1 / API 34 / SDK 2.3.2 / Service 2.3.22 / `PleosSdkTest` | 이전 1개 통과. 이번 재시험은 실행 전 프로세스 종료 |
| SDK 전체 검증 도구 | `.venv/bin/python scripts/validate_pleos.py` | 이전 Capability·GET·변경 콜백·화면·unregister·release 통과. 이번 재검증 미완료 |
| 앱 빌드 | `assembleDemoDebug`, `assemblePleosDebug` | APK 2종 성공 |
| 기기 테스트 빌드 | `assembleDemoDebugAndroidTest`, `assemblePleosDebugAndroidTest` | 성공 |
| 계약 | `scripts/check_contracts.py` | Schema 3종과 제공 예제 3개, UI 문자열 키 검사 통과 |
| 앱 소개 영상 | 실제 APK 녹화 기반 편집·AAC 디코딩 | 34초·1920×1080·30fps, 원본 차량·안전벨트·개폐·세 언어, 외부 음악 |
| 인계 패키지 | SHA256SUMS 전체 대조 | 일치 |

최종 기준 JDK는 Temurin 17.0.21+9 ARM64, Gradle 8.10.2, AGP 8.8.2, Kotlin 2.0.0이다. compile/target SDK 35, min SDK 28이다.

세 언어로 Mock 범위를 조정한 뒤 서버 26개·Mock 기기 3개·계약 검사를 다시 통과했고 두 APK를 재빌드했다. 일본어 홈과 세 언어 선택 캡처를 육안으로 확인했다. SDK·CarUx 수신과 Android 단위 시험은 같은 날 언어 변경 전에 확보한 결과이며, 이번 변경에서 재실행하지 않았다.

앱 내 시각 요소를 추가한 뒤 demo·pleos·기기 테스트 APK를 빌드했다. Mock 회귀 3개에는 3D 열림·닫힘·미수신·오래된 값과 가이드 사진 검사도 추가해 통과했다. 3D 가림을 다듬은 최종 APK로 `NativeShowcaseTest`의 19개 실제 UI 동작을 통과하고 연속 녹화했다. SDK 수신과 서버 코드는 이번 UI 변경에서 수정하지 않았다. UI 문구 129개의 세 언어 누락·치환 변수를 검사했다.

## 최신: 사용자 지정 Pleos 원본 차량·안전벨트 · 2026-11-14

사용자가 정확히 지정한 `carcue-pleos-sdk.mp4`의 안전벨트와 은색 차량 렌더 장면을 앱 내부 이미지로 넣었다. 입력 MP4의 SHA256은 `3657b7a2a8105066980b1f27ee3b78bb1e4dac57caa3383a01770cf446fa8a6e`로 유지한다. 차량은 19~20초의 21개 프레임, 안전벨트는 4초의 원본 부분이다. SDK 바이너리·원본 그래픽 리소스를 추출하지 않았다. 별도 공개 SDK 3D 위젯 연결이 아니라 원본 프레임 애니메이션이며, 안전벨트 착용 상태는 미연결이다.

demo·pleos와 두 테스트 APK 빌드가 성공했다(`pleos-reference-build.txt`, `pleos-reference-test-build.txt`). 두 전달 APK 안의 22개 PNG와 manifest가 저장소와 바이트 단위로 일치하고, 원본 MP4 해시·PNG 크기·개폐 프레임 차이를 검사했다(`pleos-reference-assets-check.txt`). 세 언어 145개 UI 자원과 참조/치환 변수 검사가 통과했다(`pleos-reference-contracts.txt`).

Mock 기기 시험 5개가 14.345초에 통과했다(`pleos-reference-flow-test.txt`). 실제 개폐 화면 픽셀 차이, 문 미확인 처리, 안전벨트 미연결 표시, 차종/시장 보존과 일본어, 기존 오류·UX 제한·가이드 복귀·로컬 HTTP Mock 왕복을 확인했다. 첫 픽셀 비교 실패는 테스트가 잠든 동안 Compose 시험 시계가 프레임을 진행하지 않는 문제였다. 실제 시간 동안 시험 프레임을 진행하도록 보완한 뒤 다시 통과했다. 홈·상태·일본어 캡처에서 원본 차량과 안전벨트 및 표시/버튼 경계를 육안 확인했다.

실제 APK 연속 촬영 1개가 49.646초에 통과했고 20개 장면을 기록했다. 전달 APK와 설치 base.apk 해시, 22개 원본 PNG/manifest의 바이트 일치를 대조했다(`carcue-native-run.json`). 기능 화면은 해당 APK 녹화에서만 가져왔다. 시작 카드도 동봉한 차량·안전벨트 PNG다. 차량 개폐 중간과 닫힘/열림, 안전벨트, 충전 가이드, AI 준비 중 표시, 영어·일본어 홈, 마무리 프레임을 디코딩하고 육안 확인했다(`pleos-reference-video-check.txt`, `pleos-reference-motion-check.txt`).

최종 소개 영상은 34초·1920×1080·30fps다. AAC를 PCM으로 디코딩해 34초·stereo 44,100Hz, peak 0.23239, RMS 0.019323, 클리핑 0을 확인했다(`pleos-reference-audio-check.json`). Scott Buckley의 기존 외부 음원 파일/해시를 유지하며 음악을 새로 합성하지 않았다. 결과별 MP4·APK 별칭과 체크섬을 갱신했다. 원본 기준 영상과 이전 앱·사진 중심 영상은 그대로 보존했다. 출처·사용 범위는 `PLEOS_VISUAL_SOURCE.md`에 기록한다.

기존 실제 SDK 문 수신 어댑터는 변경하지 않았다. 이번 Pleos AVD 재시험은 설치 서비스 지연으로 전용 AVD를 재시작하고 새 APK 설치까지 성공했지만, instrumentation이 `shortMsg=Process crashed`로 종료해 최초 GET/콜백 검증을 새로 완료하지 못했다. 이를 새 SDK 통과로 보고하지 않는다. 실패 시도는 `pleos-reference-sdk-attempt/`, 이전 성공 로그는 `archive-before-pleos-reference/sdk/` 및 기존 기본 SDK 로그에 보존한다. 서버 26개·Android 단위 6개·실제 SDK/CarUx 성공 결과는 이전 검증이며, 실차·실제 OpenAI 호출을 새로 검증하지 않았다.

## 이전: 실차 사진 중심으로 복원 · 2026-11-14

사용자가 초기 사진 중심 영상의 완성도를 선호해 홈·상태·문 상세·Mock 가이드 차량 자리를 실제 IONIQ 5/N 사진으로 복원했다. 사진은 외관 참고용으로 두고 문 수신 상태를 별도 표시한다. 기존 3D 개폐·회전·미확인 처리와 라이선스는 보조 탭에 유지한다. 소개 영상에는 3D를 넣지 않는다.

두 APK와 기기 테스트 APK 빌드가 통과했다(`photo-return-build.txt`). 실제 기기 5개 시험이 21.074초에 통과했다(`photo-return-instrumentation.txt`). 기본 홈에 사진이 표시되고 3D가 생성되지 않는 것, 차종·언어 변경 후 사진 매핑, 별도 탭에서 GPU 개폐·회전·미확인 자세가 유지되는 것을 검사했다. 기존 오류·UX 제한·가이드 복귀·로컬 HTTP Mock 왕복도 통과했다. 두 APK의 3D 원본·소스·라이선스 묶음이 그대로 포함됨을 검사했다.

실제 연속 촬영 시험 1개가 49.05초에 통과했다. 19개 장면의 새 녹화에서 설치/전달 APK의 해시와 실제 APK 안의 원본 사진 바이트를 대조했다. 소개 영상은 32초·1920×1080·30fps이며 시작·실차 사진·상태 카드·가이드·영어·일본어·마무리를 육안 확인했다(`photo-return-video-check.txt`). AAC 디코딩은 32초·2채널·44,100Hz, peak 0.23239, RMS 0.01959, 클리핑 0이다(`photo-return-audio-check.json`). 두 APK의 IONIQ 5/N 사진이 원본 JPEG와 동일하고 기록된 SHA256이 맞는지 검사했다. 기능 화면은 해당 APK에서 촬영하며, 사진을 문 개폐 영상으로 설명하지 않는다. 이번 변경은 실제 차량·새 SDK 수신·실제 AI 호출 검증이 아니다. 기존 SDK·서버 연결 상태와 이전 시험은 그대로 유지한다.

## 이전: 외부 IONIQ 5 전용 모델 교체 · 2026-11-14

기존 각진 자체 모형을 OpenX Assets의 Hyundai IONIQ 5 2022 모델로 교체했다. 원작자 andikapratamaw, 후속 가공 Dogan Ulus이며 MPL-2.0 AND CC-BY-4.0이다. 원본 Blend SHA256을 고정 커밋 LFS 포인터와 대조했다. 원본 GLB에서 37,350삼각형·30재질·44메시를 읽고 앞좌석 왼쪽 문·유리·미러 그룹과 원본 경첩을 유지했다. 물리적 왼쪽·바깥 개폐·유한 좌표·단위 법선·원본/변환 해시·정상 애니메이션 GLB를 검사했다. 8,602개 삼각형의 서로 다른 정점 법선이 변환 후에도 보존되어 곡면 보간에 사용되는지 확인했다.

`real-model-build.txt`에서 demo/pleos/기기 테스트 APK 빌드를 확인했다. 기기 회귀 5개가 48.078초에 통과했다(`real-model-instrumentation.txt`). GPU 프레임·0↔62도 개폐·픽셀 변화·회전·문 미확인의 22도 설명 자세·열림/닫힘 화면 경계를 검사했다. 기존 언어·오류/미지원·가이드 복귀·UX 제한·실제 로컬 HTTP Mock 왕복과 보조 사진 매핑도 통과했다. 서버는 이미 실행 중이던 로컬 Mock API를 사용했다.

`validate_3d_model.py --apk ...`로 두 전달 APK 안의 실제 모델, 원본 Blend/GLB, 변환 Python, 저작권·라이선스 전문이 저장소 파일과 바이트 단위로 일치함을 확인했다. 원본·소스를 APK에 동봉해 외부 서버 없이 얻을 수 있도록 했다. 앱 설정과 영상에 원작자·MPL/CC BY와 변경 사실을 표시한다.

실제 APK 연속 촬영 1개는 52.133초에 통과했다. 20개 실제 화면·개폐/회전·언어 전환의 원본과 설치/전달 APK 해시 일치를 `carcue-native-run.json`에 보관한다. 시작 카드도 같은 앱의 실제 GPU 뷰를 캡처한다. 기존 자체 모형·APK·영상은 Git 이력과 `archive-before-real-model/`에 보존했다.

최종 소개 영상은 34초·1920×1080·30fps다. 12개 시점에서 새 모델의 곡면·유리·개폐 전후/중간·회전·한국어/영어/일본어·모델 크레딧·마무리를 디코딩하고 육안 확인했다(`real-model-video-check.txt`). 최종 AAC 디코딩은 34초·stereo 44,100Hz, peak 0.23239, RMS 0.01932, 클리핑 0이다(`real-model-audio-check.json`). 원본 음악은 기존 Scott Buckley 음원을 그대로 유지한다. 소개 영상·실제 녹화·모델 캡처·설치/전달 APK의 해시 연관성을 확인하고 출력 체크섬을 갱신했다.

공식 현대 CAD나 선택 프로필과 정확히 맞는 연식·트림을 검증한 것은 아니다. 물리 차량/새 실제 SDK 수신/실제 OpenAI 호출을 추가 검증하지 않았다. 기존 SDK·서버 코드와 관련 시험 결과는 이전 검증을 유지한다.

## 이전: 자체 제작 3D 변경 검증

새 모델은 자체 제작 IONIQ 5 스타일 외형 참고 메시다. 현대 공식 CAD나 특정 연식·트림의 정확한 복제는 아니다. `validate_3d_model.py`로 두 파일의 해시·정상 GLB·유한 정점·물리적 왼쪽 문·경첩 축·바깥 방향 개폐를 검사했다. 모델은 14,734삼각형이며 문/차체는 독립 노드다.

최종 demo/pleos/기기 테스트 APK를 빌드했다(`3d-final-build.txt`). 기기 회귀 5개가 통과했다(`3d-final-instrumentation.txt`). 실제 TextureView가 렌더링한 프레임과 열린 문 62도→닫힌 문 0도, 화면 픽셀 변경, 드래그 회전, STALE의 회색 설명 자세 22도를 검사했다. 열린 문·닫힌 문 모두 GPU 비트맵 위·아래 경계의 어두운 차체/바퀴 픽셀이 없는지도 검사했다. 기존 세 언어·미수신/오류/미지원·UX 입력 제한·가이드 복귀·실제 로컬 HTTP Mock 왕복·사진 차종 매핑도 통과했다. 첫 시험의 상태 반영 전 대기와 고정 메뉴 스크롤 요청은 시험 동기화를 수정해 해결했다.

실제 APK 연속 촬영 1개가 통과했다. 20개 화면·동작의 원본 녹화와 설치 base.apk=전달 APK 해시 일치를 `carcue-native-run.json`에 보관한다. 소개 영상의 모든 기능 장면은 이 원본에서 자르며, 문 닫힘·다시 열림·회전은 각 2초다. 시작 카드 3D도 같은 APK의 GPU 뷰 비트맵이다. 최종 프레임 검수에서 하단 버튼 여백을 보완해 재빌드·재촬영했다. 이전 사진 중심 버전과 APK를 보존했다.

최종 소개 영상은 34초·1920×1080·30fps다. 개폐와 회전은 원본의 실제 터치 직전부터 편집해 움직이는 과정을 유지했다. 시작·개폐 전후와 중간 자세·회전·가이드·영어·일본어·마무리 프레임을 디코딩하고 육안 확인했다. `3d-intro-video-check-final.txt`, `3d-intro-motion-check.txt`, `3d-intro-midpoint-check.txt`에 시각을 보관한다. AAC를 PCM으로 디코딩한 결과는 34초, stereo 44,100Hz, peak 0.23239, RMS 0.01932, 클리핑 0이다. `3d-intro-audio-check.json`은 최종 MP4 해시도 기록한다. 외부 음원 원본·모델·설치/전달 APK·원본/최종 영상의 해시 일치를 확인했다. 최종 기기 5개는 17.86초, 촬영 1개는 54.224초에 통과했다.

이번 변경에서 backend/OpenAI/실제 Pleos 수신 어댑터는 바꾸지 않았다. 서버 26개, Android 단위 6개, 실제 SDK/CarUx 수신 결과는 이전에 확보한 검증이다. 이번에는 일반 AVD의 Mock 데이터와 실제 OpenGL/UI 동작을 검증했다. 물리 차량·새로운 실제 AI 호출을 검증한 것은 아니다.

## SDK 실제 수신 증거

`output/qa/pleos-sdk-events.txt`에서 다음 흐름을 확인했다.

1. Capability: `ROW_1_LEFT`, min 0 / max 1, READ_WRITE.
2. 최초 GET: 실제 SDK 값 0, 앱 수신 시각 기록.
3. Listener 등록과 실제 최초 콜백 0을 각각 기록.
4. 공식 Virtual Console에서 앞좌석 왼쪽 문을 열림으로 변경.
5. 실제 SDK 변경 콜백 1과 UI의 ‘앞좌석 왼쪽 문이 열려 있어요’ 확인.
6. 같은 Listener/영역의 `LISTENER_UNREGISTER_RETURNED`, `RELEASE_RETURNED` 확인.

값 0/1은 시험한 영역과 범위에서만 CLOSED/OPEN으로 정규화한다. 다른 영역/범위를 같은 의미로 확대하지 않는다. 등록 성공 문구나 GET만으로 변경 콜백 성공을 판단하지 않았다.

`output/qa/pleos-console-events.json`은 테스트 도구가 공식 콘솔에 보낸 시뮬레이션 요청이다. 앱에는 SDK SET을 넣지 않았다. 물리 차량을 제어하거나 실차 센서를 검증한 결과가 아니다.

## 실제 차량 UX 제한 검증

공식 Virtual Console에서 주차→Drive 및 20 km/h 조건→정차·Park를 시뮬레이션했다. 실제 `CarUxRestrictionsManager` 초기 GET false/0, 변경 callback true/80, 복귀 callback false/0을 확인했다. 로그는 `output/qa/pleos-ux-events.txt`, 화면은 `pleos-driving-restriction.png`다. 값이 없을 때 허용으로 처리하지 않으며, 실제 속도/기어로 앱이 제한을 추론하지 않는다. 속도/기어 변경은 테스트 도구의 가상 입력일 뿐이다. 실차·모든 지역 정책 검증은 아니다.

## Mock 기기 회귀 범위

- 실제 버튼으로 차량 선택 → 한국어 → 홈 → 상태 → 상세 → 종료.
- null/미수신, 지원 확인 실패, 실제 미지원, 오래된 값의 서로 다른 표시.
- Mock 주행 제한 변경 시 열린 질문 입력 제거와 제한 화면 표시.
- 가이드 단계 2에서 질문 후 돌아와도 단계 유지.
- 현재 Mock 언어 목록은 한국어·영어·일본어 3개. 실제 버튼으로 영어→일본어 변경, 일본어 홈·문 상태 표시, 단계 2 유지와 기존 가이드의 원문 언어 안내를 확인.
- 언어 변경 후 대한민국 사양 유지.
- 실제 HTTP로 로컬 FastAPI Mock 서버 왕복, NO_RELIABLE_SOURCE와 MOCK 모드 표시.
- 미등록 QR 프로필 오류 및 세션 종료 후 프로필·언어·상태·대화 초기화.

이는 48개 언어의 번역 완료나 모든 디스플레이·글자 확대 검증을 뜻하지 않는다. 한국어·영어·일본어 UI는 초안이며, 가이드 예시는 실제 조작 매뉴얼이 아니다. 세 언어 각각 129개 문구의 누락과 치환 변수 일치를 검사했다. 이전 빌드에서는 아랍어 영어 대체·RTL과 단계 숫자 방향을 확인했지만, 현재 Mock 선택 목록에서는 제외했다. RTL 확장 데이터와 배치 코드는 보존했다.

## 서버 회귀 범위

세션 소유·프로필 불일치, 자료 부족 Schema, 게시 전 템플릿 배제, 문서 버전/차종/언어/검수 상태에 따른 검색, 출처 ID 대조, 근거 없는 재서술 차단, 중복 요청·요청 ID 충돌, 삭제·만료·늦은 응답, 요청 한도, 번역 숫자·단위 보존 검사를 확인했다.

LIVE provider 시험은 **메서드/HTTP transport 대역**이다. 실제 OpenAI 요청은 수행하지 않았다. 실행 환경에 OPENAI_API_KEY와 OPENAI_MODEL이 설정되지 않은 것도 비밀값 출력 없이 확인했다. 자동 고장 진단·차량 제어 action을 생성하지 않으며 초기 답변은 검수 원문의 직접 추출로 제한한다. 번역의 부정·순서·부품명 등 의미 검수는 별도 과제로 남는다.

## 해결한 실패와 남은 검증

- 초기 JDK 18의 의존성 DNS 오류: 최신 JDK 17로 전환해 다운로드·빌드 성공.
- 초기 일반 API 37 AVD 부팅 미완료: 별도 API 35 AVD를 설치해 3개 기기 회귀 통과.
- Pleos 이미지의 표준 android.car 공유 라이브러리 필수 선언으로 설치 거부: 선택 선언과 클래스 존재 확인으로 수정, 설치·앱 실행·SDK 시험 통과. 런타임 제한 값은 SDK 조사 보고서에 별도로 기록한다.
- 서로 다른 사용자 저장소: Pleos 실행 사용자 10의 캡처를 `run-as --user 10`으로 분리해 수집.
- 실제 매뉴얼 검수, OpenAI 실호출, 실차, 다른 지역별 UX 정책, 전체 언어·폰 QR 카메라·로터리·접근성은 미검증.
- 의존 라이브러리의 비치명 경고: Starlette/AnyIO alias deprecation, 표준 Car.createCar/connect deprecation. 빌드/테스트 실패는 아님.

## 결과 파일

### 다국어 Mock 영상 추가 · 2026-11-13

`carcue-mock-languages.mp4`는 당시 demo APK를 API 35 / CarCue_UI35 / 1280×800 AVD에 설치해 녹화한 약 79초의 Android screenrecord 원본이다. 한국어 → 영어 → 일본어 → 한국어 전환, 실제 언어 버튼 터치, 각 언어의 홈·문 상태 화면을 담았다. 차량 프로필은 계속 IONIQ 5 · 2024 · KR이다. 모든 차량 값은 MOCK이며 외부 AI를 호출하지 않았다.

녹화 전 전달 APK와 기기에 설치된 base.apk의 SHA256이 `8d63511b8e8cd0cd16ce75bf1ae5037a5a6dff3e353ac028ac3a247453e3a59e`로 일치함을 검사했다. 앱 소스는 `ef8fe88`이다. JSON에는 APK·영상 해시, AVD, 언어, 관찰한 화면 문구별 시각이 있다. 시각은 호스트 기준의 근사값이다. 저장된 MP4를 macOS 영상 프레임워크로 열어 길이 78.7623초·1280×800을 확인하고, 10개 시점의 프레임을 디코딩했다. 세 언어의 홈·선택 목록·마지막 한국어 복귀 화면을 육안 확인했다. 결과는 `mock-languages-video-check.txt`와 `language-video-frames/`에 있다.

재현 도구는 `scripts/record_mock_languages.py`다. 이전 영상은 `carcue-mock-flow-initial.mp4`로 보존했다. APK 코드는 이번 녹화 작업에서 변경하지 않았다.

### 기능당 2초 편집본 추가 · 이전 28초 버전

사용자 요청에 따라 인계 SVG의 충전 사진과 실제 APK 녹화·캡처를 합쳐 `carcue-mock-short.mp4`를 만들었다. 총 14장면 × 2초 = 28초, 1280×800, 30fps다. 한국어·영어·일본어 화면과 실제 언어 선택 터치를 유지한다. 이미지 예시는 별도 자막으로 구분한다. 원본 녹화와 편집본의 출처·시간표는 `VIDEO_STORYBOARD.md`, 재현 구성은 `video-short.json`을 따른다.

초기 편집본의 14개 장면 프레임을 모두 디코딩하고 이미지, 가이드, 질문, 언어 목록, 종료 화면을 육안 확인했다. 최종 자막과 전환 구간 조정 후 해당 장면들을 다시 확인했다. 무편집 원본은 `carcue-mock-languages.mp4`로 보존한다. 외부 AI 호출과 APK 수정은 이번 편집 범위에 없다.

### 3D 차량 포함 32초 편집본 · 이전 결과

차량 그림·가이드 이미지·3D를 모두 포함해 달라는 사용자 요청으로 `carcue-mock-visuals-3d.mp4`를 추가했다. 총 16장면 × 2초 = 32초, 1280×800, 30fps다. 문이 닫힌 3D 차량은 첫 2초, 문이 열린 3D 차량은 10–12초에 배치했다. 원본 `carcue-pleos-sdk.mp4`의 차량 영역을 확대했으며, 두 구간에 Pleos 에뮬레이터 출처 자막을 넣었다. 3D는 플랫폼 시스템 UI이고 CarCue 자체 3D 렌더러 구현이 아니다. 나머지 앱 상태는 MOCK으로 구분한다.

최종 MP4 길이 32초와 11개 시점의 프레임 디코딩을 확인했다. 3D 차량의 문 닫힘·열림, 출처 자막, 장면 경계에서 자막이 사라지는 것, 가이드 이미지와 영어·일본어 전환을 육안 확인했다. 검증 로그는 `mock-visuals-3d-video-check-final.txt`, 캡처는 `visuals-3d-frames-final/`다. 렌더러의 초기 텍스트 레이어 출력 누락은 비트맵 자막 합성으로 수정했고, 차량 확대 구간의 검은 여백도 화면 비율을 맞춰 제거했다.

이전 28초 편집본과 두 녹화 원본도 보존했다. 이전 구성은 `history/VIDEO_STORYBOARD_EDITED.md`, 구간·확대 영역은 `video-short.json`, 파일별 해시는 `carcue-mock-visuals-3d.json`에서 관리한다.

### 이전: 일반 Canvas 모형과 연속 실행

사용자의 의도에 맞춰 사진·3D를 실제 APK 안에 구현했다. 홈·상태·상세의 일반 차량 위치 모형은 Compose Canvas에서 원근 투영하며 드래그로 회전한다. 신선한 문 상태만 열림·닫힘으로 연결하고 미수신·미지원·오류·오래된 값은 미확인으로 표시한다. 가이드 사진도 APK의 자산을 읽어 실제 Image 컴포넌트로 표시한다. 모델은 차종의 정확한 외형이 아니다. 세부 구현과 출처는 `NATIVE_VISUALS.md`에 있다.

`carcue-native-run.mp4`는 동일 APK에서 19개 기능 화면·동작을 실제로 실행한 연속 screenrecord 원본이다. 각 화면은 2초 유지하며 영상에 다른 이미지·Pleos 시스템 UI를 삽입하지 않는다. 설치 APK 해시를 전달 APK와 대조했다. 촬영 중 고정 메뉴에 스크롤을 요청한 자동화 실패는 표시 중인 메뉴를 바로 누르도록 수정했다. 종료 직전 대화상자 잔상이 최종 프레임으로 남지 않도록 실제 앱의 마지막 터치까지 녹화한다.

### 이전: 실차 사진 중심 소개 영상

이전 수정은 외부 무료 음원과 실차 사진을 사용했다. Scott Buckley의 **A Kind Of Hope**를 원작자 페이지의 CC BY 4.0·출처 표기 조건으로 확인해 내려받았다. 영상 크레딧과 별도 게시용 텍스트를 만들었다. 음원 합성 코드는 제거했고, 원곡을 구간 선택·음량 조정·페이드만 적용한다. 차량 기본 화면과 시작 카드에는 CC0 IONIQ 5 실차 사진을 사용하고 N 프로필에는 별도 N 사진을 매핑했다. 출처는 `MEDIA_CREDITS.md`에 정리했다.

demo·pleos·기기 테스트 APK 빌드가 성공했다. 기기 회귀 4개와 실제 촬영 1개가 통과했다. 새 테스트에서는 IONIQ 5에서 N으로 변경 후 일본어를 선택해도 N 사진·GB 시장이 유지됨을 확인했다. 136개 UI 자원의 세 언어 누락·치환 변수 검사도 통과했다. 사진 변경 전의 영상·APK는 별도 파일로 보존했다.

최종 소개 영상은 32초·1920×1080이다. 9개 시점의 프레임에서 시작 카드의 실차 사진, 실제 APK의 사진·상태·가이드·일본어, 음원 크레딧·마무리를 확인했다. 최종 AAC 디코딩 결과는 32초·2채널·44,100Hz, peak 0.2324, RMS 0.0196, 클리핑 표본 0이다. 결과는 `real-photo-intro-video-check.txt`와 `real-photo-intro-audio-check.json`이다. 아래의 자체 음악 수치는 이전 버전의 이력이다.

사용자 요청에 따라 실제 앱 원본을 바탕으로 `carcue-app-intro.mp4`를 제작했다. 시작·기능별 짧은 설명·세 언어 전환·이용 종료·마무리와 직접 만든 배경음악을 포함한다. 32초·1920×1080·30fps이며 기능 구간은 2초씩이다. 모든 기능 화면은 같은 APK 녹화에서 잘라 썼다. Mock 표시를 유지하며 AI 질문에는 답변 연결 준비 중임을 명시한다. 실제 앱 원본과 APK는 변경하지 않았다.

15개 장면의 중앙 프레임을 디코딩하고 시작·자막·3D·사진·질문·일본어·마무리를 육안 확인했다. 최종 첫 프레임의 브랜드 노출과 주요 자막도 재확인했다. MP4의 AAC를 디코딩한 결과 길이 32초, 44,100Hz, peak 0.2411, RMS 0.0609, 클리핑 표본 0이다. `app-intro-video-check.txt`, `app-intro-video-check-final.txt`, `app-intro-audio-check.json`에 증거를 남겼다. 기본 `carcue-mock-flow.mp4`는 이 소개 영상으로 갱신한다. 기획·재현은 `APP_INTRO_VIDEO.md`를 따른다.

- APK: `output/apk/carcue-demo-debug.apk`, `output/apk/carcue-pleos-debug.apk`.
- Mock 캡처: `output/qa/qa/01-profile.png` 등 기본 흐름. 최신 언어 선택·일본어 화면은 `09a-three-languages.png`, `09b-japanese-home.png`, `09c-japanese-status.png`.
- 실제 SDK 캡처: `pleos-initial-get.png`, `pleos-changed-callback.png`, `pleos-session-ended.png`.
- 로그: `output/qa/mock-instrumentation.txt`, `pleos-instrumentation.txt`, `pleos-sdk-events.txt`, `pleos-console-events.json`, `pleos-ux-events.txt`.
- 영상: 최신 소개용 `output/qa/carcue-app-intro.mp4` (`carcue-mock-flow.mp4`와 동일), 실제 실행 원본 `carcue-native-run.mp4`, 이전 편집본 `carcue-mock-visuals-3d.mp4`·`carcue-mock-short.mp4`, 이전 언어 녹화 `carcue-mock-languages.mp4`, 최초 `carcue-mock-flow-initial.mp4`, 별도 실제 SDK 영상. SDK 화면과 Mock 화면의 출처를 혼동하지 않는다.

SDK·AVD·JDK 바이너리와 APK/영상은 Git에 포함하지 않았다. source, 계약, 테스트, 실행 안내는 feature 브랜치에서 관리한다. 원격 push·병합·배포·공모전 제출은 수행하지 않았다.

실차 사진을 추가하기 전 앱 원본의 길이는 45.9814초, 해상도는 1280×800이다. `native-run-video-check-final.txt`와 `native-run-scene-check.txt`의 프레임 디코딩을 확인했고, 문 열림·닫힘·회전·가이드 사진·영어·일본어·깨끗한 종료 화면을 육안 확인했다. 실차 사진 추가 전 demo APK의 SHA256은 `3a30d6912c214d89c1e12ad86a00b5f8b6860f812bec95f93be237b39d3fbdbb`이며, 설치된 APK와 일치했다.
