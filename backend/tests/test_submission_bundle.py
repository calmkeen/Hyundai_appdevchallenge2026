"""Synthetic artifacts/temporary Git repositories; no real APK, SDK, AI or mail."""
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import package_submission as bundle


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def commit(root):
    git(root, "add", ".")
    git(root, "-c", "user.name=CarCue fixture", "-c", "user.email=fixture@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-qm", "Synthetic source")
    return git(root, "rev-parse", "HEAD")


def json_file(root, name, value):
    path = root / "output" / (name + ".json")
    path.write_text(json.dumps(value), encoding="utf-8")
    return {"source": str(path.relative_to(root)), "sha256": bundle.sha256(path)}


@pytest.fixture
def candidate(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-q")
    main = root / "android/app/src/main/Feature.kt"
    main.parent.mkdir(parents=True)
    main.write_text("// synthetic baseline\n")
    ref = commit(root)
    output = root / "output"
    output.mkdir()
    apk, video, pdf, credits = (output / n for n in ("fixture.apk", "fixture.mp4", "fixture.pdf", "credits.txt"))
    with zipfile.ZipFile(apk, "w") as archive:
        archive.writestr("AndroidManifest.xml", b"synthetic fixture; not an installable APK")
    video.write_bytes(b"\x00\x00\x00\x18ftypisomsynthetic-video")
    pdf.write_bytes(b"%PDF-1.7\nsynthetic fixture; not a reviewed document")
    credits.write_text("Synthetic credits")
    assets = {role: {"source": str(p.relative_to(root)), "sha256": bundle.sha256(p), "filename": name}
              for role, p, name in (("apk", apk, "CarCue.apk"), ("video", video, "CarCue.mp4"),
                                    ("proposal", pdf, "CarCue.pdf"), ("credits", credits, "CREDITS.txt"))}
    flags = {"paid_provider_called": False, "physical_vehicle_tested": False,
             "app_sdk_set_called": False, "seatbelt_status_connected": False}
    raw_sha, manifest_sha = "a" * 64, "b" * 64
    sdk = {"passed": True, "functional_passed": True, "video_passed": True, "mode": "showcase",
           "cleanup_errors": [], "installed_apk_sha256": {"com.carcue.app": assets["apk"]["sha256"]},
           "final_database_counts": {"sessions": 0, "results": 0, "history": 0}, "video_sha256": raw_sha,
           "fixture_private_value_not_for_export": "DO-NOT-EXPORT-RAW-QA", **flags}
    evidence = {"sdk_showcase": json_file(root, "sdk", sdk)}
    native = {"passed_selected_native_examples": True,
              "source_validation_sha256": evidence["sdk_showcase"]["sha256"],
              "installed_app_sha256": assets["apk"]["sha256"], "source_manifest_sha256": manifest_sha,
              "source_video_sha256": raw_sha}
    evidence["native_review"] = json_file(root, "native", native)
    render = {"rendered": True, "validation_passed": True, "single_apk": True, "single_process": True,
              "decoded_pcm_exact_match": True, "apk_sha256": assets["apk"]["sha256"],
              "installed_apk_sha256": assets["apk"]["sha256"], "video_sha256": assets["video"]["sha256"],
              "source_manifest_sha256": manifest_sha, "source_video_sha256": raw_sha, **flags}
    evidence["video_render"] = json_file(root, "render", render)
    evidence["video_review"] = json_file(root, "visual", {
        "passed": True, "video_sha256": assets["video"]["sha256"],
        "source_render_validation_sha256": evidence["video_render"]["sha256"],
        "source_native_review_sha256": evidence["native_review"]["sha256"],
        "source_manifest_sha256": manifest_sha, "source_video_sha256": raw_sha})
    evidence["proposal_review"] = json_file(root, "pdf-review", {
        "passed": True, "pdf_sha256": assets["proposal"]["sha256"],
        "all_pages_visually_reviewed": True, "page_count": 2})
    config = {"schema_version": 1, "candidate_id": "fixture-first-draft",
              "candidate_type": "VALIDATED_SDK_SHOWCASE_BASELINE", "inflight_boundaries_passed": False,
              "delivery_status": "DRAFT_AWAITING_USER_DELIVERY_DETAILS", "paid_ai_enabled": False,
              "validated_source_ref": ref, "repository_url": "https://github.com/example/CarCue",
              "assets": assets, "evidence": evidence}
    return root, config


def rewrite_evidence(root, config, kind, update):
    record = config["evidence"][kind]
    path = root / record["source"]
    value = json.loads(path.read_text())
    value.update(update)
    path.write_text(json.dumps(value))
    record["sha256"] = bundle.sha256(path)


def test_build_copies_only_exact_pinned_assets_and_checksums_and_leaves_originals(candidate):
    root, config = candidate
    destination = root / "output/draft.v1"
    result = bundle.stage_bundle(root, config, destination)
    expected = {a["filename"] for a in config["assets"].values()} | {
        "MANIFEST.json", "README_KO.md", "GITHUB.txt", "SHA256SUMS.txt"}
    assert {p.name for p in destination.iterdir()} == expected
    with zipfile.ZipFile(destination.parent / "draft.v1.zip") as archive:
        assert set(archive.namelist()) == expected
        assert archive.testzip() is None
        assert all(b"DO-NOT-EXPORT-RAW-QA" not in archive.read(name) for name in archive.namelist())
    for item in config["assets"].values():
        assert (destination / item["filename"]).read_bytes() == (root / item["source"]).read_bytes()
    for line in (destination / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ")
        assert bundle.sha256(destination / name) == digest
    assert result["source_commit"] == config["validated_source_ref"]
    assert result["inflight_boundaries_passed"] is False and not result["new_feature_build_included"]


@pytest.mark.parametrize("role", ["apk", "video", "proposal", "credits"])
def test_changed_asset_refuses_all_output_before_staging(candidate, role):
    root, config = candidate
    (root / config["assets"][role]["source"]).write_bytes(b"changed")
    destination = root / "output/rejected"
    with pytest.raises(bundle.CandidateError, match="SOURCE_SHA256_MISMATCH"):
        bundle.stage_bundle(root, config, destination)
    assert not destination.exists() and not destination.with_suffix(".zip").exists()


def test_failed_sdk_evidence_is_rejected_even_when_hash_is_updated(candidate):
    root, config = candidate
    rewrite_evidence(root, config, "sdk_showcase", {"passed": False})
    with pytest.raises(bundle.CandidateError, match="SUCCESSFUL_SDK_SHOWCASE_REQUIRED"):
        bundle.check_candidate(root, config)


def test_new_apk_or_new_video_cannot_inherit_old_review(candidate):
    root, config = candidate
    rewrite_evidence(root, config, "video_render", {"apk_sha256": "0" * 64})
    with pytest.raises(bundle.CandidateError, match="MATCHING_RENDER_AND_MUSIC_PROOF_REQUIRED"):
        bundle.check_candidate(root, config)


def test_pdf_edit_requires_fresh_matching_visual_review(candidate):
    root, config = candidate
    item = config["assets"]["proposal"]
    path = root / item["source"]
    path.write_bytes(b"%PDF-1.7\nupdated synthetic fixture")
    item["sha256"] = bundle.sha256(path)
    with pytest.raises(bundle.CandidateError, match="MATCHING_COMPLETE_PDF_REVIEW_REQUIRED"):
        bundle.check_candidate(root, config)


@pytest.mark.parametrize("relative", ["android/app/src/main/Feature.kt",
    "android/app/src/pleosDebug/AndroidManifest.xml", "android/app/src/debug/AndroidManifest.xml",
    "android/gradle/wrapper/gradle-wrapper.properties", "backend/requirements.txt"])
def test_product_change_cannot_masquerade_as_validated_source_but_old_ref_stays_usable(candidate, relative):
    root, config = candidate
    changed = root / relative
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("// new development only\n")
    latest = commit(root)
    with pytest.raises(bundle.CandidateError, match="SOURCE_DIFFERS_FROM_VALIDATED_APK_BASELINE"):
        bundle.check_candidate(root, config, latest)
    result, _ = bundle.check_candidate(root, config)
    assert result["source_commit"] == config["validated_source_ref"] != latest


def test_document_only_release_commit_is_allowed(candidate):
    root, config = candidate
    (root / "README.md").write_text("New reviewer instructions")
    latest = commit(root)
    result, _ = bundle.check_candidate(root, config, latest)
    assert result["source_commit"] == latest


def test_dirty_product_source_is_rejected(candidate):
    root, config = candidate
    (root / "android/app/src/main/Feature.kt").write_text("// uncommitted development\n")
    with pytest.raises(bundle.CandidateError, match="PRODUCTION_WORKTREE_DIRTY"):
        bundle.check_candidate(root, config)


@pytest.mark.parametrize("value", ["../outside.apk", "/tmp/outside.apk", "bad\\name.apk"])
def test_unsafe_archive_names_are_rejected(candidate, value):
    root, config = candidate
    config["assets"]["apk"]["filename"] = value
    with pytest.raises(bundle.CandidateError, match="SAFE_ARCHIVE_FILENAME_REQUIRED"):
        bundle.check_candidate(root, config)


def test_symlink_to_private_directory_is_rejected(candidate):
    root, config = candidate
    private = root / ".tooling/private"
    private.mkdir(parents=True)
    (private / "notes.txt").write_text("synthetic private data")
    (root / "output/alias").symlink_to(private, target_is_directory=True)
    config["assets"]["credits"].update(source="output/alias/notes.txt",
        sha256=hashlib.sha256(b"synthetic private data").hexdigest())
    with pytest.raises(bundle.CandidateError, match="PRIVATE_SOURCE_FORBIDDEN"):
        bundle.check_candidate(root, config)


@pytest.mark.parametrize("value", ["github.txt", "sha256sums.txt"])
def test_reserved_names_are_case_insensitive_on_macos(candidate, value):
    root, config = candidate
    config["assets"]["credits"]["filename"] = value
    with pytest.raises(bundle.CandidateError, match="RESERVED_ARCHIVE_FILENAME"):
        bundle.check_candidate(root, config)


def test_missing_raw_recording_hash_cannot_pass_by_matching_nulls(candidate):
    root, config = candidate
    rewrite_evidence(root, config, "sdk_showcase", {"video_sha256": None})
    rewrite_evidence(root, config, "native_review", {"source_video_sha256": None,
        "source_validation_sha256": config["evidence"]["sdk_showcase"]["sha256"]})
    rewrite_evidence(root, config, "video_render", {"source_video_sha256": None})
    rewrite_evidence(root, config, "video_review", {"source_video_sha256": None,
        "source_native_review_sha256": config["evidence"]["native_review"]["sha256"],
        "source_render_validation_sha256": config["evidence"]["video_render"]["sha256"]})
    with pytest.raises(bundle.CandidateError, match="SAME_NATIVE_RECORDING_REQUIRED"):
        bundle.check_candidate(root, config)


def test_existing_output_and_outside_location_are_not_overwritten(candidate, tmp_path):
    root, config = candidate
    output = root / "output/existing"
    output.mkdir(); (output / "user.txt").write_text("keep")
    with pytest.raises(bundle.CandidateError, match="NEW_OUTPUT_DIRECTORY_REQUIRED"):
        bundle.stage_bundle(root, config, output)
    assert (output / "user.txt").read_text() == "keep"
    with pytest.raises(bundle.CandidateError, match="DRAFT_OUTPUT_MUST_BE_UNDER_PROJECT_OUTPUT"):
        bundle.stage_bundle(root, config, tmp_path / "unapproved-final-destination")


def test_copy_integrity_failure_cleans_only_own_temporary_files(candidate, monkeypatch):
    root, config = candidate
    def damaged_copy(source, destination):
        Path(destination).write_bytes(b"damaged synthetic copy")
    monkeypatch.setattr(bundle.shutil, "copyfile", damaged_copy)
    with pytest.raises(bundle.CandidateError, match="SOURCE_CHANGED_DURING_COPY"):
        bundle.stage_bundle(root, config, root / "output/rejected")
    assert not (root / "output/rejected").exists()
    assert not list((root / "output").glob(".carcue-bundle-*"))
    assert (root / config["assets"]["apk"]["source"]).exists()


@pytest.mark.parametrize("field,value,error", [
    ("inflight_boundaries_passed", True, "INFLIGHT_COMPLETION_NOT_PROVEN"),
    ("paid_ai_enabled", True, "PAID_AI_MUST_REMAIN_DEFERRED"),
    ("delivery_status", "SENT", "DELIVERY_SCOPE_REQUIRED"),
])
def test_submission_cannot_promote_unproven_or_unrequested_claims(candidate, field, value, error):
    root, config = candidate
    config[field] = value
    with pytest.raises(bundle.CandidateError, match=error):
        bundle.check_candidate(root, config)
