"""Importer tests use synthetic records in temporary directories, never manuals."""
import copy
import importlib.util
import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("guide_import", ROOT / "scripts/import_guides.py")
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


@pytest.fixture
def content(tmp_path):
    root = tmp_path / "content"
    for folder in ("profiles", "locales", "guides"):
        (root / folder).mkdir(parents=True)
    profiles = json.loads((ROOT / "content/profiles/catalog.json").read_text())
    profiles[0].update(verification_status="VERIFIED", manual_set_id="synthetic-manual", manual_version="fixture-v1")
    (root / "profiles/catalog.json").write_text(json.dumps(profiles))
    (root / "locales/catalog.json").write_text((ROOT / "content/locales/catalog.json").read_text())
    guide = json.loads((ROOT / "content/guides/unpublished-template.json").read_text())
    guide.update(guide_id="synthetic-import", profile_ids=[profiles[0]["profile_id"]],
                 manual_set_id="synthetic-manual", source_version="fixture-v1", topic="fixture",
                 title="Synthetic importer test", body="Synthetic test content; not vehicle instructions.",
                 lifecycle="PUBLISHED", sources=[dict(source_id="fixture-source", title="Synthetic test source",
                     url="https://example.test/manual", version="fixture-v1", section="fixture-section",
                     verification_status="VERIFIED")])
    path = tmp_path / "input.json"
    path.write_text(json.dumps(guide))
    return root, path, guide


def invoke(root, command, *paths):
    return importer.run(Namespace(command=command, content_root=root, paths=list(paths)))


def test_import_is_idempotent_and_does_not_change_review_metadata(content):
    root, path, guide = content
    code, result = invoke(root, "import", path)
    assert code == 0 and result["status"] == "IMPORTED"
    stored = Path(result["file"])
    before = stored.read_bytes()
    assert json.loads(before) == guide
    assert invoke(root, "import", path)[1]["status"] == "UNCHANGED"
    assert stored.read_bytes() == before
    assert invoke(root, "check")[0] == 0
    assert len(list((root / "guides").iterdir())) == 1


def test_imported_record_is_available_through_catalog(content):
    root, path, guide = content
    from app.content import Catalog
    assert invoke(root, "import", path)[0] == 0
    assert Catalog(root).published(guide["profile_ids"][0], "ko-KR") == [guide]


def test_conflicting_same_identity_preserves_existing_file(content):
    root, path, guide = content
    _, result = invoke(root, "import", path)
    stored = Path(result["file"])
    before = stored.read_bytes()
    guide["body"] = "Different synthetic content."
    path.write_text(json.dumps(guide))
    code, result = invoke(root, "import", path)
    assert code == 1 and result["issues"][0]["code"] == "RECORD_CONFLICT"
    assert stored.read_bytes() == before
    assert len(list((root / "guides").iterdir())) == 1


def test_translation_is_distinct_record_but_requires_review(content):
    root, path, guide = content
    assert invoke(root, "import", path)[0] == 0
    guide.update(locale="en", translation_review_status="UNREVIEWED")
    path.write_text(json.dumps(guide))
    assert invoke(root, "import", path)[0] == 1
    guide.update(translation_review_status="REVIEWED", glossary_version="synthetic-glossary-v1")
    path.write_text(json.dumps(guide))
    assert invoke(root, "import", path)[0] == 0
    assert len(list((root / "guides").glob("*.json"))) == 2


def test_invalid_record_never_writes_partial_content(content):
    root, path, guide = content
    guide["sources"][0]["url"] = "https://user:secret@example.test/manual"
    path.write_text(json.dumps(guide))
    code, result = invoke(root, "import", path)
    assert code == 1 and any(i["code"] == "INVALID_SOURCE_URL" for i in result["issues"])
    assert not list((root / "guides").iterdir())


@pytest.mark.parametrize("text", ['{"guide_id":"one","guide_id":"two"}', '{"value":NaN}', '{"value":Infinity}', '['])
def test_ambiguous_or_invalid_json_is_input_error(content, text):
    root, path, _ = content
    path.write_text(text)
    code, result = invoke(root, "import", path)
    assert code == 2 and result["issues"][0]["code"] == "INPUT_ERROR"
    assert not list((root / "guides").iterdir())


def test_missing_file_has_readable_diagnostic(content):
    root, path, _ = content
    code, result = invoke(root, "check", path.with_name("missing.json"))
    assert code == 2 and result["issues"][0]["code"] == "INPUT_ERROR"


def test_catalog_audit_finds_duplicate_identity(content):
    root, path, guide = content
    for name in ("one.json", "two.json"):
        (root / "guides" / name).write_text(json.dumps(guide))
    code, result = invoke(root, "check")
    assert code == 1 and result["issues"][0]["code"] == "DUPLICATE_GUIDE_RECORD"
    assert invoke(root, "import", path)[0] == 1


def test_draft_import_never_promotes_profile_or_guide(content):
    root, path, _ = content
    from app.content import Catalog
    draft = json.loads((ROOT / "content/guides/unpublished-template.json").read_text())
    path.write_text(json.dumps(draft))
    before = (root / "profiles/catalog.json").read_bytes()
    assert invoke(root, "import", path)[0] == 0
    assert (root / "profiles/catalog.json").read_bytes() == before
    assert Catalog(root).published("demo-ioniq5-2024-kr") == []


def test_failed_atomic_write_removes_temporary_file(content, monkeypatch):
    root, _, guide = content
    def fail_link(*_):
        raise OSError("Synthetic disk failure")
    monkeypatch.setattr(importer.os, "link", fail_link)
    with pytest.raises(OSError, match="Synthetic disk failure"):
        importer.atomic_import(root / "guides", guide)
    assert not list((root / "guides").iterdir())


def test_concurrent_identical_import_is_unchanged_and_conflict_is_preserved(content):
    root, _, guide = content
    target, status = importer.atomic_import(root / "guides", guide)
    assert status == "IMPORTED"
    assert importer.atomic_import(root / "guides", guide) == (target, "UNCHANGED")
    changed = copy.deepcopy(guide)
    changed["title"] = "Conflicting synthetic title"
    with pytest.raises(ValueError, match="different content"):
        importer.atomic_import(root / "guides", changed)
    assert json.loads(target.read_text()) == guide
    assert len(list((root / "guides").iterdir())) == 1


def test_identity_cannot_escape_destination_directory(content):
    root, path, guide = content
    guide["guide_id"] = "../../outside"
    path.write_text(json.dumps(guide))
    code, result = invoke(root, "import", path)
    assert code == 0
    assert Path(result["file"]).parent == root / "guides"
    assert not (root.parent / "outside.json").exists()


def test_cli_json_output(content):
    root, path, _ = content
    result = subprocess.run([sys.executable, str(ROOT / "scripts/import_guides.py"), "check", str(path),
                             "--content-root", str(root), "--json"], capture_output=True, text=True)
    assert result.returncode == 0 and json.loads(result.stdout) == {"status": "VALID", "checked": 1, "issues": []}


def test_invalid_catalog_reports_error_without_traceback(content):
    root, path, _ = content
    (root / "profiles/catalog.json").write_text("{}")
    code, result = invoke(root, "import", path)
    assert code == 2 and result["issues"][0]["code"] == "CATALOG_ERROR"


def test_unreadable_existing_record_blocks_import_and_preserves_files(content):
    root, path, _ = content
    broken = root / "guides/broken.json"
    broken.write_text("{")
    code, result = invoke(root, "import", path)
    assert code == 2 and result["issues"][0]["code"] == "INPUT_ERROR"
    assert list((root / "guides").iterdir()) == [broken]
    assert broken.read_text() == "{"
