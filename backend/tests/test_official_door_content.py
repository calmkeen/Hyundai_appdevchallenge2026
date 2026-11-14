"""Verify shipped official-manual content and rule boundaries, not simulated SDK values."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.content import Catalog
from app.guide_rules import validate_state_guide_rules
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "ioniq5-ne1-2024-kr"
GUIDE = "ioniq5-door-open-check"
VERSION = "NE1-2024-KR-ko_KR-D202406100040-20240722"


def rules():
    return json.loads((ROOT / "content/state-guide-rules.json").read_text())


def test_official_profile_is_explicit_manual_selection_not_sdk_identification():
    catalog = Catalog()
    profile = catalog.profile(PROFILE)
    assert profile["model_code"] == "NE1" and profile["model_year"] == 2024 and profile["market_code"] == "KR"
    assert profile["verification_status"] == "VERIFIED" and profile["manual_version"] == VERSION
    assert profile["selection_method"] == "USER_CONFIRMED"
    assert profile["sdk_vehicle_identity_verified"] is False and not profile["is_demo"]
    assert all(profile["verification_status"] == "UNVERIFIED" for profile in catalog.profiles if profile.get("is_demo"))
    assert not catalog.publication_issues


@pytest.mark.parametrize("locale", ["ko-KR", "en", "ja-JP"])
def test_live_http_serves_the_exact_profile_language_and_official_sources(locale):
    app = create_app(db_path=":memory:", mode="LIVE")
    with TestClient(app) as client:
        profiles = client.get("/v1/vehicle-profiles").json()
        assert [profile["profile_id"] for profile in profiles] == [PROFILE]
        assert client.get("/v1/vehicle-profiles/demo-ioniq5-2024-kr").status_code == 404
        response = client.get("/v1/guides", params={"profile_id": PROFILE, "locale": locale, "topic": "door"})
        assert response.status_code == 200
        guide, = response.json()
        assert guide["guide_id"] == GUIDE and guide["locale"] == locale and guide["source_locale"] == "ko-KR"
        assert guide["source_version"] == VERSION and guide["lifecycle"] == "PUBLISHED"
        assert guide["translation_review_status"] == ("NOT_APPLICABLE" if locale == "ko-KR" else "REVIEWED")
        assert len(guide["steps"]) == 2
        assert {source["url"] for source in guide["sources"]} == {
            "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/idff13cd5359c.html",
            "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id0d6d99a8d21.html"}
        assert all(source["version"] == VERSION for source in guide["sources"])
        assert all("door.position" in step["related_properties"] for step in guide["steps"])
        assert client.get(f"/v1/guides/{GUIDE}", params={"profile_id": PROFILE, "locale": locale}).json() == guide
        assert client.get("/v1/guides", params={"profile_id": PROFILE, "locale": "de-DE"}).json() == []


def test_verified_state_rule_points_to_every_published_language_variant():
    assert validate_state_guide_rules(rules(), Catalog()) == []
    rule, = rules()
    assert rule["area_id"] == "ROW_1_LEFT" and rule["value"] == "OPEN"


@pytest.mark.parametrize("field,value,code", [
    ("profile_id", "demo-ioniq5-2024-kr", "RULE_PROFILE_MISMATCH"),
    ("manual_set_id", "other-manual", "RULE_PROFILE_MISMATCH"),
    ("source_version", "2025", "RULE_PROFILE_MISMATCH"),
    ("guide_id", "missing-guide", "RULE_GUIDE_UNPUBLISHED"),
    ("property_id", "lock.state", "SCHEMA_INVALID"),
    ("area_id", "ROW_1_RIGHT", "SCHEMA_INVALID"),
    ("value", "CLOSED", "SCHEMA_INVALID"),
])
def test_unverified_or_unrelated_state_scope_is_rejected(field, value, code):
    data = rules()
    data[0][field] = value
    assert code in {issue.code for issue in validate_state_guide_rules(data, Catalog())}


def test_ambiguous_rule_or_unpublished_guide_cannot_be_shipped():
    data = rules()
    assert "AMBIGUOUS_RULE" in {issue.code for issue in validate_state_guide_rules(data * 2, Catalog())}
    catalog = Catalog()
    for guide in catalog.guides:
        guide["lifecycle"] = "DRAFT"
    assert "RULE_GUIDE_UNPUBLISHED" in {issue.code for issue in validate_state_guide_rules(data, catalog)}


def test_every_translation_must_retain_the_related_property():
    catalog = Catalog()
    for guide in catalog.guides:
        if guide["guide_id"] == GUIDE and guide["locale"] == "ja-JP":
            for step in guide["steps"]:
                step["related_properties"] = []
    assert "RULE_PROPERTY_UNRELATED" in {issue.code for issue in validate_state_guide_rules(rules(), catalog)}


@pytest.mark.parametrize("kind", ["profile", "guide"])
def test_development_bootstrap_refuses_to_overwrite_reviewed_content(tmp_path, kind):
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts/prepare_content.py", tmp_path / "scripts/prepare_content.py")
    if kind == "profile":
        path = tmp_path / "content/profiles/catalog.json"
        value = [{"verification_status": "VERIFIED"}]
    else:
        path = tmp_path / "content/guides/reviewed.json"
        value = {"lifecycle": "PUBLISHED"}
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(value))
    before = {str(file): file.read_bytes() for file in tmp_path.rglob("*") if file.is_file()}
    result = subprocess.run([sys.executable, str(tmp_path / "scripts/prepare_content.py")], capture_output=True, text=True)
    assert result.returncode != 0 and "Refusing to overwrite reviewed content" in result.stderr
    assert {str(file): file.read_bytes() for file in tmp_path.rglob("*") if file.is_file()} == before
