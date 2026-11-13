"""Render CarCue introduction from verified APK footage and licensed external music."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
plan_path = ROOT / "Docs/app-intro.json"
plan = json.loads(plan_path.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert plan["schema_version"] == 2
assert set(plan["sources"]) == {"sdk"}, "All feature shots must use the same SDK app recording"
assert all(s["source"] == "sdk" for s in plan["segments"] if s["kind"] == "video")
recordings, provenance = {}, {}
for name, source in plan["sources"].items():
    evidence = ROOT / source["evidence"]
    record = json.loads(evidence.read_text())
    recordings[name] = record
    assert sha(ROOT / source["apk"]) == record["apk_sha256"] == record["installed_apk_sha256"], "Installed APK provenance mismatch"
    if source["vehicle_data"] == "MOCK":
        assert record["vehicle_data"] == "MOCK" and "MOCK" in source["caption"]
        expected = record["video_sha256"]
    else:
        assert source["vehicle_data"] == "PLEOS" and "SDK" in source["caption"] and "AVD" in source["caption"]
        assert record["type"] in ["REAL_PLEOS_SDK_EMULATOR_VISUAL_VALIDATION", "UNEDITED_REAL_PLEOS_APK_SCREENRECORD"]
        visual = record["visual_result"]
        assert visual["source"] == "PLEOS"
        if "changed_pixels" in visual:
            assert visual["changed_pixels"] > 0
        if record["type"] == "UNEDITED_REAL_PLEOS_APK_SCREENRECORD":
            assert record["single_apk"] and record["package"] == "com.carcue.app"
            assert all(s["source"] == "PLEOS" for s in record["scenes"])
        assert visual["initial_closed_sha256"] == visual["restored_closed_sha256"] != visual["open_sha256"]
        for filename, expected_hash in record["files_sha256"].items():
            assert sha(evidence.parent / filename) == expected_hash, filename
        test_log = "instrumentation.txt" if "scenes" in record else "pleos-instrumentation.txt"
        assert "OK (1 test)" in (evidence.parent / test_log).read_text()
        expected = record["video_sha256"] if "scenes" in record else record["files_sha256"][Path(source["video"]).name]
    assert sha(ROOT / source["video"]) == expected, "Source recording hash mismatch"
    with zipfile.ZipFile(ROOT / source["apk"]) as package:
        for asset in (plan["hero_asset"], plan["safety_asset"]):
            assert package.read("assets/" + asset.removeprefix("content/")) == (ROOT / asset).read_bytes()
    provenance[name] = {**source, "video_sha256": expected, "evidence_sha256": sha(evidence),
                        "apk_sha256": record["apk_sha256"], "installed_apk_sha256": record["installed_apk_sha256"]}
recording = next(record for record in recordings.values() if "reference_visuals" in record)
assert plan["hero_asset"] == recording["hero_asset"]
assert sha(ROOT / plan["hero_asset"]) == recording["hero_asset_sha256"], "Hero must match the recorded APK asset"
assert plan["safety_asset"] == recording["safety_asset"]
assert sha(ROOT / plan["safety_asset"]) == recording["safety_asset_sha256"]
reference = recording["reference_visuals"]
assert sha(ROOT / reference["source"]) == reference["source_sha256"]
# Each new run has slightly different real touch/transition times. Align cuts
# with the device timestamps rather than reusing offsets from an older APK.
for shot in plan["segments"]:
    if shot["kind"] == "video" and "scenes" in recordings[shot["source"]]:
        recording_for_shot = recordings[shot["source"]]
        events = {s["scene"]: s for s in recording_for_shot["scenes"]}
        event = events[shot["source_scene"]]
        # Test markers follow the native click/swipe and idle handshake. Include
        # their lead-in so the edit retains the moving door and the actual drag.
        shot["start"] = round((event["device_ms"] - recording_for_shot["recording_started_device_ms_approx"]) / 1000 + .10 - shot.get("lead_in_seconds", 0), 2)
assert all(s["duration"] == 2 for s in plan["segments"] if s["kind"] == "video")
plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
media = json.loads((ROOT / "Docs/media-sources.json").read_text())
music = media["music"]
audio = ROOT / plan["audio"]
audio.parent.mkdir(parents=True, exist_ok=True)
if not audio.exists():
    subprocess.run(["curl", "-fL", "--retry", "1", "--max-time", "120", "-o", str(audio), music["download_url"]], check=True)
assert sha(audio) == music["sha256"], "External music does not match the verified source"
work = ROOT / "output/qa/app-intro-work"
work.mkdir(parents=True, exist_ok=True)
binary = ROOT / ".tooling/render-app-intro"
subprocess.run(["xcrun", "swiftc", "-parse-as-library", "-suppress-warnings", "-module-cache-path",
                str(ROOT / ".tooling/swift-module-cache"), str(ROOT / "scripts/render_app_intro.swift"),
                "-o", str(binary)], cwd=ROOT, check=True)
subprocess.run([str(binary), str(plan_path)], cwd=ROOT, check=True)
out = ROOT / plan["output"]
meta = {
    "type": "PRODUCT_INTRO_EDIT_OF_REAL_APK_FOOTAGE",
    "duration_seconds": sum(s["duration"] for s in plan["segments"]),
    "resolution": [1920, 1080], "fps": 30,
    "sources": provenance,
    "plan_sha256": sha(plan_path), "video_sha256": sha(out),
    "music": music, "music_excerpt_start": plan["audio_start"], "music_volume": plan["audio_volume"],
    "vehicle_data": "PLEOS_SDK_AVD" if all(s["vehicle_data"] == "PLEOS" for s in plan["sources"].values()) else "MIXED_PLEOS_SDK_AVD_AND_MOCK",
    "sdk_validation": {key: recordings["sdk"][key] for key in ["type", "sdk_version", "vehicle_service", "visual_result", "physical_vehicle_tested"]},
    "reference_visuals": reference, "model_shown_in_intro": False,
    "hero_asset_sha256": sha(ROOT / plan["hero_asset"]),
    "safety_asset_sha256": sha(ROOT / plan["safety_asset"]),
    "seatbelt_status_connected": False, "external_ai_called": False,
    "functional_screens": "All functional and language scenes are cuts from one verified Pleos SDK APK/process recording" if len(provenance) == 1 else "Cuts from verified APK recordings; each source labelled separately",
    "segments": plan["segments"],
}
out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
credits = music["required_credit"] + "\n" + music["source_page"] + "\n" + music["license_url"] + "\n\n"
credits += "Music excerpt trimmed, volume adjusted and faded for this video.\nFor YouTube, include the music credit in the video description.\n\n"
credits += "Door state shots: real Pleos SDK 2.3.2 / Vehicle Service 2.3.22 on the official isolated AVD, not physical vehicle testing.\n"
credits += "All feature/language shots: one real Pleos SDK APK/process recording. Guide content is a debug layout preview; belt status is not connected; external AI is not called.\n\n"
credits += "Vehicle and seat belt reference visuals: exact rendered crops from the user-specified carcue-pleos-sdk.mp4.\n"
credits += "Source SHA-256: " + reference["source_sha256"] + "\n"
credits += "CarCue displays pre-rendered frames inside the native APK, not a live SDK 3D widget. Seat belt status is not connected.\n"
credits += reference["rights"] + "\n\n"
credits += "Charging-guide image: preserved existing app asset; vehicle photos and previous 3D source/license records remain in Docs/media-sources.json and the APK.\n"
out.with_name(out.stem + "-credits.txt").write_text(credits)
print(f"SAVED {out} (licensed external music)", flush=True)
