"""Render the CarCue product introduction from verified APK footage and original audio."""
import array
import hashlib
import json
import math
import random
import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
plan_path = ROOT / "Docs/app-intro.json"
plan = json.loads(plan_path.read_text())
duration = sum(s["duration"] for s in plan["segments"])
work = ROOT / "output/qa/app-intro-work"
work.mkdir(parents=True, exist_ok=True)

# An original, quiet C–F–Am–G ambient arpeggio. No downloaded music or voice samples.
rate = 44100
music = [0.0] * int(duration * rate)
rng = random.Random(20261113)
beat = 60 / 104
chords = [(48, 60, 64, 67, 74), (53, 60, 65, 69, 72), (45, 60, 64, 69, 72), (43, 59, 62, 67, 71)]


def note(start, length, midi, amplitude, pluck=False):
    freq = 440 * 2 ** ((midi - 69) / 12)
    first, count = int(start * rate), min(int(length * rate), len(music) - int(start * rate))
    for k in range(max(0, count)):
        t = k / rate
        attack = min(1, t / (.025 if pluck else .5))
        release = min(1, (length - t) / (.3 if pluck else .6))
        env = attack * release * (math.exp(-t * 3) if pluck else .75)
        tone = math.sin(2 * math.pi * freq * t) + .16 * math.sin(2 * math.pi * freq * 2 * t)
        music[first + k] += amplitude * env * tone


for bar in range(math.ceil(duration / (4 * beat))):
    start = bar * 4 * beat
    chord = chords[(bar // 2) % len(chords)]
    for pitch in chord:
        note(start, min(4 * beat + .4, duration - start), pitch, .014)
    for n, pitch in enumerate([chord[1], chord[2], chord[3], chord[4], chord[3], chord[2], chord[4], chord[2]]):
        note(start + n * beat / 2, .75, pitch + 12, .025, True)
    for n in range(4):
        note(start + n * beat, .22, chord[0] - 12, .035, True)
    # Very soft transient ticks establish rhythm without overpowering the screen.
    for n in range(8):
        a = int((start + n * beat / 2) * rate)
        for k in range(min(int(rate * .035), len(music) - a)):
            music[a + k] += rng.uniform(-1, 1) * .004 * math.exp(-k / (rate * .008))
peak = max(abs(x) for x in music)
gain = .24 / peak
pcm = array.array("h")
for i, value in enumerate(music):
    t = i / rate
    fade = min(1, t / .8, (duration - t) / 1.2)
    pcm.append(round(value * gain * max(0, fade) * 32767))
audio = ROOT / plan["audio"]
with wave.open(str(audio), "wb") as f:
    f.setparams((1, 2, rate, 0, "NONE", "not compressed"))
    f.writeframes(pcm.tobytes())
binary = ROOT / ".tooling/render-app-intro"
subprocess.run(["xcrun", "swiftc", "-parse-as-library", "-suppress-warnings", "-module-cache-path",
                str(ROOT / ".tooling/swift-module-cache"), str(ROOT / "scripts/render_app_intro.swift"),
                "-o", str(binary)], cwd=ROOT, check=True)
subprocess.run([str(binary), str(plan_path)], cwd=ROOT, check=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
out = ROOT / plan["output"]
meta = {
    "type": "PRODUCT_INTRO_EDIT_OF_REAL_APK_FOOTAGE",
    "duration_seconds": duration, "resolution": [1920, 1080], "fps": 30,
    "source_video": plan["source"], "source_sha256": sha(ROOT / plan["source"]),
    "plan_sha256": sha(plan_path), "video_sha256": sha(out),
    "apk_sha256": json.loads((ROOT / "output/qa/carcue-native-run.json").read_text())["apk_sha256"],
    "audio": "Original procedural ambient bed; no third-party recordings or voice",
    "audio_peak_before_fade": peak * gain, "vehicle_data": "MOCK", "external_ai_called": False,
    "functional_screens": "All functional screens are cuts from the same verified APK recording",
    "segments": plan["segments"],
}
out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
print(f"SAVED {out} ({duration}s)", flush=True)
