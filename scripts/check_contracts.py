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
source = (root / "android/app/src/main/java/com/carcue/app/CarCueApp.kt").read_text()
keys = set(re.findall(r'get\("(ui_[A-Za-z0-9_]+)"\)', source))
assert keys <= ui.keys(), keys - ui.keys()
assert all("ko-KR" in ui[k] and "en" in ui[k] for k in keys)
print(f"PASS {len(keys)} UI resource keys")
