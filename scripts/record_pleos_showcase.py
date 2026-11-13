"""Record the complete three-language walkthrough from one real SDK APK/process."""
import hashlib
import json
import subprocess
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ADB = ROOT / ".tooling/android-sdk/platform-tools/adb"
SERIAL, PACKAGE = "emulator-5584", "com.carcue.app"
OUT = ROOT / "output/qa/pleos-full-showcase"
MARKERS = "files/pleos-showcase"
OUT.mkdir(parents=True, exist_ok=True)


def adb(*args, check=True, timeout=15):
    return subprocess.run([str(ADB), "-s", SERIAL, *args], capture_output=True, text=True,
                          check=check, timeout=timeout).stdout.strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert adb("shell", "getprop", "ro.kernel.qemu") == "1"
assert adb("shell", "getprop", "ro.boot.qemu.avd_name") == "CarCue_Pleos21"
assert adb("shell", "getprop", "sys.boot_completed") == "1"
assert not adb("shell", "pidof", "screenrecord", check=False)
user = adb("shell", "am", "get-current-user")
assert user.isdigit() and user != "0"
apk = ROOT / "output/apk/carcue-pleos-showcase-debug.apk"
test_apk = ROOT / "android/app/build/outputs/apk/androidTest/pleos/debug/app-pleos-debug-androidTest.apk"
for path in (apk, test_apk):
    assert "Success" in adb("install", "--no-streaming", "--user", user, "-r", str(path), timeout=75)
remote_apk = adb("shell", "pm", "path", "--user", user, PACKAGE).splitlines()[0].removeprefix("package:")
reference = json.loads((ROOT / "content/illustrations/pleos-reference/manifest.json").read_text())
assert sha(ROOT / reference["source"]) == reference["source_sha256"]
with tempfile.TemporaryDirectory(dir=ROOT / ".tooling") as temp:
    installed = Path(temp) / "installed.apk"
    adb("pull", remote_apk, str(installed), timeout=30)
    installed_sha = sha(installed)
    assert installed_sha == sha(apk)
    with zipfile.ZipFile(installed) as archive:
        for path, expected in reference["output_sha256"].items():
            data = archive.read("assets/" + path)
            assert hashlib.sha256(data).hexdigest() == expected
            assert data == (ROOT / "content" / path).read_bytes()
service = adb("shell", "dumpsys", "package", "ai.pleos.playground.service.vehicle")
service_version = [s.strip() for s in service.splitlines() if "versionName=" in s or "versionCode=" in s][:2]
adb("shell", "pm", "clear", "--user", user, PACKAGE)
adb("forward", "tcp:8088", "tcp:8088")


def console(path, method="POST"):
    with urlopen(Request("http://127.0.0.1:8088" + path, method=method), timeout=8) as r:
        return json.load(r)


def app(*args, check=True):
    return adb("shell", "run-as", PACKAGE, "--user", user, *args, check=check)


def files():
    return set(app("ls", MARKERS, check=False).splitlines())


heartbeat = "/browser/session?client=carcue-sdk-showcase"
console(heartbeat)
console("/vehicle/controls?speed=0&accelerator=0&brake=0", "PUT")
console("/vehicle/gear?gear=Park", "PUT")
console("/vehicle/body?door_fl=0", "PUT")
adb("logcat", "-c")
command = [str(ADB), "-s", SERIAL, "shell", "am", "instrument", "--user", user, "-w", "-r",
           "-e", "recordShowcase", "true", "-e", "class", "com.carcue.app.PleosShowcaseTest",
           PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner"]
(OUT / "command.json").write_text(json.dumps(command, indent=2) + "\n")
log = (OUT / "instrumentation.txt").open("w")
process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
recorder = None
record_log = None
events, handled = [], set()
remote_video = "/sdcard/carcue-pleos-native-run.mp4"
success = False
try:
    deadline = time.monotonic() + 60
    while "ready" not in files():
        assert process.poll() is None, "Instrumentation exited before ready"
        assert time.monotonic() < deadline, "App startup timed out"
        console(heartbeat); time.sleep(.2)
    app_pid = adb("shell", "pidof", PACKAGE)
    record_log = (OUT / "screenrecord.txt").open("w")
    recorder = subprocess.Popen([str(ADB), "-s", SERIAL, "shell", "screenrecord", "--bit-rate", "6000000",
                                 "--time-limit", "180", remote_video], stdout=record_log, stderr=subprocess.STDOUT)
    started = round(float(adb("shell", "cat", "/proc/uptime").split()[0])*1000)
    time.sleep(1)
    app("touch", MARKERS + "/go")
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        console(heartbeat)
        present = files()
        for marker, target in [("request-open", 1), ("request-close", 0), ("request-open-en", 1), ("request-close-ja", 0)]:
            if marker in present and marker not in handled:
                state = console(f"/vehicle/body?door_fl={target}", "PUT")
                events.append({"at": datetime.now(timezone.utc).isoformat(), "marker": marker,
                               "value": target, "front_left": state["body"]["doors"]["front_left"]})
                handled.add(marker)
        if "done" in present:
            assert adb("shell", "pidof", PACKAGE) == app_pid, "App process changed during recording"
            success = True; break
        assert process.poll() is None, "Showcase test exited before done"
        time.sleep(.15)
    assert success, "SDK walkthrough timed out"
finally:
    if recorder is not None:
        pid = adb("shell", "pidof", "screenrecord", check=False)
        if pid.isdigit(): adb("shell", "kill", "-2", pid)
        recorder.wait(timeout=20); record_log.close()
    app("touch", MARKERS + "/stop", check=False)
    try: process.wait(timeout=25)
    except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=8)
    log.close()
    sdk_log = adb("logcat", "-d", "-s", "CarCueVehicle:I")
    (OUT / "sdk-events.txt").write_text(sdk_log)
    (OUT / "console-events.json").write_text(json.dumps(events, indent=2)+"\n")
    (OUT / "crash.txt").write_text(adb("logcat", "-d", "-b", "crash"))
    console("/vehicle/body?door_fl=0", "PUT"); console(heartbeat + "&closing=1")
assert success and "OK (1 test)" in (OUT / "instrumentation.txt").read_text()
cursor = 0
for token in ["GET_RECEIVED:RANGE_VERIFIED:value=0"] + [f"CALLBACK_RECEIVED:RANGE_VERIFIED:value={v}" for v in [1, 0, 1, 0]] + ["LISTENER_UNREGISTER_RETURNED", "RELEASE_RETURNED"]:
    at = sdk_log.find(token, cursor); assert at >= 0, token; cursor = at+len(token)
scenes = [json.loads(line) for line in app("cat", MARKERS+"/events.jsonl").splitlines()]
assert len(scenes) == 20 and all(s["source"] == "PLEOS" for s in scenes)
names = ["result.json", "car-initial-closed.png", "car-open.png", "car-restored-closed.png", "ko-closed.png", "ko-open.png", "ko-restored.png", "en-home.png", "en-status.png", "ja-home.png", "ja-status.png"]
for name in names:
    with (OUT / ("showcase-result.json" if name == "result.json" else name)).open("wb") as f:
        subprocess.run([str(ADB), "-s", SERIAL, "exec-out", "run-as", PACKAGE, "--user", user, "cat", MARKERS+"/"+name], stdout=f, check=True, timeout=15)
visual = json.loads((OUT / "showcase-result.json").read_text())
assert visual["initial_closed_sha256"] == visual["restored_closed_sha256"] != visual["open_sha256"]
video = OUT / "carcue-pleos-native-run.mp4"
adb("pull", remote_video, str(video), timeout=30)
metadata = {
    "type": "UNEDITED_REAL_PLEOS_APK_SCREENRECORD", "recorded_at": datetime.now(timezone.utc).isoformat(),
    "single_apk": True, "single_process_id": app_pid, "package": PACKAGE,
    "apk": str(apk), "apk_sha256": sha(apk), "installed_apk_sha256": installed_sha, "test_apk_sha256": sha(test_apk),
    "video_sha256": sha(video), "serial": SERIAL, "avd": "CarCue_Pleos21", "android_user": int(user),
    "display": adb("shell", "wm", "size"), "sdk_version": "2.3.2", "vehicle_service": service_version,
    "hold_seconds_per_function": 2, "scenes": scenes, "recording_started_device_ms_approx": started,
    "vehicle_data": "PLEOS", "visual_result": visual, "virtual_console_events": events,
    "hero_asset": "content/illustrations/pleos-reference/car/frame-020.png",
    "safety_asset": "content/illustrations/pleos-reference/seatbelt.png", "reference_visuals": reference,
    "hero_asset_sha256": sha(ROOT / "content/illustrations/pleos-reference/car/frame-020.png"),
    "safety_asset_sha256": sha(ROOT / "content/illustrations/pleos-reference/seatbelt.png"),
    "physical_vehicle_tested": False, "app_sdk_set_called": False, "inserted_external_frames": False,
    "seatbelt_status_connected": False, "external_ai_called": False,
    "files_sha256": {name: sha(OUT/name) for name in ["instrumentation.txt", "sdk-events.txt", "console-events.json", "showcase-result.json"]},
}
video.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+"\n")
print("PASS: one real SDK APK/process, 20 scenes, ko/en/ja, four callbacks, car pixels restored, session release")
