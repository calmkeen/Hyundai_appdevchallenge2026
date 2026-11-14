"""Edit one verified current Pleos recording; preserve all earlier footage/plans.

No device, server, model, download or music-generation operation is performed.
--check-plan is independent of a recording; --check-only validates supplied
evidence without rendering. A render always creates a new ignored QA directory.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCENES = ("profile", "language-ko", "door-closed", "door-open", "door-restored",
          "seatbelt", "official-guide-step2", "ask-ko", "translation-en",
          "language-en", "ask-en", "ask-ja", "drive-restricted", "end-session")
MUSIC_SHA = "d0dc554c0db9ea208b4f59e4f0c1b4446aa7ef622c7bfeffca278130a46c51f1"
PROFILE = "ioniq5-ne1-2024-kr"
GUIDE = "ioniq5-door-open-check"
MODEL = "qwen3:4b"
HASH = re.compile(r"[a-f0-9]{64}")


class InvalidEvidence(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise InvalidEvidence(code)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def existing(root, value):
    require(isinstance(value, str) and bool(value.strip()), "FILE_PATH_REQUIRED")
    path = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    require(path.is_relative_to(root.resolve()) and path.is_file(), "EXISTING_WORKSPACE_FILE_REQUIRED")
    return path


def validate_plan(plan):
    require(isinstance(plan, dict) and plan.get("schema_version") == 1, "LIVE_PLAN_SCHEMA_REQUIRED")
    segments = plan.get("segments", [])
    require(len(segments) == 16 and segments[0].get("kind") == "intro"
            and segments[-1].get("kind") == "outro", "INTRO_14_FEATURES_OUTRO_REQUIRED")
    require(segments[0].get("duration") == 3 and segments[-1].get("duration") == 3,
            "THREE_SECOND_CARDS_REQUIRED")
    require(segments[0].get("title") == "언제, 어디서든,\n평소와 같은 경험을.", "EXISTING_FIRST_MESSAGE_REQUIRED")
    require(tuple(s.get("scene_id") for s in segments[1:-1]) == SCENES
            and all(s.get("kind") == "video" and s.get("duration") == 2 for s in segments[1:-1]),
            "AGREED_FOURTEEN_TWO_SECOND_SCENES_REQUIRED")
    require(all(isinstance(s.get(k), str) and s[k].strip() for s in segments for k in ("title", "subtitle")),
            "VISIBLE_SCENE_COPY_REQUIRED")
    require(plan.get("audio_sha256") == MUSIC_SHA and plan.get("audio_start") == 12
            and plan.get("audio_volume") == 0.32 and plan.get("audio_fade_in_seconds") == 0.8
            and plan.get("audio_fade_out_seconds") == 1.4, "EXISTING_MUSIC_MIX_REQUIRED")
    require(plan.get("crop_xywh") == [854, 90, 1682, 1210], "FULL_CARCUE_PANEL_REQUIRED")
    require(plan.get("source_display") == [2560, 1440], "EXPECTED_PLEOS_DISPLAY_REQUIRED")
    require(plan.get("hero_asset") == "content/illustrations/pleos-reference/car/frame-020.png"
            and plan.get("safety_asset") == "content/illustrations/pleos-reference/seatbelt.png",
            "EXISTING_USER_REFERENCE_VISUALS_REQUIRED")
    require(plan.get("audio") == ".tooling/media/scott-buckley-a-kind-of-hope.mp3", "EXISTING_LOCAL_MUSIC_REQUIRED")
    require(sum(s["duration"] for s in segments) == 34, "THIRTY_FOUR_SECONDS_REQUIRED")
    return plan


def png_size(path):
    content = path.read_bytes()
    require(content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) >= 24, "PNG_EVIDENCE_REQUIRED")
    return list(struct.unpack(">II", content[16:24]))


def validate_language_transition(row):
    start, end = row["device_ms"], row["hold_end_device_ms"]
    clicked, completed = row.get("selection_clicked_device_ms"), row.get("transition_completed_device_ms")
    require(row.get("scene_kind") == "LANGUAGE_TRANSITION" and row.get("selected_locale") == "en"
            and row.get("locale") == "en" and row.get("page") == "HOME"
            and number(clicked) and number(completed)
            and start < clicked <= completed < min(start + 2000, end),
            "ACTUAL_ENGLISH_SELECTION_AND_HOME_TRANSITION_WITHIN_CUT_REQUIRED")


def validate_recording(root, manifest_path, plan):
    """Validate identities, scene timing and bounded provenance, never infer pixels."""
    manifest = read_json(manifest_path)
    require(manifest.get("schema_version") == 1 and manifest.get("test_pass") is True
            and manifest.get("type") == "UNEDITED_REAL_PLEOS_APK_SCREENRECORD", "PASSED_NATIVE_RECORDING_REQUIRED")
    require(manifest.get("source") == "PLEOS" and manifest.get("package") == "com.carcue.app"
            and manifest.get("single_apk") is True and manifest.get("single_process") is True
            and str(manifest.get("app_pid", "")).isdigit() and int(manifest["app_pid"]) > 0,
            "ONE_PLEOS_APK_PROCESS_REQUIRED")
    for flag in ("physical_vehicle_tested", "app_sdk_set_called", "seatbelt_status_connected", "paid_provider_called"):
        require(manifest.get(flag) is False, "EXPLICIT_PROVENANCE_BOUNDARY_REQUIRED:" + flag)
    require(manifest.get("question_translation_calls") == 0 and manifest.get("cleanup_errors") == [],
            "CLEANUP_AND_QUESTION_DEFERRAL_REQUIRED")
    video, apk = existing(root, manifest.get("video")), existing(root, manifest.get("apk"))
    require(sha(video) == manifest.get("video_sha256"), "RAW_VIDEO_HASH_MISMATCH")
    require(sha(apk) == manifest.get("apk_sha256") == manifest.get("installed_apk_sha256"), "INSTALLED_APP_HASH_MISMATCH")
    require(HASH.fullmatch(str(manifest.get("test_apk_sha256", ""))) is not None, "TEST_APK_HASH_REQUIRED")
    require(manifest.get("display") == {"width": 2560, "height": 1440}
            and manifest.get("crop_xywh") == plan["crop_xywh"], "RECORDING_DISPLAY_CROP_MISMATCH")
    files = manifest.get("files_sha256")
    require(isinstance(files, dict) and bool(files), "NATIVE_ARTIFACT_HASHES_REQUIRED")
    for filename, expected in files.items():
        require(isinstance(filename, str) and HASH.fullmatch(str(expected)) is not None, "INVALID_ARTIFACT_HASH")
        require(sha(existing(root, str(manifest_path.parent / filename))) == expected, "NATIVE_ARTIFACT_HASH_MISMATCH:" + filename)
    started = manifest.get("recording_started_device_ms")
    require(number(started) and started > 0, "RECORDING_START_TIME_REQUIRED")
    scenes = manifest.get("scenes")
    require(isinstance(scenes, list) and all(isinstance(s, dict) for s in scenes), "SCENES_REQUIRED")
    ids = [s.get("scene_id") for s in scenes]
    require(len(ids) == len(set(ids)) and set(SCENES).issubset(ids), "UNIQUE_REQUIRED_SCENES_REQUIRED")
    selected = [next(s for s in scenes if s["scene_id"] == scene_id) for scene_id in SCENES]
    last_end, cuts = started, []
    for row in selected:
        start, end = row.get("device_ms"), row.get("hold_end_device_ms")
        require(number(start) and number(end) and start >= last_end and end - start >= 2000
                and row.get("hold_seconds") == 2, "NONOVERLAPPING_TWO_SECOND_WINDOW_REQUIRED:" + row["scene_id"])
        if row["scene_id"] == "language-en":
            validate_language_transition(row)
        last_end = end
        require(row.get("source") == "PLEOS", "MOCK_SCENE_REFUSED")
        for key, size in (("compose_png", [1682, 1210]), ("physical_png", [2560, 1440])):
            path = existing(root, str(manifest_path.parent / row[key]))
            require(row[key] in files and sha(path) == files[row[key]] and png_size(path) == size,
                    "HASHED_FULL_SIZE_SCENE_PNG_REQUIRED")
        cuts.append({"scene_id": row["scene_id"], "start": (start - started) / 1000,
                     "duration": 2, "hold_start_device_ms": start, "hold_end_device_ms": end})
    by_id = {s["scene_id"]: s for s in selected}
    for scene_id, value in (("door-closed", "CLOSED"), ("door-open", "OPEN"), ("door-restored", "CLOSED")):
        row = by_id[scene_id]
        require(row.get("value") == value and row.get("read_status") == "VALUE" and row.get("received_at"),
                "ACTUAL_SDK_READING_REQUIRED:" + scene_id)
    for scene_id in ("official-guide-step2", "ask-ko", "translation-en", "ask-en", "ask-ja"):
        row = by_id[scene_id]
        require(row.get("profile_id") == PROFILE and row.get("market") == "KR"
                and row.get("ux_known") is True and row.get("ux_restricted") is False,
                "REVIEWED_KR_PROFILE_AND_UX_REQUIRED:" + scene_id)
    require(by_id["official-guide-step2"].get("guide_id") == GUIDE, "OFFICIAL_GUIDE_REQUIRED")
    asks = [by_id[scene_id] for scene_id in ("ask-ko", "ask-en", "ask-ja")]
    for row, locale in zip(asks, ("ko-KR", "en", "ja-JP")):
        require(row.get("locale") == locale and row.get("ai_provider") == "OLLAMA_LOCAL"
                and row.get("ai_model") == MODEL and HASH.fullmatch(str(row.get("request_id_hash", ""))) is not None,
                "ACTUAL_LOCAL_MULTILINGUAL_ASK_REQUIRED")
    audit = manifest.get("audit")
    hashes = [s["request_id_hash"] for s in asks]
    require(isinstance(audit, list) and len(audit) == 3 and len(set(hashes)) == 3
            and {e.get("request_id_hash") for e in audit} == set(hashes), "THREE_ASK_AUDIT_MATCHES_REQUIRED")
    require(all(e.get("provider_kind") == "OLLAMA_LOCAL" and e.get("model") == MODEL
                and e.get("operation") == "LocalPassageSelection" and e.get("outcome") == "STRUCTURED_VALIDATED"
                and e.get("http_status") == 200 for e in audit), "VALIDATED_LOCAL_MODEL_EVIDENCE_REQUIRED")
    translation = by_id["translation-en"]
    require(translation.get("ai_provider") == "STORED_GUIDE" and translation.get("ai_model") is None
            and translation.get("review_status") == "REVIEWED" and translation.get("content_kind") == "ANSWER"
            and translation.get("source_locale") == "ko-KR" and translation.get("target_locale") == "en",
            "REVIEWED_STORED_ANSWER_TRANSLATION_REQUIRED")
    drive, ended = by_id["drive-restricted"], by_id["end-session"]
    require(drive.get("ux_known") is True and drive.get("ux_restricted") is True
            and isinstance(drive.get("ux_flags"), int) and drive["ux_flags"] > 0, "ACTUAL_DRIVE_UX_RESTRICTION_REQUIRED")
    require(ended.get("session_started") is False and ended.get("deletion_pending") is False
            and ended.get("value") is None and ended.get("page") == "PROFILE", "ENDED_SESSION_RESET_REQUIRED")
    return manifest, cuts, video, apk


def local_assets(root, plan, apk=None):
    music = read_json(root / "Docs/media-sources.json")["music"]
    audio = existing(root, plan["audio"])
    require(sha(audio) == plan["audio_sha256"] == music["sha256"], "EXISTING_MUSIC_BYTES_MISMATCH")
    assets = {key: existing(root, plan[key]) for key in ("hero_asset", "safety_asset")}
    if apk is not None:
        import zipfile
        with zipfile.ZipFile(apk) as package:
            for key, path in assets.items():
                require(package.read("assets/" + plan[key].removeprefix("content/")) == path.read_bytes(),
                        "INTRO_ASSET_DIFFERS_FROM_RECORDED_APK")
    return music, audio, assets


def execute(command, cwd, log=None, timeout=180):
    result = subprocess.run([str(p) for p in command], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if log is not None:
        with log.open("x") as target:
            target.write(result.stdout + result.stderr)
    require(result.returncode == 0, "LOCAL_MEDIA_TOOL_FAILED:" + str(command[0]))
    return result.stdout


def write_json(path, value):
    with path.open("x") as target:
        json.dump(value, target, ensure_ascii=False, indent=2, allow_nan=False)
        target.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "Docs/sdk-intro-live.json")
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, help="Parent under workspace output/qa; run ID is appended")
    parser.add_argument("--run-id")
    parser.add_argument("--audio-reference", type=Path, help="Previous 34-second intro for exact decoded-PCM comparison")
    parser.add_argument("--check-plan", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    plan_path = args.plan.resolve()
    plan = validate_plan(read_json(plan_path))
    if args.check_plan:
        print(json.dumps({"plan_valid": True, "scenes": len(SCENES), "duration_seconds": 34,
                          "recording_or_runtime_tested": False}, indent=2))
        return
    require(args.manifest is not None, "ACTUAL_RECORDING_MANIFEST_REQUIRED")
    manifest_path = existing(root, str(args.manifest))
    manifest, cuts, video, apk = validate_recording(root, manifest_path, plan)
    music, audio, assets = local_assets(root, plan, apk)
    if args.check_only:
        print(json.dumps({"input_evidence_valid": True, "rendered": False, "manifest_sha256": sha(manifest_path),
                          "media_not_decoded": True, "visual_review_still_required": True}, indent=2))
        return
    require(args.run_id is not None and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id), "UNIQUE_SAFE_RENDER_RUN_ID_REQUIRED")
    parent = (args.output_dir or root / "output/qa/sdk-live-intro").resolve()
    out = parent / args.run_id
    require(parent.is_relative_to((root / "output/qa").resolve()) and not out.is_relative_to(manifest_path.parent),
            "NEW_SEPARATE_QA_OUTPUT_REQUIRED")
    require(not out.exists(), "REFUSING_EXISTING_RENDER_DIRECTORY")
    reference = existing(root, str(args.audio_reference or root / "output/qa/carcue-full-sdk-intro.mp4"))
    out.mkdir(parents=True, exist_ok=False)
    state = {"rendered": False, "validation_passed": False, "visual_review_status": "PENDING_INDEPENDENT_REVIEW",
             "run_id": args.run_id, "started_at": datetime.now(timezone.utc).isoformat(),
             "source_manifest": str(manifest_path), "source_manifest_sha256": sha(manifest_path),
             "source_video_sha256": sha(video), "plan_sha256": sha(plan_path)}
    try:
        binary = out / "render-sdk-intro"
        cache = out / "swift-module-cache"
        cache.mkdir()
        execute(["xcrun", "swiftc", "-parse-as-library", "-suppress-warnings", "-module-cache-path", cache,
                 ROOT / "scripts/render_sdk_intro.swift", "-o", binary], root, out / "compile.log")
        probe = json.loads(execute([binary, "probe", video], root))
        require([probe["width"], probe["height"]] == plan["source_display"], "RAW_DISPLAY_SIZE_MISMATCH")
        require(0 < probe["duration_seconds"] <= 360.1, "SINGLE_RECORDING_MAXIMUM_360_SECONDS")
        require(all(c["start"] >= 0 and c["start"] + 2 <= probe["duration_seconds"] for c in cuts), "CUT_OUTSIDE_RAW_RECORDING")
        prepared = copy.deepcopy(plan)
        prepared["output"] = str(out / "carcue-sdk-live-intro.mp4")
        prepared["audio"] = str(audio)
        prepared.update({key: str(path) for key, path in assets.items()})
        prepared["sources"] = {"sdk": {"video": str(video), "caption": "실제 Pleos SDK 연결 앱 · 전용 AVD", "crop_xywh": plan["crop_xywh"]}}
        prepared["music_credit"] = music["required_credit"]
        for shot, cut in zip(prepared["segments"][1:-1], cuts):
            shot.update(source="sdk", start=cut["start"])
        prepared_path = out / "resolved-plan.json"
        write_json(prepared_path, prepared)
        work = out / "work"
        work.mkdir()
        execute([binary, "render", prepared_path, work], root, out / "render.log")
        rendered = Path(prepared["output"])
        state.update(rendered=True, output=str(rendered), video_sha256=sha(rendered))
        final_probe = json.loads(execute([binary, "probe", rendered], root))
        require([final_probe["width"], final_probe["height"]] == [1920, 1080]
                and abs(final_probe["duration_seconds"] - 34) < 0.05
                and abs(final_probe["fps"] - 30) < 0.05 and final_probe["audio_tracks"] == 1,
                "RENDER_FORMAT_MISMATCH")
        execute([binary, "pcm", reference, out / "previous-intro.pcm"], root)
        execute([binary, "pcm", rendered, out / "current-intro.pcm"], root)
        pcm_hash = sha(out / "current-intro.pcm")
        require((out / "current-intro.pcm").stat().st_size > 0
                and pcm_hash == sha(out / "previous-intro.pcm"), "BACKGROUND_MUSIC_PCM_DIFFERS_FROM_PREVIOUS_INTRO")
        frames = out / "frames"
        frames.mkdir()
        frame_times = [("intro", 1.5), *[(scene, 4 + 2 * i) for i, scene in enumerate(SCENES)], ("outro", 32.5)]
        frame_hashes = {}
        for scene, at in frame_times:
            target = frames / (scene + ".png")
            execute([binary, "frame", rendered, str(at), target], root)
            require(png_size(target) == [1920, 1080], "FULL_RESOLUTION_REVIEW_FRAME_REQUIRED")
            frame_hashes[str(target.relative_to(out))] = sha(target)
        credits = (music["required_credit"] + "\n" + music["source_page"] + "\n" + music["license_url"]
                   + "\nMusic: identical original MP3, 12s start, gain 0.32 and 0.8s/1.4s fades; include this credit in a published video description.\n\n"
                   + "All functional scenes: one current Pleos SDK APK/process continuous screenrecord on the dedicated AVD, not a physical vehicle.\n"
                   + "Actual free local Ollama/qwen3:4b selects reviewed complete answer units; server assembles stored source text and cautions. Saved ANSWER translation makes no additional model call.\n"
                   + "Selected 2024 Korean-market IONIQ 5 manual; profile is not SDK/VIN vehicle authentication. Not OEM or human-expert certification.\n"
                   + "Car and belt: user-specified Pleos rendered reference frames inside the app, not a live SDK 3D widget. Belt sensor is not connected. No redistribution license for Pleos visuals is asserted.\n")
        with (out / "credits.txt").open("x") as target:
            target.write(credits)
        state.update(rendered=True, validation_passed=True, finished_at=datetime.now(timezone.utc).isoformat(),
                     output=str(rendered), video_sha256=sha(rendered), output_probe=final_probe,
                     raw_probe=probe, single_apk=True, single_process=True, app_pid=manifest["app_pid"],
                     apk_sha256=manifest["apk_sha256"], installed_apk_sha256=manifest["installed_apk_sha256"],
                     test_apk_sha256=manifest["test_apk_sha256"], source_cuts=cuts,
                     source_display=plan["source_display"], crop_xywh=plan["crop_xywh"], music=music,
                     audio_start=12, audio_volume=0.32, audio_fades=[0.8, 1.4],
                     previous_intro=str(reference), previous_intro_sha256=sha(reference), decoded_pcm_sha256=pcm_hash,
                     decoded_pcm_exact_match=True, rendered_review_frames=frame_hashes,
                     physical_vehicle_tested=False, app_sdk_set_called=False, seatbelt_status_connected=False,
                     actual_local_ask_calls=3, stored_answer_translation_calls=0, paid_provider_called=False,
                     question_translation_calls=0, model_selection_not_freeform_instruction_generation=True,
                     visual_review_limit="Frame export and hash checks are not independent visual/semantic QA; all 16 frames and source physical screenshots require review.")
    except Exception as exc:
        state.update(error_type=type(exc).__name__, error=str(exc), finished_at=datetime.now(timezone.utc).isoformat())
        raise
    finally:
        write_json(out / "render-validation.json", state)
    print(json.dumps({"output": state["output"], "video_sha256": state["video_sha256"],
                      "duration_seconds": 34, "decoded_music_pcm_match": True,
                      "visual_review_status": state["visual_review_status"]}, indent=2))


if __name__ == "__main__":
    main()
