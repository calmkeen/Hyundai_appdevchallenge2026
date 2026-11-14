"""Complete-caution policy/API/upgrade tests. No actual model, SDK or external HTTP."""
import asyncio
import copy
import hashlib
import itertools
import json
import sys
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import answer_policy
from app.answer_policy import answer_units, closing_bundle_text, payload_digest, validate_answer, validate_bundle_registry
from app.content import Catalog
from app.local_provider import LocalProviderError, OllamaProvider
from app.main import create_app
from app.models import AskRequest, ModelAnswer

ROOT = Path(__file__).resolve().parents[2]
PROFILE, GUIDE = "ioniq5-ne1-2024-kr", "ioniq5-door-open-check"
LOCALES = ("ko-KR", "en", "ja-JP")
QUESTIONS = {"ko-KR": "문을 닫기 전에 무엇을 확인해야 하나요?",
             "en": "What should I check before closing the door?", "ja-JP": "ドアを閉める前に何を確認すればいいですか？"}


class Fixture:
    kind, model = "UNKNOWN", "complete-caution-test-double"
    def __init__(self, transform=None):
        self.calls, self.translation_calls = 0, 0
        self.transform = transform

    async def ask(self, request, guides, history):
        self.calls += 1
        unit = answer_units(guides)[0]
        value = {"status": "ANSWERED", "answer": unit["text"], "source_ids": unit["source_ids"], "follow_up_question": None}
        if self.transform:
            value = self.transform(value, guides[0])
        return ModelAnswer(**value)

    async def translate(self, request):
        self.translation_calls += 1
        raise AssertionError("Stored manual translation must never call a provider")


@contextmanager
def api(locale="ko-KR", catalog=None, provider=None):
    catalog, provider = catalog or Catalog(), provider or Fixture()
    app = create_app(db_path=":memory:", catalog=catalog, provider=provider, mode="LIVE")
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": locale}).json()
        headers = {"Authorization": "Bearer " + session["token"]}
        yield app, client, catalog, provider, session, headers


def ask(session, locale="ko-KR"):
    return {"request_id": "closing-check", "session_id": session["session_id"], "profile_id": PROFILE,
            "locale": locale, "question": QUESTIONS[locale],
            "guide_context": {"guide_id": GUIDE, "step_id": "check-closure-display"}}


def partial(guide, index):
    if index == 0:
        return guide["body"]
    step = guide["steps"][index - 1]
    return "\n".join([step["body"], *step["official_cautions"]])


def seed_result(app, session, request_id, value):
    with app.state.store.transaction() as db:
        fingerprint = db.execute("SELECT fingerprint FROM results WHERE session=? AND request=?",
                                 (session["session_id"], request_id)).fetchone()[0]
        db.execute("UPDATE results SET response=? WHERE session=? AND request=?",
                   (json.dumps(value, ensure_ascii=False), session["session_id"], request_id))
    return fingerprint


def assert_fingerprint(app, session, request_id, expected):
    with app.state.store.transaction() as db:
        assert db.execute("SELECT fingerprint FROM results WHERE session=? AND request=?",
                          (session["session_id"], request_id)).fetchone()[0] == expected


def test_registered_payload_and_bundle_pins_match_all_three_immutable_published_records():
    registry = json.loads((ROOT / "content/answer-bundles.json").read_text())
    catalog = Catalog()
    assert validate_bundle_registry(registry, catalog.guides) == []
    for locale in LOCALES:
        guide = catalog.published(PROFILE, locale)[0]
        unit, = answer_units([guide])
        assert unit["unit_id"].endswith(":closing-bundle:v1")
        assert unit["text"] == "\n".join([guide["body"], *[part for step in guide["steps"] for part in [step["body"], *step["official_cautions"]]]])
        assert unit["source_ids"] == [source["source_id"] for source in guide["sources"]]
        assert len(unit["source_ids"]) == 2 and len(unit["text"]) <= 3000


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("part_index", range(5), ids=["summary", "pinch-body", "pinch-caution", "closure-body", "closure-caution"])
def test_removing_any_required_body_or_caution_is_rejected_even_with_both_citations(locale, part_index):
    guide = Catalog().published(PROFILE, locale)[0]
    parts = [guide["body"]]
    for step in guide["steps"]:
        parts.extend([step["body"], *step["official_cautions"]])
    unit, = answer_units([guide])
    incomplete = unit["text"].replace(parts[part_index], "", 1)
    provider = Fixture(lambda value, _: {**value, "answer": incomplete})
    with api(locale, provider=provider) as (_, client, _, _, session, headers):
        result = client.post("/v1/ask", json=ask(session, locale), headers=headers).json()
        assert result["status"] == "TEMPORARILY_UNAVAILABLE"
        assert result["answer"] != incomplete and result["citations"] == result["actions"] == []
        assert provider.calls == 1


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("old_unit", [0, 1, 2], ids=["old-body", "old-pinch-step", "old-closure-step"])
def test_old_complete_partial_unit_is_no_longer_a_current_answer_or_translation(locale, old_unit):
    guide = Catalog().published(PROFILE, locale)[0]
    text = partial(guide, old_unit)
    provider = Fixture(lambda value, _: {**value, "answer": text})
    with api(locale, provider=provider) as (_, client, _, _, session, headers):
        answer = client.post("/v1/ask", json=ask(session, locale), headers=headers).json()
        assert answer["status"] == "TEMPORARILY_UNAVAILABLE" and answer["citations"] == []
        target = LOCALES[(LOCALES.index(locale) + 1) % len(LOCALES)]
        result = client.post("/v1/translate", json={"request_id": "legacy-answer", "session_id": session["session_id"],
            "profile_id": PROFILE, "source_locale": locale, "target_locale": target, "text": text, "content_kind": "ANSWER"}, headers=headers).json()
        assert result["status"] == "TEMPORARILY_UNAVAILABLE" and result["translated_text"] is None
        assert result["ai_provider"] == "NOT_CALLED" and provider.translation_calls == 0


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("only_source", [0, 1])
def test_a_bundle_with_only_one_of_the_two_required_sources_is_rejected(locale, only_source):
    provider = Fixture(lambda value, _: {**value, "source_ids": [value["source_ids"][only_source]]})
    with api(locale, provider=provider) as (_, client, _, _, session, headers):
        result = client.post("/v1/ask", json=ask(session, locale), headers=headers).json()
        assert result["status"] == "TEMPORARILY_UNAVAILABLE" and result["citations"] == []


@pytest.mark.parametrize("change", ["profile", "manual", "version", "locale", "missing-step", "empty-caution", "changed-caution", "changed-source", "topic"])
def test_protected_identity_never_falls_back_to_old_units_on_scope_or_payload_change(change):
    guide = copy.deepcopy(Catalog().published(PROFILE, "ko-KR")[0])
    if change == "profile": guide["profile_ids"] = ["another-profile"]
    elif change == "manual": guide["manual_set_id"] = "another-manual"
    elif change == "version": guide["source_version"] = "future-version-needs-policy-review"
    elif change == "locale": guide["locale"] = "de-DE"
    elif change == "missing-step": guide["steps"] = guide["steps"][1:]
    elif change == "empty-caution": guide["steps"][0]["official_cautions"] = []
    elif change == "changed-caution": guide["steps"][0]["official_cautions"][0] += " changed"
    elif change == "changed-source": guide["sources"][0]["source_id"] = "unknown-source"
    else: guide["topic"] = "charging"
    assert answer_units([guide]) == []


@pytest.mark.parametrize("registry", [None, {}, {"schema_version": 1, "bundles": []}])
def test_missing_or_broken_registry_blocks_protected_answers_without_affecting_unrelated_guides(monkeypatch, registry):
    protected = Catalog().published(PROFILE, "ko-KR")[0]
    other = copy.deepcopy(protected); other["guide_id"] = "synthetic-unrelated-guide"
    monkeypatch.setattr(answer_policy, "_REGISTRY", registry)
    assert answer_units([protected]) == []
    assert len(answer_units([other])) == 3


@pytest.mark.parametrize("field", ["payload_sha256", "bundle_sha256"])
def test_invalid_pin_does_not_promote_old_partial_units(monkeypatch, field):
    registry = copy.deepcopy(answer_policy._REGISTRY)
    registry["bundles"][0]["records"][0][field] = "0" * 64
    monkeypatch.setattr(answer_policy, "_REGISTRY", registry)
    assert answer_units(Catalog().published(PROFILE, "ko-KR")) == []


def test_oversized_even_repinned_bundle_is_rejected_without_truncation(monkeypatch):
    guide = copy.deepcopy(Catalog().published(PROFILE, "ko-KR")[0]); guide["body"] = "x" * 3001
    registry = copy.deepcopy(answer_policy._REGISTRY); pin = registry["bundles"][0]["records"][0]
    pin["payload_sha256"] = payload_digest(guide); pin["bundle_sha256"] = hashlib.sha256(closing_bundle_text(guide).encode()).hexdigest()
    monkeypatch.setattr(answer_policy, "_REGISTRY", registry)
    assert answer_units([guide]) == []


@pytest.mark.parametrize("locale", LOCALES)
def test_missing_caution_in_an_otherwise_published_record_prevents_any_model_call(locale):
    catalog = Catalog(); guide = next(g for g in catalog.guides if g.get("guide_id") == GUIDE and g["locale"] == locale)
    guide["steps"][0]["official_cautions"] = []
    assert catalog.published(PROFILE, locale) == [guide]
    with api(locale, catalog) as (_, client, _, provider, session, headers):
        result = client.post("/v1/ask", json=ask(session, locale), headers=headers).json()
        assert result["status"] == "NO_RELIABLE_SOURCE" and result["ai_provider"] == "NOT_CALLED"
        assert provider.calls == 0 and result["citations"] == []


@pytest.mark.parametrize("locale", LOCALES)
def test_local_model_cannot_select_the_previous_second_step_id(locale):
    guide = Catalog().published(PROFILE, locale)[0]
    old_id = ":".join((GUIDE, locale, guide["source_version"])) + ":step:check-closure-display"
    body = {"model": "qwen3:4b", "done": True, "done_reason": "stop", "message": {"role": "assistant", "content": json.dumps({"status": "ANSWERED", "unit_id": old_id})}}
    provider = OllamaProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body)))
    with pytest.raises(LocalProviderError, match="LOCAL_INVALID_SELECTION"):
        asyncio.run(provider.ask(AskRequest(**ask({"session_id": "synthetic-session"}, locale)), [guide], []))


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("old_unit", [0, 1, 2])
def test_existing_db_partial_answer_cache_is_rejected_without_recalculation_or_fingerprint_loss(locale, old_unit):
    with api(locale) as (app, client, catalog, provider, session, headers):
        payload = ask(session, locale)
        current = client.post("/v1/ask", json=payload, headers=headers).json()
        assert current["status"] == "ANSWERED" and provider.calls == 1
        old_text = partial(catalog.published(PROFILE, locale)[0], old_unit)
        fingerprint = seed_result(app, session, payload["request_id"], {**current, "answer": old_text})
        for _ in range(2):
            rejected = client.post("/v1/ask", json=payload, headers=headers).json()
            assert rejected["status"] == "NO_RELIABLE_SOURCE" and rejected["ai_provider"] == "NOT_CALLED"
            assert old_text not in rejected["answer"] and rejected["citations"] == []
            assert provider.calls == 1
            assert_fingerprint(app, session, payload["request_id"], fingerprint)


@pytest.mark.parametrize("field,value", [("profile_id", "other-car"), ("source_version", "old-version"), ("url", "https://example.test/other-manual")])
def test_even_current_bundle_cache_requires_current_canonical_citation_metadata(field, value):
    with api() as (app, client, _, provider, session, headers):
        payload = ask(session); current = client.post("/v1/ask", json=payload, headers=headers).json()
        current["citations"][0][field] = value
        seed_result(app, session, payload["request_id"], current)
        rejected = client.post("/v1/ask", json=payload, headers=headers).json()
        assert rejected["status"] == "NO_RELIABLE_SOURCE" and rejected["citations"] == [] and provider.calls == 1


@pytest.mark.parametrize("source,target", list(itertools.permutations(LOCALES, 2)))
@pytest.mark.parametrize("old_unit", [0, 1, 2])
def test_existing_db_legacy_answer_translation_cannot_replay_after_upgrade(source, target, old_unit):
    with api(target) as (app, client, catalog, provider, session, headers):
        text = partial(catalog.published(PROFILE, source)[0], old_unit)
        payload = {"request_id": "old-translation", "session_id": session["session_id"], "profile_id": PROFILE,
            "source_locale": source, "target_locale": target, "content_kind": "ANSWER", "text": text}
        first = client.post("/v1/translate", json=payload, headers=headers).json()
        legacy = {**first, "status": "TRANSLATED", "translated_text": partial(catalog.published(PROFILE, target)[0], old_unit),
            "review_status": "REVIEWED", "ai_provider": "STORED_GUIDE"}
        fingerprint = seed_result(app, session, payload["request_id"], legacy)
        for _ in range(2):
            result = client.post("/v1/translate", json=payload, headers=headers).json()
            assert result["status"] == "TEMPORARILY_UNAVAILABLE" and result["translated_text"] is None
            assert result["ai_provider"] == "NOT_CALLED" and result["review_status"] == "UNREVIEWED"
            assert result["original_text"] == text
            assert provider.calls == provider.translation_calls == 0
            assert_fingerprint(app, session, payload["request_id"], fingerprint)
