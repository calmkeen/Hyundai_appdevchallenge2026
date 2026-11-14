"""Shared, side-effect-free checks for importing and serving reviewed guides.

VERIFIED source metadata is an editor's assertion, not a network verification.
The policy checks that assertion and its scope; it never fetches source URLs or
promotes a draft, a profile, or a translation to a reviewed state.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator


_SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "contracts/guide.schema.json").read_text())
_VALIDATOR = Draft202012Validator(_SCHEMA)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


def _pointer(parts):
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def _valid_https_url(value):
    """Require an unambiguous HTTPS URI with a DNS host and no credentials."""
    if (not value or any(character.isspace() for character in value) or "\\" in value
            or any(ord(character) < 32 or ord(character) == 127 for character in unquote(value))):
        return False
    try:
        parsed = urlsplit(value)
        # Reading hostname/port also rejects malformed brackets and ports.
        host, port = parsed.hostname, parsed.port
        if (parsed.scheme != "https" or not host or parsed.username is not None
                or parsed.password is not None or parsed.netloc.endswith(":")):
            return False
        if port is not None and not 1 <= port <= 65535:
            return False
        # Manuals must name their publisher rather than use a local/IP endpoint.
        labels = host.rstrip(".").encode("idna").decode("ascii").split(".")
        return (len(labels) >= 2 and len(host) <= 253
                and not all(label.isdigit() for label in labels)
                and all(re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                        for label in labels))
    except (ValueError, UnicodeError):
        return False


def validate_guide(guide: dict, profiles: list[dict], locales: list[dict]) -> list[ValidationIssue]:
    """Return structural and publication errors without changing any input.

    Structurally valid non-published records may contain planning placeholders.
    Publication requires a complete, reviewed record in a known vehicle/manual
    and language scope. Paths use JSON Pointer; an empty path denotes the root.
    """
    issues = [ValidationIssue("SCHEMA_INVALID", _pointer(error.absolute_path), error.message)
              for error in _VALIDATOR.iter_errors(guide)]
    if issues or guide["lifecycle"] != "PUBLISHED":
        return issues

    def issue(code, path, message):
        issues.append(ValidationIssue(code, path, message))

    def nonblank(value, path):
        if not isinstance(value, str) or not value.strip():
            issue("BLANK_FIELD", path, "Published content must not be blank.")
            return False
        return True

    for field in ("guide_id", "manual_set_id", "source_version", "topic", "title", "body"):
        nonblank(guide[field], "/" + field)

    registered_locales = {item.get("locale") for item in locales}
    for field in ("locale", "source_locale"):
        if guide[field] not in registered_locales:
            issue("UNKNOWN_LOCALE", "/" + field, "Locale is not registered in the content catalog.")

    for index, profile_id in enumerate(guide["profile_ids"]):
        path = f"/profile_ids/{index}"
        matches = [profile for profile in profiles if profile.get("profile_id") == profile_id]
        if not matches:
            issue("UNKNOWN_PROFILE", path, "Vehicle profile is not registered in the content catalog.")
            continue
        if len(matches) != 1:
            issue("AMBIGUOUS_PROFILE", path, "Vehicle profile ID is not unique in the content catalog.")
            continue
        profile = matches[0]
        if profile.get("verification_status") != "VERIFIED":
            issue("UNVERIFIED_PROFILE", path, "Published guides require a verified vehicle profile.")
        if profile.get("manual_set_id") != guide["manual_set_id"]:
            issue("MANUAL_SET_MISMATCH", "/manual_set_id", "Manual set does not match the vehicle profile.")
        if profile.get("manual_version") != guide["source_version"]:
            issue("MANUAL_VERSION_MISMATCH", "/source_version", "Manual version does not match the vehicle profile.")

    translated = guide["locale"] != guide["source_locale"]
    review = guide["translation_review_status"]
    if review == "UNREVIEWED" or (translated and review != "REVIEWED"):
        issue("TRANSLATION_NOT_REVIEWED", "/translation_review_status",
              "Published translations require REVIEWED; original content cannot be UNREVIEWED.")
    if translated and (not isinstance(guide["glossary_version"], str) or not guide["glossary_version"].strip()):
        issue("MISSING_GLOSSARY_VERSION", "/glossary_version", "Published translations require a glossary version.")

    source_ids = set()
    for index, source in enumerate(guide["sources"]):
        path = f"/sources/{index}"
        for field in ("source_id", "title", "version", "section"):
            nonblank(source[field], path + "/" + field)
        if source["source_id"] in source_ids:
            issue("DUPLICATE_SOURCE_ID", path + "/source_id", "Source IDs must be unique within a guide.")
        source_ids.add(source["source_id"])
        if not _valid_https_url(source["url"]):
            issue("INVALID_SOURCE_URL", path + "/url", "Source URL must use HTTPS with a valid host and no embedded credentials.")
        if source["version"] != guide["source_version"]:
            issue("SOURCE_VERSION_MISMATCH", path + "/version", "Source version must match the guide's manual version.")

    step_ids = set()
    for index, step in enumerate(guide["steps"]):
        path = f"/steps/{index}"
        for field in ("step_id", "title", "body"):
            nonblank(step[field], path + "/" + field)
        if step["step_id"] in step_ids:
            issue("DUPLICATE_STEP_ID", path + "/step_id", "Step IDs must be unique within a guide.")
        step_ids.add(step["step_id"])
        if step["order"] != index + 1:
            issue("INVALID_STEP_ORDER", path + "/order", "Steps must appear in contiguous order starting at 1.")
        if not step["source_ids"]:
            issue("MISSING_STEP_SOURCE", path + "/source_ids", "Published steps require at least one verified source reference.")
        for ref_index, source_id in enumerate(step["source_ids"]):
            if source_id not in source_ids:
                issue("UNKNOWN_STEP_SOURCE", path + f"/source_ids/{ref_index}", "Step source ID is not defined in this guide.")
    return issues
