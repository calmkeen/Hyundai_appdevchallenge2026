"""Official Virtual Console simulation against an isolated emulator, never a physical vehicle.

Requires installed Pleos/test APKs. The app itself only reads; writes are simulator fixtures.
"""
import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

p = argparse.ArgumentParser()
p.add_argument("--adb", default=".tooling/android-sdk/platform-tools/adb")
p.add_argument("--serial", default="emulator-5584")
args = p.parse_args()
if not args.serial.startswith("emulator-"):
    raise SystemExit("Refusing a physical vehicle/device")
adb = [args.adb, "-s", args.serial]
if subprocess.check_output(adb + ["shell", "getprop", "ro.kernel.qemu"], text=True).strip() != "1":
    raise SystemExit("Not an Android emulator")
out = Path("output/qa")
out.mkdir(parents=True, exist_ok=True)
subprocess.run(adb + ["forward", "tcp:8088", "tcp:8088"], check=True)


def console(path, method="GET"):
    with urlopen(Request("http://127.0.0.1:8088" + path, method=method), timeout=8) as r:
        return json.load(r)


heartbeat = "/browser/session?client=carcue-sdk-validation"
console(heartbeat, "POST")
console("/vehicle/body?door_fl=0", "PUT")
subprocess.run(adb + ["logcat", "-c"], check=True)
changed = False
events = []
with (out / "pleos-instrumentation.txt").open("w") as log:
    process = subprocess.Popen(adb + ["shell", "am", "instrument", "-w", "-r", "-e", "class",
        "com.carcue.app.PleosSdkTest", "com.carcue.app.test/androidx.test.runner.AndroidJUnitRunner"], stdout=log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 180
        while process.poll() is None and time.monotonic() < deadline:
            console(heartbeat, "POST")
            text = subprocess.check_output(adb + ["logcat", "-d", "-s", "CarCueVehicle:I"], text=True)
            if "SDK_TEST:INITIAL_CAPTURED" in text and not changed:
                state = console("/vehicle/body?door_fl=1", "PUT")
                events.append({"at": datetime.now(timezone.utc).isoformat(), "request": "Virtual Console PUT door_fl=1", "front_left": state["body"]["doors"]["front_left"]})
                changed = True
            time.sleep(1)
        if process.poll() is None:
            process.terminate()
            raise RuntimeError("SDK test timed out")
    finally:
        final = subprocess.check_output(adb + ["logcat", "-d", "-s", "CarCueVehicle:I"], text=True)
        (out / "pleos-sdk-events.txt").write_text(final)
        (out / "pleos-console-events.json").write_text(json.dumps(events, indent=2))
        console("/vehicle/body?door_fl=0", "PUT")
        console(heartbeat + "&closing=1", "POST")
result = (out / "pleos-instrumentation.txt").read_text()
required = ["CAPABILITY_RECEIVED", "GET_RECEIVED:RANGE_VERIFIED", "CALLBACK_RECEIVED:RANGE_VERIFIED", "LISTENER_UNREGISTER_RETURNED", "RELEASE_RETURNED"]
if "OK (1 test)" not in result or not all(event in final for event in required):
    raise SystemExit("SDK validation failed; see output/qa logs")
print("PASS: real SDK capability, GET, changed callback, UI screenshot, unregister, release")
