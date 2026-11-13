"""Real SDK CLOSED -> OPEN -> CLOSED and native car pixel evidence on the isolated AVD.

Only the host writes official Virtual Console fixtures. CarCue remains read-only.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "com.carcue.app"
p = argparse.ArgumentParser()
p.add_argument("--adb", default=".tooling/android-sdk/platform-tools/adb")
p.add_argument("--serial", default="emulator-5584")
p.add_argument("--output-dir", default="output/qa/pleos-sdk-retest")
p.add_argument("--record", action="store_true")
args = p.parse_args()
out = ROOT / args.output_dir
out.mkdir(parents=True, exist_ok=True)
base = [str(ROOT / args.adb), "-s", args.serial]


def adb(*parts, timeout=12, check=True):
    return subprocess.run(base + list(parts), text=True, capture_output=True,
                          timeout=timeout, check=check).stdout.strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if not args.serial.startswith("emulator-") or adb("shell", "getprop", "ro.kernel.qemu") != "1":
    raise SystemExit("Refusing a physical vehicle/device")
avd = adb("shell", "getprop", "ro.boot.qemu.avd_name")
assert avd == "CarCue_Pleos21", "Use the isolated Pleos AVD"
assert adb("shell", "getprop", "sys.boot_completed") == "1"
user = adb("shell", "am", "get-current-user")
assert user.isdigit() and user != "0", "Wait for the foreground automotive user"
assert not adb("shell", "pidof", "screenrecord", check=False), "Existing recorder is active"
apk = ROOT / "android/app/build/outputs/apk/pleos/debug/app-pleos-debug.apk"
with tempfile.TemporaryDirectory(dir=ROOT / ".tooling") as temp:
    installed = Path(temp) / "installed.apk"
    remote = adb("shell", "pm", "path", "--user", user, PACKAGE).splitlines()[0].removeprefix("package:")
    adb("pull", remote, str(installed), timeout=30)
    installed_sha = sha(installed)
    assert installed_sha == sha(apk), "Install the current pleos APK first"
service = adb("shell", "dumpsys", "package", "ai.pleos.playground.service.vehicle")
service_version = [s.strip() for s in service.splitlines() if "versionName=" in s or "versionCode=" in s][:2]
adb("forward", "tcp:8088", "tcp:8088")


def console(path, method="GET"):
    with urlopen(Request("http://127.0.0.1:8088" + path, method=method), timeout=8) as r:
        return json.load(r)


def app_command(*parts):
    return adb("shell", "run-as", PACKAGE, "--user", user, *parts)


recorder = None
record_log = None
video_remote = "/sdcard/carcue-sdk-visual-check.mp4"


def stop_recording():
    global recorder
    if recorder is not None:
        pid = adb("shell", "pidof", "screenrecord", check=False)
        if pid.isdigit():
            adb("shell", "kill", "-2", pid)
        recorder.wait(timeout=20)
        record_log.close()
        recorder = None


heartbeat = "/browser/session?client=carcue-sdk-validation"
events = []
process = None
console(heartbeat, "POST")
console("/vehicle/body?door_fl=0", "PUT")
try:
    app_command("rm", "-f", "files/sdk-validation-finish")
    adb("logcat", "-c")
    command = base + ["shell", "am", "instrument", "--user", user, "-w", "-r", "-e", "class",
                      "com.carcue.app.PleosSdkTest", PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner"]
    (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (out / "pleos-instrumentation.txt").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        phase, seen_at = 0, None
        deadline = time.monotonic() + 180
        while process.poll() is None and time.monotonic() < deadline:
            console(heartbeat, "POST")
            text = adb("logcat", "-d", "-s", "CarCueVehicle:I")
            now = time.monotonic()
            marker = ["SDK_TEST:INITIAL_CAPTURED", "SDK_TEST:OPEN_CAPTURED", "SDK_TEST:RESTORED_CAPTURED"][min(phase, 2)]
            if phase < 3 and marker in text:
                if seen_at is None:
                    seen_at = now
                    if phase == 0 and args.record:
                        record_log = (out / "screenrecord.txt").open("w")
                        recorder = subprocess.Popen(base + ["shell", "screenrecord", "--bit-rate", "6000000",
                            "--time-limit", "120", video_remote], stdout=record_log, stderr=subprocess.STDOUT)
                if now - seen_at >= 2:
                    if phase < 2:
                        target = 1 if phase == 0 else 0
                        state = console(f"/vehicle/body?door_fl={target}", "PUT")
                        events.append({"at": datetime.now(timezone.utc).isoformat(),
                            "request": f"Virtual Console PUT door_fl={target}",
                            "front_left": state["body"]["doors"]["front_left"]})
                    else:
                        stop_recording()
                        app_command("touch", "files/sdk-validation-finish")
                    phase += 1
                    seen_at = None
            time.sleep(.25)
        if process.poll() is None:
            process.terminate()
            raise RuntimeError("SDK visual test timed out")
finally:
    stop_recording()
    if process is not None and process.poll() is None:
        process.terminate()
    final = adb("logcat", "-d", "-s", "CarCueVehicle:I")
    (out / "pleos-sdk-events.txt").write_text(final)
    (out / "pleos-console-events.json").write_text(json.dumps(events, indent=2) + "\n")
    (out / "crash.txt").write_text(adb("logcat", "-d", "-b", "crash"))
    (out / "process-events.txt").write_text(adb("logcat", "-d", "-b", "events", "-s", "am_crash", "am_kill", "am_proc_died"))
    console("/vehicle/body?door_fl=0", "PUT")
    console(heartbeat + "&closing=1", "POST")

result = (out / "pleos-instrumentation.txt").read_text()
required = ["CAPABILITY_RECEIVED", "GET_RECEIVED:RANGE_VERIFIED:value=0", "CALLBACK_RECEIVED:RANGE_VERIFIED:value=1",
            "RESTORED_CAPTURED:exact_pixels_restored=true", "LISTENER_UNREGISTER_RETURNED", "RELEASE_RETURNED"]
assert "OK (1 test)" in result and all(event in final for event in required), "SDK validation failed; inspect the dedicated output directory"
cursor = 0
for event in ["GET_RECEIVED:RANGE_VERIFIED:value=0", "SDK_TEST:INITIAL_CAPTURED",
              "CALLBACK_RECEIVED:RANGE_VERIFIED:value=1", "SDK_TEST:OPEN_CAPTURED",
              "CALLBACK_RECEIVED:RANGE_VERIFIED:value=0", "SDK_TEST:RESTORED_CAPTURED",
              "LISTENER_UNREGISTER_RETURNED", "RELEASE_RETURNED"]:
    found = final.find(event, cursor)
    assert found >= 0, "Missing or out-of-order SDK evidence: " + event
    cursor = found + len(event)
names = ["pleos-initial-get.png", "pleos-changed-callback.png", "pleos-restored-callback.png", "pleos-session-ended.png",
         "sdk-car-initial-closed.png", "sdk-car-open.png", "sdk-car-restored-closed.png", "sdk-visual-result.json"]
for name in names:
    with (out / name).open("wb") as f:
        subprocess.run(base + ["exec-out", "run-as", PACKAGE, "--user", user, "cat", "files/qa/" + name],
                       stdout=f, stderr=subprocess.PIPE, check=True, timeout=15)
visual = json.loads((out / "sdk-visual-result.json").read_text())
for key, name in [("initial_closed_sha256", "sdk-car-initial-closed.png"),
                  ("open_sha256", "sdk-car-open.png"), ("restored_closed_sha256", "sdk-car-restored-closed.png")]:
    assert visual[key] == sha(out / name)
assert visual["source"] == "PLEOS" and visual["initial_closed_sha256"] == visual["restored_closed_sha256"] != visual["open_sha256"]
if args.record:
    adb("pull", video_remote, str(out / "carcue-pleos-sdk-visual-check.mp4"), timeout=30)
evidence_names = names + ["command.json", "pleos-instrumentation.txt", "pleos-sdk-events.txt",
                          "pleos-console-events.json", "crash.txt", "process-events.txt"]
if args.record:
    evidence_names += ["carcue-pleos-sdk-visual-check.mp4", "screenrecord.txt"]
metadata = {
    "type": "REAL_PLEOS_SDK_EMULATOR_VISUAL_VALIDATION", "validated_at": datetime.now(timezone.utc).isoformat(),
    "serial": args.serial, "avd": avd, "android_user": int(user), "sdk_version": "2.3.2", "vehicle_service": service_version,
    "apk": str(apk), "apk_sha256": sha(apk), "installed_apk_sha256": installed_sha,
    "visual_result": visual, "virtual_console_events": events,
    "physical_vehicle_tested": False, "app_sdk_set_called": False, "seatbelt_status_connected": False, "external_ai_called": False,
    "files_sha256": {name: sha(out / name) for name in evidence_names},
}
(out / "result.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
print("PASS: real SDK capability, GET, OPEN/CLOSED callbacks; car pixels changed/restored; unregister/release; installed APK hash verified")
