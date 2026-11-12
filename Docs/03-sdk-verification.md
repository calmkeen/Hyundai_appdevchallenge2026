# SDK 검증 기록

기준일: 2026-11-12. 문서 확인, 배포 코드 확인, 빌드, 런타임을 구분한다.

## 완료
- 공식 Pleos 샘플 및 배포 Vehicle SDK 코드 확인.
- 연료 퍼센트, EV SOC, 문 상태 조회·구독 API 선언 확인.
- NaviHelper 목적지·경유지 전달 문서 확인.
- macOS에서 사용자 저장소 clone 및 Git remote 연결.
- Gradle 8.10.2 다운로드와 공식 샘플 빌드 명령 실행.

## 빌드 결과
공식 샘플 빌드는 Android SDK Platform 35 및 Build Tools 35 라이선스 미동의로 실패했다.
**앱 컴파일·APK 설치·Vehicle Service 연결·GET·콜백 수신은 아직 성공하지 않았다.**
사용자가 Android Studio 컴포넌트를 설치 중이며, 추가 설치와 약관 승인 단계는 별도로 관리한다.

## API 근거와 제한
| 항목 | 확인 | 제한 |
|---|---|---|
| Fuel | getFuelPercent, nullable Int %, CAR_ENERGY | 연료 종류·주유구 위치 자동 조회 의미 아님 |
| SOC | getEvBatteryStateOfCharge, nullable Int %, CAR_ENERGY | 반납 시점·충전시간·주행 가능성 예측 아님 |
| Door | getCurrentDoorPosition/registerDoorPosition, CAR_DOORS | 지원 영역·값 범위·실제 이벤트 수신 확인 필요 |
| Tire | 저압 상태 관련 API | 정확한 psi/kPa 수치 미확인 |
| 차량 언어 | Vehicle SDK에서 시스템 언어 변경 함수 미발견 | 불가능 확정 아님. 앱 UI 언어와 구분 |
| 차종 자동 식별 | VIN/CRN 관련 상세 목록 | 모델·트림·매뉴얼 자동 매칭 미확인 |
| NaviHelper | 목적지·경유지 요청 문서 | 요청 접수와 실제 경로 완료 구분 |
| 음성·위치 | 상세 문서/샘플 있음 | 신청 안내의 준비 중 표시와 상충, 계정·실행 검증 필요 |

## 실제 수신 시험
1. Pleos Connect 호환 AVD 부팅.
2. 읽기 권한만 선언한 앱 설치.
3. capability 결과 기록.
4. GET 응답과 시각 기록.
5. 구독 등록 후 Virtual Console에서 값을 변경.
6. 실제 callback과 화면 반영 확인.
7. 서비스 미연결·null·미지원 처리 확인.
8. 권한과 차량별 차이를 명시.

등록 성공 문구만으로 콜백 수신을 성공 처리하지 않는다. 가상 데이터는 명확히 표시한다.

## Git 상태
원격은 연결되어 있으나 마지막 push dry-run은 GitHub HTTPS 인증이 없어 실패했다.
원격 반영·PR 생성·병합은 완료되지 않았다. 토큰·키를 코드에 저장하지 않는다.
