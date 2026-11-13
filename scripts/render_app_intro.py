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
recording = json.loads((ROOT / "output/qa/carcue-native-run.json").read_text())
assert sha(ROOT / plan["source"]) == recording["video_sha256"], "Source recording hash mismatch"
assert sha(Path(recording["apk"])) == recording["apk_sha256"] == recording["installed_apk_sha256"], "Record the current APK before editing"
assert plan["hero_asset"] == recording["hero_asset"]
assert sha(ROOT / plan["hero_asset"]) == recording["hero_asset_sha256"], "Hero must match the recorded APK asset"
with zipfile.ZipFile(recording["apk"]) as package:
    assert package.read("assets/" + plan["hero_asset"].removeprefix("content/")) == (ROOT / plan["hero_asset"]).read_bytes()
# Each new run has slightly different real touch/transition times. Align cuts
# with the device timestamps rather than reusing offsets from an older APK.
events = {s["scene"]: s for s in recording["scenes"]}
for shot in plan["segments"]:
    if shot["kind"] == "video":
        event = events[shot["source_scene"]]
        # Test markers follow the native click/swipe and idle handshake. Include
        # their lead-in so the edit retains the moving door and the actual drag.
        shot["start"] = round((event["device_ms"] - recording["recording_started_device_ms_approx"]) / 1000 + .10 - shot.get("lead_in_seconds", 0), 2)
plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
sources = json.loads((ROOT / "Docs/media-sources.json").read_text())
music = sources["music"]
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
    "source_video": plan["source"], "source_sha256": sha(ROOT / plan["source"]),
    "plan_sha256": sha(plan_path), "video_sha256": sha(out),
    "apk_sha256": json.loads((ROOT / "output/qa/carcue-native-run.json").read_text())["apk_sha256"],
    "music": music, "music_excerpt_start": plan["audio_start"], "music_volume": plan["audio_volume"],
    "vehicle_data": "MOCK",
    "vehicle_photos": sources["vehicle_photos"], "model_shown_in_intro": False,
    "hero_asset_sha256": sha(ROOT / plan["hero_asset"]), "external_ai_called": False,
    "functional_screens": "All functional screens are cuts from the same verified APK recording",
    "segments": plan["segments"],
}
out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
credits = music["required_credit"] + "\n" + music["source_page"] + "\n" + music["license_url"] + "\n\n"
credits += "Music excerpt trimmed, volume adjusted and faded for this video.\nFor YouTube, include the music credit in the video description.\n\n"
credits += "Optional 3D model available in the APK, not used in this video:\n3D: andikapratamaw (2022), Dogan Ulus (2026), MPL-2.0 AND CC-BY-4.0, adapted.\n"
credits += "https://github.com/vevalabs/openx-assets\nhttps://sketchfab.com/andikapratamaw\nhttps://www.mozilla.org/MPL/2.0/\nhttps://creativecommons.org/licenses/by/4.0/\n"
credits += "Adapted: axes, original front-left hinge/door group, animation, native materials and contact shadow. Original model/source and license texts are included in the APK.\n"
credits += "Vehicle photos used in the app/video: crash71100 / Calreyn88, CC0 1.0, Wikimedia Commons.\n"
for image in sources["vehicle_photos"]: credits += image["source"] + "\n"
out.with_name("carcue-app-intro-credits.txt").write_text(credits)
print(f"SAVED {out} (licensed external music)", flush=True)
