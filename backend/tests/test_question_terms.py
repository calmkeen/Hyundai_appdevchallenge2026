"""Scoped vocabulary checks using shipped content and native HTTP test doubles."""
import copy
import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.content import Catalog
from app.local_provider import OllamaProvider
from app.main import create_app
from app.models import ModelTranslation
from app.provider import DisabledProvider
from app.translation_terms import DEFAULT_PATH, QuestionTerms, load_question_terms, validate_target_terms

PROFILE = "ioniq5-ne1-2024-kr"
VERSION = "carcue-assistant-question-v1"
JA = "表示されたドアを閉める前に何を確認しますか？"
EN = "What should I check before closing the indicated door?"


@pytest.mark.parametrize("source,target,text,expected", [
    ("en", "ja-JP", EN, "表示されたドア"),
    ("ja-JP", "ko-KR", JA, "표시된 문"),
    ("auto", "ko-KR", JA, "표시된 문"),
    ("auto", "ja-JP", "ｉｎｄｉｃａｔｅｄ　ｄｏｏｒ", "表示されたドア"),
])
def test_exact_scoped_phrase_lookup_including_auto_and_nfkc(source, target, text, expected):
    match = load_question_terms().lookup(Catalog().profile(PROFILE), source, target, text)
    assert match["version"] == VERSION and len(match["terms"]) == 1
    term = match["terms"][0]
    assert term["term_id"] == "INDICATED_DOOR" and term["target"] == expected
    assert term["source_locale"] == ("ja-JP" if text == JA else "en")


@pytest.mark.parametrize("field,value", [
    ("profile_id", "another-car"), ("verification_status", "UNVERIFIED"),
    ("manual_set_id", "another-manual"), ("manual_version", "old-version"),
])
def test_other_or_unverified_profiles_and_manual_versions_get_no_terms(field, value):
    profile = dict(Catalog().profile(PROFILE), **{field: value})
    assert load_question_terms().lookup(profile, "en", "ja-JP", EN) is None


@pytest.mark.parametrize("source,target,text", [
    ("en-US", "ja-JP", EN), ("en", "de-DE", EN), ("en", "ja-JP", "What about the door?"),
])
def test_missing_source_term_or_unconfigured_language_gets_no_fallback(source, target, text):
    assert load_question_terms().lookup(Catalog().profile(PROFILE), source, target, text) is None


@pytest.mark.parametrize("change", ["unreviewed", "term-unreviewed", "unknown-profile", "wrong-version", "unknown-locale", "invented-phrase", "duplicate"])
def test_unregistered_or_unreviewed_term_records_are_rejected(change):
    data = json.loads(DEFAULT_PATH.read_text())
    if change == "unreviewed": data["status"] = "DRAFT"
    if change == "term-unreviewed": data["terms"][0]["review_status"] = "UNREVIEWED"
    if change == "unknown-profile": data["scope"]["profile_id"] = "unregistered-profile"
    if change == "wrong-version": data["scope"]["source_version"] = "old-version"
    if change == "unknown-locale": data["terms"][0]["phrases"]["xx-XX"] = "invented"
    if change == "invented-phrase": data["terms"][0]["phrases"]["en"] = "invented problem condition"
    if change == "duplicate": data["terms"].append(copy.deepcopy(data["terms"][0]))
    with pytest.raises(ValueError):
        QuestionTerms.from_data(data, Catalog())


def test_missing_indicated_door_is_rejected_without_claiming_full_semantic_review():
    match = load_question_terms().lookup(Catalog().profile(PROFILE), "auto", "ko-KR", JA)
    with pytest.raises(ValueError, match="REQUIRED_TERM_MISSING"):
        validate_target_terms(match, "문제가 발생했을 때 닫기 전에 무엇을 확인해야 하나요?")
    assert validate_target_terms(match, "표시된 문을 닫기 전에 무엇을 확인하나요?") == VERSION
    # This vocabulary check cannot judge every added condition or the whole meaning.
    assert validate_target_terms(match, "문제가 발생했을 때 표시된 문을 닫기 전에 무엇을 확인하나요?") == VERSION


@pytest.mark.parametrize("source,target,text,detected,translated,passed", [
    ("en", "ja-JP", EN, "en", "表示されたドアを閉める前に何を確認しますか？", True),
    ("auto", "ko-KR", JA, "ja-JP", "표시된 문을 닫기 전에 무엇을 확인하나요?", True),
    ("auto", "ko-KR", JA, "ja-JP", "문제가 발생했을 때 닫기 전에 무엇을 확인해야 하나요?", False),
    ("en", "ja-JP", EN, "en", "ドアを閉める前に何を確認しますか？", False),
])
def test_native_prompt_hints_and_api_term_guard_keep_new_translation_unreviewed(source, target, text, detected, translated, passed):
    wires = []
    def handler(request):
        wire = json.loads(request.content)
        wires.append(wire)
        payload = json.loads(wire["messages"][1]["content"])
        assert payload["matching_terms"][0]["term_id"] == "INDICATED_DOOR"
        assert payload["matching_terms"][0]["target"] == ("표시된 문" if target == "ko-KR" else "表示されたドア")
        assert payload["glossary_version"] == VERSION
        assert "use each provided target phrase exactly" in wire["messages"][0]["content"]
        assert "condition that is absent from the source" in wire["messages"][0]["content"]
        assert "translated_text MUST contain every phrase above literally" in wire["messages"][0]["content"]
        assert json.dumps([payload["matching_terms"][0]["target"]], ensure_ascii=False) in wire["messages"][0]["content"]
        return httpx.Response(200, json={"model": "qwen3:4b", "done": True, "done_reason": "stop",
            "prompt_eval_count": 30, "eval_count": 20, "message": {"role": "assistant", "content": json.dumps(
                {"source_locale": detected, "translated_text": translated}, ensure_ascii=False)}})
    provider = OllamaProvider(model="qwen3:4b", transport=httpx.MockTransport(handler))
    app = create_app(db_path=":memory:", provider=provider, mode="LIVE")
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": target}).json()
        result = client.post("/v1/translate", headers={"Authorization": "Bearer " + session["token"]}, json={
            "request_id": "question-term-test", "session_id": session["session_id"], "profile_id": PROFILE,
            "source_locale": source, "target_locale": target, "text": text, "content_kind": "QUESTION"}).json()
    assert len(wires) == 1 and result["review_status"] == "UNREVIEWED" and result["glossary_version"] == VERSION
    assert result["status"] == ("TRANSLATED" if passed else "TEMPORARILY_UNAVAILABLE")
    assert result["translated_text"] == (translated if passed else None)
    # A rejected translation stays unavailable, but the completed actual-provider
    # path must not be mislabeled NOT_CALLED. This is still an HTTP test double.
    assert result["ai_provider"] == "OLLAMA_LOCAL" and result["ai_model"] == "qwen3:4b"


@pytest.mark.parametrize("mode", ["MOCK", "LIVE"])
def test_mock_or_disabled_translation_remains_not_called(mode):
    provider = DisabledProvider()
    app = create_app(db_path=":memory:", provider=provider, mode=mode)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": "ko-KR"}).json()
        result = client.post("/v1/translate", headers={"Authorization": "Bearer " + session["token"]}, json={
            "request_id": "not-called-test", "session_id": session["session_id"], "profile_id": PROFILE,
            "source_locale": "auto", "target_locale": "ko-KR", "text": JA, "content_kind": "QUESTION"}).json()
    assert result["status"] == "TEMPORARILY_UNAVAILABLE" and result["translated_text"] is None
    assert result["ai_provider"] == "NOT_CALLED" and result["ai_model"] is None and not provider.events


def test_fake_provider_does_not_receive_new_attributes():
    class Fake:
        async def translate(self, request):
            return ModelTranslation(source_locale="en", translated_text="테스트 질문입니다.")
    fake = Fake()
    app = create_app(db_path=":memory:", provider=fake, mode="LIVE")
    assert not hasattr(fake, "term_lookup") and not hasattr(fake, "source_locales")
    app.state.store.connection.close()
