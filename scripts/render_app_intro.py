"""Render CarCue introduction from verified APK footage and licensed external music."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
plan_path = ROOT / "Docs/app-intro.json"
plan = json.loads(plan_path.read_text())
sources = json.loads((ROOT / "Docs/media-sources.json").read_text())
music = sources["music"]
audio = ROOT / plan["audio"]
audio.parent.mkdir(parents=True, exist_ok=True)
if not audio.exists():
    subprocess.run(["curl", "-fL", "--retry", "1", "--max-time", "120", "-o", str(audio), music["download_url"]], check=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
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
    "vehicle_data": "MOCK", "external_ai_called": False,
    "functional_screens": "All functional screens are cuts from the same verified APK recording",
    "segments": plan["segments"],
}
out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
credits = music["required_credit"] + "\n" + music["source_page"] + "\n" + music["license_url"] + "\n\n"
credits += "Music excerpt trimmed, volume adjusted and faded for this video.\nFor YouTube, include the music credit in the video description.\n\n"
credits += "Vehicle photos: crash71100 / Calreyn88, CC0 1.0, Wikimedia Commons.\n"
for image in sources["vehicle_photos"]: credits += image["source"] + "\n"
out.with_name("carcue-app-intro-credits.txt").write_text(credits)
print(f"SAVED {out} (licensed external music)", flush=True)
