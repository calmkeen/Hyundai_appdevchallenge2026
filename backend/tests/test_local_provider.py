"""Native Ollama HTTP doubles only; no model download or actual AI/network calls."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.answer_policy import answer_units, validate_answer
from app.content import Catalog
from app.local_provider import LocalProviderError, OllamaProvider
from app.models import AskRequest, ModelTranslation, TranslateRequest

PROFILE = "ioniq5-ne1-2024-kr"


def question(locale="ko-KR"):
    return AskRequest(request_id="private-request-id", session_id="private-session-id", profile_id=PROFILE,
                      locale=locale, question="문을 닫기 전에 무엇을 확인하나요?",
                      guide_context={"guide_id": "ioniq5-door-open-check", "step_id": "check-closure-display"},
                      vehicle_context=[{"property_id": "door.position", "area_id": "ROW_1_LEFT",
                                        "value": "OPEN", "read_status": "VALUE", "source": "PLEOS"}])


def completed(value, **changes):
    return {"model": "qwen3:4b", "done": True, "done_reason": "stop", "prompt_eval_count": 42,
            "eval_count": 12, "message": {"role": "assistant", "content": json.dumps(value)}, **changes}


@pytest.mark.parametrize("locale", ["ko-KR", "en", "ja-JP"])
def test_local_model_selects_only_a_reviewed_unit_and_server_keeps_every_caution(locale):
    guides = Catalog().published(PROFILE, locale)
    unit = answer_units(guides)[0]
    calls, audit = [], []

    def handler(request):
        calls.append(request)
        assert str(request.url) == "http://127.0.0.1:11434/api/chat"
        assert "authorization" not in request.headers
        assert request.extensions["timeout"]["connect"] == 5
        assert request.extensions["timeout"]["read"] == 120
        wire = json.loads(request.content)
        assert wire["model"] == "qwen3:4b" and wire["stream"] is False and wire["think"] is False
        assert wire["options"] == {"temperature": 0, "num_ctx": 8192, "num_predict": 1500}
        schema = wire["format"]
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == {"status", "unit_id"}
        choice = schema["properties"]["unit_id"]["anyOf"][0]
        assert choice == {"const": unit["unit_id"], "type": "string"}
        payload = json.loads(wire["messages"][1]["content"])
        assert payload["locale"] == locale and payload["question"] == question(locale).question
        assert payload["vehicle_context"][0]["value"] == "OPEN"
        assert payload["history"] == [["older question", "older answer"]] * 3
        assert len(payload["candidates"]) == 1
        assert payload["candidates"][0]["text"] == unit["text"]
        assert payload["guide_context"]["step_id"] == "check-closure-display"
        assert "source_ids" not in payload["candidates"][0]
        return httpx.Response(200, json=completed({"status": "ANSWERED", "unit_id": unit["unit_id"]}))

    provider = OllamaProvider(transport=httpx.MockTransport(handler), audit=audit.append)
    answer = asyncio.run(provider.ask(question(locale), guides, [("older question", "older answer")] * 4))
    assert validate_answer(answer, guides) == unit
    assert all(part in answer.answer for step in guides[0]["steps"] for part in [step["body"], *step["official_cautions"]])
    assert len(calls) == len(audit) == 1 and provider.key == ""
    event = audit[0]
    assert event["model"] == "qwen3:4b" and event["prompt_tokens"] == 42 and event["output_tokens"] == 12
    assert event["outcome"] == "STRUCTURED_VALIDATED" and event["duration_ms"] >= 0
    assert event["request_id_hash"] == hashlib.sha256(b"private-request-id").hexdigest()
    assert len(event["response_digest"]) == 64
    serialized = json.dumps(event)
    for private in ("private-request-id", "private-session-id", question().question, unit["text"], "older answer"):
        assert private not in serialized


@pytest.mark.parametrize("status", ["NO_RELIABLE_SOURCE", "NEED_MORE_INFO"])
def test_null_non_answer_returns_only_a_server_replaceable_marker(status):
    provider = OllamaProvider(transport=httpx.MockTransport(lambda _: httpx.Response(
        200, json=completed({"status": status, "unit_id": None}))))
    result = asyncio.run(provider.ask(question(), Catalog().published(PROFILE, "ko-KR"), []))
    assert result.status == result.answer == status and result.source_ids == [] and result.follow_up_question is None


@pytest.mark.parametrize("selection", [
    {"status": "ANSWERED", "unit_id": "invented"},
    {"status": "ANSWERED", "unit_id": None},
    {"status": "ANSWERED", "unit_id": "invented", "answer": "Never use generated prose"},
])
def test_unknown_null_or_freeform_answer_selection_is_rejected(selection):
    provider = OllamaProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completed(selection))))
    with pytest.raises(LocalProviderError, match="LOCAL_INVALID_SELECTION"):
        asyncio.run(provider.ask(question(), Catalog().published(PROFILE, "ko-KR"), []))
    assert provider.events[-1]["outcome"] == "FAILED"


def test_non_answer_must_not_carry_a_selected_passage():
    guides = Catalog().published(PROFILE, "ko-KR")
    provider = OllamaProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completed(
        {"status": "NO_RELIABLE_SOURCE", "unit_id": answer_units(guides)[0]["unit_id"]}))))
    with pytest.raises(LocalProviderError, match="LOCAL_INVALID_SELECTION"):
        asyncio.run(provider.ask(question(), guides, []))


@pytest.mark.parametrize("body,code", [
    (completed({}, done=False), "LOCAL_INCOMPLETE"),
    (completed({}, done_reason="length"), "LOCAL_INCOMPLETE"),
    (completed({}, message={"role": "assistant", "content": "", "refusal": "private refusal text"}), "LOCAL_REFUSAL"),
    (completed({"refusal": "private refusal text"}), "LOCAL_REFUSAL"),
    (completed({}, message={"role": "assistant", "content": "not json private response"}), "LOCAL_INVALID_RESPONSE"),
    (completed({}, error="private model failure"), "LOCAL_SERVER_ERROR"),
])
def test_incomplete_refusal_or_invalid_output_is_classified_without_content_leak(body, code):
    provider = OllamaProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body)))
    with pytest.raises(LocalProviderError) as caught:
        asyncio.run(provider.structured({}, ModelTranslation, "test instructions"))
    assert caught.value.code == str(caught.value) == code
    assert provider.events[-1]["error_code"] == code
    assert "private" not in json.dumps(list(provider.events))


@pytest.mark.parametrize("error,code", [
    (httpx.ReadTimeout("private timeout details"), "LOCAL_TIMEOUT"),
    (httpx.ConnectError("private connection details"), "LOCAL_CONNECTION_ERROR"),
])
def test_transport_failures_are_safe_and_never_fall_back(error, code):
    calls = []
    def handler(request):
        calls.append(request)
        raise error
    provider = OllamaProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(LocalProviderError, match=code):
        asyncio.run(provider.structured({}, ModelTranslation, "test instructions"))
    assert len(calls) == 1 and calls[0].url.host == "127.0.0.1"
    assert "private" not in json.dumps(list(provider.events))


@pytest.mark.parametrize("status", [302, 404, 500])
def test_http_errors_and_redirects_do_not_leak_or_follow_a_remote_target(status):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="private server response", headers={"Location": "https://api.openai.com/"})
    provider = OllamaProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(LocalProviderError, match="LOCAL_HTTP_ERROR") as caught:
        asyncio.run(provider.structured({}, ModelTranslation, "test instructions"))
    assert caught.value.http_status == status and len(calls) == 1
    assert "private" not in json.dumps(list(provider.events))


@pytest.mark.parametrize("url", [
    "https://127.0.0.1:11434", "http://example.test:11434", "http://127.0.0.1:11434/api/chat",
    "http://user:password@localhost:11434", "http://127.0.0.1:11434?key=private", "http://localhost:",
])
def test_non_loopback_or_ambiguous_configuration_is_rejected_without_requests(url):
    with pytest.raises(ValueError, match="loopback"):
        OllamaProvider(base_url=url)


def test_translation_uses_native_payload_and_a_dedicated_prompt():
    calls = []
    def handler(request):
        calls.append(request)
        wire = json.loads(request.content)
        assert wire["options"]["num_predict"] == 3000
        assert set(wire["format"]["properties"]) == {"source_locale", "translated_text"}
        system = wire["messages"][0]["content"]
        assert "Translate only" in system and "verbatim excerpt" not in system and "Select one" not in system
        payload = json.loads(wire["messages"][1]["content"])
        assert payload["source_locale"] == "en" and payload["target_locale"] == "ko-KR"
        assert "session_id" not in payload and "request_id" not in payload
        return httpx.Response(200, json=completed({"source_locale": "en", "translated_text": "25 kPa를 넘지 마세요."}))
    provider = OllamaProvider(transport=httpx.MockTransport(handler))
    request = TranslateRequest(request_id="private-translation", session_id="private-session", profile_id=PROFILE,
                               source_locale="en", target_locale="ko-KR", text="Do not exceed 25 kPa.", content_kind="QUESTION")
    result = asyncio.run(provider.translate(request))
    assert result.translated_text == "25 kPa를 넘지 마세요." and len(calls) == 1


@pytest.mark.parametrize("budget", [0, -1, 3001, True])
def test_generation_budget_is_bounded_before_any_request(budget):
    provider = OllamaProvider(transport=httpx.MockTransport(lambda _: pytest.fail("must not request")))
    with pytest.raises(LocalProviderError, match="LOCAL_INVALID_TOKEN_BUDGET"):
        asyncio.run(provider.structured({}, ModelTranslation, "test", max_output_tokens=budget))


def test_empty_sources_never_call_any_model():
    provider = OllamaProvider(transport=httpx.MockTransport(lambda _: pytest.fail("must not request")))
    answer = asyncio.run(provider.ask(question(), [], []))
    assert answer.status == "NO_RELIABLE_SOURCE" and not provider.events
