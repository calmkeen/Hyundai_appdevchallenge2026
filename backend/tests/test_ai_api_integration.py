"""Local API integration with explicit deterministic test doubles.

Uses the shipped, reviewed manual catalog and an in-memory ASGI/SQLite app.
The UNKNOWN provider is not Ollama or OpenAI; these tests make no model/network calls
and do not establish translation quality or device UI behavior. They exercise
the response fields consumed by the UI and the server's grounding safeguards.
"""

import copy
import itertools
import json
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.answer_policy import answer_units
from app.content import Catalog
from app.main import FOLLOW_UP_MESSAGES, NO_SOURCE_MESSAGES, create_app
from app.models import ModelAnswer, ModelTranslation


PROFILE = "ioniq5-ne1-2024-kr"
GUIDE = "ioniq5-door-open-check"
LOCALES = ("ko-KR", "en", "ja-JP")
QUESTIONS = {
    "ko-KR": "문을 닫기 전에 무엇을 확인해야 하나요?",
    "en": "What should I check before closing the door?",
    "ja-JP": "ドアを閉める前に何を確認すればいいですか？",
}
ORIGINAL = "Do not exceed 25 kPa."
FIXTURE_TRANSLATION = "25 kPa를 넘지 마세요."


class DeterministicLocalFixture:
    """Provider-port test double, explicitly identified in API responses."""

    kind = "UNKNOWN"
    model = "deterministic-local-test-double"

    def __init__(self, *, unit_index=0, ask_failures=0, translation_failures=0,
                 answer_status="ANSWERED", translation_source="en"):
        self.unit_index = unit_index
        self.ask_failures = ask_failures
        self.translation_failures = translation_failures
        self.answer_status = answer_status
        self.translation_source = translation_source
        self.ask_calls = 0
        self.translation_calls = 0
        self.received_guides = []
        self.received_history = []

    async def ask(self, request, guides, history):
        self.ask_calls += 1
        self.received_guides.append(copy.deepcopy(guides))
        self.received_history.append(copy.deepcopy(history))
        if self.ask_failures:
            self.ask_failures -= 1
            raise TimeoutError("Synthetic provider timeout; not a real model call.")
        if self.answer_status != "ANSWERED":
            # Deliberately untrusted Japanese prose, citations and follow-up.
            return ModelAnswer(status=self.answer_status,
                answer="この車は安全なので、そのまま運転してください。",
                source_ids=["invented-source-from-test-double"],
                follow_up_question="unchecked-model-follow-up")
        unit = answer_units(guides)[self.unit_index]
        return ModelAnswer(status="ANSWERED", answer=unit["text"],
                           source_ids=unit["source_ids"], follow_up_question=None)

    async def translate(self, request):
        self.translation_calls += 1
        if self.translation_failures:
            self.translation_failures -= 1
            raise TimeoutError("Synthetic translation timeout; not a real model call.")
        return ModelTranslation(source_locale=self.translation_source,
                                translated_text=FIXTURE_TRANSLATION)


@contextmanager
def session_for(provider, locale="ko-KR"):
    catalog = Catalog()
    app = create_app(db_path=":memory:", mode="LIVE", catalog=catalog, provider=provider)
    with TestClient(app) as client:
        response = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": locale})
        assert response.status_code == 201
        session = response.json()
        headers = {"Authorization": "Bearer " + session["token"]}
        yield app, client, catalog, session, headers


def ask_payload(session, locale="ko-KR", request_id="official-question"):
    return {"request_id": request_id, "session_id": session["session_id"],
            "profile_id": PROFILE, "locale": locale, "question": QUESTIONS[locale]}


def translation_payload(session, request_id="dynamic-translation", source_locale="auto"):
    return {"request_id": request_id, "session_id": session["session_id"],
            "profile_id": PROFILE, "source_locale": source_locale, "target_locale": "ko-KR",
            "text": ORIGINAL, "content_kind": "QUESTION"}


def saved_result(app, session, request_id):
    with app.state.store.transaction() as db:
        row = db.execute("SELECT fingerprint,response FROM results WHERE session=? AND request=?",
                         (session["session_id"], request_id)).fetchone()
    assert row is not None
    return row[0], json.loads(row[1])


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("unit_index", [0, 1, 2], ids=["whole-body", "pinch-step", "closure-step"])
def test_official_questions_return_complete_reviewed_units_and_exact_citations(locale, unit_index):
    provider = DeterministicLocalFixture(unit_index=unit_index)
    with session_for(provider, locale) as (_, client, catalog, session, headers):
        guides = catalog.published(PROFILE, locale)
        assert len(guides) == 1 and guides[0]["guide_id"] == GUIDE
        unit = answer_units(guides)[unit_index]
        response = client.post("/v1/ask", json=ask_payload(session, locale), headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert provider.ask_calls == 1 and provider.translation_calls == 0
        assert provider.received_guides == [guides]
        assert result["status"] == "ANSWERED" and result["locale"] == locale
        assert result["answer"] == unit["text"]
        if unit_index:
            step = guides[0]["steps"][unit_index - 1]
            assert result["answer"] == "\n".join([step["body"], *step["official_cautions"]])
        source_index = {source["source_id"]: source for source in guides[0]["sources"]}
        assert result["citations"] == [{
            "source_id": source_id, "guide_id": GUIDE, "profile_id": PROFILE,
            "manual_set_id": guides[0]["manual_set_id"], "source_version": guides[0]["source_version"],
            "title": source_index[source_id]["title"], "url": source_index[source_id]["url"],
            "section": source_index[source_id]["section"],
        } for source_id in unit["source_ids"]]
        assert result["actions"] == [{"kind": "OPEN_GUIDE", "target_id": GUIDE},
                                      {"kind": "REFRESH_STATUS", "target_id": "door.position"}]
        assert result["mode"] == "LIVE"
        assert result["ai_provider"] == "UNKNOWN"
        assert result["ai_model"] == provider.model
        assert catalog.profile(PROFILE)["market_code"] == "KR"


@pytest.mark.parametrize("source_locale,target_locale", list(itertools.permutations(LOCALES, 2)))
def test_all_stored_guide_language_pairs_use_reviewed_target_without_provider(source_locale, target_locale):
    provider = DeterministicLocalFixture()
    with session_for(provider, target_locale) as (_, client, catalog, session, headers):
        original = catalog.published(PROFILE, source_locale)[0]
        target = catalog.published(PROFILE, target_locale)[0]
        payload = {"request_id": "stored-guide-pair", "session_id": session["session_id"],
                   "profile_id": PROFILE, "source_locale": "auto", "target_locale": target_locale,
                   "text": original["body"], "content_kind": "GUIDE", "guide_id": GUIDE}
        response = client.post("/v1/translate", json=payload, headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "TRANSLATED"
        assert result["source_locale"] == source_locale and result["target_locale"] == target_locale
        assert result["original_text"] == original["body"] and result["translated_text"] == target["body"]
        assert result["review_status"] == target["translation_review_status"]
        assert result["glossary_version"] == target["glossary_version"]
        assert result["ai_provider"] == "STORED_GUIDE" and result["ai_model"] is None
        assert provider.ask_calls == provider.translation_calls == 0
        # Stored results are idempotent too; a second request never invokes a model.
        assert client.post("/v1/translate", json=payload, headers=headers).json() == result
        assert provider.ask_calls == provider.translation_calls == 0


@pytest.mark.parametrize("source_locale,target_locale", list(itertools.product(LOCALES, repeat=2)))
@pytest.mark.parametrize("unit_index", [0, 1, 2], ids=["whole-body", "pinch-step-with-caution", "closure-step-with-caution"])
@pytest.mark.parametrize("detect_source", [True, False], ids=["auto-source", "explicit-source"])
def test_answer_translations_use_exact_reviewed_units_in_every_language_direction(
        source_locale, target_locale, unit_index, detect_source):
    provider = DeterministicLocalFixture()
    with session_for(provider, target_locale) as (_, client, catalog, session, headers):
        original = catalog.published(PROFILE, source_locale)[0]
        target = catalog.published(PROFILE, target_locale)[0]
        original_unit = answer_units([original])[unit_index]
        target_unit = answer_units([target])[unit_index]
        if unit_index:
            original_step = original["steps"][unit_index - 1]
            target_step = target["steps"][unit_index - 1]
            assert original_step["step_id"] == target_step["step_id"]
            assert original_step["official_cautions"] and target_step["official_cautions"]
            assert target_unit["text"] == "\n".join([target_step["body"], *target_step["official_cautions"]])
        payload = {"request_id": "reviewed-answer-unit", "session_id": session["session_id"],
                   "profile_id": PROFILE, "source_locale": "auto" if detect_source else source_locale,
                   "target_locale": target_locale, "text": original_unit["text"], "content_kind": "ANSWER"}
        response = client.post("/v1/translate", json=payload, headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "TRANSLATED"
        assert result["original_text"] == original_unit["text"]
        assert result["source_locale"] == source_locale and result["target_locale"] == target_locale
        assert result["translated_text"] == target_unit["text"]
        assert result["review_status"] == target["translation_review_status"]
        assert result["glossary_version"] == target["glossary_version"]
        assert result["ai_provider"] == "STORED_GUIDE" and result["ai_model"] is None
        assert result["mode"] == "LIVE"
        assert provider.ask_calls == provider.translation_calls == 0
        assert client.post("/v1/translate", json=payload, headers=headers).json() == result
        assert provider.ask_calls == provider.translation_calls == 0


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("invalid_kind", [
    "unknown-text", "altered-body", "pinch-step-without-caution", "closure-step-without-caution",
    "caution-only", "wrong-source-body", "wrong-source-step",
])
def test_unmatched_or_incomplete_answers_never_fall_back_to_model_translation(locale, invalid_kind):
    provider = DeterministicLocalFixture()
    with session_for(provider) as (_, client, catalog, session, headers):
        original = catalog.published(PROFILE, locale)[0]
        unit = answer_units([original])[0]
        text, source_locale = unit["text"], "auto"
        if invalid_kind == "unknown-text":
            text = "Unknown manual answer; no reviewed equivalent exists."
        elif invalid_kind == "altered-body":
            text += " "
        elif invalid_kind.endswith("step-without-caution"):
            index = 0 if invalid_kind.startswith("pinch") else 1
            step = original["steps"][index]
            assert step["official_cautions"]
            text = step["body"]
        elif invalid_kind == "caution-only":
            text = original["steps"][0]["official_cautions"][0]
        elif invalid_kind.startswith("wrong-source"):
            source_locale = next(candidate for candidate in LOCALES if candidate != locale)
            if invalid_kind.endswith("step"):
                text = answer_units([original])[1]["text"]
        payload = {"request_id": "unreviewed-answer", "session_id": session["session_id"],
                   "profile_id": PROFILE, "source_locale": source_locale, "target_locale": "ko-KR",
                   "text": text, "content_kind": "ANSWER"}
        response = client.post("/v1/translate", json=payload, headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "TEMPORARILY_UNAVAILABLE" and result["translated_text"] is None
        assert result["original_text"] == text and result["source_locale"] == source_locale
        assert result["target_locale"] == "ko-KR"
        assert result["review_status"] == "UNREVIEWED" and result["glossary_version"] is None
        assert result["ai_provider"] == "NOT_CALLED" and result["ai_model"] is None
        assert provider.ask_calls == provider.translation_calls == 0
        # A retry is permitted, but must still never generate an unchecked instruction.
        assert client.post("/v1/translate", json=payload, headers=headers).json() == result
        assert provider.ask_calls == provider.translation_calls == 0


def test_answer_with_unknown_explicit_source_locale_is_rejected_without_provider():
    provider = DeterministicLocalFixture()
    with session_for(provider) as (_, client, catalog, session, headers):
        original = catalog.published(PROFILE, "en")[0]
        payload = translation_payload(session, source_locale="not-registered")
        payload.update(content_kind="ANSWER", text=original["body"])
        response = client.post("/v1/translate", json=payload, headers=headers)
        assert response.status_code == 422 and response.json()["detail"] == "LOCALE_NOT_REGISTERED"
        assert provider.ask_calls == provider.translation_calls == 0


@pytest.mark.parametrize("operation", ["ask", "translate"])
def test_transient_failures_allow_same_input_retry_keep_fingerprint_and_then_cache_success(operation):
    provider = DeterministicLocalFixture(ask_failures=int(operation == "ask"),
                                         translation_failures=int(operation == "translate"))
    with session_for(provider) as (app, client, _, session, headers):
        payload = ask_payload(session) if operation == "ask" else translation_payload(session)
        endpoint = "/v1/" + operation
        first_response = client.post(endpoint, json=payload, headers=headers)
        assert first_response.status_code == 200
        first = first_response.json()
        assert first["status"] == "TEMPORARILY_UNAVAILABLE"
        fingerprint, persisted_first = saved_result(app, session, payload["request_id"])
        assert persisted_first == first and len(fingerprint) == 64
        assert app.state.store.context(session["session_id"]) == []
        assert provider.ask_calls + provider.translation_calls == 1

        different = dict(payload)
        different["question" if operation == "ask" else "text"] = (
            "문이 닫혔는지 어떻게 확인하나요?" if operation == "ask" else "Do not exceed 26 kPa.")
        conflict = client.post(endpoint, json=different, headers=headers)
        assert conflict.status_code == 409
        assert conflict.json()["detail"] == "REQUEST_ID_REUSED_WITH_DIFFERENT_INPUT"
        assert provider.ask_calls + provider.translation_calls == 1
        assert saved_result(app, session, payload["request_id"]) == (fingerprint, first)

        retried_response = client.post(endpoint, json=payload, headers=headers)
        assert retried_response.status_code == 200
        success = retried_response.json()
        assert success["status"] == ("ANSWERED" if operation == "ask" else "TRANSLATED")
        assert success["ai_provider"] == provider.kind and success["ai_model"] == provider.model
        assert provider.ask_calls + provider.translation_calls == 2
        assert saved_result(app, session, payload["request_id"]) == (fingerprint, success)
        assert client.post(endpoint, json=payload, headers=headers).json() == success
        assert provider.ask_calls + provider.translation_calls == 2
        assert client.post(endpoint, json=different, headers=headers).status_code == 409
        assert provider.ask_calls + provider.translation_calls == 2
        assert saved_result(app, session, payload["request_id"]) == (fingerprint, success)
        history = app.state.store.context(session["session_id"])
        assert len(history) == (1 if operation == "ask" else 0)
        if operation == "ask":
            assert provider.received_history == [[], []]


@pytest.mark.parametrize("status", ["NO_RELIABLE_SOURCE", "NEED_MORE_INFO"])
def test_non_answered_japanese_model_prose_citations_and_followup_are_replaced(status):
    provider = DeterministicLocalFixture(answer_status=status)
    with session_for(provider, "ja-JP") as (app, client, _, session, headers):
        payload = ask_payload(session, "ja-JP")
        response = client.post("/v1/ask", json=payload, headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert provider.ask_calls == 1
        assert result["status"] == status and result["answer"] == NO_SOURCE_MESSAGES["ja-JP"]
        assert result["citations"] == [] and result["actions"] == []
        assert result["follow_up_question"] == (FOLLOW_UP_MESSAGES["ja-JP"] if status == "NEED_MORE_INFO" else None)
        assert result["ai_provider"] == provider.kind
        wire = json.dumps(result, ensure_ascii=False)
        for unchecked in ("この車は安全", "invented-source-from-test-double", "unchecked-model-follow-up"):
            assert unchecked not in wire
        assert app.state.store.context(session["session_id"]) == []
        assert client.post("/v1/ask", json=payload, headers=headers).json() == result
        assert provider.ask_calls == 1


@pytest.mark.parametrize("requested_source,returned_source", [
    ("ja-JP", "en"),  # Explicit input language cannot be silently changed.
    ("auto", "auto"),  # A detection request is not a detected BCP-47 language.
    ("auto", "not-registered"),
    ("auto", "ar"),  # Registered but PLANNED is also unavailable for processing.
])
def test_dynamic_translation_rejects_mismatched_unknown_or_unimplemented_source_locale(requested_source, returned_source):
    provider = DeterministicLocalFixture(translation_source=returned_source)
    with session_for(provider) as (_, client, _, session, headers):
        payload = translation_payload(session, source_locale=requested_source)
        response = client.post("/v1/translate", json=payload, headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert provider.translation_calls == 1
        assert result["status"] == "TEMPORARILY_UNAVAILABLE" and result["translated_text"] is None
        assert result["original_text"] == ORIGINAL and result["source_locale"] == requested_source
        assert result["review_status"] == "UNREVIEWED" and result["glossary_version"] is None


@pytest.mark.parametrize("source_locale", ["auto", "en"])
def test_successful_dynamic_translation_preserves_original_and_remains_unreviewed(source_locale):
    provider = DeterministicLocalFixture()
    with session_for(provider) as (_, client, _, session, headers):
        payload = translation_payload(session, source_locale=source_locale)
        response = client.post("/v1/translate", json=payload, headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "TRANSLATED"
        assert result["source_locale"] == "en" and result["target_locale"] == "ko-KR"
        assert result["original_text"] == ORIGINAL and result["translated_text"] == FIXTURE_TRANSLATION
        assert result["review_status"] == "UNREVIEWED" and result["glossary_version"] is None
        assert result["ai_provider"] == "UNKNOWN" and result["ai_model"] == provider.model
        assert provider.translation_calls == 1 and provider.ask_calls == 0


def test_unregistered_explicit_input_locale_is_rejected_before_provider_call():
    provider = DeterministicLocalFixture()
    with session_for(provider) as (_, client, _, session, headers):
        payload = translation_payload(session, source_locale="not-registered")
        response = client.post("/v1/translate", json=payload, headers=headers)
        assert response.status_code == 422 and response.json()["detail"] == "LOCALE_NOT_REGISTERED"
        assert provider.ask_calls == provider.translation_calls == 0
