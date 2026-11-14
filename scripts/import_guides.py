"""Validate or atomically import an editor-reviewed, versioned guide record.

This tool never changes review status or fetches manual URLs. Run with the
backend environment: python scripts/import_guides.py check [guide.json ...].
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.guide_policy import validate_guide

IDENTITY_FIELDS = ("guide_id", "locale", "manual_set_id", "source_version")


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON object key: {key}")
        value[key] = item
    return value


def load_json(path):
    def invalid_constant(value):
        raise ValueError(f"Invalid JSON constant: {value}")

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object,
                      parse_constant=invalid_constant)


def identity(guide):
    return tuple(guide[field] for field in IDENTITY_FIELDS)


def validate_records(paths, profiles, locales):
    records, issues = [], []
    for path in paths:
        try:
            guide = load_json(path)
        except (OSError, ValueError) as error:
            issues.append({"file": str(path), "code": "INPUT_ERROR", "path": "", "message": str(error)})
            continue
        errors = validate_guide(guide, profiles, locales)
        issues.extend({"file": str(path), **asdict(error)} for error in errors)
        if not errors:
            records.append((path, guide))
    return records, issues


def duplicate_issues(records):
    seen, issues = {}, []
    for path, guide in records:
        key = identity(guide)
        if key in seen:
            issues.append({"file": str(path), "code": "DUPLICATE_GUIDE_RECORD", "path": "",
                           "message": f"Record identity already exists in {seen[key]}."})
        else:
            seen[key] = path
    return issues


def atomic_import(directory, guide):
    """Publish one complete file without replacing any existing destination."""
    key = json.dumps(identity(guide), ensure_ascii=False, separators=(",", ":"))
    target = directory / ("guide-" + hashlib.sha256(key.encode()).hexdigest() + ".json")
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                         prefix=".guide-import-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(guide, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # A hard link makes the complete file visible in one operation and fails
        # if another importer has already created the same immutable identity.
        os.link(temporary, target)
        return target, "IMPORTED"
    except FileExistsError:
        if load_json(target) == guide:
            return target, "UNCHANGED"
        raise ValueError("Destination already contains different content; use a new reviewed record version.")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(args):
    root = args.content_root
    try:
        profiles = load_json(root / "profiles/catalog.json")
        locales = load_json(root / "locales/catalog.json")
        if not all(isinstance(items, list) and all(isinstance(item, dict) for item in items)
                   for items in (profiles, locales)):
            raise ValueError("Profile and locale catalogs must contain arrays of objects.")
    except (OSError, ValueError) as error:
        return 2, {"status": "INVALID", "issues": [
            {"file": str(root), "code": "CATALOG_ERROR", "path": "", "message": str(error)}]}

    directory = root / "guides"
    existing = sorted(directory.glob("*.json"))
    paths = args.paths if args.paths else existing
    records, issues = validate_records(paths, profiles, locales)
    issues.extend(duplicate_issues(records))
    if issues:
        return (2 if any(issue["code"] == "INPUT_ERROR" for issue in issues) else 1), {"status": "INVALID", "issues": issues}
    if args.command == "check":
        return 0, {"status": "VALID", "checked": len(records), "issues": []}

    current, issues = validate_records(existing, profiles, locales)
    issues.extend(duplicate_issues(current))
    if issues:
        return (2 if any(issue["code"] == "INPUT_ERROR" for issue in issues) else 1), {"status": "INVALID", "issues": issues}
    guide = records[0][1]
    for path, stored in current:
        if identity(stored) == identity(guide):
            if stored == guide:
                return 0, {"status": "UNCHANGED", "file": str(path), "issues": []}
            return 1, {"status": "INVALID", "issues": [{"file": str(args.paths[0]),
                "code": "RECORD_CONFLICT", "path": "", "message":
                "Record identity already contains different content; import a new reviewed version. Existing files were preserved."}]}
    try:
        target, status = atomic_import(directory, guide)
        return 0, {"status": status, "file": str(target), "issues": []}
    except (OSError, ValueError) as error:
        return 2, {"status": "INVALID", "issues": [{"file": str(directory),
            "code": "WRITE_ERROR", "path": "", "message": str(error)}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "import"):
        sub = commands.add_parser(command)
        sub.add_argument("paths", type=Path, nargs="*" if command == "check" else 1)
        sub.add_argument("--content-root", type=Path, default=ROOT / "content")
        sub.add_argument("--json", action="store_true", help="Output machine-readable diagnostics.")
    args = parser.parse_args()
    code, result = run(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(result["status"], result.get("file", f"{result.get('checked', 0)} guide record(s)"))
        for issue in result["issues"]:
            print(f"{issue['file']} {issue['path'] or '/'} [{issue['code']}] {issue['message']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
