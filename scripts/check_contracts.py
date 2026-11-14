"""Validate supplied contracts and ensure unpublished content cannot be mistaken for production."""
import json
import re
import sys
from pathlib import Path
from jsonschema import Draft202012Validator

root = Path(__file__).resolve().parents[1]
for schema_name, fixture_name in [
    ("vehicle-snapshot.schema.json", "vehicle-snapshot.mock.json"),
    ("ask-response.schema.json", "ask-response.mock.json"),
    ("guide.schema.json", "guide.template.json"),
]:
    schema = json.loads((root / "contracts" / schema_name).read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads((root / "contracts" / fixture_name).read_text()))
    print(f"PASS {fixture_name}")
ui = json.loads((root / "content/locales/ui.json").read_text())
source = "\n".join(p.read_text() for p in (root / "android/app/src/main/java/com/carcue/app").glob("*.kt"))
keys = set(re.findall(r'get\("(ui_[A-Za-z0-9_]+)"\)', source))
assert keys <= ui.keys(), keys - ui.keys()
locales = json.loads((root / "content/locales/catalog.json").read_text())
mock_locales = {l["locale"] for l in locales if l.get("mock_visible")}
assert mock_locales == {"ko-KR", "en", "ja-JP"}
for key, translations in ui.items():
    for locale in mock_locales:
        assert translations.get(locale), (key, locale)
        assert set(re.findall(r"\{\w+\}", translations[locale])) == set(re.findall(r"\{\w+\}", translations["en"])), (key, locale)
print(f"PASS {len(keys)} referenced UI keys; {len(ui)} resources in all 3 mock languages, placeholders preserved")
sys.path.insert(0, str(root / "backend"))
from app.content import Catalog
from app.guide_rules import validate_state_guide_rules
from app.official_links import validate_support_contacts
Draft202012Validator.check_schema(json.loads((root / "contracts/support-contact.schema.json").read_text()))
catalog = Catalog()
for profile in catalog.profiles:
    support_issues = validate_support_contacts(profile, catalog.locales)
    assert not support_issues, (profile["profile_id"], support_issues)
print(f"PASS {sum(len(profile.get('support_contacts', [])) for profile in catalog.profiles)} registered official WEBSITE support reference(s), exact profile market")
Draft202012Validator.check_schema(json.loads((root / "contracts/state-guide-rules.schema.json").read_text()))
rules = json.loads((root / "content/state-guide-rules.json").read_text())
issues = validate_state_guide_rules(rules, Catalog())
assert not issues, issues
print(f"PASS {len(rules)} verified SDK state-to-guide rule(s), exact profile/manual and published content")
