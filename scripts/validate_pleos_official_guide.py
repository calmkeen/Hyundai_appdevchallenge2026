"""Validate real Pleos AVD door callbacks -> published official manual guide.

Only this host driver changes the isolated Virtual Console fixtures. The app uses
SDK capability/GET/listeners and never calls SET. PLEOS here means SDK data from
the official AVD, not a physical vehicle or SDK identification of the car model.
Each invocation uses a new host/device evidence directory; no pm clear, logcat
clear, stash, existing QA deletion, or existing recording overwrite is performed.
"""
import argparse
import base64
import hashlib
import json
import re
import secrets
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from pleos_console import PleosConsoleSession

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "com.carcue.app"
PROFILE_ID = "ioniq5-ne1-2024-kr"
MANUAL_SET_ID = "hyundai-ioniq5-ne1-2024-kr"
GUIDE_ID = "ioniq5-door-open-check"
SOURCE_VERSION = "NE1-2024-KR-ko_KR-D202406100040-20240722"
SOURCE_URLS = {
    "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/idff13cd5359c.html",
    "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id0d6d99a8d21.html",
}
SCREENSHOTS = [
    "initial-get-closed.png", "callback-open.png", "official-guide-sources.png",
    "official-guide-manual-version.png", "official-guide-source-1.png", "official-guide-source-2.png",
    "official-guide-open.png", "guide-callback-closed.png", "guide-refresh-get-closed.png",
    "driving-guide-blocked.png", "parked-return.png", "session-ended.png",
    "car-initial-closed.png", "car-callback-open.png", "car-restored-closed.png",
]
PHASES = [
    "INITIAL_GET_CLOSED", "OFFICIAL_GUIDE_OPEN", "CALLBACK_CLOSED",
    "EXPLICIT_REFRESH_GET_CLOSED", "DRIVING_GUIDE_BLOCKED",
    "RESTRICTED_NAVIGATION_REJECTED", "PARKED_RETURN", "SESSION_ENDED",
]
# Store a small allowlist rather than raw logcat / raw vehicle service payloads.
SDK_EVENT = re.compile(
    r"(PLEOS:(?:INITIALIZE_RETURNED_NOT_DATA|"
    r"CAPABILITY_RECEIVED:ROW_1_LEFT:min=0:max=1:access=[A-Z_]+|"
    r"(?:GET|CALLBACK)_RECEIVED:RANGE_VERIFIED:value=[01]:area=ROW_1_LEFT|"
    r"LISTENER_REGISTERED_NOT_CALLBACK|LISTENER_UNREGISTER_RETURNED|RELEASE_RETURNED)|"
    r"UX:(?:GET|CALLBACK):requires=(?:true|false):flags=[0-9]+)\s*$"
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default=".tooling/android-sdk/platform-tools/adb")
    parser.add_argument("--serial", default="emulator-5584")
    parser.add_argument("--avd", default="CarCue_Pleos21")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8001")
    parser.add_argument("--apk", default="android/app/build/outputs/apk/pleos/debug/app-pleos-debug.apk")
    parser.add_argument("--test-apk", default="android/app/build/outputs/apk/androidTest/pleos/debug/app-pleos-debug-androidTest.apk")
    parser.add_argument("--install", action="store_true", help="Replace both APKs with -r; preserve app data")
    parser.add_argument("--install-timeout", type=int, default=180, help="Host APK-install deadline; SDK/UI assertions keep their own deadlines")
    parser.add_argument("--console-ready-timeout", type=int, default=60, help="Bounded wait for the Console door/speed/gear DDS bridge before fixture writes")
    parser.add_argument("--source-version", default=SOURCE_VERSION)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("official-guide-%Y%m%dT%H%M%SZ-") + secrets.token_hex(3))
    parser.add_argument("--output-dir", default="output/qa/pleos-official-guide", help="Parent directory; run ID is appended")
    parser.add_argument("--record", action="store_true", help="Optional unedited AVD screen recording, unique filename")
    parser.add_argument("--normal-launch-evidence", help="Previously verified normal-launch-smoke.json from this installed app build")
    args = parser.parse_args()
    require(90 <= args.install_timeout <= 600, "Install timeout must be between 90 and 600 seconds")
    require(5 <= args.console_ready_timeout <= 180, "Console readiness timeout must be between 5 and 180 seconds")
    require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id)), "Invalid run ID")
    require(bool(re.fullmatch(r"[A-Za-z0-9_-]{1,100}", args.source_version)), "Invalid source version")
    require(args.serial.startswith("emulator-"), "Refusing a physical device")
    backend = args.backend_url.rstrip("/")
    parsed_backend = urlparse(backend)
    require(parsed_backend.scheme == "http" and parsed_backend.hostname in {"127.0.0.1", "localhost"}
            and parsed_backend.port == 8001 and parsed_backend.path == "", "Use the dedicated loopback LIVE backend on port 8001")
    out = (ROOT / args.output_dir / args.run_id).resolve()
    out.mkdir(parents=True, exist_ok=False)
    adb_path = (ROOT / args.adb).resolve()
    base = [str(adb_path), "-s", args.serial]
    apk, test_apk = (ROOT / args.apk).resolve(), (ROOT / args.test_apk).resolve()
    markers = "files/qa/" + args.run_id
    remote_video = "/sdcard/carcue-" + args.run_id + ".mp4"

    def adb(*parts, timeout=15, check=True):
        return subprocess.run(base + list(parts), text=True, capture_output=True, timeout=timeout, check=check).stdout.strip()

    def request(url, method="GET"):
        with urlopen(Request(url, method=method, headers={"Accept": "application/json"}), timeout=10) as response:
            return json.load(response)

    def console(path, method="GET"):
        return lease.request(path, method)

    def app(*parts, check=True):
        return adb("shell", "run-as", PACKAGE, "--user", user, *parts, check=check)

    def marker_files():
        return set(app("ls", "-1", markers, check=False).splitlines())

    def collect(name):
        with (out / name).open("xb") as target:
            subprocess.run(base + ["exec-out", "run-as", PACKAGE, "--user", user, "cat", markers + "/" + name],
                           stdout=target, stderr=subprocess.PIPE, check=True, timeout=20)

    require(adb("shell", "getprop", "ro.kernel.qemu") == "1", "Refusing a physical vehicle/device")
    avd = adb("shell", "getprop", "ro.boot.qemu.avd_name")
    require(avd == args.avd and avd in {"CarCue_Pleos21", "CarCue_Pleos21_LocalAI"}, "Use only the dedicated CarCue Pleos AVD")
    android_api = adb("shell", "getprop", "ro.build.version.sdk")
    require(android_api == "34", "Expected the official API34 Pleos AVD")
    require(adb("shell", "getprop", "sys.boot_completed") == "1", "AVD not booted")
    user = adb("shell", "am", "get-current-user")
    require(user.isdigit() and user != "0", "Wait for the foreground automotive user")
    require(adb("shell", "service", "check", "car_service") == "Service car_service: found",
            "Car UX service is not registered; restore the isolated AVD before testing")
    require(not adb("shell", "pidof", "screenrecord", check=False), "An existing recorder is active")
    require(apk.is_file() and test_apk.is_file(), "Build the current Pleos APKs first")
    normal_launch = None
    if args.normal_launch_evidence:
        smoke_path = Path(args.normal_launch_evidence).resolve()
        smoke = json.loads(smoke_path.read_text())
        installed = json.loads(smoke_path.with_name("installed-app.json").read_text())
        require(smoke.get("physical_app_visible") is True and installed["installed_app_sha256"] == sha(apk),
                "Normal launch physical smoke must match the current app APK")
        normal_launch = {"evidence": str(smoke_path), "evidence_sha256": sha(smoke_path),
                         "physical_app_visible": True, "app_sha256": installed["installed_app_sha256"],
                         "capture_method": smoke["capture_method"]}
    health = request(backend + "/health")
    require(health == {"status": "ok", "mode": "LIVE"}, "Dedicated backend must be LIVE")
    profile = request(backend + "/v1/vehicle-profiles/" + PROFILE_ID)
    require(profile["verification_status"] == "VERIFIED" and profile["manual_set_id"] == MANUAL_SET_ID
            and profile["manual_version"] == args.source_version, "Official profile/manual identity mismatch")
    guides = request(backend + "/v1/guides?" + urlencode({"profile_id": PROFILE_ID, "locale": "ko-KR"}))
    candidates = [guide for guide in guides if guide["guide_id"] == GUIDE_ID]
    require(len(candidates) == 1, "LIVE backend must return one official door guide")
    guide = candidates[0]
    require(guide["lifecycle"] == "PUBLISHED" and PROFILE_ID in guide["profile_ids"]
            and guide["manual_set_id"] == MANUAL_SET_ID and guide["source_version"] == args.source_version
            and {source["url"] for source in guide["sources"]} == SOURCE_URLS
            and all(source["verification_status"] == "VERIFIED" for source in guide["sources"]),
            "LIVE guide metadata/source mismatch")
    print("PRECHECK PASS: isolated API34 AVD/user; LIVE official profile, guide, manual version and both sources", flush=True)
    if args.install:
        for path in (apk, test_apk):
            print("INSTALL: " + path.name + " (preserving app data)", flush=True)
            try:
                require("Success" in adb("install", "--no-streaming", "--user", user, "-r", str(path), timeout=args.install_timeout), "APK replacement failed")
            except Exception as exc:
                (out / "preflight-failure.json").write_text(json.dumps({
                    "run_id": args.run_id, "phase": "APK_INSTALL", "error_type": type(exc).__name__,
                    "apk_name": path.name, "apk_sha256": sha(path), "install_timeout_seconds": args.install_timeout,
                    "instrumentation_started": False, "physical_vehicle_tested": False,
                }, indent=2) + "\n")
                raise
            print("INSTALL PASS: " + path.name, flush=True)
    installed_hashes = {}
    with tempfile.TemporaryDirectory(dir=out, prefix="installed-hash-") as temp:
        for package, expected in ((PACKAGE, apk), (PACKAGE + ".test", test_apk)):
            paths = adb("shell", "pm", "path", "--user", user, package).splitlines()
            require(len(paths) == 1 and paths[0].startswith("package:"), "Expected one installed base APK")
            local = Path(temp) / (package + ".apk")
            adb("pull", paths[0].removeprefix("package:"), str(local), timeout=60)
            require(sha(local) == sha(expected), "Installed APK differs from the current build: " + package)
            installed_hashes[package] = sha(local)
    print("INSTALLED HASH PASS: app and instrumentation match the current build", flush=True)
    require(not app("ls", "-d", markers, check=False), "App evidence directory already exists; choose a new run ID")
    require(not adb("shell", "ls", remote_video, check=False), "Remote recording path already exists; choose a new run ID")
    service = adb("shell", "dumpsys", "package", "ai.pleos.playground.service.vehicle")
    service_version = [line.strip() for line in service.splitlines()
                       if "versionName=" in line or "versionCode=" in line][:2]
    device_timezone = adb("shell", "getprop", "persist.sys.timezone")
    # Directory creation is exclusive in the instrumentation as well; never remove previous evidence.
    adb("forward", "tcp:8088", "tcp:8088")
    lease = PleosConsoleSession(base_url="http://127.0.0.1:8088", client="carcue-" + args.run_id)
    fixtures, handled = [], set()
    process = recorder = record_log = None
    recorder_pid = None
    recording_started = False
    recording_error = None
    video_file = None
    success = False
    sdk_events = []
    error = None
    cleanup_errors = []
    cleanup_attempts = []
    restored_fixture = None
    command = base + ["shell", "am", "instrument", "--user", user, "-w", "-r",
                      "-e", "validateOfficialGuide", "true", "-e", "runId", args.run_id,
                      "-e", "expectedSourceVersion", args.source_version,
                      "-e", "expectedSourceUrlsBase64", base64.urlsafe_b64encode(json.dumps(sorted(SOURCE_URLS)).encode()).decode(),
                      "-e", "class", "com.carcue.app.PleosOfficialGuideTest",
                      PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner"]
    (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")

    def fixture(phase, path):
        console(path, "PUT")
        # Only controlled request fields are stored, never the console's full vehicle response.
        fixtures.append({"at": datetime.now(timezone.utc).isoformat(), "phase": phase, "request": path})

    def stop_recording():
        nonlocal recorder
        if recorder is not None:
            if recorder_pid and remote_video in adb("shell", "cat", "/proc/" + recorder_pid + "/cmdline", check=False):
                adb("shell", "kill", "-2", recorder_pid)
            try:
                recorder.wait(timeout=20)
            except subprocess.TimeoutExpired:
                recorder.terminate(); recorder.wait(timeout=8)
            record_log.close()
            recorder = None

    def cleanup_step(phase, action, default=None):
        try:
            return action()
        except Exception as exc:
            cleanup_errors.append({"phase": phase, "error_type": type(exc).__name__})
            return default

    with lease:
        try:
            lease.wait_ready(timeout=args.console_ready_timeout)
            (out / "console-readiness.json").write_text(json.dumps(lease.diagnostics(), indent=2) + "\n")
            print("CONSOLE READY: independent heartbeat; door/speed/pedals DDS and gear bridge verified", flush=True)
            fixture("INITIAL_PARK", "/vehicle/controls?speed=0&accelerator=0&brake=0")
            fixture("INITIAL_PARK", "/vehicle/gear?gear=Park")
            fixture("INITIAL_CLOSED", "/vehicle/body?door_fl=0")
            if args.record:
                record_log = (out / "screenrecord.txt").open("x")
                recorder = subprocess.Popen(base + ["shell", "screenrecord", "--bit-rate", "6000000", "--time-limit", "180", remote_video],
                                            stdout=record_log, stderr=subprocess.STDOUT)
                until = time.monotonic() + 5
                while time.monotonic() < until:
                    pid = adb("shell", "pidof", "screenrecord", check=False)
                    if pid.isdigit() and remote_video in adb("shell", "cat", "/proc/" + pid + "/cmdline", check=False):
                        recorder_pid = pid
                        break
                    if recorder.poll() is not None:
                        break
                    time.sleep(.1)
                if recorder_pid is not None:
                    recording_started = True
                elif recorder.poll() is not None:
                    recording_error = {"phase": "STARTUP", "exit_code": recorder.returncode}
                    record_log.close()
                    recorder = None
                    print("OPTIONAL RECORDING FAILED: recorder exited before startup; SDK/UI assertions will still run", flush=True)
                else:
                    require(False, "Could not identify this run's recorder")
            with (out / "instrumentation.txt").open("x") as log:
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                print("INSTRUMENTATION STARTED: " + args.run_id, flush=True)
                deadline = time.monotonic() + 240
                while time.monotonic() < deadline:
                    present = marker_files()
                    for marker, paths in [
                        ("request-open", ["/vehicle/body?door_fl=1"]),
                        ("request-close", ["/vehicle/body?door_fl=0"]),
                        ("request-drive", ["/vehicle/gear?gear=Drive", "/vehicle/controls?speed=20&accelerator=0&brake=0"]),
                        ("request-park", ["/vehicle/controls?speed=0&accelerator=0&brake=0", "/vehicle/gear?gear=Park"]),
                    ]:
                        if marker in present and marker not in handled:
                            for path in paths:
                                fixture(marker, path)
                            handled.add(marker)
                            print("EXTERNAL CONSOLE FIXTURE: " + marker, flush=True)
                    if "done" in present:
                        success = True
                        app("touch", markers + "/host-finished")
                        break
                    require(process.poll() is None, "Instrumentation exited before done")
                    time.sleep(.25)
                require(success, "SDK official-guide validation timed out")
                process.wait(timeout=30)
        except Exception as exc:
            # Do not serialize arbitrary response contents or user/device data into the report.
            error = type(exc).__name__
            raise
        finally:
            # An ADB/recording timeout must not skip external Park/0/CLOSED restoration.
            # Retain such failures and reject an overall pass after restoration.
            cleanup_step("STOP_RECORDING", stop_recording)
            if process is not None and process.poll() is None:
                cleanup_step("RELEASE_INSTRUMENTATION_WAIT", lambda: app("touch", markers + "/host-finished", check=False))
                process.terminate()
                cleanup_step("WAIT_HOST_PROCESS", lambda: process.wait(timeout=10))
            logs = cleanup_step("READ_SCOPED_LOGS", lambda: adb("logcat", "-d", "-v", "brief", "-s", "CarCueVehicle:I", "CarCueOfficialGuide:I", "*:S"), "")
            begin = logs.find("OFFICIAL_GUIDE:" + args.run_id + ":BEGIN")
            scoped = logs[begin:] if begin >= 0 else ""
            end = scoped.find("OFFICIAL_GUIDE:" + args.run_id + ":DONE")
            if end >= 0:
                scoped = scoped[:end]
            sdk_events = [match.group(1) for line in scoped.splitlines() if (match := SDK_EVENT.search(line))]
            (out / "sdk-events.txt").write_text("\n".join(sdk_events) + "\n")
            # The independent heartbeat remains alive through slow ADB calls and teardown.
            # Require the actual domain bridge again before restoring external fixtures.
            for attempt in range(1, 4):
                try:
                    lease.wait_ready(timeout=10)
                    fixture("RESTORE_PARK", "/vehicle/controls?speed=0&accelerator=0&brake=0")
                    fixture("RESTORE_PARK", "/vehicle/gear?gear=Park")
                    fixture("RESTORE_CLOSED", "/vehicle/body?door_fl=0")
                    body = console("/vehicle/body")
                    controls = console("/vehicle/controls")
                    gear = console("/vehicle/gear")
                    restored_fixture = {"front_left": body.get("body", body)["doors"]["front_left"],
                                        "speed_kph": controls["speed_kph"], "gear": gear["actual"]["value"]}
                    require(restored_fixture == {"front_left": False, "speed_kph": 0, "gear": "Park"},
                            "Final external fixture values differ from Park/0/CLOSED")
                    cleanup_attempts.append({"attempt": attempt, "restored": True})
                    print("RESTORE PASS: external console confirms Park / speed 0 / front-left closed", flush=True)
                    break
                except Exception as exc:
                    cleanup_attempts.append({"attempt": attempt, "restored": False, "error_type": type(exc).__name__,
                                             "http_status": getattr(exc, "code", None)})
                    time.sleep(.5)
            (out / "console-session.json").write_text(json.dumps(lease.diagnostics(), indent=2) + "\n")
            (out / "console-events.json").write_text(json.dumps(fixtures, indent=2) + "\n")
            (out / "run-status.json").write_text(json.dumps({"run_id": args.run_id, "instrumentation_done": success,
                                                            "error_type": error, "cleanup_attempts": cleanup_attempts,
                                                            "cleanup_errors": cleanup_errors,
                                                            "restored_fixture": restored_fixture,
                                                            "physical_vehicle_tested": False}, indent=2) + "\n")

    (out / "console-session-final.json").write_text(json.dumps(lease.diagnostics(), indent=2) + "\n")
    require(not cleanup_errors, "Host teardown/log capture failed; fixture restoration was still attempted")
    require(restored_fixture == {"front_left": False, "speed_kph": 0, "gear": "Park"}, "Host fixture restoration failed; inspect run-status.json")
    require("OK (1 test)" in (out / "instrumentation.txt").read_text(), "Instrumentation assertions failed")
    expected_events = [
        "PLEOS:CAPABILITY_RECEIVED:ROW_1_LEFT:min=0:max=1:access=",
        "PLEOS:GET_RECEIVED:RANGE_VERIFIED:value=0:area=ROW_1_LEFT",
        "PLEOS:CALLBACK_RECEIVED:RANGE_VERIFIED:value=1:area=ROW_1_LEFT",
        "PLEOS:CALLBACK_RECEIVED:RANGE_VERIFIED:value=0:area=ROW_1_LEFT",
        "PLEOS:GET_RECEIVED:RANGE_VERIFIED:value=0:area=ROW_1_LEFT",
        "UX:CALLBACK:requires=true:", "UX:CALLBACK:requires=false:",
        "PLEOS:LISTENER_UNREGISTER_RETURNED", "PLEOS:RELEASE_RETURNED",
    ]
    cursor = 0
    for event in expected_events:
        while cursor < len(sdk_events) and not sdk_events[cursor].startswith(event):
            cursor += 1
        require(cursor < len(sdk_events), "Missing/out-of-order allowlisted SDK event: " + event)
        cursor += 1
    for name in SCREENSHOTS + ["result.json", "events.jsonl"]:
        collect(name)
    visual = json.loads((out / "result.json").read_text())
    phases = [json.loads(line) for line in (out / "events.jsonl").read_text().splitlines()]
    require([item["phase"] for item in phases] == PHASES, "Missing UI/runtime phases")
    require(all(item["source"] == "PLEOS" for item in phases), "A phase did not use Source.PLEOS")
    require(visual["profile_id"] == PROFILE_ID and visual["guide_id"] == GUIDE_ID
            and visual["manual_set_id"] == MANUAL_SET_ID and visual["source_version"] == args.source_version
            and set(visual["source_urls"]) == SOURCE_URLS, "Runtime official guide identity mismatch")
    for key, name in [("initial_closed_sha256", "car-initial-closed.png"),
                      ("callback_open_sha256", "car-callback-open.png"),
                      ("restored_closed_sha256", "car-restored-closed.png")]:
        require(visual[key] == sha(out / name), "Screenshot digest mismatch")
    require(visual["initial_closed_sha256"] == visual["restored_closed_sha256"] != visual["callback_open_sha256"],
            "Door visualization was not changed/restored")
    require(handled == {"request-open", "request-close", "request-drive", "request-park"}, "Missing external fixture phase")
    if args.record and recording_started:
        try:
            adb("pull", remote_video, str(out / "screenrecord.mp4"), timeout=60)
            require((out / "screenrecord.mp4").stat().st_size > 0, "Empty optional recording")
            video_file = "screenrecord.mp4"
        except Exception as exc:
            recording_error = {"phase": "COLLECT", "error_type": type(exc).__name__}
            print("OPTIONAL RECORDING FAILED: collection did not produce a usable file", flush=True)
    artifacts = [path for path in out.iterdir() if path.is_file()]
    metadata = {
        "type": "REAL_PLEOS_AVD_OFFICIAL_GUIDE_VALIDATION", "validated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id, "serial": args.serial, "avd": avd, "android_api": int(android_api), "android_user": int(user),
        "backend_mode": health["mode"], "app_server_url": "http://10.0.2.2:8001", "declared_sdk_version": "2.3.2",
        "vehicle_service": service_version,
        "device_timezone": device_timezone, "normal_launch_smoke": normal_launch,
        "apk_sha256": sha(apk), "test_apk_sha256": sha(test_apk), "installed_apk_sha256": installed_hashes,
        "profile_id": PROFILE_ID, "manual_set_id": MANUAL_SET_ID, "source_version": args.source_version,
        "guide_id": GUIDE_ID, "source_urls": sorted(SOURCE_URLS), "visual_result": visual,
        "phases": phases, "virtual_console_events": fixtures, "restored_fixture": restored_fixture,
        "cleanup_attempts": cleanup_attempts,
        "physical_vehicle_tested": False, "profile_selected_by_user": True, "sdk_identified_vehicle_model": False,
        "app_sdk_set_called": False, "external_ai_called": False, "seatbelt_status_connected": False,
        "screen_recording": {"requested": args.record, "started": recording_started, "file": video_file,
                             "capture_error": recording_error,
                             "app_screen_visibility_verified": False,
                             "review_required": "Optional physical-display recording needs separate visual QA; instrumentation screenshots/assertions prove app behavior"},
        "vehicle_log_policy": "allowlisted door.position ROW_1_LEFT/UX/lifecycle events only; no VIN or raw vehicle payloads",
        "files_sha256": {path.name: sha(path) for path in artifacts},
    }
    (out / "validation-result.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print("PASS: real Pleos AVD capability/GET/callbacks -> official guide and sources; refresh; driving block; park; release")
    print(out)


if __name__ == "__main__":
    main()
