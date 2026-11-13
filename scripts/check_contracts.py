"""Validate supplied contracts and ensure unpublished content cannot be mistaken for production."""
import json
import re
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
