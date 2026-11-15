#!/usr/bin/env python3
"""Check and stage an explicit, hash-pinned CarCue submission candidate.

No SDK, model, mail, network, installation, or repository mutation is performed.
Only explicitly listed artifacts are copied; raw QA, credentials and databases
are never swept into the bundle. Validation precedes all output creation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_PATHS = (
    "android", "content",
    "backend/app", "backend/requirements.lock.txt", "contracts",
)
REQUIRED_ASSETS = {"apk", "video", "proposal", "credits"}
REQUIRED_EVIDENCE = {"sdk_showcase", "native_review", "video_render", "video_review", "proposal_review"}


class CandidateError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise CandidateError(code)


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def source_file(root, raw):
    require(isinstance(raw, str) and raw and "\\" not in raw, "INVALID_SOURCE_PATH")
    relative = PurePosixPath(raw)
    require(not relative.is_absolute() and ".." not in relative.parts, "SOURCE_MUST_BE_PROJECT_RELATIVE")
    require(not any(part.startswith(".env") or part in {".git", ".tooling", ".venv"}
                    for part in relative.parts), "PRIVATE_SOURCE_FORBIDDEN")
    require(not raw.endswith((".sqlite3", ".sqlite3-wal", ".sqlite3-shm", ".jks", ".keystore")),
            "PRIVATE_SOURCE_FORBIDDEN")
    path = root.joinpath(*relative.parts)
    resolved = path.resolve()
    require(resolved.is_relative_to(root), "SOURCE_ESCAPES_PROJECT")
    require(not any(part.startswith(".env") or part in {".git", ".tooling", ".venv"}
                    for part in resolved.relative_to(root).parts), "PRIVATE_SOURCE_FORBIDDEN")
    require(path.is_file() and not path.is_symlink(), "REGULAR_SOURCE_FILE_REQUIRED")
    return path


def filename(raw):
    require(isinstance(raw, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", raw)),
            "SAFE_ARCHIVE_FILENAME_REQUIRED")
    return raw


def pinned_file(root, row):
    require(isinstance(row, dict), "FILE_RECORD_REQUIRED")
    expected = row.get("sha256")
    require(isinstance(expected, str) and bool(re.fullmatch(r"[a-f0-9]{64}", expected)), "PINNED_SHA256_REQUIRED")
    path = source_file(root, row.get("source"))
    require(sha256(path) == expected, "SOURCE_SHA256_MISMATCH")
    return path


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=20)
    require(result.returncode == 0, "GIT_SOURCE_REFERENCE_FAILED")
    return result.stdout.strip()


def resolve_source(root, reference, baseline):
    for ref in (reference, baseline):
        require(isinstance(ref, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/._-]{0,159}", ref)),
                "SAFE_SOURCE_REFERENCE_REQUIRED")
    commit = git(root, "rev-parse", "--verify", reference + "^{commit}")
    base = git(root, "rev-parse", "--verify", baseline + "^{commit}")
    require(not git(root, "status", "--porcelain", "--untracked-files=all", "--", *PRODUCTION_PATHS),
            "PRODUCTION_WORKTREE_DIRTY")
    require(not git(root, "diff", "--name-only", base, commit, "--", *PRODUCTION_PATHS),
            "SOURCE_DIFFERS_FROM_VALIDATED_APK_BASELINE")
    return commit, base


def check_candidate(root, config, source_ref=None):
    root = Path(root).resolve()
    require(isinstance(config, dict), "CANDIDATE_OBJECT_REQUIRED")
    require(config.get("schema_version") == 1, "UNSUPPORTED_CANDIDATE_SCHEMA")
    require(config.get("candidate_type") == "VALIDATED_SDK_SHOWCASE_BASELINE", "CANDIDATE_SCOPE_REQUIRED")
    require(config.get("inflight_boundaries_passed") is False, "INFLIGHT_COMPLETION_NOT_PROVEN")
    require(config.get("delivery_status") == "DRAFT_AWAITING_USER_DELIVERY_DETAILS", "DELIVERY_SCOPE_REQUIRED")
    require(config.get("paid_ai_enabled") is False, "PAID_AI_MUST_REMAIN_DEFERRED")
    identifier = filename(config.get("candidate_id"))
    repo = config.get("repository_url")
    require(isinstance(repo, str) and bool(re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)),
            "CANONICAL_GITHUB_REPOSITORY_REQUIRED")
    assets, evidence = config.get("assets"), config.get("evidence")
    require(isinstance(assets, dict) and set(assets) == REQUIRED_ASSETS, "EXACT_SUBMISSION_ASSET_SET_REQUIRED")
    require(isinstance(evidence, dict) and set(evidence) == REQUIRED_EVIDENCE, "COMPLETE_REVIEW_EVIDENCE_REQUIRED")
    asset_paths = {role: pinned_file(root, item) for role, item in assets.items()}
    names = {role: filename(item.get("filename")) for role, item in assets.items()}
    folded_names = {name.casefold() for name in names.values()}
    require(len(folded_names) == len(names), "DUPLICATE_ARCHIVE_FILENAME")
    require(not folded_names & {"manifest.json", "readme_ko.md", "github.txt", "sha256sums.txt"},
            "RESERVED_ARCHIVE_FILENAME")
    require(names["apk"].endswith(".apk") and names["video"].endswith(".mp4")
            and names["proposal"].endswith(".pdf") and names["credits"].endswith(".txt"), "ASSET_EXTENSIONS_REQUIRED")
    with zipfile.ZipFile(asset_paths["apk"]) as archive:
        require("AndroidManifest.xml" in archive.namelist(), "ANDROID_APK_REQUIRED")
    with asset_paths["video"].open("rb") as stream:
        require(stream.read(12)[4:8] == b"ftyp", "MP4_CONTAINER_REQUIRED")
    with asset_paths["proposal"].open("rb") as stream:
        require(stream.read(5) == b"%PDF-", "PDF_DOCUMENT_REQUIRED")
    records = {}
    for kind, item in evidence.items():
        path = pinned_file(root, item)
        records[kind] = json.loads(path.read_text(encoding="utf-8"))
        require(isinstance(records[kind], dict), "EVIDENCE_OBJECT_REQUIRED")
    sdk, native, render, visual, proposal = (records[k] for k in
        ("sdk_showcase", "native_review", "video_render", "video_review", "proposal_review"))
    apk_sha, video_sha, pdf_sha = (assets[k]["sha256"] for k in ("apk", "video", "proposal"))
    require(sdk.get("passed") is True and sdk.get("functional_passed") is True
            and sdk.get("video_passed") is True and sdk.get("mode") == "showcase"
            and sdk.get("cleanup_errors") == [], "SUCCESSFUL_SDK_SHOWCASE_REQUIRED")
    require(sdk.get("installed_apk_sha256", {}).get("com.carcue.app") == apk_sha,
            "INSTALLED_SDK_APK_MUST_MATCH")
    require(sdk.get("final_database_counts") == {"sessions": 0, "results": 0, "history": 0},
            "SHOWCASE_SESSION_CLEANUP_REQUIRED")
    for item in (sdk, render):
        require(item.get("paid_provider_called") is False and item.get("physical_vehicle_tested") is False
                and item.get("app_sdk_set_called") is False and item.get("seatbelt_status_connected") is False,
                "VALIDATED_SCOPE_FLAGS_REQUIRED")
    require(native.get("passed_selected_native_examples") is True
            and native.get("source_validation_sha256") == evidence["sdk_showcase"]["sha256"]
            and native.get("installed_app_sha256") == apk_sha, "MATCHING_NATIVE_REVIEW_REQUIRED")
    require(render.get("rendered") is True and render.get("validation_passed") is True
            and render.get("single_apk") is True and render.get("single_process") is True
            and render.get("decoded_pcm_exact_match") is True
            and render.get("apk_sha256") == apk_sha and render.get("installed_apk_sha256") == apk_sha
            and render.get("video_sha256") == video_sha, "MATCHING_RENDER_AND_MUSIC_PROOF_REQUIRED")
    require(visual.get("passed") is True and visual.get("video_sha256") == video_sha
            and visual.get("source_render_validation_sha256") == evidence["video_render"]["sha256"]
            and visual.get("source_native_review_sha256") == evidence["native_review"]["sha256"],
            "MATCHING_VIDEO_REVIEW_REQUIRED")
    shared_manifest = native.get("source_manifest_sha256")
    raw_video = native.get("source_video_sha256")
    require(isinstance(shared_manifest, str) and bool(re.fullmatch(r"[a-f0-9]{64}", shared_manifest))
            and isinstance(raw_video, str) and bool(re.fullmatch(r"[a-f0-9]{64}", raw_video))
            and render.get("source_manifest_sha256") == shared_manifest
            and visual.get("source_manifest_sha256") == shared_manifest
            and sdk.get("video_sha256") == native.get("source_video_sha256")
            == render.get("source_video_sha256") == visual.get("source_video_sha256"),
            "SAME_NATIVE_RECORDING_REQUIRED")
    require(proposal.get("passed") is True and proposal.get("pdf_sha256") == pdf_sha
            and proposal.get("all_pages_visually_reviewed") is True
            and isinstance(proposal.get("page_count"), int) and not isinstance(proposal["page_count"], bool)
            and proposal["page_count"] > 0, "MATCHING_COMPLETE_PDF_REVIEW_REQUIRED")
    commit, baseline = resolve_source(root, source_ref or config.get("validated_source_ref"), config.get("validated_source_ref"))
    manifest = {
        "schema_version": 1, "candidate_id": identifier, "candidate_type": config["candidate_type"],
        "delivery_status": config["delivery_status"], "source_commit": commit,
        "validated_production_baseline": baseline, "github_url": repo + "/tree/" + commit,
        "apk_mode": "PLEOS_AVD_SDK_DEBUG", "paid_ai_enabled": False,
        "ai": "Actual local Ollama/qwen3:4b passage selection; ANSWER/GUIDE use stored reviewed translations",
        "inflight_boundaries_passed": False, "physical_vehicle_tested": False,
        "seatbelt_status_connected": False, "new_feature_build_included": False,
        "assets": {role: {"filename": names[role], "sha256": assets[role]["sha256"],
                          "bytes": asset_paths[role].stat().st_size} for role in sorted(assets)},
        "evidence_sha256": {kind: evidence[kind]["sha256"] for kind in sorted(evidence)},
        "remaining_device_tests": ["in-flight language change", "in-flight Drive transition", "in-flight session end"],
    }
    return manifest, asset_paths


def reviewer_readme(manifest):
    assets = manifest["assets"]
    return f"""# CarCue 1차 제출 검토용 묶음

언제, 어디서든, 평소와 같은 경험을.

이 묶음은 검증된 SDK 시연 APK·해당 APK의 34초 영상·최신 기획서를 고정한 초안입니다.
수신자·메일·최종 제출 위치는 아직 확정하지 않았으며 이 도구는 전송하지 않습니다.

- APK: {assets['apk']['filename']} (일반 폰용 Mock APK가 아닌 Pleos 개발용 debug APK)
- 영상: {assets['video']['filename']} (실제 같은 SDK 앱 화면, 기능당 약2초, 기존 무료 음악)
- 기획서: {assets['proposal']['filename']}
- GitHub: {manifest['github_url']} (APK와 동일한 제품 코드 범위의 고정 커밋)
- 출처·음악: {assets['credits']['filename']}

## 실행 환경

검증 환경은 Pleos Connect2.1 / Android14(API34) / Vehicle SDK2.3.2 / Service2.3.22입니다.
일반 Android 폰에는 Pleos Vehicle Service가 없으므로 차량 SDK 전체 동작을 확인할 수 없습니다.
차량 앱에는 CarCue 서버(http://10.0.2.2:8001), 서버에는 무료 로컬 Ollama(http://127.0.0.1:11434)가 필요합니다.
AI 모델·SDK 바이너리·서버 키·개인 세션 DB는 APK 외부이며 이 묶음에 포함하지 않습니다.
서버·모델이 없어도 같은 프로필/판본/언어의 동봉 검토 안내를 제공하며 연결 상태를 구분합니다.
전체 설정·실행 명령은 고정 커밋의 Docs/RUNBOOK.md 및 Docs/LOCAL_AI_INTEGRATION.md를 따릅니다.

## 확인된 범위

문 상태 GET·열림/닫힘 callback·차량 그림 변화, 한국어/영어/일본어,
공식2024KR 아이오닉5 문 안내, 무료 로컬 AI 선택, 저장 번역,
정상 Drive/Park 제한·가이드 복귀·정상 이용 종료를 같은 APK 시연에서 확인했습니다.
실차·VIN 자동 인증·안전벨트 센서 연결·모든 언어/임의 질문의 품질 완료를 뜻하지 않습니다.

## 남은 확인

AI 처리 중 언어 변경·Drive·이용 종료의 세 기기 시험은 전체 미완료입니다.
언어/Drive의 부분 증명과 정상 종료 시연을 처리 중 종료 시험의 성공으로 계산하지 않습니다.
유료 AI·자동 전환·생성 QUESTION 번역은 보류이며 ANSWER/GUIDE는 저장 검토 번역입니다.
추가 기능 개발본은 이 검증 APK와 섞지 않았습니다. 최신 개발 진척은 develop 브랜치에서 별도로 관리합니다.

모든 파일의 정확한 해시는 MANIFEST.json과 SHA256SUMS.txt를 확인해주세요.
"""


def stage_bundle(root, config, output_dir, source_ref=None):
    root, destination = Path(root).resolve(), Path(output_dir).resolve()
    output_root = (root / "output").resolve()
    require(output_root.is_relative_to(root) and destination.is_relative_to(output_root) and destination != output_root,
            "DRAFT_OUTPUT_MUST_BE_UNDER_PROJECT_OUTPUT")
    zip_path = destination.parent / (destination.name + ".zip")
    require(not destination.exists(), "NEW_OUTPUT_DIRECTORY_REQUIRED")
    require(not zip_path.exists(), "NEW_ZIP_PATH_REQUIRED")
    manifest, paths = check_candidate(root, config, source_ref)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".carcue-bundle-", dir=destination.parent))
    temporary_zip = None
    try:
        for role, path in paths.items():
            target = temporary / manifest["assets"][role]["filename"]
            shutil.copyfile(path, target)
            require(sha256(target) == manifest["assets"][role]["sha256"], "SOURCE_CHANGED_DURING_COPY")
        (temporary / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (temporary / "README_KO.md").write_text(reviewer_readme(manifest), encoding="utf-8")
        (temporary / "GITHUB.txt").write_text(manifest["github_url"] + "\n", encoding="utf-8")
        members = sorted(p for p in temporary.iterdir() if p.is_file())
        checksums = "".join(f"{sha256(path)}  {path.name}\n" for path in members)
        (temporary / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
        with tempfile.NamedTemporaryFile(prefix=".carcue-bundle-", suffix=".zip", dir=destination.parent, delete=False) as stream:
            temporary_zip = Path(stream.name)
        with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_STORED) as archive:
            for path in sorted(temporary.iterdir()):
                item = zipfile.ZipInfo(path.name, date_time=(2026, 11, 15, 0, 0, 0))
                item.external_attr = 0o100644 << 16
                archive.writestr(item, path.read_bytes())
        with zipfile.ZipFile(temporary_zip) as archive:
            require(archive.testzip() is None, "ZIP_CRC_FAILED")
            require(set(archive.namelist()) == {p.name for p in temporary.iterdir()}, "EXACT_ZIP_INVENTORY_REQUIRED")
        require(not destination.exists() and not zip_path.exists(), "OUTPUT_APPEARED_DURING_STAGING")
        temporary.rename(destination)
        temporary_zip.rename(zip_path)
        return manifest
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
        if temporary_zip is not None and temporary_zip.exists():
            temporary_zip.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "build"))
    parser.add_argument("--candidate", type=Path, default=ROOT / "Docs/SUBMISSION_CANDIDATE.json")
    parser.add_argument("--source-ref", help="Production-identical release commit; defaults to validated baseline")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        config = json.loads(args.candidate.read_text(encoding="utf-8"))
        if args.command == "build":
            require(args.output_dir is not None, "EXPLICIT_DRAFT_OUTPUT_REQUIRED")
            manifest = stage_bundle(ROOT, config, args.output_dir, args.source_ref)
        else:
            manifest, _ = check_candidate(ROOT, config, args.source_ref)
        print(json.dumps({"passed": True, "candidate_id": manifest["candidate_id"],
                          "source_commit": manifest["source_commit"], "delivery_status": manifest["delivery_status"]}))
    except (CandidateError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
