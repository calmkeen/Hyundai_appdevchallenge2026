"""Canonical answer assembly over publication-validated, reviewed summaries.

Protected registered guides are indivisible: step context cannot remove earlier
prerequisites or explicit caution summaries. This is not new OEM text,
translation certification, or vehicle identity verification.
"""
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
_SCHEMA = json.loads((ROOT / "contracts/answer-bundles.schema.json").read_text())
_VALIDATOR = Draft202012Validator(_SCHEMA)
# Reserve the deployed guide namespace even if a registry entry is removed or
# corrupted: configuration failure must never restore the old partial units.
_REQUIRED_GUIDES = {"ioniq5-door-open-check"}
_PROTECTED_GUIDES = _REQUIRED_GUIDES | {
    "ioniq5-ac-charging-check", "ioniq5-seat-mirror-before-driving", "ioniq5-cluster-display-check",
}


def payload_digest(guide):
    return hashlib.sha256(json.dumps(guide, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def closing_bundle_text(guide):
    # Kept as a compatible name for deployed door callers; assembly is topic-independent.
    return "\n".join([guide["body"], *[part for step in guide["steps"]
        for part in ([step["body"], *step["official_cautions"]] if guide["topic"] == "door"
                     else [step["title"], step["body"], *step["official_cautions"]])]])


def _rules(registry):
    if not _VALIDATOR.is_valid(registry):
        return None
    rules = registry["bundles"]
    ids = [rule["guide_id"] for rule in rules]
    if len(ids) != len(set(ids)) or not _REQUIRED_GUIDES.issubset(ids):
        return None
    for rule in rules:
        if (len(rule["locales"]) != len(set(rule["locales"]))
                or len(rule["source_ids"]) != len(set(rule["source_ids"]))
                or len(rule["profile_ids"]) != len(set(rule["profile_ids"]))
                or [step["order"] for step in rule["required_steps"]] != list(range(1, len(rule["required_steps"]) + 1))
                or len({step["step_id"] for step in rule["required_steps"]}) != len(rule["required_steps"])
                or len({pin["locale"] for pin in rule["records"]}) != len(rule["records"])
                or {pin["locale"] for pin in rule["records"]} != set(rule["locales"])):
            return None
        required_cautions = rule.get("required_caution_step_ids", [step["step_id"] for step in rule["required_steps"]])
        if not set(required_cautions).issubset(step["step_id"] for step in rule["required_steps"]):
            return None
        if rule["topic"] == "door" and set(required_cautions) != {step["step_id"] for step in rule["required_steps"]}:
            return None
    return rules


def _bundle(guide, rule):
    try:
        if (guide["guide_id"] != rule["guide_id"] or guide["profile_ids"] != rule["profile_ids"]
                or guide["manual_set_id"] != rule["manual_set_id"] or guide["source_version"] != rule["source_version"]
                or guide["topic"] != rule["topic"] or guide["locale"] not in rule["locales"]
                or guide["lifecycle"] != "PUBLISHED"
                or [source["source_id"] for source in guide["sources"]] != rule["source_ids"]
                or [{"step_id": step["step_id"], "order": step["order"], "source_ids": step["source_ids"]}
                    for step in guide["steps"]] != rule["required_steps"]
                or any(not step["official_cautions"] for step in guide["steps"] if step["step_id"] in
                       rule.get("required_caution_step_ids", [item["step_id"] for item in rule["required_steps"]]))
                or {ref for step in guide["steps"] for ref in step["source_ids"]} != set(rule["source_ids"])):
            return None
        pin = next(item for item in rule["records"] if item["locale"] == guide["locale"])
        text = closing_bundle_text(guide)
        if (not text or len(text) > 3000 or payload_digest(guide) != pin["payload_sha256"]
                or hashlib.sha256(text.encode()).hexdigest() != pin["bundle_sha256"]):
            return None
        identity = ":".join((guide["guide_id"], guide["locale"], guide["source_version"]))
        return {"unit_id": identity + rule["unit_suffix"], "guide_id": guide["guide_id"],
                "text": text, "source_ids": list(rule["source_ids"])}
    except (KeyError, TypeError, ValueError, StopIteration):
        return None


def validate_bundle_registry(registry, guides=None):
    """Static registry checks, optionally checking all locale pins against content."""
    rules = _rules(registry)
    if rules is None:
        return ["INVALID_ANSWER_BUNDLE_REGISTRY"]
    issues = []
    if guides is not None:
        for rule in rules:
            for locale in rule["locales"]:
                candidates = [g for g in guides if g.get("guide_id") == rule["guide_id"] and g.get("locale") == locale]
                if len(candidates) != 1 or _bundle(candidates[0], rule) is None:
                    issues.append("BUNDLE_RECORD_PIN_MISMATCH:" + rule["guide_id"] + ":" + locale)
    return issues


try:
    _REGISTRY = json.loads((ROOT / "content/answer-bundles.json").read_text())
except (OSError, ValueError):
    _REGISTRY = None


def answer_units(guides):
    units = []
    rules = _rules(_REGISTRY)
    for guide in guides:
        registered = next((rule for rule in rules or [] if rule["guide_id"] == guide["guide_id"]), None)
        if guide["guide_id"] in _PROTECTED_GUIDES or registered is not None:
            unit = _bundle(guide, registered) if registered is not None else None
            if unit is not None:
                units.append(unit)
            continue
        identity = ":".join((guide["guide_id"], guide["locale"], guide["source_version"]))
        units.append({
            "unit_id": identity + ":body", "guide_id": guide["guide_id"],
            "text": guide["body"],
            "source_ids": [source["source_id"] for source in guide["sources"]],
        })
        for step in guide["steps"]:
            units.append({
                "unit_id": identity + ":step:" + step["step_id"],
                "guide_id": guide["guide_id"],
                "text": "\n".join([step["body"], *step["official_cautions"]]),
                "source_ids": list(step["source_ids"]),
            })
    return units


def validate_answer(output, guides):
    """Return one exactly grounded ANSWERED unit or raise a stable ValueError.

    The API layer separately replaces other model statuses with localized server
    text. No whitespace trimming or substring match may drop a caution/negation.
    """
    def field(name):
        return output.get(name) if isinstance(output, dict) else getattr(output, name, None)

    if field("status") != "ANSWERED":
        raise ValueError("ANSWER_STATUS_REQUIRED")
    text, citations = field("answer"), field("source_ids")
    if not isinstance(text, str) or not text:
        raise ValueError("EMPTY_GROUNDED_ANSWER")
    if (not isinstance(citations, list) or not citations
            or any(not isinstance(source_id, str) or not source_id for source_id in citations)
            or len(citations) != len(set(citations))):
        raise ValueError("INVALID_ANSWER_CITATIONS")
    matches = [unit for unit in answer_units(guides)
               if text == unit["text"] and set(citations) == set(unit["source_ids"])]
    if not matches:
        raise ValueError("ANSWER_NOT_GROUNDED_IN_COMPLETE_UNIT")
    if len(matches) != 1:
        raise ValueError("AMBIGUOUS_ANSWER_UNIT")
    return matches[0]
