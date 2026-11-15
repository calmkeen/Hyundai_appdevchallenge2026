"""Actual Pleos SDK/local-model showcase or late-response boundaries.

No installation, data/log clearing, provider/HTTP mocks or app SDK SET. The host
alone changes isolated AVD fixtures. Every invocation uses new QA artifacts.
"""
import argparse
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from pleos_console import ConsoleHeartbeatError, PleosConsoleSession
from validate_local_ai import AuditCursor, digest, require
from validate_pleos_official_guide import SDK_EVENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.content import Catalog

PACKAGE = "com.carcue.app"
PROFILE = "ioniq5-ne1-2024-kr"
GUIDE = "ioniq5-door-open-check"
MODEL_DIGEST = "359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7"
SDK_FAILURE_EVENT = re.compile(
    r"(PLEOS:(?:PERMISSION_DENIED|INITIALIZE_FAILED|CAPABILITY_FAILED|AREA_UNSUPPORTED|"
    r"READ_TIMEOUT|GET_FAILED|CALLBACK_FAILED|LISTENER_REGISTRATION_FAILED|UNREGISTER_FAILED|RELEASE_FAILED))\s*$"
)
SCENES = ["profile", "language-ko", "door-closed", "door-open", "door-restored", "seatbelt",
          "official-guide-step2", "ask-ko", "translation-en", "language-en", "ask-en", "ask-ja",
          "drive-restricted", "end-session"]
LOCALES = ["ko-KR", "en", "ja-JP"]
PHASES = [p for i, source in enumerate(LOCALES) for p in ("ask-" + source, "stored-" + source + "-to-" + LOCALES[(i + 1) % 3])]


def sha(path):
    return digest(path.read_bytes())


def bundle(guide):
    return "\n".join([guide["body"], *[part for step in guide["steps"] for part in (step["body"], *step["official_cautions"])]] )


def sanitized(row):
    result = {key: value for key, value in row.items() if key not in {"request_id", "answer_request_id", "cancelled_request_id"}}
    for key in ("request_id", "answer_request_id", "cancelled_request_id"):
        if row.get(key): result[key + "_hash"] = digest(row[key].encode())
    return result


class AuditObservation:
    """Observe the real audit independently of potentially slow ADB calls.

    This never calls a provider or changes its completion. First-seen time is
    still an upper bound on completion, so the in-flight proof stays conservative.
    """
    def __init__(self, audit):
        self.audit = audit
        self.first_seen = {}
        self.error = None
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self.observe, daemon=True, name="real-audit-observer")

    def observe(self):
        while not self.stop.is_set():
            try:
                rows = self.audit.events()
                observed = time.monotonic()
                with self.lock:
                    for row in rows:
                        self.first_seen.setdefault(row.get("request_id_hash"), observed)
            except RuntimeError as exc:
                # A concurrent append may briefly expose an incomplete line.
                # The main validator still requires complete, sanitized final records.
                if str(exc) != "AUDIT_RECORD_INCOMPLETE":
                    self.error = str(exc)
                    return
            except Exception:
                self.error = "AUDIT_OBSERVER_READ_FAILED"
                return
            self.stop.wait(.02)

    def start(self):
        self.worker.start()
        return self

    def completed_at(self, hashed):
        require(self.error is None and self.worker.is_alive(), "AUDIT_OBSERVER_FAILED")
        with self.lock:
            return self.first_seen.get(hashed)

    def close(self):
        self.stop.set()
        self.worker.join(timeout=2)
        require(not self.worker.is_alive() and self.error is None, "AUDIT_OBSERVER_FAILED")


def validate_audit(events, hashes, model):
    require(len(events) == len(hashes) == 3 and {e.get("request_id_hash") for e in events} == hashes, "EXACT_THREE_ACTUAL_MODEL_CALLS_REQUIRED")
    require(len({e.get("response_digest") for e in events}) == 3, "DISTINCT_MODEL_RESPONSES_REQUIRED")
    for event in events:
        require(event.get("provider_kind") == "OLLAMA_LOCAL" and event.get("model") == model
                and event.get("operation") == "LocalPassageSelection" and event.get("outcome") == "STRUCTURED_VALIDATED"
                and event.get("error_code") is None and event.get("http_status") == 200
                and re.fullmatch(r"[a-f0-9]{64}", event.get("response_digest", ""))
                and isinstance(event.get("duration_ms"), int) and not isinstance(event["duration_ms"], bool) and event["duration_ms"] > 0
                and all(isinstance(event.get(key), int) and not isinstance(event[key], bool) and event[key] > 0
                        for key in ("prompt_tokens", "output_tokens")), "ACTUAL_LOCAL_AUDIT_INVALID")


def validate_showcase(records, scenes, events, guides, model):
    require([r.get("phase") for r in records] == PHASES, "EXACT_SIX_RESPONSE_PHASES_REQUIRED")
    hashes, ids = set(), set()
    for i, row in enumerate(records):
        translated, source = bool(i % 2), LOCALES[i // 2]
        target = LOCALES[(i // 2 + 1) % 3] if translated else source
        guide = guides[target]
        request = row.get("request_id", "")
        require(str(uuid.UUID(request)) == request and request not in ids, "DISTINCT_RUNTIME_UUID_REQUIRED")
        ids.add(request)
        require(row.get("source") == "PLEOS" and row.get("capability") == "SUPPORTED" and row.get("read_status") == "VALUE"
                and row.get("value") == "CLOSED" and row.get("ux_known") is True and row.get("ux_restricted") is False
                and row.get("ux_flags") == 0 and row.get("mode") == "LIVE" and row.get("error") is None
                and row.get("profile_id") == PROFILE and row.get("market") == "KR", "ACTUAL_SDK_AND_UX_REQUIRED")
        received = datetime.fromisoformat(row["received_at"].replace("Z", "+00:00"))
        recorded = datetime.fromisoformat(row["recorded_at"].replace("Z", "+00:00"))
        require(0 <= (recorded - received).total_seconds() * 1000 <= row["state_ttl_ms"] == 60000, "FRESH_SDK_READING_REQUIRED")
        require(row.get("locale") == target and row.get("source_locale") == source and row.get("target_locale") == target
                and row.get("text") == bundle(guide) and row.get("unit_suffix") == ":closing-bundle:v1"
                and row.get("all_cautions_ui_visible") is True, "COMPLETE_LOCALIZED_BUNDLE_REQUIRED")
        require(row.get("status") == ("TRANSLATED" if translated else "ANSWERED")
                and row.get("ai_provider") == ("STORED_GUIDE" if translated else "OLLAMA_LOCAL")
                and row.get("ai_model") == (None if translated else model), "AI_PROVENANCE_MISMATCH")
        if translated:
            require(row.get("review_status") == guide["translation_review_status"] and row.get("content_kind") == "ANSWER"
                    and row.get("answer_request_id") == records[i - 1]["request_id"], "STORED_ANSWER_REVIEW_OR_BINDING_INVALID")
        else:
            require(row.get("answer_request_id") == request, "ANSWER_REQUEST_BINDING_INVALID")
            hashes.add(digest(request.encode()))
        expected = [{"source_id": s["source_id"], "guide_id": GUIDE, "profile_id": PROFILE,
            "manual_set_id": guide["manual_set_id"], "source_version": guide["source_version"], "url": s["url"]} for s in guide["sources"]]
        require(row.get("citations") == expected, "CANONICAL_OFFICIAL_CITATIONS_REQUIRED")
    validate_audit(events, hashes, model)
    require([s.get("scene_id") for s in scenes] == SCENES, "EXACT_FOURTEEN_SCENES_REQUIRED")
    require(len({s.get("app_pid") for s in [*records, *scenes]}) == 1, "SINGLE_APP_PROCESS_REQUIRED")
    for scene in scenes:
        require(scene.get("source") == "PLEOS" and scene.get("hold_seconds") == 2
                and scene["hold_end_device_ms"] - scene["device_ms"] >= 2000, "STABLE_TWO_SECOND_SDK_SCENE_REQUIRED")
    by = {s["scene_id"]: s for s in scenes}
    for name, value in (("door-closed", "CLOSED"), ("door-open", "OPEN"), ("door-restored", "CLOSED")):
        require(by[name].get("value") == value and by[name].get("read_status") == "VALUE", "DOOR_VISUAL_SCENE_VALUE_INVALID")
    require(by["drive-restricted"].get("ux_known") is True and by["drive-restricted"].get("ux_restricted") is True, "ACTUAL_DRIVE_SCENE_REQUIRED")
    require(by["end-session"].get("page") == "PROFILE" and by["end-session"].get("session_started") is False
            and by["end-session"].get("deletion_pending") is False and by["end-session"].get("value") is None,
            "CLEAN_END_SCENE_REQUIRED")
    transition = by["language-en"]
    require(transition.get("scene_kind") == "LANGUAGE_TRANSITION" and transition.get("selected_locale") == "en"
            and transition.get("from_locale") != "en" and transition.get("locale") == "en" and transition.get("page") == "HOME"
            and transition["device_ms"] < transition["selection_clicked_device_ms"] <= transition["transition_completed_device_ms"]
            < transition["device_ms"] + 2000, "ACTUAL_TWO_SECOND_LANGUAGE_SELECTION_REQUIRED")
    return hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("showcase", "late"), required=True)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--test-apk", type=Path, required=True)
    parser.add_argument("--audit-file", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True, help="Explicit test-owned SQLite; counts only, never session/token reads")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/qa/multilingual-session-20261115")
    parser.add_argument("--adb", type=Path, default=ROOT / ".tooling/android-sdk/platform-tools/adb")
    parser.add_argument("--avd", default="CarCue_Pleos21_LocalAI")
    parser.add_argument("--serial", default="emulator-5584")
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--record", action="store_true", help="Showcase only, one continuous screenrecord with an explicit 360-second limit")
    parser.add_argument("--media-tool-source", type=Path, default=ROOT / "scripts/render_sdk_intro.swift",
                        help="Approved new AVFoundation tool source; compiled only to the new QA directory for read-only video probing")
    args = parser.parse_args()
    require(args.serial == "emulator-5584" and args.avd == "CarCue_Pleos21_LocalAI", "PRESERVED_AVD_REQUIRED")
    require(not args.record or args.mode == "showcase", "RECORD_SHOWCASE_ONLY")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id) is not None, "SAFE_RUN_ID_REQUIRED")
    out = (args.output_dir / args.run_id).resolve()
    require(out.is_relative_to((ROOT / "output/qa").resolve()), "NEW_IGNORED_QA_DIRECTORY_REQUIRED")
    require(args.database.resolve().is_relative_to((ROOT / "output/qa").resolve()) and args.database.is_file(), "EXPLICIT_TEST_OWNED_DATABASE_REQUIRED")
    out.mkdir(parents=True, exist_ok=False)
    base = [str(args.adb.resolve()), "-s", args.serial]
    markers = "files/qa/" + args.run_id + "/sdk-session"
    report = {"passed": False, "functional_passed": False, "mode": args.mode, "run_id": args.run_id,
        "started_at": datetime.now(timezone.utc).isoformat(), "cleanup_errors": [], "fixtures": [], "late_boundaries": {},
        "physical_vehicle_tested": False, "app_sdk_set_called": False, "paid_provider_called": False,
        "question_translation_calls": 0, "seatbelt_status_connected": False, "semantic_review_status": "PENDING_INDEPENDENT_REVIEW"}
    process, recorder, record_log, lease, audit, observation = None, None, None, None, None, None
    functional, recorded_ok, native_done, stop_sent = False, not args.record, False, False
    handled, pending, completed = set(), {}, set()
    pid, records, scenes, result, guides = None, None, None, None, None
    video = out / "sdk-session-raw.mp4"
    remote_video = "/sdcard/carcue-sdk-session-" + args.run_id + ".mp4"
    record_started = None

    def adb(*parts, timeout=20, check=True):
        try:
            p = subprocess.run(base + list(parts), capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            # Preserve the operation, never command output or private payloads.
            if parts[:2] == ("shell", "run-as"):
                operation = "APP_QA_" + str(parts[5]).upper()
            elif parts[:2] == ("shell", "am"):
                operation = "ACTIVITY_" + str(parts[2]).upper().replace("-", "_")
            else:
                operation = str(parts[0]).upper().replace("-", "_")
            report.setdefault("adb_timeouts", []).append({"operation": operation, "timeout_seconds": timeout})
            raise
        require(not check or p.returncode == 0, "ADB_COMMAND_FAILED")
        return p.stdout.strip()

    def app(*parts, check=True):
        return adb("shell", "run-as", PACKAGE, "--user", "10", *parts, check=check)

    def names():
        return set(app("ls", "-1", markers, check=False).splitlines())

    def signal(name):
        app("touch", markers + "/" + name)

    def marker(name):
        return json.loads(app("cat", markers + "/" + name))

    def collect():
        for name in names():
            if re.fullmatch(r"[A-Za-z0-9_.-]+\.(?:json|jsonl|png)", name) is None or (out / name).exists(): continue
            with (out / name).open("xb") as target:
                subprocess.run(base + ["exec-out", "run-as", PACKAGE, "--user", "10", "cat", markers + "/" + name],
                               stdout=target, stderr=subprocess.PIPE, timeout=30, check=True)

    def counts():
        with sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True, timeout=5) as db:
            return {table: db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] for table in ("sessions", "results", "history")}

    def fixture(phase, path):
        lease.request(path, "PUT")
        report["fixtures"].append({"phase": phase, "request": path, "at": datetime.now(timezone.utc).isoformat()})

    def park(phase):
        lease.wait_ready(timeout=30)
        for path in ("/vehicle/controls?speed=0&accelerator=0&brake=0", "/vehicle/gear?gear=Park", "/vehicle/body?door_fl=0"):
            fixture(phase, path)
        b, c, g = [lease.request(path) for path in ("/vehicle/body", "/vehicle/controls", "/vehicle/gear")]
        state = {"front_left": b.get("body", b)["doors"]["front_left"], "speed_kph": c["speed_kph"], "gear": g["actual"]["value"]}
        require(state == {"front_left": False, "speed_kph": 0, "gear": "Park"}, "PARK_ZERO_CLOSED_REQUIRED")
        report[phase.lower() + "_fixture"] = state

    def cleanup_step(name, action):
        try: return action()
        except Exception as exc: report["cleanup_errors"].append({"phase": name, "type": type(exc).__name__})

    try:
        for prop, expected in (("ro.kernel.qemu", "1"), ("ro.boot.qemu.avd_name", args.avd), ("ro.build.version.sdk", "34"), ("sys.boot_completed", "1")):
            require(adb("shell", "getprop", prop) == expected, "AVD_BOOT_IDENTITY_MISMATCH")
        require(adb("shell", "am", "get-current-user") == "10", "CURRENT_USER_10_REQUIRED")
        require(adb("shell", "service", "check", "car_service") == "Service car_service: found", "REGISTERED_CAR_SERVICE_REQUIRED")
        require(not adb("shell", "pidof", "screenrecord", check=False), "PREEXISTING_RECORDER_REFUSED")
        report["device_timezone"] = adb("shell", "getprop", "persist.sys.timezone")
        report["initial_database_counts"] = counts()
        require(all(n == 0 for n in report["initial_database_counts"].values()), "DATABASE_NOT_EMPTY_REFUSE_SHARED_DATA")
        with tempfile.TemporaryDirectory(dir=out, prefix="installed-hashes-") as temp:
            installed = {}
            for package, apk in ((PACKAGE, args.apk.resolve()), (PACKAGE + ".test", args.test_apk.resolve())):
                require(apk.is_file(), "INPUT_APK_REQUIRED")
                paths = adb("shell", "pm", "path", "--user", "10", package).splitlines()
                require(len(paths) == 1 and paths[0].startswith("package:/data/app/"), "ONE_INSTALLED_BASE_APK_REQUIRED")
                local = Path(temp) / (package + ".apk")
                adb("pull", paths[0].removeprefix("package:"), str(local), timeout=60)
                require(sha(local) == sha(apk), "INSTALLED_APK_HASH_MISMATCH")
                installed[package] = sha(local)
            report["installed_apk_sha256"] = installed
        require(not app("ls", "-d", markers, check=False), "DEVICE_QA_DIRECTORY_ALREADY_EXISTS")
        catalog = Catalog()
        guides = {locale: next(g for g in catalog.published(PROFILE, locale) if g["guide_id"] == GUIDE) for locale in LOCALES}
        with httpx.Client(timeout=httpx.Timeout(10, connect=3), trust_env=False, follow_redirects=False) as client:
            def get(url):
                r = client.get(url); require(r.status_code == 200, "PREFLIGHT_HTTP_FAILED"); return r.json()
            require(get("http://127.0.0.1:8001/health") == {"status": "ok", "mode": "LIVE"}, "LIVE_BACKEND_REQUIRED")
            model, = [m for m in get("http://127.0.0.1:11434/api/tags").get("models", []) if m.get("name") == args.model]
            require(model.get("digest") == MODEL_DIGEST, "EXACT_MODEL_DIGEST_REQUIRED")
            report["local_model"] = {"name": args.model, "digest": model["digest"], "ollama_version": get("http://127.0.0.1:11434/api/version").get("version")}
            from urllib.parse import urlencode
            for locale, guide in guides.items():
                require(get("http://127.0.0.1:8001/v1/guides/" + GUIDE + "?" + urlencode({"profile_id": PROFILE, "locale": locale})) == guide,
                        "SERVER_GUIDE_DIFFERS_FROM_REVIEWED_CATALOG")
        adb("forward", "tcp:8088", "tcp:8088")
        lease = PleosConsoleSession(client="carcue-session-" + args.run_id).start()
        park("INITIAL")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP"); adb("shell", "wm", "dismiss-keyguard")
        policy = adb("shell", "dumpsys", "window", "policy")
        report["keyguard"] = [line.strip() for line in policy.splitlines() if re.search(r"currentUser|showing=|mIsShowing", line, re.I)]
        require(re.search(r"(?:currentUser|mCurrentUserId)=10\b", policy, re.I) is not None
                and re.search(r"(?:showing|mIsShowing)=false\b", policy, re.I) is not None
                and re.search(r"(?:showing|mIsShowing)=true\b", policy, re.I) is None, "KEYGUARD_NOT_READY")
        # WAKEUP is asynchronous on the stock AVD; require the observed state,
        # rather than treating a successfully queued key as a ready display.
        awake_by, retry_wake_at = time.monotonic() + 20, time.monotonic() + 3
        while True:
            power = adb("shell", "dumpsys", "power")
            if "mWakefulness=Awake" in power:
                break
            require(time.monotonic() < awake_by, "AWAKE_DISPLAY_REQUIRED")
            if time.monotonic() >= retry_wake_at:
                adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
                retry_wake_at = time.monotonic() + 3
            time.sleep(.3)
        if args.mode == "showcase":
            adb("shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1", timeout=30)
            launch = adb("shell", "am", "start", "--user", "10", "-W", "-f", "0x10020000", "-n", PACKAGE + "/.MainActivity", timeout=30)
            report["normal_launch"] = {"route": "official LAUNCHER then existing-task selection", "activity_wait_status_ok": "Status: ok" in launch}
            require("Status: ok" in launch, "NORMAL_APP_LAUNCH_FAILED")
        else:
            # On the stock AVD, replacing a live launcher TaskView process can
            # race OEM task removal against the new instrumentation process.
            # The separate showcase covers normal launch. This mode starts only
            # the owned, empty-session test app through InstrumentationRule.
            adb("shell", "am", "force-stop", "--user", "10", PACKAGE)
            stopped_by = time.monotonic() + 10
            while adb("shell", "pidof", PACKAGE, check=False):
                require(time.monotonic() < stopped_by, "OWN_TEST_APP_DID_NOT_STOP")
                time.sleep(.2)
            report["normal_launch"] = {"route": "INSTRUMENTATION_RULE_AFTER_OWN_PACKAGE_FORCE_STOP",
                                       "normal_launcher_verified": False, "userdata_cleared": False}
        audit = AuditCursor(args.audit_file.resolve())
        if args.mode == "late":
            observation = AuditObservation(audit).start()
        method = "connectedShowcaseFlow" if args.mode == "showcase" else "lateResponseBoundaries"
        command = base + ["shell", "am", "instrument", "--user", "10", "-w", "-r", "-e", "validateSdkSessionFlow", "true",
            "-e", "sessionFlowMode", args.mode, "-e", "runId", args.run_id, "-e", "expectedLocalModel", args.model,
            "-e", "class", "com.carcue.app.PleosSessionBoundariesTest#" + method,
            PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner"]
        (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        with (out / "instrumentation.txt").open("x") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            deadline, ready, progress = time.monotonic() + 600, False, time.monotonic() + 30
            activity_reselected = False
            while process.poll() is None and time.monotonic() < deadline:
                try: lease.check_heartbeat()
                except ConsoleHeartbeatError:
                    # The independent heartbeat keeps recovering. Do not suspend real
                    # SDK/audit observations behind fixture-readiness HTTP waits.
                    # Every external mutation below still requires wait_ready(), as
                    # do INITIAL/RESTORED Park checks and lease shutdown.
                    require(lease.diagnostics()["heartbeat_running"], "CONSOLE_HEARTBEAT_THREAD_STOPPED")
                    report["console_observation_recovery_checks"] = report.get("console_observation_recovery_checks", 0) + 1
                present = names()
                if args.mode == "late" and not activity_reselected and "activity-ready" in present:
                    activity = marker("activity-ready")
                    pid = activity["app_pid"]
                    require(isinstance(pid, int) and not isinstance(pid, bool) and pid > 0
                            and str(pid) in adb("shell", "pidof", PACKAGE).split(), "INSTRUMENTATION_APP_PID_NOT_RUNNING")
                    launch = adb("shell", "am", "start", "--user", "10", "-W", "-f", "0x10020000",
                                 "-n", PACKAGE + "/.MainActivity", timeout=30)
                    require("Status: ok" in launch, "INSTRUMENTATION_TASK_RESELECT_FAILED")
                    require(str(pid) in adb("shell", "pidof", PACKAGE).split(), "TASK_RESELECT_REPLACED_APP_PROCESS")
                    report["app_pid"] = pid
                    report["activity_reselect"] = {"route": "instrumentation-task-reselect", "app_pid_before": pid,
                        "app_pid_after": pid, "activity_wait_status_ok": True, "normal_launcher_verified": False,
                        "native_initial_window_focused": activity.get("window_focused")}
                    signal("activity-go")
                    activity_reselected = True
                if not ready and "ready" in present:
                    first = json.loads(app("cat", markers + "/events.jsonl").splitlines()[0])
                    require(pid is None or first["app_pid"] == pid, "NATIVE_APP_PID_CHANGED_AFTER_RESELECT")
                    pid = first["app_pid"]
                    require(str(pid) in adb("shell", "pidof", PACKAGE).split(), "NATIVE_APP_PID_NOT_RUNNING")
                    if args.mode == "late":
                        require(activity_reselected and "activity-focus.json" in present, "ACTUAL_INSTRUMENTATION_WINDOW_FOCUS_REQUIRED")
                        focused = marker("activity-focus.json")
                        require(focused.get("app_pid") == pid and focused.get("window_focused") is True,
                                "ACTUAL_INSTRUMENTATION_WINDOW_FOCUS_REQUIRED")
                        report["activity_reselect"]["native_window_focus_confirmed"] = True
                    report["app_pid"] = pid
                    if args.record:
                        record_log = (out / "screenrecord.txt").open("x")
                        recorder = subprocess.Popen(base + ["shell", "screenrecord", "--bit-rate", "6000000", "--time-limit", "360", remote_video], stdout=record_log, stderr=subprocess.STDOUT)
                        record_started = round(float(adb("shell", "cat", "/proc/uptime").split()[0]) * 1000)
                        time.sleep(1)
                    signal("go"); ready = True
                for name, paths in (("request-open", ("/vehicle/body?door_fl=1",)), ("request-close", ("/vehicle/body?door_fl=0",)),
                                    ("request-warm-drive", ("/vehicle/gear?gear=Drive", "/vehicle/controls?speed=20&accelerator=0&brake=0")),
                                    ("request-warm-park", ("/vehicle/controls?speed=0&accelerator=0&brake=0", "/vehicle/gear?gear=Park")),
                                    ("request-drive", ("/vehicle/gear?gear=Drive", "/vehicle/controls?speed=20&accelerator=0&brake=0")),
                                    ("request-park", ("/vehicle/controls?speed=0&accelerator=0&brake=0", "/vehicle/gear?gear=Park"))):
                    if name in present and name not in handled:
                        lease.wait_ready(timeout=30)
                        for path in paths: fixture(name, path)
                        handled.add(name)
                if args.mode == "late":
                    for name in ("locale", "drive", "end"):
                        if "pending-" + name in present and name not in pending:
                            row = marker("pending-" + name); request = row["request_id"]
                            require(str(uuid.UUID(request)) == request and row.get("busy") is True, "ACTUAL_PENDING_REQUEST_REQUIRED")
                            require(row.get("source") == "PLEOS" and row.get("capability") == "SUPPORTED"
                                    and row.get("read_status") == "VALUE" and row.get("value") == "CLOSED"
                                    and row.get("ux_known") is True and row.get("ux_restricted") is False and row.get("ux_flags") == 0
                                    and row.get("profile_id") == PROFILE and row.get("market") == "KR", "ACTUAL_PENDING_SDK_CONTEXT_REQUIRED")
                            received = datetime.fromisoformat(row["received_at"].replace("Z", "+00:00"))
                            recorded = datetime.fromisoformat(row["recorded_at"].replace("Z", "+00:00"))
                            require(0 <= (recorded - received).total_seconds() * 1000 <= row["state_ttl_ms"] == 60000,
                                    "FRESH_PENDING_SDK_CONTEXT_REQUIRED")
                            hashed = digest(request.encode())
                            require(not any(e.get("request_id_hash") == hashed for e in audit.events()), "INFLIGHT_NOT_EXERCISED")
                            pending[name] = {"request_id_hash": hashed, "boundary_lower_monotonic": time.monotonic(), "pending_native": sanitized(row)}
                            signal("boundary-go-" + name)
                        if name in pending and "boundary-" + name in present and "boundary_observed_monotonic" not in pending[name]:
                            require(not any(e.get("request_id_hash") == pending[name]["request_id_hash"] for e in audit.events()), "INFLIGHT_NOT_EXERCISED")
                            pending[name]["boundary_observed_monotonic"] = time.monotonic()
                            pending[name]["boundary_native"] = sanitized(marker("boundary-" + name))
                        if name in pending and "boundary_observed_monotonic" in pending[name] and name not in completed:
                            matching = [e for e in audit.events() if e.get("request_id_hash") == pending[name]["request_id_hash"]]
                            if matching:
                                done = observation.completed_at(pending[name]["request_id_hash"])
                                if done is None: continue
                                event, = matching
                                elapsed = (done - pending[name]["boundary_lower_monotonic"]) * 1000
                                duration = event.get("duration_ms")
                                require(done >= pending[name]["boundary_observed_monotonic"]
                                        and isinstance(duration, int) and not isinstance(duration, bool)
                                        and elapsed < duration - 1, "INFLIGHT_NOT_EXERCISED")
                                pending[name].update(model_done_observed_monotonic=done, elapsed_after_boundary_lower_ms=elapsed,
                                                     provider_duration_ms=duration, provider_started_before_boundary_proven=True,
                                                     completion_after_native_boundary_proven=True,
                                                     completion_observation="INDEPENDENT_REAL_AUDIT_POLL_20MS", duration_rounding_margin_ms=1)
                                signal("model-finished-" + name); completed.add(name)
                        if name in pending and "checked-" + name in present:
                            pending[name]["checked_native"] = sanitized(marker("checked-" + name))
                if "done" in present:
                    native_done = True
                    signal("stop"); stop_sent = True
                if time.monotonic() >= progress:
                    print("WAIT actual SDK/local-provider " + args.mode + "; independent lease active", flush=True); progress = time.monotonic() + 30
                try: process.wait(timeout=min(.1, max(.01, deadline - time.monotonic())))
                except subprocess.TimeoutExpired: pass
            require(process.poll() is not None, "NATIVE_600S_DEADLINE")
        text = (out / "instrumentation.txt").read_text()
        require(process.returncode == 0 and "OK (1 test)" in text and "FAILURES!!!" not in text and native_done, "NATIVE_ASSERTIONS_FAILED")
        collect(); result = json.loads((out / "result.json").read_text())
        require(result.get("passed") is True and result.get("app_pid") == pid and result.get("asks") == 3
                and result.get("session_end_asserted") is True and result.get("deletion_pending") is False,
                "NATIVE_COMPLETION_CONTRACT_FAILED")
        events = [json.loads(line) for line in (out / "events.jsonl").read_text().splitlines() if line.strip()]
        require(all(row.get("app_pid") == pid for row in events), "SINGLE_NATIVE_PROCESS_REQUIRED")
        report["events"] = [sanitized(row) for row in events]
        if args.mode == "showcase":
            records = [json.loads(line) for line in (out / "responses.jsonl").read_text().splitlines() if line.strip()]
            scenes = [json.loads(line) for line in (out / "scenes.jsonl").read_text().splitlines() if line.strip()]
            validate_showcase(records, scenes, audit.events(), guides, args.model)
            require(handled == {"request-open", "request-close", "request-drive", "request-park"}, "ALL_EXTERNAL_FIXTURE_PHASES_REQUIRED")
            pixels = json.loads((out / "car-pixels.json").read_text())
            require(pixels["closed"] == pixels["restored"] != pixels["open"], "SDK_VEHICLE_PIXELS_NOT_RESTORED")
            require({"LOCALE_CHANGE_CLEARED_OLD_TRANSLATION_AND_CONSENT", "EDITED_INPUT_RESET_CONSENT",
                     "RETAINED_ANSWER_LANGUAGE_EXPLICIT_en", "RETAINED_ANSWER_LANGUAGE_EXPLICIT_ja-JP",
                     "TWO_BACKS_RETAINED_ORIGINAL_GUIDE_STEP"}.issubset({e["phase"] for e in events}),
                    "LANGUAGE_DRAFT_CONSENT_COVERAGE_REQUIRED")
            report["responses"] = [sanitized(row) for row in records]
        else:
            require(completed == {"locale", "drive", "end"} and all("checked_native" in row for row in pending.values()), "ALL_THREE_LATE_BOUNDARIES_REQUIRED")
            routes = {"locale": "PRODUCTION_LANGUAGE_HANDLERS_ON_MAIN_THREAD_WHILE_INFLIGHT",
                      "drive": "ACTUAL_PLATFORM_UX_CALLBACK_WHILE_INFLIGHT",
                      "end": "PRODUCTION_END_SESSION_HANDLER_ON_MAIN_THREAD_WHILE_INFLIGHT"}
            require(all(row["boundary_native"].get("route") == routes[name] for name, row in pending.items()),
                    "EXPLICIT_PRODUCTION_ACTION_ROUTE_REQUIRED")
            ended = pending["end"]["boundary_native"]
            require(ended.get("page") == "PROFILE" and ended.get("session_started") is False
                    and ended.get("profile_id") is None and ended.get("value") is None
                    and ended["session_epoch"] > pending["end"]["pending_native"]["session_epoch"], "ACTUAL_SESSION_EPOCH_END_REQUIRED")
            validate_audit(audit.events(), {row["request_id_hash"] for row in pending.values()}, args.model)
            require(handled == {"request-warm-drive", "request-warm-park", "request-drive", "request-park"}, "ACTUAL_DRIVE_RESTORE_REQUIRED")
            require("ACTUAL_UX_WARMUP_DRIVE_AND_PARK" in {e["phase"] for e in events}, "ACTUAL_UX_WARMUP_REQUIRED")
            captures = {}
            for name in ("late-locale", "late-drive", "late-drive-restored", "late-end"):
                capture = json.loads((out / (name + "-capture.json")).read_text())
                require(capture.get("app_pid") == pid and capture.get("compose_capture") == "ACTUAL_CURRENT_APP_ROOT"
                        and capture.get("method") == "UIAUTOMATION_REAL_DISPLAY"
                        and isinstance(capture.get("attempts"), int) and capture["attempts"] > 0
                        and (out / (name + ".png")).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "ACTUAL_APP_CAPTURE_REQUIRED")
                require(capture.get("window_focused") is True and capture.get("activity_destroyed") is False
                        and isinstance(capture.get("activity_identity"), int)
                        and not isinstance(capture["activity_identity"], bool)
                        and capture["activity_identity"] == capture.get("prepared_activity_identity")
                        and capture.get("compose_test_clock_auto_advance") is False
                        and isinstance(capture.get("late_manual_frames_pumped"), int)
                        and not isinstance(capture["late_manual_frames_pumped"], bool)
                        and capture["late_manual_frames_pumped"] > 0, "ORIGINAL_FOCUSED_ACTIVITY_AND_COMMITTED_FRAMES_REQUIRED")
                if name == "late-drive":
                    require(capture.get("physical_required") is False and capture.get("ux_known") is True
                            and capture.get("ux_restricted") is True, "DRIVE_CAPTURE_SCOPE_INVALID")
                else:
                    require(capture.get("physical_required") is True and capture.get("passed") is True,
                            "UNRESTRICTED_REAL_DISPLAY_CAPTURE_REQUIRED")
                physical = out / (name + "-physical.png")
                if capture.get("passed") is True:
                    require(capture.get("physical_unavailable") is False and physical.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"),
                            "ACTUAL_DISPLAY_CAPTURE_REQUIRED")
                else:
                    require(name == "late-drive" and capture.get("physical_unavailable") is True and not physical.exists(),
                            "UNAVAILABLE_DISPLAY_MUST_NOT_BE_SUBSTITUTED")
                captures[name] = capture
            report["physical_captures"] = captures
            report["physical_capture_complete"] = all(c["passed"] for c in captures.values())
            report["display_capture_limitations"] = [] if report["physical_capture_complete"] else [
                "DRIVE_GLOBAL_CAPTURE_UNAVAILABLE_ACTUAL_COMPOSE_CAPTURE_PRESERVED"]
        report["native_result"] = result
        functional = True
    except Exception as exc:
        code = str(exc) if isinstance(exc, RuntimeError) and re.fullmatch(r"[A-Z0-9_]{1,100}", str(exc)) else "VALIDATION_EXCEPTION"
        report["failure"] = {"type": type(exc).__name__, "code": code}
    finally:
        if process is not None and process.poll() is None:
            if not stop_sent: cleanup_step("SIGNAL_STOP", lambda: signal("stop"))
            cleanup_step("STOP_ACTIVE_TEST_APP", lambda: adb("shell", "am", "force-stop", "--user", "10", PACKAGE))
            cleanup_step("WAIT_HOST_INSTRUMENTATION", lambda: process.wait(timeout=15))
            if process.poll() is None:
                cleanup_step("TERMINATE_HOST_ADB", process.terminate)
                cleanup_step("WAIT_TERMINATED_HOST_ADB", lambda: process.wait(timeout=5))
        if recorder is not None:
            def stop_recording():
                if recorder.poll() is None:
                    ids = adb("shell", "pidof", "screenrecord", check=False).split()
                    require(len(ids) == 1 and ids[0].isdigit(), "OWN_RECORDER_PID_REQUIRED")
                    adb("shell", "kill", "-2", ids[0])
                recorder.wait(timeout=20)
                require(recorder.returncode == 0, "SCREENRECORD_NONZERO_EXIT")
            cleanup_step("STOP_SCREENRECORD", stop_recording)
            if record_log is not None: record_log.close()
            cleanup_step("PULL_RAW_VIDEO", lambda: adb("pull", remote_video, str(video), timeout=60))
        if process is not None: cleanup_step("COLLECT_NATIVE_EVIDENCE", collect)
        if pid is not None:
            def sdk_logs():
                raw = adb("logcat", "-d", "--pid", str(pid), "-v", "brief", "-s", "CarCueVehicle:I", "*:S")
                safe = [m.group(1) for line in raw.splitlines()
                        if (m := SDK_EVENT.search(line) or SDK_FAILURE_EVENT.search(line))]
                (out / "sdk-events.json").write_text(json.dumps(safe, indent=2) + "\n")
                report["sdk_failure_events"] = [event for event in safe if SDK_FAILURE_EVENT.fullmatch(event)]
                require(any("PLEOS:GET_RECEIVED" in e for e in safe) and "PLEOS:LISTENER_UNREGISTER_RETURNED" in safe
                        and "PLEOS:RELEASE_RETURNED" in safe and any("UX:CALLBACK:requires=true" in e for e in safe)
                        and any("UX:CALLBACK:requires=false" in e for e in safe), "SDK_LIFECYCLE_OR_REAL_UX_EVIDENCE_MISSING")
                if args.mode == "late":
                    require(sum("UX:CALLBACK:requires=true" in e for e in safe) >= 2
                            and sum("UX:CALLBACK:requires=false" in e for e in safe) >= 2,
                            "WARMUP_AND_INFLIGHT_REAL_UX_CALLBACKS_REQUIRED")
                if args.mode == "showcase": require(any("CALLBACK_RECEIVED:RANGE_VERIFIED:value=1" in e for e in safe)
                    and any("CALLBACK_RECEIVED:RANGE_VERIFIED:value=0" in e for e in safe), "ACTUAL_DOOR_CALLBACK_EVIDENCE_MISSING")
                report["sdk_events"] = safe
            cleanup_step("SCOPED_SDK_LOGS", sdk_logs)
        if lease is not None:
            cleanup_step("RESTORE_FIXTURES", lambda: park("RESTORED"))
            cleanup_step("CLOSE_LEASE", lease.close)
            report["console_session"] = lease.diagnostics()
        report["late_boundaries"] = pending
        if audit is not None:
            report["audit"] = cleanup_step("FINAL_AUDIT_READ", audit.events)
            if functional:
                cleanup_step("FINAL_AUDIT_CONTRACT", lambda: validate_audit(report["audit"],
                    {digest(row["request_id"].encode()) for row in records if row["phase"].startswith("ask-")} if args.mode == "showcase"
                    else {row["request_id_hash"] for row in pending.values()}, args.model))
        if observation is not None:
            cleanup_step("CLOSE_AUDIT_OBSERVER", observation.close)
            report["audit_observer"] = {"independent": True, "poll_interval_seconds": .02,
                "thread_stopped": not observation.worker.is_alive(), "error": observation.error}
        report["final_database_counts"] = cleanup_step("FINAL_DATABASE_COUNTS", counts)
        if functional and report["final_database_counts"] is not None:
            cleanup_step("CONFIRM_DATABASE_EMPTY", lambda: require(all(n == 0 for n in report["final_database_counts"].values()), "SESSION_DATA_REMAINS"))
        if functional and args.record:
            def inspect_video():
                require(video.is_file() and video.stat().st_size > 100000, "RAW_RECORDING_MISSING")
                source = args.media_tool_source.resolve()
                require(source.is_file() and source.is_relative_to(ROOT) and source.name == "render_sdk_intro.swift",
                        "APPROVED_VIDEO_PROBE_SOURCE_MISSING")
                source_hash = sha(source)
                binary, cache = out / "video-probe", out / "swift-module-cache"
                cache.mkdir()
                compile_probe = subprocess.run(["/usr/bin/xcrun", "swiftc", "-parse-as-library", "-suppress-warnings",
                    "-module-cache-path", str(cache), str(source), "-o", str(binary)], capture_output=True, text=True, timeout=120)
                require(compile_probe.returncode == 0 and sha(source) == source_hash, "VIDEO_PROBE_COMPILE_FAILED")
                probe = subprocess.run([str(binary), "probe", str(video)], capture_output=True, text=True, timeout=30, check=True)
                info = json.loads(probe.stdout)
                duration = info["duration_seconds"]
                require(0 < duration <= 360.1 and info["width"] == 2560 and info["height"] == 1440, "RAW_VIDEO_SIZE_OR_LENGTH_INVALID")
                for scene in scenes:
                    start = (scene["device_ms"] - record_started) / 1000
                    require(start >= 0 and start + 2 <= duration and (scene["hold_end_device_ms"] - record_started) / 1000 <= duration + .1,
                            "VIDEO_DOES_NOT_CONTAIN_EVERY_STABLE_SCENE")
                report["video_probe"] = info | {"probe_source_sha256": source_hash}
                report["video_sha256"] = sha(video)
                return True
            recorded_ok = cleanup_step("INSPECT_CONTINUOUS_VIDEO", inspect_video) is True
        report["functional_passed"] = functional
        report["video_passed"] = recorded_ok if args.record else None
        report["passed"] = bool(functional and recorded_ok and not report["cleanup_errors"] and report.get("restored_fixture"))
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["files_sha256"] = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
        (out / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        if report["passed"] and args.record:
            manifest = {"schema_version": 1, "type": "UNEDITED_REAL_PLEOS_APK_SCREENRECORD", "test_pass": True,
                "video": str(video), "video_sha256": sha(video), "apk": str(args.apk.resolve()), "apk_sha256": sha(args.apk.resolve()),
                "installed_apk_sha256": report["installed_apk_sha256"][PACKAGE], "test_apk_sha256": sha(args.test_apk.resolve()),
                "package": PACKAGE, "single_apk": True, "single_process": True, "app_pid": pid, "source": "PLEOS",
                "recording_started_device_ms": record_started, "scenes": [sanitized(row) for row in scenes], "audit": report["audit"],
                "cleanup_errors": [], "physical_vehicle_tested": False, "app_sdk_set_called": False, "seatbelt_status_connected": False,
                "paid_provider_called": False, "question_translation_calls": 0, "files_sha256": report["files_sha256"],
                "display": {"width": 2560, "height": 1440}, "crop_xywh": [854, 90, 1682, 1210],
                "visual_review_status": "PENDING_INDEPENDENT_REVIEW", "sdk_events": report.get("sdk_events", [])}
            (out / "showcase-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(("PASS actual " if report["passed"] else "FAIL ") + args.mode + ": " + str(out), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
