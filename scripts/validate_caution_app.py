"""Opt-in real Pleos/local-AI caution UI checks; no installs or generated translations.

Requires already installed exact APKs and a prewarmed LIVE free local backend.
Only this isolated emulator's Console fixtures are set to Park/0/CLOSED and
restored finally. Existing userdata, logs, browser and security settings remain.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from pleos_console import ConsoleHeartbeatError, PleosConsoleSession
from validate_local_ai import AuditCursor, digest, require

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.content import Catalog

PACKAGE = "com.carcue.app"
PROFILE = "ioniq5-ne1-2024-kr"
GUIDE = "ioniq5-door-open-check"
MODEL_DIGEST = "359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7"
SOURCES = ["hyundai-ne1-2024-kr-door-open-warning", "hyundai-ne1-2024-kr-door-pinch-caution"]
QUESTIONS = {
    "ko-KR": "문을 닫기 전에 무엇을 확인해야 하나요?",
    "en": "What should I check before closing the indicated door?",
    "ja-JP": "表示されたドアを閉める前に何を確認しますか？",
}
CASES = [("ko-KR", "check-pinch-area", "en"), ("en", "check-closure-display", "ja-JP"), ("ja-JP", None, "ko-KR")]
PHASES = [phase for source, _, target in CASES for phase in ("ask-" + source, "stored-" + source + "-to-" + target)]
PROHIBITIONS = {
    "ko-KR": "몸의 일부가 문틈에 있으면 닫지 마세요.",
    "en": "Do not close the door while any body part is in the opening.",
    "ja-JP": "体の一部が開口部にある状態では、ドアを閉めないでください。",
}


def sha(path):
    return digest(path.read_bytes())


def closing_parts(guide):
    require([s["step_id"] for s in guide["steps"]] == ["check-pinch-area", "check-closure-display"], "EXACT_REVIEWED_STEPS_REQUIRED")
    return [guide["body"], *[text for step in guide["steps"] for text in (step["body"], *step["official_cautions"])]]


def caution_texts(guide):
    return [text for step in guide["steps"] for text in step["official_cautions"]]


def validate_runtime(records, events, guides, profile, model):
    require([r.get("phase") for r in records] == PHASES, "EXACT_CAUTION_PHASES_REQUIRED")
    hashes, requests, summaries = set(), set(), []
    previous_gets = 0
    for index, row in enumerate(records):
        source, step, target = CASES[index // 2]
        translated = bool(index % 2)
        locale = target if translated else source
        guide = guides[locale]
        require(row.get("question") == QUESTIONS[source] and row.get("locale") == locale
                and row.get("context_origin") == ("HOME" if step is None else "GUIDE")
                and row.get("context_guide_id") == (None if step is None else GUIDE)
                and row.get("context_step_id") == step, "QUESTION_OR_ENTRY_CONTEXT_CHANGED")
        require(row.get("profile_id") == PROFILE and row.get("profile_name") == profile["display_name"]
                and row.get("market") == "KR", "PROFILE_DISPLAY_IDENTITY_MISMATCH")
        require(row.get("mode") == "LIVE" and row.get("error") is None
                and row.get("status") == ("TRANSLATED" if translated else "ANSWERED")
                and row.get("content_kind") == "ANSWER" and row.get("source_locale") == source,
                "NATIVE_ANSWER_OR_TRANSLATION_INVALID")
        request_id = row.get("request_id", "")
        require(str(uuid.UUID(request_id)) == request_id and uuid.UUID(request_id).version == 4
                and request_id not in requests, "DISTINCT_UUID_REQUEST_REQUIRED")
        requests.add(request_id)
        if translated:
            require(row.get("ai_provider") == "STORED_GUIDE" and row.get("ai_model") is None
                    and row.get("review_status") == guide["translation_review_status"]
                    and row.get("review_status") == ("NOT_APPLICABLE" if target == "ko-KR" else "REVIEWED")
                    and row.get("answer_request_id") == records[index - 1]["request_id"], "STORED_ANSWER_NOT_CANONICAL")
        else:
            require(row.get("ai_provider") == "OLLAMA_LOCAL" and row.get("ai_model") == model
                    and row.get("answer_request_id") == request_id, "ACTUAL_LOCAL_ANSWER_REQUIRED")
            hashes.add(digest(request_id.encode()))
        expected_text = "\n".join(closing_parts(guide))
        cautions = caution_texts(guide)
        require(row.get("text") == expected_text and row.get("required_cautions") == cautions
                and PROHIBITIONS[locale] in cautions and row.get("unit_suffix") == ":closing-bundle:v1"
                and row.get("all_cautions_ui_visible") is True and row.get("activity_window_focused") is True, "COMPLETE_ORDERED_CAUTION_BUNDLE_REQUIRED")
        expected_citations = [{"source_id": item["source_id"], "guide_id": GUIDE, "profile_id": PROFILE,
            "manual_set_id": guide["manual_set_id"], "source_version": guide["source_version"], "url": item["url"]}
            for item in guide["sources"]]
        require([item["source_id"] for item in expected_citations] == SOURCES
                and row.get("citations") == expected_citations, "EXACT_OFFICIAL_CITATIONS_REQUIRED")
        require(row.get("vehicle_source") == "PLEOS" and row.get("capability") == "SUPPORTED"
                and row.get("read_status") == "VALUE" and row.get("door") == "CLOSED"
                and row.get("ux_known") is True and row.get("ux_restricted") is False
                and row.get("ux_flags") == 0, "ACTUAL_SDK_OR_UX_GUARD_FAILED")
        count = row.get("sdk_get_count")
        require(isinstance(count, int) and not isinstance(count, bool) and count > previous_gets, "FRESH_SDK_GET_PER_PHASE_REQUIRED")
        previous_gets = count
        recorded = datetime.fromisoformat(row["recorded_at"].replace("Z", "+00:00"))
        received = datetime.fromisoformat(row["received_at"].replace("Z", "+00:00"))
        ttl = row.get("state_ttl_ms")
        require(isinstance(ttl, int) and not isinstance(ttl, bool) and 0 < ttl <= 60000
                and 0 <= (recorded - received).total_seconds() * 1000 <= ttl,
                "SDK_READING_EXPIRED_AT_CAPTURE")
        require(isinstance(row.get("elapsed_ms"), int) and row["elapsed_ms"] >= 0, "NATIVE_DURATION_REQUIRED")
        summaries.append({key: value for key, value in row.items() if key not in {"request_id", "answer_request_id"}}
                         | {"request_id_hash": digest(request_id.encode()),
                            "answer_request_id_hash": digest(row["answer_request_id"].encode())})
    require(len(events) == len(hashes) == 3 and {e.get("request_id_hash") for e in events} == hashes,
            "EXACT_THREE_ASK_MODEL_CALLS_REQUIRED")
    require(len({e.get("response_digest") for e in events}) == 3, "DISTINCT_MODEL_RESPONSES_REQUIRED")
    for event in events:
        require(event.get("provider_kind") == "OLLAMA_LOCAL" and event.get("model") == model
                and event.get("operation") == "LocalPassageSelection" and event.get("outcome") == "STRUCTURED_VALIDATED"
                and event.get("error_code") is None and event.get("http_status") == 200
                and re.fullmatch(r"[a-f0-9]{64}", event.get("response_digest", ""))
                and isinstance(event.get("duration_ms"), int) and event["duration_ms"] >= 0
                and all(isinstance(event.get(key), int) and not isinstance(event[key], bool) and event[key] > 0
                        for key in ("prompt_tokens", "output_tokens")), "MODEL_AUDIT_NOT_REAL_VALIDATED_LOCAL_CALL")
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--test-apk", type=Path, required=True)
    parser.add_argument("--audit-file", type=Path, required=True)
    parser.add_argument("--adb", type=Path, default=ROOT / ".tooling/android-sdk/platform-tools/adb")
    parser.add_argument("--serial", default="emulator-5584")
    parser.add_argument("--avd", default="CarCue_Pleos21_LocalAI")
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--expected-model-digest", default=MODEL_DIGEST)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/qa/answer-cautions-20261114")
    args = parser.parse_args()
    require(args.serial == "emulator-5584" and args.avd == "CarCue_Pleos21_LocalAI", "PRESERVED_PLEOS_AVD_REQUIRED")
    require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id)), "SAFE_UNIQUE_RUN_ID_REQUIRED")
    require(bool(re.fullmatch(r"[a-f0-9]{64}", args.expected_model_digest)), "EXACT_MODEL_DIGEST_REQUIRED")
    out = (args.output_dir / args.run_id).resolve()
    require(out.is_relative_to((ROOT / "output/qa").resolve()), "IGNORED_QA_DIRECTORY_REQUIRED")
    out.mkdir(parents=True, exist_ok=False)
    base = [str(args.adb.resolve()), "-s", args.serial]
    markers = "files/qa/" + args.run_id + "/caution-answers"
    files = ["responses.jsonl", "result.json", "done", *[phase + ".png" for phase in PHASES], *[phase + "-physical.png" for phase in PHASES]]
    report = {"passed": False, "run_id": args.run_id, "started_at": datetime.now(timezone.utc).isoformat(),
        "validation_scope": "ACTUAL_NATIVE_THREE_CONTEXTS_AND_STORED_ANSWER_TRANSLATIONS",
        "semantic_review_status": "PENDING_INDEPENDENT_REVIEW", "native_full_nine_cell_matrix": False,
        "physical_vehicle_tested": False, "sdk_identified_vehicle_model": False, "app_sdk_set_called": False,
        "paid_provider_called": False, "question_translation_calls": 0,
        "cleanup_errors": [], "console_fixtures": [], "console_recoveries": []}
    process, lease, audit, records, functional = None, None, None, None, False

    def adb(*parts, timeout=20, check=True):
        result = subprocess.run(base + list(parts), capture_output=True, text=True, timeout=timeout)
        require(not check or result.returncode == 0, "ADB_COMMAND_FAILED")
        return result.stdout.strip()

    def app(*parts, check=True):
        return adb("shell", "run-as", PACKAGE, "--user", "10", *parts, check=check)

    def collect(name):
        require(re.fullmatch(r"[A-Za-z0-9_.-]+", name) is not None, "SAFE_ARTIFACT_NAME_REQUIRED")
        with (out / name).open("xb") as target:
            subprocess.run(base + ["exec-out", "run-as", PACKAGE, "--user", "10", "cat", markers + "/" + name],
                           stdout=target, stderr=subprocess.PIPE, timeout=30, check=True)

    def park(phase):
        lease.wait_ready(timeout=30)
        for path in ("/vehicle/controls?speed=0&accelerator=0&brake=0", "/vehicle/gear?gear=Park", "/vehicle/body?door_fl=0"):
            lease.request(path, "PUT")
            report["console_fixtures"].append({"phase": phase, "request": path})
        body, controls, gear = [lease.request(path) for path in ("/vehicle/body", "/vehicle/controls", "/vehicle/gear")]
        state = {"front_left": body.get("body", body)["doors"]["front_left"], "speed_kph": controls["speed_kph"], "gear": gear["actual"]["value"]}
        require(state == {"front_left": False, "speed_kph": 0, "gear": "Park"}, "PARK_ZERO_CLOSED_NOT_CONFIRMED")
        report[phase.lower() + "_fixture"] = state

    try:
        for prop, expected in (("ro.kernel.qemu", "1"), ("ro.boot.qemu.avd_name", args.avd), ("ro.build.version.sdk", "34"), ("sys.boot_completed", "1")):
            require(adb("shell", "getprop", prop) == expected, "AVD_BOOT_IDENTITY_MISMATCH")
        require(adb("shell", "am", "get-current-user") == "10", "CURRENT_USER_10_REQUIRED")
        require(adb("shell", "service", "check", "car_service") == "Service car_service: found", "CAR_SERVICE_REQUIRED")
        report["device_timezone"] = adb("shell", "getprop", "persist.sys.timezone")
        installed = {}
        with tempfile.TemporaryDirectory(dir=out, prefix="installed-hash-") as temp:
            for package, expected in ((PACKAGE, args.apk.resolve()), (PACKAGE + ".test", args.test_apk.resolve())):
                require(expected.is_file(), "INPUT_APK_REQUIRED")
                paths = adb("shell", "pm", "path", "--user", "10", package).splitlines()
                require(len(paths) == 1 and paths[0].startswith("package:/data/app/"), "ONE_INSTALLED_APK_REQUIRED")
                local = Path(temp) / (package + ".apk")
                adb("pull", paths[0].removeprefix("package:"), str(local), timeout=60)
                require(sha(local) == sha(expected), "INSTALLED_APK_HASH_MISMATCH")
                installed[package] = sha(local)
        report["installed_apk_sha256"] = installed
        require(not app("ls", "-d", markers, check=False), "APP_QA_DIRECTORY_ALREADY_EXISTS")
        catalog = Catalog()
        profile = catalog.profile(PROFILE)
        guides = {locale: next(g for g in catalog.published(PROFILE, locale) if g["guide_id"] == GUIDE) for locale in QUESTIONS}
        with httpx.Client(timeout=httpx.Timeout(10, connect=3), trust_env=False, follow_redirects=False) as client:
            def get(url):
                response = client.get(url)
                require(response.status_code == 200, "PREFLIGHT_HTTP_FAILED")
                return response.json()
            require(get("http://127.0.0.1:8001/health") == {"status": "ok", "mode": "LIVE"}, "LIVE_BACKEND_REQUIRED")
            model, = [m for m in get("http://127.0.0.1:11434/api/tags").get("models", []) if m.get("name") == args.model]
            require(model.get("digest") == args.expected_model_digest, "LOCAL_MODEL_DIGEST_MISMATCH")
            report["local_model"] = {"name": args.model, "digest": model["digest"], "ollama_version": get("http://127.0.0.1:11434/api/version").get("version")}
            for locale, guide in guides.items():
                from urllib.parse import urlencode
                actual = get("http://127.0.0.1:8001/v1/guides/" + GUIDE + "?" + urlencode({"profile_id": PROFILE, "locale": locale}))
                require(actual == guide, "SERVER_REVIEWED_GUIDE_DIFFERS_FROM_LOCAL_CATALOG")
        adb("forward", "tcp:8088", "tcp:8088")
        lease = PleosConsoleSession(client="carcue-cautions-" + args.run_id).start()
        park("INITIAL")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
        adb("shell", "wm", "dismiss-keyguard")
        policy = adb("shell", "dumpsys", "window", "policy")
        screen = [line.strip() for line in policy.splitlines() if re.search(r"currentUser|showing=|keyguardShowing|mIsShowing", line, re.I)]
        report["keyguard_preflight"] = screen
        require(re.search(r"(?:currentUser|mCurrentUserId)=10\b", policy, re.I) is not None
                and re.search(r"(?:showing|mIsShowing|keyguardShowing)=true\b", policy, re.I) is None
                and re.search(r"(?:showing|mIsShowing)=false\b", policy, re.I) is not None, "KEYGUARD_USER10_NOT_READY")
        power = adb("shell", "dumpsys", "power")
        require("mWakefulness=Awake" in power, "PHYSICAL_DISPLAY_NOT_AWAKE")
        launch = adb("shell", "am", "start", "-W", "--user", "10", "-n", PACKAGE + "/.MainActivity", timeout=40)
        require("Status: ok" in launch, "NORMAL_ACTIVITY_LAUNCH_FAILED")
        activities = adb("shell", "dumpsys", "activity", "activities")
        require(any(PACKAGE + "/" in line and "ResumedActivity" in line for line in activities.splitlines()), "NORMAL_ACTIVITY_NOT_RESUMED")
        report["normal_launch"] = {"route": "explicit user10 MAIN Activity launch with platform -W first-display wait", "status": "ok"}
        with (out / "normal-launch-physical.png").open("xb") as target:
            subprocess.run(base + ["exec-out", "screencap", "-p"], stdout=target, stderr=subprocess.PIPE, timeout=30, check=True)
        require((out / "normal-launch-physical.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "PHYSICAL_SCREENSHOT_MISSING")
        # API matrix calls must have finished before this cursor; only this native run contributes its three model calls.
        audit = AuditCursor(args.audit_file.resolve())
        command = base + ["shell", "am", "instrument", "--user", "10", "-w", "-r", "-e", "validateCautionAnswers", "true",
            "-e", "runId", args.run_id, "-e", "expectedLocalModel", args.model, "-e", "class",
            "com.carcue.app.PleosCautionAnswersTest#actualClosingCautionsAcrossContextsAndStoredTranslations",
            PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner"]
        (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        print("RUN actual native three ASK + three stored translations: " + args.run_id, flush=True)
        with (out / "instrumentation.txt").open("x") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 600
            progress_at = time.monotonic() + 30
            while process.poll() is None and time.monotonic() < deadline:
                try:
                    lease.check_heartbeat()
                except ConsoleHeartbeatError:
                    recovery = {"before": lease.diagnostics()}
                    report["console_recoveries"].append(recovery)
                    lease.wait_ready(timeout=min(30, max(.01, deadline - time.monotonic())))
                    recovery["after"] = lease.diagnostics()
                if time.monotonic() >= progress_at:
                    print("WAIT actual caution app; independent Console heartbeat active", flush=True)
                    progress_at = time.monotonic() + 30
                try:
                    process.wait(timeout=min(.5, max(.01, deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    pass
            require(process.poll() is not None, "NATIVE_600S_DEADLINE")
        text = (out / "instrumentation.txt").read_text()
        require(process.returncode == 0 and "OK (1 test)" in text and "FAILURES!!!" not in text, "NATIVE_ASSERTIONS_FAILED")
        for name in files:
            collect(name)
        require((out / "done").read_text() == "pass\n", "NATIVE_DONE_MARKER_MISSING")
        result = json.loads((out / "result.json").read_text())
        require(result.get("passed") is True and result.get("asks") == 3 and result.get("stored_answer_translations") == 3
                and result.get("question_translation_calls") == 0 and result.get("session_end_asserted") is True
                and result.get("deletion_pending") is False, "NATIVE_COMPLETION_CONTRACT_FAILED")
        report["native_result"] = result
        records = [json.loads(line) for line in (out / "responses.jsonl").read_text().splitlines() if line.strip()]
        report["phases"] = validate_runtime(records, audit.events(), guides, profile, args.model)
        for phase in PHASES:
            require((out / (phase + ".png")).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "NATIVE_SCREENSHOT_MISSING")
        functional = True
    except Exception as exc:
        code = str(exc) if isinstance(exc, RuntimeError) and re.fullmatch(r"[A-Z0-9_]{1,100}", str(exc)) else "VALIDATION_EXCEPTION"
        report["failure"] = {"type": type(exc).__name__, "code": code}
    finally:
        if process is not None and process.poll() is None:
            try:
                process.terminate(); process.wait(timeout=10)
            except Exception as exc:
                report["cleanup_errors"].append({"phase": "HOST_PROCESS_WAIT", "type": type(exc).__name__})
                try:
                    process.kill(); process.wait(timeout=5)
                except Exception as stop_error:
                    report["cleanup_errors"].append({"phase": "HOST_PROCESS_KILL", "type": type(stop_error).__name__})
        if process is not None and not functional:
            try:
                present = set(app("ls", "-1", markers, check=False).splitlines())
                for name in [*files, "failure.json", "failure.png"]:
                    if name in present and not (out / name).exists():
                        collect(name)
            except Exception as exc:
                report["cleanup_errors"].append({"phase": "PARTIAL_EVIDENCE", "type": type(exc).__name__})
        if lease is not None:
            try:
                park("RESTORED")
            except Exception as exc:
                report["cleanup_errors"].append({"phase": "FIXTURE_RESTORE", "type": type(exc).__name__})
            try:
                lease.close()
            except Exception as exc:
                report["cleanup_errors"].append({"phase": "LEASE_CLOSE", "type": type(exc).__name__})
            report["console_session"] = lease.diagnostics()
        if audit is not None:
            try:
                report["audit_events"] = audit.events()
                require(len(report["audit_events"]) == 3, "FINAL_AUDIT_CALL_COUNT_CHANGED")
                if functional:
                    validate_runtime(records, report["audit_events"], guides, profile, args.model)
            except Exception as exc:
                report["cleanup_errors"].append({"phase": "FINAL_AUDIT", "type": type(exc).__name__})
        report["passed"] = bool(functional and not report["cleanup_errors"] and report.get("restored_fixture"))
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["files_sha256"] = {path.name: sha(path) for path in out.iterdir() if path.is_file()}
        (out / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(("PASS functional caution coverage; independent meaning review required: " if report["passed"] else "FAIL caution UI: ") + str(out), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
