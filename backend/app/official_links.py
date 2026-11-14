"""Resolve registered official references, never a model-supplied URL.

VERIFIED is a content editor's source assertion, not OEM approval or a network
availability guarantee. Resolution rechecks the current profile and publication
scope; UI language never changes the vehicle's sales market.
"""
import json
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from .guide_policy import ValidationIssue, _valid_https_url


_SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "contracts/support-contact.schema.json").read_text())
_VALIDATOR = Draft202012Validator(_SCHEMA)


def validate_support_contacts(profile, locales):
    """Validate the complete per-profile registry; invalid registries fail closed."""
    issues = []
    contacts = profile.get("support_contacts", [])
    if not isinstance(contacts, list):
        return [ValidationIssue("INVALID_SUPPORT_CONTACTS", "/support_contacts", "Expected a contact array.")]
    registered_locales = {item.get("locale") for item in locales}
    ids = set()
    for index, contact in enumerate(contacts):
        prefix = f"/support_contacts/{index}"
        errors = list(_VALIDATOR.iter_errors(contact))
        if errors:
            issues.extend(ValidationIssue("INVALID_SUPPORT_CONTACT", prefix, "Support contact does not match the contract.") for _ in errors)
            continue
        if contact["id"] in ids:
            issues.append(ValidationIssue("DUPLICATE_SUPPORT_ID", prefix + "/id", "Support IDs must be unique within a profile."))
        ids.add(contact["id"])
        if (profile.get("verification_status") != "VERIFIED"
                or any(not isinstance(profile.get(field), str) or not profile[field].strip()
                       for field in ("profile_id", "manual_set_id", "manual_version"))):
            issues.append(ValidationIssue("UNVERIFIED_SUPPORT_PROFILE", prefix, "Support requires a verified profile and manual scope."))
        if contact["market_code"] != profile.get("market_code"):
            issues.append(ValidationIssue("SUPPORT_MARKET_MISMATCH", prefix + "/market_code", "Support market must match the vehicle, not the UI language."))
        if contact["source_locale"] not in registered_locales:
            issues.append(ValidationIssue("UNKNOWN_SUPPORT_LOCALE", prefix + "/source_locale", "Support source language must be registered."))
        if contact["verification_status"] != "VERIFIED":
            issues.append(ValidationIssue("UNVERIFIED_SUPPORT_CONTACT", prefix, "Only verified support references may be offered."))
        if not contact["title"].strip():
            issues.append(ValidationIssue("BLANK_SUPPORT_TITLE", prefix + "/title", "A support title is required."))
        for field in ("url", "evidence_url"):
            if not _valid_https_url(contact[field]):
                issues.append(ValidationIssue("INVALID_SUPPORT_URL", prefix + "/" + field, "Support and evidence must use unambiguous HTTPS DNS URLs."))
        try:
            reviewed = datetime.fromisoformat(contact["reviewed_at"].replace("Z", "+00:00"))
            if reviewed.tzinfo is None or reviewed.utcoffset().total_seconds() != 0:
                raise ValueError("UTC required")
        except (ValueError, AttributeError):
            issues.append(ValidationIssue("INVALID_SUPPORT_REVIEW_TIME", prefix + "/reviewed_at", "Review time must be an ISO 8601 UTC timestamp."))
    return issues


def registered_support_contacts(profile, locales):
    if profile is None or validate_support_contacts(profile, locales):
        return []
    return list(profile.get("support_contacts", []))


def resolve_support(profile, locales, target_id):
    """IDs only. A URL, unknown ID, or invalid registry cannot become an action."""
    matches = [item for item in registered_support_contacts(profile, locales) if item["id"] == target_id]
    return dict(matches[0]) if len(matches) == 1 else None


def resolve_manual(guides, profile, target_id):
    """Resolve a citation source ID only inside the currently published scope.

    Callers supply publication-validated guides. Legacy raw-URL step actions are
    deliberately ignored. Conflicting metadata for an ID is ambiguous and closed.
    """
    if not profile or profile.get("verification_status") != "VERIFIED":
        return None
    matches = []
    for guide in guides:
        if (profile["profile_id"] not in guide["profile_ids"]
                or guide["manual_set_id"] != profile.get("manual_set_id")
                or guide["source_version"] != profile.get("manual_version")):
            continue
        for source in guide["sources"]:
            if (source["source_id"] == target_id and source.get("verification_status") == "VERIFIED"
                    and source.get("version") == profile.get("manual_version") and _valid_https_url(source["url"])):
                item = {"source_id": source["source_id"], "guide_id": guide["guide_id"], "profile_id": profile["profile_id"],
                        "manual_set_id": guide["manual_set_id"], "source_version": guide["source_version"],
                        "title": source["title"], "url": source["url"], "section": source["section"]}
                if item not in matches:
                    matches.append(item)
    return matches[0] if len(matches) == 1 else None


def support_actions(contacts):
    """Assemble IDs from the catalog's scope-validated support contacts."""
    return [{"kind": "OPEN_SUPPORT", "target_id": item["id"]}
            for item in contacts]


def manual_actions(citations, guides, profile):
    """Server-owned action assembly from canonical, validated citation identities."""
    actions = []
    for citation in citations:
        resolved = resolve_manual(guides, profile, citation.get("source_id"))
        if resolved is not None and resolved == citation:
            action = {"kind": "OPEN_MANUAL", "target_id": resolved["source_id"]}
            if action not in actions:
                actions.append(action)
    return actions
