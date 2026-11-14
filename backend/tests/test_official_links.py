"""Registry/API regression only; no external browser, vehicle or model calls."""
import copy
import json
import sys
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.answer_policy import answer_units
from app.content import Catalog
from app.main import create_app
from app.models import ModelAnswer
from app.official_links import manual_actions, resolve_manual, validate_support_contacts


ROOT = Path(__file__).resolve().parents[2]
PROFILE = "ioniq5-ne1-2024-kr"
SUPPORT = "hyundai-kr-customer-support"
URL = "https://www.hyundai.com/kr/ko/e/customer/center"
LOCALES = ("ko-KR", "en", "ja-JP")


class ReviewedUnitFixture:
    """Deterministic provider-port fixture, never a connected AI provider."""
    kind = "UNKNOWN"
    model = "official-links-test-fixture"

    def __init__(self):
        self.calls = 0

    async def ask(self, request, guides, history):
        self.calls += 1
        unit = answer_units(guides)[0]
        return ModelAnswer(status="ANSWERED", answer=unit["text"], source_ids=unit["source_ids"], follow_up_question=None)


def test_actual_registry_has_one_kr_website_and_keeps_demo_profiles_unverified():
    catalog = Catalog()
    contacts = catalog.support_contacts(PROFILE)
    assert len(contacts) == 1
    assert contacts[0] == {
        "id": SUPPORT, "kind": "WEBSITE", "title": "현대자동차 고객 문의", "url": URL,
        "market_code": "KR", "source_locale": "ko-KR", "verification_status": "VERIFIED",
        "evidence_url": URL, "reviewed_at": "2026-11-14T12:45:09.962773Z",
    }
    assert validate_support_contacts(catalog.profile(PROFILE), catalog.locales) == []
    assert catalog.support(PROFILE, SUPPORT) == contacts[0]
    assert catalog.support(PROFILE, URL) is None
    assert catalog.support(PROFILE, "unknown-id") is None
    assert catalog.support("demo-ioniq5-2024-kr", SUPPORT) is None
    assert catalog.support("demo-ioniq5n-2025-gb", SUPPORT) is None


@pytest.mark.parametrize("field,value", [
    ("kind", "PHONE"), ("id", URL), ("id", "valid-id\n"), ("title", "  "),
    ("market_code", "JP"), ("source_locale", "not-registered"),
    ("verification_status", "UNVERIFIED"), ("reviewed_at", "not-a-date"),
    ("reviewed_at", "2026-11-14T12:45:09"),
    ("reviewed_at", "2026-11-14T12:45:09+09:00"),
    ("url", "http://www.hyundai.com/kr/ko/e/customer/center"),
    ("url", "https://user:password@www.hyundai.com/support"),
    ("url", "https://www.hyundai.com/support%0aheader"),
    ("url", "https://localhost/support"), ("url", "https://127.0.0.1/support"),
    ("url", "https://www.hyundai.com:/support"), ("url", "https://www.hyundai.com:65536/support"),
    ("evidence_url", "javascript:alert(1)"),
])
def test_invalid_support_metadata_fails_closed_in_validation_and_runtime(field, value):
    catalog = Catalog()
    catalog.profile(PROFILE)["support_contacts"][0][field] = value
    assert validate_support_contacts(catalog.profile(PROFILE), catalog.locales)
    assert catalog.support_contacts(PROFILE) == []
    assert catalog.support(PROFILE, SUPPORT) is None


@pytest.mark.parametrize("mutation", ["duplicate", "unverified-profile", "missing-manual", "unexpected-field"])
def test_ambiguous_or_unverified_registries_are_not_exposed(mutation):
    catalog = Catalog()
    profile = catalog.profile(PROFILE)
    if mutation == "duplicate":
        profile["support_contacts"].append(copy.deepcopy(profile["support_contacts"][0]))
    elif mutation == "unverified-profile":
        profile["verification_status"] = "UNVERIFIED"
    elif mutation == "missing-manual":
        profile["manual_set_id"] = None
    else:
        profile["support_contacts"][0]["phone"] = "unregistered-number"
    assert validate_support_contacts(profile, catalog.locales)
    assert catalog.public_profile(profile)["support_contacts"] == []


@pytest.mark.parametrize("locale", LOCALES)
def test_api_uses_kr_registered_ids_independently_of_display_language(locale):
    catalog, provider = Catalog(), ReviewedUnitFixture()
    app = create_app(db_path=":memory:", mode="LIVE", catalog=catalog, provider=provider)
    with TestClient(app) as client:
        before = client.get(f"/v1/vehicle-profiles/{PROFILE}").json()
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": locale}).json()
        payload = {"request_id": "registered-links-" + locale, "session_id": session["session_id"],
                   "profile_id": PROFILE, "locale": locale, "question": "door ドア 문"}
        result = client.post("/v1/ask", json=payload, headers={"Authorization": "Bearer " + session["token"]}).json()
        assert result["status"] == "ANSWERED" and provider.calls == 1
        manual_ids = [item["target_id"] for item in result["actions"] if item["kind"] == "OPEN_MANUAL"]
        assert manual_ids == [item["source_id"] for item in result["citations"]]
        assert {"kind": "OPEN_SUPPORT", "target_id": SUPPORT} in result["actions"]
        for source_id in manual_ids:
            source = catalog.manual_source(PROFILE, locale, source_id)
            assert source is not None and source["profile_id"] == PROFILE
            assert "/NE1/2024/ko_KR/" in source["url"]
        assert all(not (action["target_id"] or "").startswith("https:") for action in result["actions"])
        assert before == client.get(f"/v1/vehicle-profiles/{PROFILE}").json()
        assert before["market_code"] == "KR" and before["support_contacts"][0]["url"] == URL
        jsonschema.validate(result, json.loads((ROOT / "contracts/ask-response.schema.json").read_text()))


@pytest.mark.parametrize("locale,question", [
    ("ko-KR", "브레이크액 교환방법은?"), ("en", "How do I replace brake fluid?"),
    ("ja-JP", "ブレーキフルードの交換方法は？"),
])
def test_unsupported_question_offers_registered_support_without_model_or_unrelated_manual(locale, question):
    provider = ReviewedUnitFixture()
    app = create_app(db_path=":memory:", mode="LIVE", provider=provider)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": locale}).json()
        result = client.post("/v1/ask", json={"request_id": "unsupported", "session_id": session["session_id"],
            "profile_id": PROFILE, "locale": locale, "question": question},
            headers={"Authorization": "Bearer " + session["token"]}).json()
        assert result["status"] == "NO_RELIABLE_SOURCE" and result["ai_provider"] == "NOT_CALLED"
        assert provider.calls == 0 and result["citations"] == []
        assert result["actions"] == [{"kind": "SELECT_PROFILE", "target_id": None},
                                      {"kind": "OPEN_SUPPORT", "target_id": SUPPORT}]


def test_manual_resolver_rejects_raw_url_other_profile_version_and_ambiguous_source():
    catalog = Catalog()
    guides = catalog.published(PROFILE, "ko-KR")
    source = guides[0]["sources"][0]
    assert catalog.manual_source(PROFILE, "ko-KR", source["url"]) is None
    assert catalog.manual_source("demo-ioniq5n-2025-gb", "ko-KR", source["source_id"]) is None
    old_profile = copy.deepcopy(catalog.profile(PROFILE))
    old_profile["manual_version"] = "old-version"
    assert resolve_manual(guides, old_profile, source["source_id"]) is None
    conflicting = copy.deepcopy(guides[0])
    conflicting["sources"][0]["url"] = "https://example.test/conflicting-source"
    assert resolve_manual([*guides, conflicting], catalog.profile(PROFILE), source["source_id"]) is None
    canonical = catalog.manual_source(PROFILE, "ko-KR", source["source_id"])
    assert canonical is not None
    assert manual_actions([{**canonical, "url": "https://example.test/unregistered"}], guides, catalog.profile(PROFILE)) == []


def test_legacy_published_url_action_remains_preserved_but_is_never_resolved_as_an_id():
    catalog = Catalog()
    guide = catalog.published(PROFILE, "ko-KR")[0]
    legacy = next(action for step in guide["steps"] for action in step["actions"] if action["kind"] == "OPEN_MANUAL")
    assert legacy["target_id"].startswith("https://ownersmanual.hyundai.com/")
    assert catalog.manual_source(PROFILE, "ko-KR", legacy["target_id"]) is None


@pytest.mark.parametrize("kind", ["OPEN_MANUAL", "OPEN_SUPPORT"])
@pytest.mark.parametrize("target", [None, "", URL, "javascript:alert(1)"])
def test_response_contract_rejects_external_url_or_null_action_targets(kind, target):
    schema = json.loads((ROOT / "contracts/ask-response.schema.json").read_text())["properties"]["actions"]["items"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"kind": kind, "target_id": target}, schema)


def test_public_profile_api_drops_invalid_support_registry_on_every_read():
    catalog = Catalog()
    catalog.profile(PROFILE)["support_contacts"][0]["market_code"] = "US"
    app = create_app(db_path=":memory:", mode="LIVE", catalog=catalog, provider=ReviewedUnitFixture())
    with TestClient(app) as client:
        assert client.get(f"/v1/vehicle-profiles/{PROFILE}").json()["support_contacts"] == []
        assert all(profile["support_contacts"] == [] for profile in client.get("/v1/vehicle-profiles").json())


def test_duplicate_profile_identity_cannot_offer_a_support_action():
    catalog = Catalog()
    catalog.profiles.append(copy.deepcopy(catalog.profile(PROFILE)))
    assert catalog.support_contacts(PROFILE) == []
    assert catalog.support(PROFILE, SUPPORT) is None


@pytest.mark.parametrize("source_id", ["source with space", "https://example.test/source", "x" * 129, "source\nid", "source-id\n"])
def test_publication_valid_source_id_outside_action_contract_cannot_become_manual_target(source_id):
    catalog, provider = Catalog(), ReviewedUnitFixture()
    guide = next(item for item in catalog.guides if item.get("guide_id") == "ioniq5-door-open-check" and item["locale"] == "ko-KR")
    previous = guide["sources"][0]["source_id"]
    guide["sources"][0]["source_id"] = source_id
    for step in guide["steps"]:
        step["source_ids"] = [source_id if ref == previous else ref for ref in step["source_ids"]]
    assert catalog.published(PROFILE, "ko-KR") == [guide]  # Preserve the broader publication contract.
    assert catalog.manual_source(PROFILE, "ko-KR", source_id) is None
    app = create_app(db_path=":memory:", mode="LIVE", catalog=catalog, provider=provider)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": "ko-KR"}).json()
        result = client.post("/v1/ask", json={"request_id": "legacy-source-id", "session_id": session["session_id"],
            "profile_id": PROFILE, "locale": "ko-KR", "question": "문을 닫기 전에 무엇을 확인하나요?"},
            headers={"Authorization": "Bearer " + session["token"]}).json()
        assert result["status"] == "ANSWERED" and provider.calls == 1
        assert source_id in [citation["source_id"] for citation in result["citations"]]
        manual_targets = [action["target_id"] for action in result["actions"] if action["kind"] == "OPEN_MANUAL"]
        assert manual_targets == [guide["sources"][1]["source_id"]]
        assert {"kind": "OPEN_SUPPORT", "target_id": SUPPORT} in result["actions"]
        jsonschema.validate(result, json.loads((ROOT / "contracts/ask-response.schema.json").read_text()))
