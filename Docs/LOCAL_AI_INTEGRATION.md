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

## 답변과 번역의 경계

- `ask`: 검수된 자료를 검색한 뒤 모델이 완전한 안내 단위의 ID를 선택한다. 서버가 해당 본문 또는 단계+공식 주의문 전체와 정확한 출처를 반환한다. 모델이 차량 조작 절차를 새로 작성하지 않는다.
- `ANSWER` / `GUIDE` 번역: 원문·언어·매뉴얼 판본이 맞는 완전한 저장 단위를 찾고, 대응하는 검수 번역을 반환한다. `STORED_GUIDE`이며 모델 호출은 0회다. 한국어 원문은 `NOT_APPLICABLE`, 영어·일본어는 `REVIEWED`와 저장 용어집 버전을 유지한다.
- 원문 불일치·주의문 제거·명시 원문 언어 불일치인 `ANSWER`는 번역 없이 `TEMPORARILY_UNAVAILABLE`을 반환한다. 미등록 언어는 입력 검증에서 거절한다. 매칭할 검수 근거가 없는 질문은 `NO_RELIABLE_SOURCE`이며 모델을 호출하지 않는다.
- 동적 모델 번역은 `QUESTION`에 한정한다. 결과는 항상 `UNREVIEWED`다. 구조·언어·숫자/단위 검증은 의미 정확성을 보증하지 않는다.
- 단일 문 상태로 모든 문 닫힘, 잠금, 고장 원인 또는 주행 안전을 판정하지 않는다. 프로필은 문서 범위 선택이며 실제 자동차종 인증을 뜻하지 않는다.

네이티브 요청은 `format=<JSON Schema>`, `stream:false`, `think:false`, `temperature:0`, `num_ctx:8192`를 사용한다. 완결 응답과 JSON 스키마를 검증하고, 시간 초과·거절·잘린 응답·유효하지 않은 선택은 사용 가능한 답변으로 노출하지 않는다. [Chat API](https://docs.ollama.com/api/chat), [구조화 출력](https://docs.ollama.com/capabilities/structured-outputs), [thinking 설정](https://docs.ollama.com/capabilities/thinking).

## 실행과 재검증

저장소 루트에서 실행한다. 이미 설치된 런타임·모델과 `.venv`를 사용하며, 각 `NEW_RUN`을 한 번도 쓰지 않은 실행명으로 바꾼다. 기존 증거 디렉터리는 덮어쓰지 않는다.

```bash
OLLAMA_MODELS="$PWD/.tooling/ollama-models" OLLAMA_HOST=127.0.0.1:11434 \
  .tooling/ollama/Ollama.app/Contents/Resources/ollama serve
```

별도 터미널에서 백엔드를 실행한다.

```bash
.venv/bin/python scripts/run_local_ai_backend.py \
  --model qwen3:4b --ollama-url http://127.0.0.1:11434 --port 8001 \
  --evidence-dir output/qa/NEW_RUN/server
```

다른 터미널에서 실제 로컬 HTTP 검증을 수행한다. 서버와 동일한 실행명의 audit 경로를 사용한다.

```bash
.venv/bin/python scripts/validate_local_ai.py \
  --backend-url http://127.0.0.1:8001 --ollama-url http://127.0.0.1:11434 \
  --model qwen3:4b --audit-file output/qa/NEW_RUN/server/provider-events.jsonl \
  --output-dir output/qa/NEW_RUN/validation
```

검증기는 실제 호출과 중복 요청의 호출 수, 저장 번역의 무호출, 미지원 질문, 세션 삭제를 확인한다. audit는 요청 ID 해시·모델·호출 종류·토큰 수·시간·응답 digest 등 제한된 메타데이터만 기록한다. 세션 토큰은 결과에 보존하지 않는다. `validation.json`의 기능 통과와 별도의 의미 검토를 구분한다.

## 확인 결과와 제한

- `output/qa/live-ai-20261114/real-local-api-02/validation.json`: 실제 로컬 모델 호출 6회(3언어 질문 3회 + `QUESTION` 번역 3회), 기능 검증 통과. 저장 `ANSWER` 3건·`GUIDE` 6방향, 미일치 답변·미지원 질문·중복 요청·세션 정리도 확인했다.
- 같은 폴더 `semantic-review.json`: 질문 답변 3건, 질문 번역 3건, 저장 답변 3건, 저장 가이드 6방향을 독립 AI 보조로 대조했다. 선택된 사례의 의미·순서·주의문·출처 범위가 유지됐다. OEM·인간 전문가·원어민 인증이 아니며, 미래의 임의 질문 번역은 계속 `UNREVIEWED`다.
- `real-local-api-01`은 기능 통과 후 의미 검토에서 동적 안내 번역 2건을 제품 사용 부적합으로 판정했다. 영어→일본어 금지문 역전과 한국어→영어의 전체 도어/계기판 표시 범위 손실이 있었다. 당시 API가 미리 차단한 것으로 보고하지 않는다. 이 실패 후 `ANSWER`를 저장 검수 단위 번역으로 변경했고, 원기록·거절 판정을 보존했다.
- 백엔드 회귀 테스트 **320개 통과**. 이 중 `test_ai_api_integration.py` 102개는 명시적 결정론적 테스트 대역을 사용한다. 실제 모델 검증 6회와 혼동하지 않는다. 기존 Starlette AnyIO 사용 중단 예고 경고 1건이 남는다.
- 기존 Android JVM 테스트 52개 결과는 별도 범위다. 이 백엔드 검증만으로 현재 APK의 설치·화면·SDK/AI 연결 통과를 주장하지 않는다. 앱 검증은 별도 [LOCAL_AI_APP_VALIDATION.md](LOCAL_AI_APP_VALIDATION.md)에 기록한다.

근거 매뉴얼은 `ioniq5-ne1-2024-kr` / `NE1-2024-KR-ko_KR-D202406100040-20240722`의 한국 판매 IONIQ 5 공식 자료에 한정한다. 모델의 다국어 지원, JSON 형식 성공 또는 숫자 보존만으로 차량 안내의 의미 안전성이 검증되지는 않는다.
