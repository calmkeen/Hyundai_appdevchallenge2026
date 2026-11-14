"""Validate the shipped mapping from a verified SDK state scope to published content."""
import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

from .guide_policy import ValidationIssue

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "contracts/state-guide-rules.schema.json").read_text())


def validate_state_guide_rules(rules, catalog):
    issues = [ValidationIssue("SCHEMA_INVALID", "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in error.absolute_path), error.message)
              for error in Draft202012Validator(SCHEMA).iter_errors(rules)]
    if issues:
        return issues
    ids = Counter(rule["rule_id"] for rule in rules)
    scopes = Counter(tuple(rule[key] for key in ("profile_id", "manual_set_id", "source_version", "property_id", "area_id", "value"))
                     for rule in rules)
    for index, rule in enumerate(rules):
        path = f"/{index}"
        scope = tuple(rule[key] for key in ("profile_id", "manual_set_id", "source_version", "property_id", "area_id", "value"))
        if ids[rule["rule_id"]] != 1 or scopes[scope] != 1:
            issues.append(ValidationIssue("AMBIGUOUS_RULE", path, "Rule IDs and state scopes must be unique."))
        profile = catalog.profile(rule["profile_id"])
        if (not profile or profile.get("verification_status") != "VERIFIED"
                or profile.get("manual_set_id") != rule["manual_set_id"] or profile.get("manual_version") != rule["source_version"]):
            issues.append(ValidationIssue("RULE_PROFILE_MISMATCH", path, "Rule must match a verified profile and its manual edition."))
            continue
        guides = [guide for guide in catalog.published(rule["profile_id"])
                  if guide["guide_id"] == rule["guide_id"]]
        if not guides:
            issues.append(ValidationIssue("RULE_GUIDE_UNPUBLISHED", path + "/guide_id", "Rule must reference published content for this exact profile/manual."))
        elif any(not any(rule["property_id"] in step["related_properties"] for step in guide["steps"]) for guide in guides):
            issues.append(ValidationIssue("RULE_PROPERTY_UNRELATED", path + "/property_id", "Every published language variant must explicitly cover the mapped property."))
    return issues
