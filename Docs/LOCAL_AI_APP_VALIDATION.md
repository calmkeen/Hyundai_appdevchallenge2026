# Pleos 앱과 무료 로컬 AI 검증

2026-11-14. 최종 **App08 기본 모드가 66.646초에 통과**했다. 한국어·영어·일본어 질문 응답과 검수된 저장 번역을 실제 Pleos APK·로컬 Ollama로 확인했다. 자유 QUESTION 번역은 기본 비활성화이며, 과거 실험의 의미 오류와 실패 판정은 그대로 보존한다.

## 최종 실행 대상

| 항목 | App08-default 확인값 |
|---|---|
| 앱 APK | `output/apk/carcue-pleos-local-ai-final-debug.apk` |
| 앱 SHA-256 | `ddbca88ce3f522872ee35c90a0a5b7875fcc1664d411a28e983e0b89dc960a1f` |
| 테스트 APK SHA-256 | `0008b8921fc3ef748e41fdcedfb44726630cb72c682680038d3d0ea3fee60a66` |
| AVD / 사용자 | `CarCue_Pleos21_LocalAI`, `emulator-5584`, API 34, user 10 |
| SDK / 차량 서비스 | Pleos SDK 2.3.2 / VehicleService 2.3.22 |
| AI / 서버 | Ollama 0.40.16, `qwen3:4b`, 기본 서버 `local-server-06-default`, 포트 8001 |
| 모델 digest | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` |
| 프로필 / 판본 | `ioniq5-ne1-2024-kr` / `NE1-2024-KR-ko_KR-D202406100040-20240722` |
| 원기록 | `output/qa/local-ai-app-20261114/local-ai-app-20261114-08-default/` |

입력 APK와 기기에서 pull한 설치 APK 해시가 일치했다. 모델은 Mac `.tooling/ollama-models`에서 실행하며 APK에 포함하지 않는다. 유료 API 호출·자동 유료 전환은 없다. 구성·라이선스는 [LOCAL_AI_INTEGRATION.md](LOCAL_AI_INTEGRATION.md)에 기록했다.

## 최종 기본 모드 결과

`validation.json`은 `DEFAULT_LOCAL_ANSWERS_AND_STORED_TRANSLATIONS / passed:true`다. 네이티브 계측 **66.646초, 1개 시나리오 통과**, PNG 5개를 보존했다.

| 단계 | 실제 앱 결과 | 모델 호출 |
|---|---|---:|
| 1·2·3 | KO·EN·JA 질문 → 완전한 검수 단계+금지문·출처, `LIVE / OLLAMA_LOCAL` | 3 |
| 4 | 일본어 답변 → 저장 한국어 단계+주의문, ‘원문 안내’, `NOT_APPLICABLE` | 0 |
| 5 | 한국어 가이드 → 저장 영어 본문, ‘Reviewed saved translation’, `REVIEWED` | 0 |

모델 audit 3건은 질문 3건의 요청 해시와 정확히 대응한다. 저장 번역 2건은 추가 호출이 없다. 앱은 차량 출처 `PLEOS`를 유지했고, 세션 삭제·문 닫힘/Park/속도 0 복구·heartbeat lease 종료를 확인했다. `cleanup_errors=[]`이며 앱 SDK SET은 호출하지 않았다.

새 `semantic-review.json`에서 5개 이미지를 직접 대조하고 원본 artifact 해시를 확인했다. 세 언어 답변은 문을 닫기 전 신체 끼임 확인과 닫지 말라는 금지문 전체를 유지한다. 저장 번역도 원문·대상 문구와 제목이 맞고, 영어 전체 본문은 모든 도어·후드·테일게이트 닫힘과 계기판 경고문·열림 표시 모두 해제를 유지한다. **이 사례의 검수 매뉴얼 범위만 통과**하며 OEM·인간 전문가·원어민 인증이나 임의 미래 답변의 품질 보증은 아니다.

자유 QUESTION 번역의 기본 거절은 별도 실제 API `output/qa/live-ai-20261114/default-question-deferral-02/validation.json`에서 확인했다. KO→EN·EN→JA·JA→KO 모두 번역문 없이 `TEMPORARILY_UNAVAILABLE / NOT_CALLED`, audit 0건, 세션 삭제 3건이다. 이 검증은 App08의 추가 화면 단계가 아니다. 앞선 deferral-01의 DELETE 응답 검사 오류 진단도 보존했다. `generated_translation_quality_passed:false`를 유지한다.

## 별도 SDK 회귀와 환경

같은 최종 앱의 SDK 회귀는 `output/qa/pleos-official-guide/official-guide-local-ai-final-20261114-02/`에서 **23.192초 통과**했다. 실제 SDK GET·문 열림/닫힘 callback·공식 가이드·주행 제한·Park 복귀·세션 해제를 확인했다. 설치 해시는 위 앱과 일치하며 이 회귀에서는 외부 AI를 호출하지 않았다. 세부 근거는 [SDK_OFFICIAL_GUIDE_VALIDATION.md](SDK_OFFICIAL_GUIDE_VALIDATION.md)에 있다.

`fresh-avd-setup.json`은 기존 `CarCue_Pleos21` userdata를 보존하고 동일 읽기 전용 시스템 이미지·하드웨어 설정으로 별도 AVD를 만든 기록이다. 보안·UX 보호 조건을 완화하지 않았다. `bootstrap-readiness.json`에서 heartbeat·DDS/bridge 준비, user 10, `car_service` 등록을 확인했다. 기존 환경에서는 `car_service` 부재와 UX 준비 실패를 관측했다.

`output/qa/local-ai-app-20261114/environment-cleanup.json`은 최종 fixture 복구·모든 Console lease 종료·AVD 정상 종료·ADB 목록 비움·기존/새 userdata 보존을 확인했다. 기본 백엔드와 Ollama는 실행 상태로 유지했다. 다시 앱을 검증하려면 AVD 준비가 필요하다. 원격 Git 게시 상태는 이 실행 검증과 별도다.

## 보존한 실험·실패

| 실행 | 판정과 한계 |
|---|---|
| API01 | 기능 통과 후 안내 번역 2건 의미 부적합. 이후 ANSWER를 검수 저장 단위로 변경 |
| API02·03 | 당시 선택 사례 기능·의미 검토 통과. 미래 생성 번역 품질로 확대하지 않음 |
| API04·05 strict | 각각 JA→KO·EN→JA 거절로 전체 실행 실패 |
| API06-guarded | 거절 포함 기능 통과. 반환 JA→KO 질문→명령 의미 오류로 생성 품질은 false |
| 앱01·02·03 | 각각 자동감지 `auto` 반환, Console 초기 준비, `DeadObjectException` 실패 |
| 앱04·05 | 각각 heartbeat, UX 준비 실패. 이전 데이터·판정 보존 |
| 앱06 | native 100.421초 기능 통과 후 JA→KO 조건 추가·대상 누락과 저장 제목 불일치 발견 |
| 앱07-guarded | native 90.759초 통과·저장 제목 수정·오류 화면 확인. 원 host는 FINAL_AUDIT 실패 유지, JA→KO 의미 부적합 |
| 앱08-default | 자유 질문 번역을 끈 최종 기본 모드: 5단계·실제 3호출·정리 통과 |

App07의 8PNG 독립 검토는 일본어 일시불가 배너·원문 유지·새 요청 재시도·이전 번역 부재와 저장 제목 수정을 확인했다. JA→KO는 여전히 질문을 명령으로 바꿨다. 원 `validation.json`의 `passed:false`는 최종 host 감사에 guarded 플래그를 전달하지 않은 오류이며 그대로 보존한다. 별도 `host-audit-diagnostic.json`의 사후 확인은 원판정을 바꾸지 않는다. 실험 서버의 결과를 현재 QUESTION-off 기본 정책의 성공으로 소급하지 않는다.

## 재검증 명령과 범위

기본 서버는 [로컬 AI 실행 명령](LOCAL_AI_INTEGRATION.md#실행과-재검증)처럼 draft 활성화 플래그 없이 실행한다. 아래는 실행 중인 최종 기본 서버의 audit 경로를 사용한 검수 매뉴얼 전용 시나리오다. 서버를 새로 실행하면 해당 새 audit 경로로 바꾸고, `NEW_UNIQUE_RUN`도 새 이름으로 정한다. 동일 해시 APK가 user 10에 설치돼 있어야 하며 host 검증기는 설치하지 않는다.

```bash
.venv/bin/python scripts/validate_local_ai_app.py \
  --adb .tooling/android-sdk/platform-tools/adb --serial emulator-5584 \
  --avd CarCue_Pleos21_LocalAI --apk output/apk/carcue-pleos-local-ai-final-debug.apk \
  --test-apk .tooling/worktrees/android-local-ai/android/app/build/outputs/apk/androidTest/pleos/debug/app-pleos-debug-androidTest.apk \
  --audit-file output/qa/live-ai-20261114/local-server-06-default/provider-events.jsonl \
  --backend-url http://127.0.0.1:8001 --ollama-url http://127.0.0.1:11434 --model qwen3:4b \
  --output-dir output/qa/local-ai-app-20261114 --run-id NEW_UNIQUE_RUN --reviewed-manual-only
```

개발자 실험만 서버에 `--enable-draft-question-translation`을 추가한다. strict 생성 번역 3건 성공을 요구하는 앱 시나리오는 `--reviewed-manual-only`를 빼고, 거절 UI까지 허용하는 실험은 대신 `--allow-question-rejection`을 사용한다. 실험은 생성 번역 품질 통과를 뜻하지 않는다. 대상 용어 guard도 용어 누락만 부분 확인하며 전체 의미를 보증하지 않는다.

백엔드 **370개 통과 / 9.65초**의 근거는 `output/qa/live-ai-20261114/backend-question-deferral-tests-20261114T100213Z.log`다. 기존 AnyIO 경고 1건이 남는다. Android JVM 52개·SDK 회귀·앱 통합 검증은 각각 별도 범위다. 이미지는 Compose Window capture이므로 물리 디스플레이 합성·screenrecord 가시성의 통과 근거가 아니다. 실제 차량 시험·SDK 자동차종 식별은 하지 않았고 단일 문 값으로 잠금·모든 개구부·주행 안전을 추정하지 않는다.


## 후속 원문 연결 run06의 의미 검토 · 2026-11-14

`official-resources-20261114-06`에서 실제 무료Qwen3:4b1회/19.246초·등록출처/후속버튼·SDK8회왕복은 통과했다. 단, 현재 가이드step2에서 ‘문을 닫기 전에 무엇을 확인해야 하나요?’를 물었을 때 ‘출발 전 닫힘/계기판 확인’ 단위를 선택해 step1끼임주의를 포함하지 않았다. 원문밖생성/부정역전은 관측되지 않았지만 이 질문의 완전한의미적합성PASS로 세지 않는다. 현재단계와다른질문의관련성/필수주의문 보장은 후속범위다. 원기록과 독립17PNG검토는 `OFFICIAL_RESOURCE_APP_VALIDATION.md`와 해당run의 visual-review.json을 따른다. 질문/증거를 바꾸거나 유료모델로자동대체하지 않았다.

## 후속: 닫기 전 주의문 누락 보완 · 2026-11-14

위 run06의 부분 답변과 당시 한계는 보존한다. 후속 `feature/ai-complete-caution-answers`에서 해당 문 안내의 본문·두 단계·모든 주의문을 묶은 단위만 허용하고, 과거 부분 답변/번역 캐시도 차단했다. 같은 닫기 전 질문을 3언어×3문맥 실제 API9개와 실제 SDK 앱3문맥/3저장번역으로 재시험했다. 출처 두 절 재검토·물리 화면·독립 의미 검토·실패 이력·범위는 [AI_CAUTION_VALIDATION.md](AI_CAUTION_VALIDATION.md)를 따른다. 유료 AI와 생성 QUESTION 번역 기본 보류를 유지하며 임의 질문 전체의 정확성 완료로 확대하지 않는다.
