"""Synthetic publication fixtures; these are not real vehicle instructions."""

import copy
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.content import Catalog
from app.guide_policy import validate_guide
from app.main import create_app


PROFILE = "fixture-car-2026-test"


@pytest.fixture
def records():
    profiles = [{"profile_id": PROFILE, "verification_status": "VERIFIED",
                 "manual_set_id": "synthetic-manual", "manual_version": "test-v1"}]
    locales = [{"locale": "ko-KR"}, {"locale": "en"}, {"locale": "ja-JP"}]
    guide = {
        "guide_id": "synthetic-guide", "profile_ids": [PROFILE],
        "manual_set_id": "synthetic-manual", "source_version": "test-v1",
        "topic": "synthetic", "title": "Synthetic fixture", "body": "Not actual vehicle guidance.",
        "locale": "ko-KR", "source_locale": "ko-KR", "glossary_version": None,
        "lifecycle": "PUBLISHED", "translation_review_status": "NOT_APPLICABLE",
        "sources": [{"source_id": "test-source", "title": "Synthetic test source, not a real manual",
                     "url": "https://example.test/manual%20fixture#section", "version": "test-v1",
                     "section": "synthetic-section", "verification_status": "VERIFIED"}],
        "steps": [{"step_id": "test-step", "order": 1, "title": "Synthetic step",
                   "body": "Only a policy test fixture.", "image_asset_id": None,
                   "official_cautions": [], "source_ids": ["test-source"],
                   "related_properties": [], "actions": []}],
    }
    return guide, profiles, locales


def codes(guide, profiles, locales):
    return {issue.code for issue in validate_guide(guide, profiles, locales)}


def catalog_with(records):
    guide, profiles, locales = records
    catalog = Catalog()
    catalog.guides, catalog.profiles, catalog.locales = [guide], profiles, locales
    return catalog


def test_valid_original_and_reviewed_translation_preserve_inputs(records):
    guide, profiles, locales = records
    original = copy.deepcopy(records)
    assert validate_guide(guide, profiles, locales) == []
    assert records == original
    guide.update(locale="ja-JP", translation_review_status="REVIEWED", glossary_version="synthetic-glossary-v1")
    assert validate_guide(guide, profiles, locales) == []


@pytest.mark.parametrize("lifecycle", ["PLANNED", "DRAFT", "REVIEWED"])
def test_unpublished_planning_placeholders_remain_allowed(records, lifecycle):
    guide, profiles, locales = records
    guide.update(lifecycle=lifecycle, profile_ids=["PROFILE_REPLACE_ME"],
                 manual_set_id=None, source_version=None, locale="LOCALE_REPLACE_ME",
                 source_locale="SOURCE_LOCALE_REPLACE_ME", translation_review_status="UNREVIEWED",
                 title="", body="", sources=[], steps=[])
    assert validate_guide(guide, profiles, locales) == []
    assert catalog_with(records).published(PROFILE) == []


def test_existing_unpublished_handoff_template_is_not_rejected():
    catalog = Catalog()
    assert catalog.publication_issues == {}
    assert catalog.published("demo-ioniq5-2024-kr", "ko-KR") == []
    assert all(profile["verification_status"] == "UNVERIFIED" for profile in catalog.profiles if profile.get("is_demo"))


@pytest.mark.parametrize("url", [
    "", "http://example.test/manual", "https://", "https:///manual", "https://?path=manual",
    "https://reviewer@example.test/manual", "https://user:password@example.test/manual",
    "https://example.test@attacker.test/manual", "https://example.test:bad/manual",
    "https://example.test:65536/manual", "https://example.test:/manual",
    "https://example.test\\@attacker.test/manual", "https://example.test\n/manual",
    "https://example.test/%0aheader", "https://localhost/manual", "https://127.0.0.1/manual",
    "https://bad_host.example/manual", "https://-bad.example/manual", "https://[::1]/manual",
])
def test_source_url_requires_valid_publisher_host_without_credentials(records, url):
    guide, profiles, locales = records
    guide["sources"][0]["url"] = url
    assert "INVALID_SOURCE_URL" in codes(guide, profiles, locales)


@pytest.mark.parametrize("field,value,expected", [
    ("profile_ids", ["unknown-profile"], "UNKNOWN_PROFILE"),
    ("manual_set_id", "other-manual", "MANUAL_SET_MISMATCH"),
    ("source_version", "other-version", "MANUAL_VERSION_MISMATCH"),
    ("locale", "not-registered", "UNKNOWN_LOCALE"),
    ("source_locale", "not-registered", "UNKNOWN_LOCALE"),
    ("title", " \t", "BLANK_FIELD"), ("body", "\n", "BLANK_FIELD"),
    ("guide_id", " ", "BLANK_FIELD"), ("topic", " ", "BLANK_FIELD"),
    ("manual_set_id", " ", "BLANK_FIELD"), ("source_version", " ", "BLANK_FIELD"),
    ("translation_review_status", "UNREVIEWED", "TRANSLATION_NOT_REVIEWED"),
])
def test_publication_scope_and_nonblank_fields(records, field, value, expected):
    guide, profiles, locales = records
    guide[field] = value
    assert expected in codes(guide, profiles, locales)


def test_all_scoped_profiles_must_be_verified_and_match_manual(records):
    guide, profiles, locales = records
    profiles.append({**profiles[0], "profile_id": "unverified-second-car", "verification_status": "UNVERIFIED"})
    guide["profile_ids"].append("unverified-second-car")
    assert "UNVERIFIED_PROFILE" in codes(guide, profiles, locales)
    assert catalog_with(records).published(PROFILE, "ko-KR") == []
    profiles[-1].update(verification_status="VERIFIED", manual_set_id="different-manual")
    assert "MANUAL_SET_MISMATCH" in codes(guide, profiles, locales)
    profiles[-1].update(manual_set_id="synthetic-manual", manual_version="different-version")
    assert "MANUAL_VERSION_MISMATCH" in codes(guide, profiles, locales)


def test_ambiguous_vehicle_profile_cannot_publish(records):
    guide, profiles, locales = records
    profiles.append(copy.deepcopy(profiles[0]))
    assert "AMBIGUOUS_PROFILE" in codes(guide, profiles, locales)


@pytest.mark.parametrize("change", ["unknown-field", "missing-title", "unverified-source", "null-section", "wrong-type", "non-object"])
def test_schema_errors_return_diagnostics_instead_of_raising(records, change):
    guide, profiles, locales = records
    if change == "unknown-field": guide["not-in-contract"] = True
    if change == "missing-title": del guide["title"]
    if change == "unverified-source": guide["sources"][0]["verification_status"] = "UNVERIFIED"
    if change == "null-section": guide["sources"][0]["section"] = None
    if change == "wrong-type": guide["steps"] = "not-an-array"
    if change == "non-object": guide = []
    issues = validate_guide(guide, profiles, locales)
    assert issues and all(issue.code == "SCHEMA_INVALID" for issue in issues)


@pytest.mark.parametrize("field,value,expected", [
    ("version", "wrong-version", "SOURCE_VERSION_MISMATCH"),
    ("section", " ", "BLANK_FIELD"), ("version", " ", "BLANK_FIELD"),
    ("title", " ", "BLANK_FIELD"), ("source_id", " ", "BLANK_FIELD"),
])
def test_source_metadata_is_complete_and_matches_guide(records, field, value, expected):
    guide, profiles, locales = records
    guide["sources"][0][field] = value
    assert expected in codes(guide, profiles, locales)


def test_duplicate_source_and_step_ids_and_unknown_references_are_rejected(records):
    guide, profiles, locales = records
    guide["sources"].append(copy.deepcopy(guide["sources"][0]))
    guide["steps"].append(copy.deepcopy(guide["steps"][0]))
    guide["steps"][1].update(order=2, source_ids=["invented-source"])
    found = codes(guide, profiles, locales)
    assert {"DUPLICATE_SOURCE_ID", "DUPLICATE_STEP_ID", "UNKNOWN_STEP_SOURCE"} <= found
    issues = validate_guide(guide, profiles, locales)
    assert any(issue.code == "UNKNOWN_STEP_SOURCE" and issue.path == "/steps/1/source_ids/0" for issue in issues)


@pytest.mark.parametrize("orders", [[2], [1, 3], [1, 1], [2, 1]])
def test_step_order_is_contiguous_and_matches_render_order(records, orders):
    guide, profiles, locales = records
    guide["steps"] = [{**copy.deepcopy(guide["steps"][0]), "step_id": f"step-{index}", "order": order}
                      for index, order in enumerate(orders)]
    assert "INVALID_STEP_ORDER" in codes(guide, profiles, locales)


@pytest.mark.parametrize("field,value,expected", [
    ("title", " ", "BLANK_FIELD"), ("body", " ", "BLANK_FIELD"),
    ("step_id", " ", "BLANK_FIELD"), ("source_ids", [], "MISSING_STEP_SOURCE"),
])
def test_published_steps_require_text_and_source_references(records, field, value, expected):
    guide, profiles, locales = records
    guide["steps"][0][field] = value
    assert expected in codes(guide, profiles, locales)


@pytest.mark.parametrize("review", ["UNREVIEWED", "NOT_APPLICABLE"])
def test_translations_cannot_bypass_review_by_changing_source_locale(records, review):
    guide, profiles, locales = records
    guide.update(locale="en", translation_review_status=review, glossary_version="fixture-v1")
    assert "TRANSLATION_NOT_REVIEWED" in codes(guide, profiles, locales)


@pytest.mark.parametrize("glossary", [None, "", " "])
def test_reviewed_translation_requires_glossary_version(records, glossary):
    guide, profiles, locales = records
    guide.update(locale="ja-JP", translation_review_status="REVIEWED", glossary_version=glossary)
    assert "MISSING_GLOSSARY_VERSION" in codes(guide, profiles, locales)


def test_catalog_refreshes_validation_after_profile_or_guide_changes(records):
    guide, profiles, _ = records
    catalog = catalog_with(records)
    assert catalog.published(PROFILE, "ko-KR") == [guide]
    guide["sources"][0]["url"] = "https://user:secret@example.test/manual"
    assert catalog.published(PROFILE, "ko-KR") == []
    assert any(issue.code == "INVALID_SOURCE_URL" for issue in catalog.publication_issues[0])
    guide["sources"][0]["url"] = "https://example.test/manual"
    assert catalog.published(PROFILE, "ko-KR") == [guide]
    assert catalog.publication_issues == {}
    profiles[0]["verification_status"] = "UNVERIFIED"
    assert catalog.published(PROFILE, "ko-KR") == []
    assert any(issue.code == "UNVERIFIED_PROFILE" for issue in catalog.publication_issues[0])


def test_duplicate_catalog_record_fails_closed_but_translation_is_distinct(records):
    guide, _, _ = records
    catalog = catalog_with(records)
    catalog.guides.append(copy.deepcopy(guide))
    assert catalog.published(PROFILE, "ko-KR") == []
    assert set(catalog.publication_issues) == {0, 1}
    assert all(issues[0].code == "DUPLICATE_GUIDE_RECORD" for issues in catalog.publication_issues.values())
    catalog.guides[1].update(locale="en", translation_review_status="REVIEWED", glossary_version="fixture-v1")
    assert catalog.published(PROFILE, "ko-KR") == [guide]
    assert catalog.published(PROFILE, "en") == [catalog.guides[1]]
    assert catalog.publication_issues == {}


def test_same_guide_id_can_have_a_distinct_manual_version_and_profile(records):
    guide, profiles, _ = records
    catalog = catalog_with(records)
    versioned = copy.deepcopy(guide)
    versioned.update(profile_ids=["fixture-car-next-manual"], source_version="test-v2")
    versioned["sources"][0]["version"] = "test-v2"
    profiles.append({**profiles[0], "profile_id": "fixture-car-next-manual", "manual_version": "test-v2"})
    catalog.guides.append(versioned)
    assert catalog.published(PROFILE, "ko-KR") == [guide]
    assert catalog.published("fixture-car-next-manual", "ko-KR") == [versioned]
    assert catalog.publication_issues == {}


def test_invalid_colliding_record_cannot_make_publication_identity_appear_unique(records):
    guide, _, _ = records
    catalog = catalog_with(records)
    invalid = copy.deepcopy(guide)
    invalid["title"] = None
    catalog.guides.append(invalid)
    assert catalog.published(PROFILE, "ko-KR") == []
    assert all(any(issue.code == "DUPLICATE_GUIDE_RECORD" for issue in issues)
               for issues in catalog.publication_issues.values())


def test_catalog_load_excludes_structurally_invalid_record_without_hiding_valid_one(records, tmp_path):
    guide, profiles, locales = records
    for directory in ("guides", "profiles", "locales"):
        (tmp_path / directory).mkdir()
    (tmp_path / "profiles/catalog.json").write_text(json.dumps(profiles))
    (tmp_path / "locales/catalog.json").write_text(json.dumps(locales))
    (tmp_path / "guides/valid.json").write_text(json.dumps(guide))
    invalid = copy.deepcopy(guide)
    invalid.update(guide_id="invalid-guide", title=None)
    (tmp_path / "guides/invalid.json").write_text(json.dumps(invalid))
    catalog = Catalog(tmp_path)
    assert catalog.published(PROFILE, "ko-KR") == [guide]
    assert any(issue.code == "SCHEMA_INVALID" for issue in catalog.publication_issues[0])


@pytest.mark.parametrize("change", ["credentials", "blank-text", "version", "unreviewed-translation", "schema"])
def test_actual_guide_routes_exclude_invalid_published_content(records, change):
    guide, _, _ = records
    catalog = catalog_with(records)
    app = create_app(db_path=":memory:", mode="LIVE", catalog=catalog)
    with TestClient(app) as client:
        params = {"profile_id": PROFILE, "locale": "ko-KR"}
        assert client.get("/v1/guides", params=params).json() == [guide]
        if change == "credentials": guide["sources"][0]["url"] = "https://official.example.test@attacker.test/"
        if change == "blank-text": guide["steps"][0]["body"] = " "
        if change == "version": guide["source_version"] = "mismatched-version"
        if change == "unreviewed-translation": guide["source_locale"] = "en"
        if change == "schema": guide["body"] = None
        assert client.get("/v1/guides", params=params).json() == []
        assert client.get("/v1/guides/synthetic-guide", params=params).status_code == 404
        assert catalog.publication_issues[0]
