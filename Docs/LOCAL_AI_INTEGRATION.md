# 무료 로컬 AI 연결

2026-11-14 기준. 사용자의 요청에 따라 유료 AI 연결을 보류하고, Mac M1·RAM 16GB에서 Ollama와 Qwen3를 실제 실행했다. 이 문서는 백엔드 검증 범위를 기록한다.

## 실행 구성

| 항목 | 확인한 값 |
|---|---|
| 런타임 | Ollama 0.40.16, macOS arm64 네이티브 |
| 모델 | `qwen3:4b`, Q4_K_M, 2,497,293,931 bytes |
| 모델 digest | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` |
| 모델 라이선스 | Apache 2.0; 한국어·영어·일본어를 포함한 다국어 지원 모델 |
| 실행 파일 | `.tooling/ollama/Ollama.app/Contents/Resources/ollama` |
| 모델 저장소 | `.tooling/ollama-models/` |
| 통신 | 백엔드 `127.0.0.1:8001` → Ollama `127.0.0.1:11434/api/chat` |

공식 근거: [모델·용량](https://ollama.com/library/qwen3:4b), [라이선스](https://ollama.com/library/qwen3:4b/blobs/d18a5cc71b84), [Qwen3 발행자 설명·언어 목록](https://qwenlm.github.io/blog/qwen3/), [macOS 설치 조건](https://docs.ollama.com/macos).

기본 `CARCUE_AI_PROVIDER=DISABLED`를 유지한다. 무료 로컬 연결은 `OLLAMA_LOCAL`을 명시하거나 아래 전용 실행 스크립트로 선택한다. 유료 서비스로 자동 전환하지 않는다. 기존 OpenAI 어댑터와 테스트는 보존했으나 현재 실행 factory에서는 선택하지 않는다. API 키를 사용하지 않으며, 모델·런타임·QA 결과는 APK와 Git에 포함하지 않는다.

로컬 AI를 선택해도 제품 기본 정책은 **자유 QUESTION 번역 비활성화**다. 무료 질문 응답과 검수된 저장 ANSWER/GUIDE 번역은 유지한다. 생성 질문 번역은 개발자가 서버 실행 시 `--enable-draft-question-translation`을 명시한 실험에서만 허용하며 품질 완료 기능으로 제공하지 않는다.

## 답변과 번역의 경계

- `ask`: 검수된 자료를 검색한 뒤 모델이 완전한 안내 단위의 ID를 선택한다. 서버가 해당 본문 또는 단계+공식 주의문 전체와 정확한 출처를 반환한다. 모델이 차량 조작 절차를 새로 작성하지 않는다.
- `ANSWER` / `GUIDE` 번역: 원문·언어·매뉴얼 판본이 맞는 완전한 저장 단위를 찾고, 대응하는 검수 번역을 반환한다. `STORED_GUIDE`이며 모델 호출은 0회다. 한국어 원문은 `NOT_APPLICABLE`, 영어·일본어는 `REVIEWED`와 저장 용어집 버전을 유지한다.
- 원문 불일치·주의문 제거·명시 원문 언어 불일치인 `ANSWER`는 번역 없이 `TEMPORARILY_UNAVAILABLE`을 반환한다. 미등록 언어는 입력 검증에서 거절한다. 매칭할 검수 근거가 없는 질문은 `NO_RELIABLE_SOURCE`이며 모델을 호출하지 않는다.
- 개발자 opt-in 동적 모델 번역은 `QUESTION`에 한정한다. 결과는 항상 `UNREVIEWED`다. `source_locale:auto`는 감지 요청이며 결과 언어가 아니다. 응답 스키마의 언어 enum은 Catalog의 처리 가능 언어만 허용하고, 명시 원문 언어는 그 값 하나로 제한한다. 구조·언어·숫자/단위 검증은 의미 정확성을 보증하지 않는다.
- 질문 용어집 `content/glossary/assistant-question-v1.json`의 `carcue-assistant-question-v1`은 게시 본문에 있는 ‘표시된 문 / indicated door / 表示されたドア’만 대상으로 한다. 검수된 프로필·매뉴얼 세트·판본이 정확히 맞고 원문에 이 용어가 있을 때 번역 힌트를 전달하며, 출력의 대응 용어가 빠지면 번역을 반환하지 않는다. 적용 버전은 `glossary_version`에 표시하지만 결과는 계속 `UNREVIEWED`다. 원문에 용어가 없는 질문에는 이 검사가 적용되지 않고, 용어를 남긴 채 조건을 추가하는 등 전체 의미 오류를 보증하지 않는다.
- 단일 문 상태로 모든 문 닫힘, 잠금, 고장 원인 또는 주행 안전을 판정하지 않는다. 프로필은 문서 범위 선택이며 실제 자동차종 인증을 뜻하지 않는다.

네이티브 요청은 `format=<JSON Schema>`, `stream:false`, `think:false`, `temperature:0`, `num_ctx:8192`를 사용한다. 완결 응답과 JSON 스키마를 검증하고, 시간 초과·거절·잘린 응답·유효하지 않은 선택은 사용 가능한 답변으로 노출하지 않는다. [Chat API](https://docs.ollama.com/api/chat), [구조화 출력](https://docs.ollama.com/capabilities/structured-outputs), [thinking 설정](https://docs.ollama.com/capabilities/thinking).

## 실행과 재검증

저장소 루트에서 실행한다. 이미 설치된 런타임·모델과 `.venv`를 사용하며, 각 `NEW_RUN`을 한 번도 쓰지 않은 실행명으로 바꾼다. 기존 증거 디렉터리는 덮어쓰지 않는다.

```bash
OLLAMA_MODELS="$PWD/.tooling/ollama-models" OLLAMA_HOST=127.0.0.1:11434 \
  .tooling/ollama/Ollama.app/Contents/Resources/ollama serve
```

별도 터미널에서 기본 백엔드를 실행한다. 자유 질문 번역 활성화 플래그를 넣지 않는다. 기본 앱 검증은 [앱 검증 명령](LOCAL_AI_APP_VALIDATION.md#재검증-명령과-범위)의 `--reviewed-manual-only`를 사용한다.

```bash
.venv/bin/python scripts/run_local_ai_backend.py \
  --model qwen3:4b --ollama-url http://127.0.0.1:11434 --port 8001 \
  --evidence-dir output/qa/NEW_RUN/server
```

다음 API 생성 질문 검증은 **개발자 실험용**이다. 먼저 별도 실험 서버를 명시적 opt-in으로 실행한다. 기존 서버와 동시에 같은 포트를 사용하지 않으며 각 `NEW_DRAFT_RUN`은 새 실행명이어야 한다.

```bash
.venv/bin/python scripts/run_local_ai_backend.py \
  --model qwen3:4b --ollama-url http://127.0.0.1:11434 --port 8001 \
  --evidence-dir output/qa/NEW_DRAFT_RUN/server --enable-draft-question-translation
```

다른 터미널의 기본 strict API 검증은 생성 질문 3건 모두 성공해야 한다. 거절 화면/응답까지 확인하는 실험은 아래 검증 명령에 `--allow-question-rejection`을 명시한다. 이때도 서버 opt-in은 필수이며 자유 번역 품질 통과를 뜻하지 않는다.

```bash
.venv/bin/python scripts/validate_local_ai.py \
  --backend-url http://127.0.0.1:8001 --ollama-url http://127.0.0.1:11434 \
  --model qwen3:4b --audit-file output/qa/NEW_DRAFT_RUN/server/provider-events.jsonl \
  --output-dir output/qa/NEW_DRAFT_RUN/validation
```

검증기는 실제 호출과 중복 요청의 호출 수, 저장 번역의 무호출, 미지원 질문, 세션 삭제를 확인한다. audit는 요청 ID 해시·모델·호출 종류·토큰 수·시간·응답 digest 등 제한된 메타데이터만 기록한다. 세션 토큰은 결과에 보존하지 않는다. `validation.json`의 기능 통과와 별도의 의미 검토를 구분한다.

## 확인 결과와 제한

- 최종 기본 서버는 `local-server-06-default`, 포트 8001이다. `output/qa/live-ai-20261114/default-question-deferral-02/validation.json`에서 자유 QUESTION 번역 KO→EN·EN→JA·JA→KO 모두 본문 없이 거절하고 실제 audit 0건·세션 삭제 3건을 확인했다. deferral-01의 DELETE 응답 검사 오류 진단도 보존한다.
- 최종 실제 앱 `output/qa/local-ai-app-20261114/local-ai-app-20261114-08-default/validation.json`은 **기본 모드 통과 / 66.646초**다. 5단계·PNG 5개에서 질문 응답 3건은 실제 모델을 3회 호출하고 저장 번역 2건은 무호출이었다. 전체 host 판정·세션 삭제·fixture 복구·lease 종료도 통과했다. 새 `semantic-review.json`은 5개 화면의 완전 검수 문구·금지문·저장 제목을 AI 보조로 대조해 해당 매뉴얼 사례 범위에서 통과했다. 자유 번역 품질은 계속 false이며 일반 품질·OEM·인간 검수 인증이 아니다.
- 개발자 실험 `output/qa/live-ai-20261114/real-local-api-06-guarded/validation.json`은 **guarded 기능 검증 통과**다. 실제 모델 호출 6회(질문 3·질문 번역 3), 번역 반환 2건·EN→JA 거절 1건, 저장 ANSWER 3건·GUIDE 6방향·부정 사례·세션 삭제까지 확인했다. 거절을 허용하는 명시적 실행 범위이며 `generated_translation_quality_passed:false`다.
- API06의 새 `semantic-review.json`에서 답변 3건·저장 번역 9건은 검수된 완전 단위와 정확히 일치했고 KO→EN 질문 번역은 의미를 유지했다. JA→KO는 `表示されたドアを閉める前に何を確認しますか？`를 `문을 닫기 전에 표시된 문을 확인하세요.`로 바꿔 질문을 명령으로 전환했다. 대상 용어를 보존해도 전체 의미는 실패한 사례이며, API는 이를 `TRANSLATED / UNREVIEWED`로 반환했다. EN→JA는 본문 없이 거절돼 번역 품질 통과로 계산하지 않는다. 전체 생성 번역의 의미·제품 통과를 주장하지 않는다.
- 가장 최근 strict 실행 `output/qa/live-ai-20261114/real-local-api-05/validation.json`은 **실패**다. 실제 호출 5회까지 진행한 뒤 EN→JA 질문 번역이 `TEMPORARILY_UNAVAILABLE / translated_text:null`로 거절됐다. 추가 프롬프트 조정 후에도 모든 질문 번역 성공을 확인하지 못했으므로 튜닝을 중단하고 유료 AI 보류를 유지한다. 질문 번역 품질 완료를 주장하지 않는다.
- 앞선 `real-local-api-04/validation.json`도 실패로 보존했다. 실제 모델 호출 6회 후 JA→KO 질문 번역에서 대상 용어 검사를 통과하지 못해 `TEMPORARILY_UNAVAILABLE / translated_text:null`을 반환했다. 응답의 `NOT_CALLED` 표기와 별개로 실제 호출 수는 audit 6회가 근거다. 새 정책의 전체 실호출 통과로 계산하지 않는다.
- 이전 strict 성공 `output/qa/live-ai-20261114/real-local-api-03/validation.json`: 실제 로컬 모델 호출 6회(3언어 질문 3회 + `source_locale:auto`인 `QUESTION` 번역 3회), 기능 검증 통과. 감지 결과는 각 입력에 맞는 `ko-KR`·`en`·`ja-JP`였다. 저장 `ANSWER` 3건·`GUIDE` 6방향, 미일치 답변·미지원 질문·중복 요청·세션 정리도 확인했다.
- 같은 폴더 `semantic-review.json`: 질문 답변 3건, 자동 언어 감지 질문 번역 3건, 저장 답변 3건, 저장 가이드 6방향을 독립 AI 보조로 대조했다. 선택된 사례의 의미·순서·주의문·출처 범위가 유지됐다. OEM·인간 전문가·원어민 인증이 아니며, 미래의 임의 질문 번역은 계속 `UNREVIEWED`다.
- 앞선 `real-local-api-02`의 기능 통과·예제 한정 의미 검토는 보존했다. 해당 실행의 동적 질문 번역은 명시 원문 언어를 사용했으므로 자동 감지 성공 근거로 확대하지 않는다.
- 별도 `auto-source-diagnostic-01.json`에서는 실제 모델이 원문 언어를 `auto`로 돌려주는 결함을 확인했다. 기존 진단을 보존하고 응답 언어 enum과 명시 언어 일치 검증을 보강했다. run03이 자동 감지 경로를 다시 확인한 결과다. 직접 제공자 진단 실패를 과거 공개 API 성공으로 기록하지 않는다.
- `real-local-api-01`은 기능 통과 후 의미 검토에서 동적 안내 번역 2건을 제품 사용 부적합으로 판정했다. 영어→일본어 금지문 역전과 한국어→영어의 전체 도어/계기판 표시 범위 손실이 있었다. 당시 API가 미리 차단한 것으로 보고하지 않는다. 이 실패 후 `ANSWER`를 저장 검수 단위 번역으로 변경했고, 원기록·거절 판정을 보존했다.
- 앱 run06에서는 기능 통과 뒤 JA→KO 생성 질문의 조건 추가·대상 누락을 발견했다. 이 실패 후 위 용어 힌트·대상 용어 검사를 추가했다. 과거 실행이 이 검사로 보호됐다고 기록하지 않으며, 새 정책의 실제 API·앱 결과는 별도 새 실행으로 확인한다.
- 앱07-guarded는 기본 보류 정책 적용 전 실험 서버에서 네이티브 시나리오 90.759초 통과와 8개 화면을 확보했다. 원래 host 결과는 최종 감사에 strict 옵션이 잘못 적용돼 `passed:false`이며 그대로 보존했다. 별도 `host-audit-diagnostic.json`의 사후 guarded 감사 확인은 원판정을 바꾸지 않는다. 오류 화면·저장 번역 제목 수정은 확인했으나 JA→KO 질문→명령 의미 오류가 남아 생성 번역 품질은 false다. 이 실험은 제품 기본 QUESTION-off와 구분한다.
- 기본 질문 번역 비활성화까지 포함한 백엔드 회귀 테스트 **370개 통과 / 9.65초**(`output/qa/live-ai-20261114/backend-question-deferral-tests-20261114T100213Z.log`). 이전 364개·336개 로그도 보존했다. 결정론적 테스트 대역과 실제 모델 검증을 구분하며 기존 Starlette AnyIO 사용 중단 예고 경고 1건이 남는다.
- 기존 Android JVM 테스트 52개·SDK 회귀·최종 실제 앱 검증은 각각 별도 범위다. APK 해시·호출 수·화면·한계는 [LOCAL_AI_APP_VALIDATION.md](LOCAL_AI_APP_VALIDATION.md)에 기록한다. 환경 정리 기록은 Console lease 종료·AVD 정상 종료·ADB 목록 비움·기존/새 userdata 보존을 확인하며 기본 서버와 Ollama는 유지했다. 이 문서는 원격 Git 반영 완료를 주장하지 않는다.

근거 매뉴얼은 `ioniq5-ne1-2024-kr` / `NE1-2024-KR-ko_KR-D202406100040-20240722`의 한국 판매 IONIQ 5 공식 자료에 한정한다. 모델의 다국어 지원, JSON 형식 성공 또는 숫자 보존만으로 차량 안내의 의미 안전성이 검증되지는 않는다.
