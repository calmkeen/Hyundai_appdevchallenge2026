"""Record one real APK walkthrough. No image insertion, SDK system UI or video montage."""
import hashlib
import json
import subprocess
import tempfile
import zipfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADB = ROOT / ".tooling/android-sdk/platform-tools/adb"
SERIAL = "emulator-5582"
PACKAGE = "com.carcue.app.demo"
OUT = ROOT / "output/qa"
MARKERS = "files/native-recording"


def adb(*args, check=True, timeout=30):
    r = subprocess.run([str(ADB), "-s", SERIAL, *args], capture_output=True, text=True, timeout=timeout, check=check)
    return r.stdout.strip()


def marker(name):
    return adb("shell", "run-as", PACKAGE, "cat", f"{MARKERS}/{name}", check=False)


def signal(name):
    adb("shell", "run-as", PACKAGE, "touch", f"{MARKERS}/{name}")


def wait_marker(name, timeout, process):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if marker(name):
            return
        if process.poll() is not None:
            raise RuntimeError(f"Instrumentation exited before {name}; see native-showcase-instrumentation.txt")
        time.sleep(.15)
    raise TimeoutError(name)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert SERIAL.startswith("emulator-") and adb("shell", "getprop", "ro.kernel.qemu") == "1"
assert adb("shell", "getprop", "sys.boot_completed") == "1"
assert not adb("shell", "pidof", "screenrecord", check=False)
apk = ROOT / "output/apk/carcue-demo-debug.apk"
test_apk = ROOT / "android/app/build/outputs/apk/androidTest/demo/debug/app-demo-debug-androidTest.apk"
for path in (apk, test_apk):
    assert "Success" in adb("install", "-r", str(path), timeout=60)
base = adb("shell", "pm", "path", PACKAGE).removeprefix("package:")
with tempfile.TemporaryDirectory(dir=ROOT / ".tooling") as temp:
    installed = Path(temp) / "installed.apk"
    adb("pull", base, str(installed))
    installed_hash = sha(installed)
    assert installed_hash == sha(apk)
    hero_asset = "content/illustrations/ioniq5-real.jpg"
    with zipfile.ZipFile(installed) as archive:
        hero_bytes = archive.read("assets/illustrations/ioniq5-real.jpg")
    assert hero_bytes == (ROOT / hero_asset).read_bytes()
    hero_sha256 = hashlib.sha256(hero_bytes).hexdigest()
adb("shell", "pm", "clear", PACKAGE)
OUT.mkdir(parents=True, exist_ok=True)
log = (OUT / "native-showcase-instrumentation.txt").open("w")
process = subprocess.Popen([str(ADB), "-s", SERIAL, "shell", "am", "instrument", "-w", "-r", "-e", "recordShowcase", "true",
                           "-e", "class", "com.carcue.app.NativeShowcaseTest",
                           PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner"], stdout=log, stderr=subprocess.STDOUT)
wait_marker("ready", 60, process)
touches = adb("shell", "settings", "get", "system", "show_touches")
adb("shell", "settings", "put", "system", "show_touches", "1")
remote = "/sdcard/carcue-native-run.mp4"
recorder = subprocess.Popen([str(ADB), "-s", SERIAL, "shell", "screenrecord", "--bit-rate", "6000000", "--time-limit", "180", remote], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
started = round(float(adb("shell", "cat", "/proc/uptime").split()[0]) * 1000)
success = False
try:
    time.sleep(1)
    signal("go")
    wait_marker("done", 140, process)
    # A final real tap on the idle CarCue header ensures the recorder receives
    # a clean frame after the end-session dialog has completely disappeared.
    adb("shell", "input", "tap", "80", "60")
    time.sleep(.6)
    success = True
finally:
    pid = adb("shell", "pidof", "screenrecord", check=False)
    if pid.isdigit():
        adb("shell", "kill", "-2", pid)
    recorder.communicate(timeout=20)
    adb("shell", "settings", "delete" if touches == "null" else "put", "system", "show_touches", *([] if touches == "null" else [touches]))
    signal("stop")
    process.wait(timeout=25)
    log.close()
if not success:
    raise RuntimeError("Walkthrough failed; raw recording is not published")
result = (OUT / "native-showcase-instrumentation.txt").read_text()
assert "OK (1 test)" in result, result[-3000:]
video = OUT / "carcue-native-run.mp4"
adb("pull", remote, str(video))
assert video.stat().st_size > 100000
events = [json.loads(line) for line in marker("events.jsonl").splitlines()]
info = {
    "type": "UNEDITED_REAL_APK_SCREENRECORD",
    "recorded_at": datetime.now(timezone.utc).isoformat(),
    "apk": str(apk), "apk_sha256": sha(apk), "installed_apk_sha256": installed_hash,
    "video_sha256": sha(video), "serial": SERIAL,
    "avd": adb("shell", "getprop", "ro.boot.qemu.avd_name"), "display": adb("shell", "wm", "size"),
    "hold_seconds_per_function": 2, "scenes": events,
    "recording_started_device_ms_approx": started,
    "graphics": "Bundled CC0 real IONIQ 5 / IONIQ 5 N photos; received status displayed separately; 3D remains an optional app tab",
    "hero_asset": hero_asset, "hero_asset_sha256": hero_sha256,
    "model_shown_in_recording": False,
    "inserted_external_frames": False, "pleos_system_ui_inserted": False,
    "vehicle_data": "MOCK", "external_ai_called": False,
}
video.with_suffix(".json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
print(f"SAVED {video}; {len(events)} real app scenes, identical installed APK hash", flush=True)
