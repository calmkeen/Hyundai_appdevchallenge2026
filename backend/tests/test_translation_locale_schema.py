"""Native HTTP doubles validate locale grammar, not real model language quality."""
import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.local_provider import LocalProviderError, OllamaProvider
from app.models import ModelTranslation, TranslateRequest
from app.provider import ProviderError

SUPPORTED = ("ko-KR", "en", "ja-JP")


def request(source="auto"):
    return TranslateRequest(request_id="test-request", session_id="not-a-real-session", profile_id="ioniq5-ne1-2024-kr",
                            source_locale=source, target_locale="en", text="문을 닫기 전에 무엇을 확인하나요?", content_kind="QUESTION")


def provider_with(reply_source, inspect=lambda wire: None, supported=SUPPORTED):
    def handler(http_request):
        wire = json.loads(http_request.content)
        inspect(wire)
        return httpx.Response(200, json={"model": "qwen3:4b", "done": True, "done_reason": "stop",
            "prompt_eval_count": 20, "eval_count": 10, "message": {"role": "assistant", "content": json.dumps(
                {"source_locale": reply_source, "translated_text": "What should I check before closing the door?"})}})
    provider = OllamaProvider(model="qwen3:4b", transport=httpx.MockTransport(handler))
    provider.source_locales = supported
    return provider


@pytest.mark.parametrize("detected", SUPPORTED)
def test_auto_native_schema_allows_only_configured_source_languages(detected):
    def inspect(wire):
        schema = wire["format"]
        assert schema["title"] == "ModelTranslation" and schema["additionalProperties"] is False
        assert schema["properties"]["source_locale"]["enum"] == list(SUPPORTED)
        assert "auto" not in schema["properties"]["source_locale"]["enum"]
        assert json.loads(wire["messages"][1]["content"])["source_locale"] == "auto"
        assert "NEVER return auto" in wire["messages"][0]["content"]
    provider = provider_with(detected, inspect)
    result = asyncio.run(provider.translate(request()))
    assert isinstance(result, ModelTranslation) and result.source_locale == detected
    assert provider.events[-1]["operation"] == "ModelTranslation"
    assert provider.events[-1]["outcome"] == "STRUCTURED_VALIDATED"


@pytest.mark.parametrize("invalid", ["auto", "ko", "en-US", "zh-CN", None])
def test_auto_or_unregistered_model_output_is_rejected_before_api_validation(invalid):
    provider = provider_with(invalid)
    with pytest.raises(LocalProviderError, match="LOCAL_INVALID_RESPONSE"):
        asyncio.run(provider.translate(request()))
    assert provider.events[-1]["outcome"] == "FAILED"
    assert provider.events[-1]["error_code"] == "LOCAL_INVALID_RESPONSE"


def test_schema_uses_injected_catalog_languages_rather_than_a_fixed_three_language_list():
    configured = ("en", "fr-FR")
    def inspect(wire):
        assert wire["format"]["properties"]["source_locale"]["enum"] == list(configured)
    result = asyncio.run(provider_with("fr-FR", inspect, configured).translate(request()))
    assert result.source_locale == "fr-FR"


def test_explicit_source_is_retained_as_the_only_schema_choice():
    def inspect(wire):
        assert wire["format"]["properties"]["source_locale"]["const"] == "en"
        assert json.loads(wire["messages"][1]["content"])["source_locale"] == "en"
    result = asyncio.run(provider_with("en", inspect).translate(request("en")))
    assert result.source_locale == "en"


def test_explicit_source_cannot_be_changed_even_to_another_supported_tag():
    provider = provider_with("ko-KR")
    with pytest.raises(LocalProviderError, match="LOCAL_INVALID_RESPONSE"):
        asyncio.run(provider.translate(request("en")))
    assert provider.events[-1]["outcome"] == "FAILED"


@pytest.mark.parametrize("configured,source,code", [
    ((), "auto", "TRANSLATION_SOURCE_LOCALES_INVALID"),
    (("en", "auto"), "auto", "TRANSLATION_SOURCE_LOCALES_INVALID"),
    (SUPPORTED, "fr-FR", "TRANSLATION_SOURCE_LOCALE_UNSUPPORTED"),
])
def test_empty_invalid_or_unsupported_config_never_requests_a_model(configured, source, code):
    provider = OllamaProvider(model="qwen3:4b", transport=httpx.MockTransport(lambda _: pytest.fail("must not request")))
    provider.source_locales = configured
    with pytest.raises(ProviderError, match=code):
        asyncio.run(provider.translate(request(source)))
    assert not provider.events


def test_dynamic_locale_schema_does_not_mutate_shared_translation_model():
    asyncio.run(provider_with("en").translate(request("en")))
    assert ModelTranslation.model_json_schema()["properties"]["source_locale"]["type"] == "string"
    assert "enum" not in ModelTranslation.model_json_schema()["properties"]["source_locale"]
