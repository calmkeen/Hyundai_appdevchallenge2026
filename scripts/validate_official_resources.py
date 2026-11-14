"""Exercise registered HTTPS actions in the preserved official Pleos AVD.

No Console fixture writes, browser installation, pm clear, logcat clear or paid
provider calls. Native assertions distinguish handler dispatch from page loading.
"""
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from pleos_console import PleosConsoleSession

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "com.carcue.app"
BROWSER = "org.chromium.webview_shell/.WebViewBrowserActivity"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--serial", default="emulator-5584")
    parser.add_argument("--install", action="store_true", help="Replace APKs using -r; preserve app data")
    parser.add_argument("--apk", default="android/app/build/outputs/apk/pleos/debug/app-pleos-debug.apk")
    parser.add_argument("--test-apk", default="android/app/build/outputs/apk/androidTest/pleos/debug/app-pleos-debug-androidTest.apk")
    args = parser.parse_args()
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id), "Invalid run ID")
    require(args.serial.startswith("emulator-"), "Refusing physical devices")
    out = ROOT / "output/qa/official-links-20261114" / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    base = [str(ROOT / ".tooling/android-sdk/platform-tools/adb"), "-s", args.serial]
    user = "10"

    def adb(*parts, timeout=20, check=True):
        result = subprocess.run(base + list(parts), capture_output=True, text=True, timeout=timeout)
        if check:
            require(result.returncode == 0, "ADB command failed: " + result.stderr.strip())
        return result.stdout.strip()

    actual = {
        "qemu": adb("shell", "getprop", "ro.kernel.qemu"),
        "avd": adb("shell", "getprop", "ro.boot.qemu.avd_name"),
        "api": adb("shell", "getprop", "ro.build.version.sdk"),
        "boot": adb("shell", "getprop", "sys.boot_completed"),
        "user": adb("shell", "am", "get-current-user"),
        "car_service": adb("shell", "service", "check", "car_service"),
        "https_handler": adb("shell", "cmd", "package", "resolve-activity", "--brief", "--user", user,
                             "-a", "android.intent.action.VIEW", "-c", "android.intent.category.BROWSABLE",
                             "-d", "https://ownersmanual.hyundai.com/"),
    }
    (out / "device-preflight.json").write_text(json.dumps(actual, indent=2) + "\n")
    require(actual["qemu"] == "1" and actual["avd"] == "CarCue_Pleos21_LocalAI" and actual["api"] == "34"
            and actual["boot"] == "1" and actual["user"] == user and actual["car_service"] == "Service car_service: found",
            "Use only the booted, preserved official Pleos API34 AVD/user10")
    require(actual["https_handler"].splitlines()[-1] == BROWSER, "Expected the existing stock HTTPS handler")
    with urlopen("http://127.0.0.1:8001/health", timeout=10) as response:
        require(json.load(response) == {"status": "ok", "mode": "LIVE"}, "Dedicated LIVE backend required")
    apk, test_apk = ROOT / args.apk, ROOT / args.test_apk
    with zipfile.ZipFile(test_apk) as archive:
        require(any(b"PleosOfficialResourcesTest" in archive.read(name) for name in archive.namelist() if name.endswith(".dex")),
                "Rebuild the current instrumentation APK")
    if args.install:
        for path in (apk, test_apk):
            print("INSTALL -r " + path.name, flush=True)
            result = adb("install", "--user", user, "-r", str(path), timeout=240)
            (out / (path.name + ".install.txt")).write_text(result + "\n")
            require("Success" in result, "APK install did not report success")
    installed_path = adb("shell", "pm", "path", "--user", user, PACKAGE).splitlines()
    require(len(installed_path) == 1 and installed_path[0].startswith("package:/data/app/"), "Expected one base APK")
    installed = out / "installed-base.apk"
    adb("pull", installed_path[0].removeprefix("package:"), str(installed), timeout=60)
    require(sha(installed) == sha(apk), "Installed app differs from the tested APK")
    (out / "installed-app.json").write_text(json.dumps({"app_sha256": sha(apk), "test_apk_sha256": sha(test_apk),
        "installed_app_sha256": sha(installed), "preserved_user_data": True, "browser_installed_by_test": False}, indent=2) + "\n")
    markers = "files/qa/" + args.run_id
    # Wake this isolated emulator without changing lock, timeout or security settings.
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    dismiss = adb("shell", "wm", "dismiss-keyguard")
    launch = adb("shell", "am", "start", "-W", "--user", user, "-n", PACKAGE + "/.MainActivity", timeout=40)
    activity_state = adb("shell", "dumpsys", "activity", "activities")
    power = adb("shell", "dumpsys", "power")
    window = adb("shell", "dumpsys", "window", "policy")
    screen = {"dismiss_result": dismiss, "normal_launch": launch,
        "resumed": [line.strip() for line in activity_state.splitlines() if "ResumedActivity" in line],
        "power": [line.strip() for line in power.splitlines() if "mWakefulness=" in line],
        "keyguard": [line.strip() for line in window.splitlines() if "showing=" in line.lower() or "keyguardshowing=" in line.lower()],
        "security_settings_changed": False}
    (out / "screen-preflight.json").write_text(json.dumps(screen, indent=2) + "\n")
    require("mWakefulness=Awake" in power, "Emulator display must be awake for UI testing")
    require(any(line.strip() == "showing=false" for line in window.splitlines()), "AVD keyguard/System UI is not ready; do not relax app UX checks")
    require(any(PACKAGE + "/" in line for line in screen["resumed"]), "Normal CarCue launch must be resumed before instrumentation")
    started = datetime.now(timezone.utc)
    command = base + ["shell", "am", "instrument", "--user", user, "-w", "-e", "class",
        "com.carcue.app.PleosOfficialResourcesTest#registeredManualAndSupportDispatchReturnWithActualSdk",
        "-e", "validateOfficialResources", "true", "-e", "runId", args.run_id,
        "-e", "expectedExternalResult", "INTENT_DISPATCHED", "-e", "expectedLocalModel", "qwen3:4b",
        "com.carcue.app.test/androidx.test.runner.AndroidJUnitRunner"]
    print("RUN actual stock handler/SDK/local model", flush=True)
    adb("forward", "tcp:8088", "tcp:8088")
    lease = PleosConsoleSession(client="carcue-" + args.run_id, heartbeat_timeout=2.0, heartbeat_max_age=6.0)
    try:
        with lease:
            lease.wait_ready(timeout=90)
            run = None
            try:
                run = subprocess.run(command, capture_output=True, text=True, timeout=600)
                (out / "instrumentation.txt").write_text(run.stdout + run.stderr)
                print(run.stdout[-4000:], flush=True)
            finally:
                names = adb("shell", "run-as", PACKAGE, "--user", user, "ls", "-1", markers, check=False).splitlines()
                for name in names:
                    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
                        continue
                    with (out / name).open("xb") as target:
                        subprocess.run(base + ["exec-out", "run-as", PACKAGE, "--user", user, "cat", markers + "/" + name],
                                       stdout=target, stderr=subprocess.PIPE, timeout=30, check=True)
            lease.wait_ready(timeout=30)
    finally:
        diagnostics = lease.diagnostics()
        diagnostics["close_completed"] = not diagnostics["heartbeat_running"] and diagnostics["close_error"] is None
        diagnostics["fixture_writes"] = False
        (out / "console-lease.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
    require(run is not None and run.returncode == 0 and "OK (1 test)" in run.stdout, "Native resource integration failed; evidence preserved")
    result = json.loads((out / "result.json").read_text())
    require(result.get("passed") is True and result.get("page_loaded_asserted") is False and (out / "done").is_file(), "Missing completed native proof")
    (out / "host-result.json").write_text(json.dumps({"passed": True, "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(), "device": actual, "app_sha256": sha(apk),
        "native_result": result, "physical_vehicle_tested": False, "stock_browser_install_or_change": False}, indent=2) + "\n")
    print("PASS: 8 stock Browser2 debug-route roundtrips, fresh SDK GET, preserved guide/step, local ask; page loading not asserted", flush=True)


if __name__ == "__main__":
    main()
