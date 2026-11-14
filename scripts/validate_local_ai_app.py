"""Opt-in actual Pleos app/local-AI run; installed APKs only, no install or SDK SET.

The host changes only isolated AVD Console fixtures. Instrumentation asserts UI,
canonical stored translations and session deletion. Window screenshots do not
assert physical-display composition. Every run preserves a new QA directory.
"""
import argparse
import json
import re
import secrets
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from pleos_console import ConsoleHeartbeatError, PleosConsoleSession
from validate_local_ai import AuditCursor, digest, loopback, require

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "com.carcue.app"
PROFILE = "ioniq5-ne1-2024-kr"
PHASES = ["ask-ko-KR", "question-translation-ko-KR-to-en", "ask-en", "question-translation-en-to-ja-JP",
          "ask-ja-JP", "question-translation-ja-JP-to-ko-KR", "stored-answer-ja-to-ko", "stored-guide-ko-to-en"]
LOCALES = ["ko-KR", "en", "en", "ja-JP", "ja-JP", "ko-KR", "ko-KR", "en"]
REVIEWED_PHASES = ["ask-ko-KR", "ask-en", "ask-ja-JP", "stored-answer-ja-to-ko", "stored-guide-ko-to-en"]
REVIEWED_LOCALES = ["ko-KR", "en", "ja-JP", "ko-KR", "en"]


def sha(path):
    return digest(path.read_bytes())


def validate_runtime(records, events, model, allow_question_rejection=False, reviewed_manual_only=False):
    phases = REVIEWED_PHASES if reviewed_manual_only else PHASES
    locales = REVIEWED_LOCALES if reviewed_manual_only else LOCALES
    calls = 3 if reviewed_manual_only else 6
    require([item.get("phase") for item in records] == phases, "EXACT_RUNTIME_PHASES_REQUIRED")
    summaries, model_hashes = [], set()
    for index, item in enumerate(records):
        require(item.get("vehicle_source") == "PLEOS" and item.get("mode") == "LIVE"
                and item.get("profile_id") == PROFILE and item.get("locale") == locales[index]
                and isinstance(item.get("elapsed_ms"), int)
                and item["elapsed_ms"] >= 0, "RUNTIME_SDK_MODE_PROFILE_OR_ERROR_MISMATCH")
        question = item["phase"].startswith("question-translation-")
        ask = item["phase"].startswith("ask-")
        stored_answer = item["phase"] == "stored-answer-ja-to-ko"
        rejected = (allow_question_rejection and question
                    and item.get("status") == "UNAVAILABLE")
        require(item.get("error") == ("TRANSLATION_UNAVAILABLE" if rejected else None),
                "UNEXPECTED_APP_ERROR")
        request_id = item.get("request_id", "")
        require(str(uuid.UUID(request_id)) == request_id and uuid.UUID(request_id).version == 4, "RUNTIME_UUID_REQUIRED")
        hashed = digest(request_id.encode())
        if ask or question:
            require(item.get("ai_provider") == "OLLAMA_LOCAL" and item.get("ai_model") == model, "RUNTIME_LOCAL_MODEL_REQUIRED")
            model_hashes.add(hashed)
            if ask:
                require(item.get("status") == "ANSWERED" and item.get("citations", 0) > 0, "GROUNDED_APP_ANSWER_REQUIRED")
            else:
                require(item.get("content_kind") == "QUESTION" and item.get("review_status") == "UNREVIEWED",
                        "APP_QUESTION_KIND_OR_REVIEW_INVALID")
                if rejected:
                    require(item.get("translation_status") == "TEMPORARILY_UNAVAILABLE"
                            and item.get("translation_empty") is True
                            and item.get("retry_new_request") is True, "APP_REJECTION_NOT_FAIL_CLOSED")
                else:
                    require(item.get("status") == "TRANSLATED"
                            and item.get("translation_source_locale") == locales[index - 1], "APP_QUESTION_TRANSLATION_INVALID")
        else:
            require(item.get("status") == "TRANSLATED" and item.get("ai_provider") == "STORED_GUIDE"
                    and item.get("ai_model") is None and item.get("content_kind") == ("ANSWER" if stored_answer else "GUIDE")
                    and item.get("review_status") == ("NOT_APPLICABLE" if stored_answer else "REVIEWED")
                    and item.get("translation_source_locale") == ("ja-JP" if stored_answer else "ko-KR"), "APP_STORED_TRANSLATION_INVALID")
        summaries.append({key: value for key, value in item.items() if key != "request_id"} | {"request_id_hash": hashed})
    require(len({item["request_id_hash"] for item in summaries}) == len(phases), "DISTINCT_APP_REQUESTS_REQUIRED")
    require(len(events) == len(model_hashes) == calls and {event.get("request_id_hash") for event in events} == model_hashes,
            "EXACT_APP_MODEL_CALLS_REQUIRED")
    require(len({event.get("response_digest") for event in events}) == calls, "UNIQUE_MODEL_RESPONSES_REQUIRED")
    by_hash = {item["request_id_hash"]: item for item in summaries}
    for event in events:
        phase = by_hash[event["request_id_hash"]]["phase"]
        require(event.get("provider_kind") == "OLLAMA_LOCAL" and event.get("model") == model
                and event.get("outcome") == "STRUCTURED_VALIDATED" and event.get("error_code") is None
                and event.get("http_status") == 200
                and event.get("operation") == ("LocalPassageSelection" if phase.startswith("ask-") else "ModelTranslation")
                and re.fullmatch(r"[a-f0-9]{64}", event.get("response_digest", ""))
                and isinstance(event.get("duration_ms"), int) and event["duration_ms"] >= 0
                and all(isinstance(event.get(key), int) and not isinstance(event[key], bool) and event[key] > 0
                        for key in ("prompt_tokens", "output_tokens")), "APP_MODEL_AUDIT_INVALID")
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", type=Path, default=ROOT / ".tooling/android-sdk/platform-tools/adb")
    parser.add_argument("--serial", default="emulator-5584")
    parser.add_argument("--avd", default="CarCue_Pleos21")
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--test-apk", type=Path, required=True)
    parser.add_argument("--audit-file", type=Path, required=True)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8001")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen3:4b")
    scenario = parser.add_mutually_exclusive_group()
    scenario.add_argument("--allow-question-rejection", action="store_true",
                        help="Test guarded draft rejection separately; does not certify generated translation quality")
    scenario.add_argument("--reviewed-manual-only", action="store_true",
                          help="Test default free AI answers and stored reviewed translations; no draft question generation")
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("local-ai-app-%Y%m%dT%H%M%SZ-") + secrets.token_hex(3))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/qa/local-ai-app", help="Parent directory; run ID is appended")
    args = parser.parse_args()
    phases = REVIEWED_PHASES if args.reviewed_manual_only else PHASES
    require(args.serial == "emulator-5584" and args.avd in {"CarCue_Pleos21", "CarCue_Pleos21_LocalAI"}, "DEDICATED_PLEOS_AVD_ONLY")
    require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id)), "INVALID_RUN_ID")
    backend, ollama = loopback(args.backend_url), loopback(args.ollama_url)
    require(backend in {"http://127.0.0.1:8001", "http://localhost:8001"}, "LIVE_BACKEND_PORT_8001_REQUIRED")
    out = (args.output_dir / args.run_id).resolve()
    require(out.is_relative_to((ROOT / "output/qa").resolve()), "IGNORED_QA_OUTPUT_REQUIRED")
    out.mkdir(parents=True, exist_ok=False)
    base = [str(args.adb.resolve()), "-s", args.serial]
    markers = "files/qa/" + args.run_id + "/local-ai"
    report = {"passed": False, "run_id": args.run_id, "validation_scope": "FUNCTIONAL_ONLY",
              "semantic_review_status": "PENDING_INDEPENDENT_REVIEW", "physical_vehicle_tested": False,
              "sdk_identified_vehicle_model": False, "app_sdk_set_called": False,
              "app_session_end_asserted": False,
              "screenshot_method": "Compose Window capture; physical-display visibility not asserted",
              "cleanup_errors": [], "console_fixtures": []}
    report["console_recoveries"] = []
    report["question_rejection_allowed"] = args.allow_question_rejection
    if args.allow_question_rejection:
        report["validation_scope"] = "GUARDED_QUESTION_AND_REVIEWED_MANUAL"
    if args.reviewed_manual_only:
        report["validation_scope"] = "DEFAULT_LOCAL_ANSWERS_AND_STORED_TRANSLATIONS"
    process, lease, audit, records, functional = None, None, None, None, False

    def adb(*parts, timeout=15, check=True):
        return subprocess.run(base + list(parts), text=True, capture_output=True, timeout=timeout, check=check).stdout.strip()

    def app(*parts, check=True):
        return adb("shell", "run-as", PACKAGE, "--user", "10", *parts, check=check)

    def collect(name):
        require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+", name)), "INVALID_ARTIFACT_NAME")
        with (out / name).open("xb") as target:
            subprocess.run(base + ["exec-out", "run-as", PACKAGE, "--user", "10", "cat", markers + "/" + name],
                           stdout=target, stderr=subprocess.PIPE, timeout=30, check=True)

    def park(phase):
        lease.wait_ready(timeout=30)
        for path in ("/vehicle/controls?speed=0&accelerator=0&brake=0", "/vehicle/gear?gear=Park", "/vehicle/body?door_fl=0"):
            lease.request(path, "PUT")
            report["console_fixtures"].append({"phase": phase, "request": path})
        body, controls, gear = [lease.request(path) for path in ("/vehicle/body", "/vehicle/controls", "/vehicle/gear")]
        state = {"front_left": body.get("body", body)["doors"]["front_left"],
                 "speed_kph": controls["speed_kph"], "gear": gear["actual"]["value"]}
        require(state == {"front_left": False, "speed_kph": 0, "gear": "Park"}, "PARK_ZERO_CLOSED_NOT_CONFIRMED")
        report[phase.lower() + "_fixture"] = state

    try:
        for prop, expected in (("ro.kernel.qemu", "1"), ("ro.boot.qemu.avd_name", args.avd),
                               ("ro.build.version.sdk", "34"), ("sys.boot_completed", "1")):
            require(adb("shell", "getprop", prop) == expected, "AVD_BOOT_IDENTITY_MISMATCH")
        require(adb("shell", "am", "get-current-user") == "10", "FOREGROUND_AUTOMOTIVE_USER_10_REQUIRED")
        require(adb("shell", "service", "check", "car_service") == "Service car_service: found",
                "CAR_UX_SERVICE_NOT_REGISTERED")
        report["platform_car_service_registered"] = True
        report.update(serial=args.serial, avd=args.avd, android_api=34, android_user=10,
                      device_timezone=adb("shell", "getprop", "persist.sys.timezone"))
        installed = {}
        with tempfile.TemporaryDirectory(dir=out, prefix="installed-hash-") as temp:
            for package, expected in ((PACKAGE, args.apk.resolve()), (PACKAGE + ".test", args.test_apk.resolve())):
                require(expected.is_file(), "INPUT_APK_NOT_FOUND")
                paths = adb("shell", "pm", "path", "--user", "10", package).splitlines()
                require(len(paths) == 1 and paths[0].startswith("package:"), "SINGLE_INSTALLED_APK_REQUIRED")
                local = Path(temp) / (package + ".apk")
                adb("pull", paths[0].removeprefix("package:"), str(local), timeout=60)
                require(sha(local) == sha(expected), "INSTALLED_APK_DIFFERS_FROM_INPUT")
                installed[package] = sha(local)
        report["installed_apk_sha256"] = installed
        report["input_apk_sha256"] = {"app": sha(args.apk.resolve()), "test": sha(args.test_apk.resolve())}
        require(not app("ls", "-d", markers, check=False), "APP_QA_DIRECTORY_ALREADY_EXISTS")
        service = adb("shell", "dumpsys", "package", "ai.pleos.playground.service.vehicle")
        report["vehicle_service"] = [line.strip() for line in service.splitlines() if "versionName=" in line or "versionCode=" in line][:2]
        with httpx.Client(timeout=httpx.Timeout(15, connect=5), trust_env=False, follow_redirects=False) as client:
            def get(url):
                response = client.get(url)
                require(response.status_code == 200, "PREFLIGHT_HTTP_FAILED")
                return response.json()
            require(get(backend + "/health") == {"status": "ok", "mode": "LIVE"}, "LIVE_BACKEND_REQUIRED")
            models = [model for model in get(ollama + "/api/tags").get("models", []) if model.get("name") == args.model]
            require(len(models) == 1 and re.fullmatch(r"[a-f0-9]{64}", models[0].get("digest", "")), "EXACT_LOCAL_MODEL_REQUIRED")
            report["local_model"] = {"name": args.model, "digest": models[0]["digest"], "ollama_version": get(ollama + "/api/version").get("version")}
            require(isinstance(report["local_model"]["ollama_version"], str)
                    and bool(report["local_model"]["ollama_version"]), "OLLAMA_VERSION_REQUIRED")
        adb("forward", "tcp:8088", "tcp:8088")
        lease = PleosConsoleSession(client="carcue-" + args.run_id).start()
        park("INITIAL")
        audit = AuditCursor(args.audit_file.resolve())
        command = base + ["shell", "am", "instrument", "--user", "10", "-w", "-r", "-e", "validateLocalAi", "true",
                          "-e", "validateGuardedLocalAi", str(args.allow_question_rejection).lower(),
                          "-e", "validateReviewedLocalAi", str(args.reviewed_manual_only).lower(),
                          "-e", "runId", args.run_id, "-e", "expectedLocalModel", args.model, "-e", "class",
                          "com.carcue.app.PleosLocalAiFlowTest#" + (
                              "actualLocalAskAndStoredTranslationsInThreeLanguages" if args.reviewed_manual_only else
                              "actualLocalAskAndGuardedQuestionTranslationInThreeLanguages" if args.allow_question_rejection else
                              "actualLocalAskAndQuestionTranslationInThreeLanguages"),
                          PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner"]
        (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        print("PRECHECK PASS; actual app/local-model instrumentation starting: " + args.run_id, flush=True)
        with (out / "instrumentation.txt").open("x") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 600
            progress_at = time.monotonic() + 30
            while process.poll() is None and time.monotonic() < deadline:
                try:
                    lease.check_heartbeat()
                except ConsoleHeartbeatError:
                    # This AI test issues no fixture writes during instrumentation.
                    # A transient HTTP renewal error may recover while native SDK/UI
                    # assertions continue. Require the same strict DDS flags again
                    # within the existing total host deadline; never fake readiness.
                    recovery = {"before": lease.diagnostics()}
                    report["console_recoveries"].append(recovery)
                    lease.wait_ready(timeout=min(30, max(.01, deadline - time.monotonic())))
                    recovery["after"] = lease.diagnostics()
                if time.monotonic() >= progress_at:
                    print("WAIT actual app instrumentation; heartbeat remains independent", flush=True)
                    progress_at = time.monotonic() + 30
                try:
                    process.wait(timeout=min(.5, max(.01, deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    pass
            require(process.poll() is not None, "APP_INSTRUMENTATION_600S_DEADLINE")
        text = (out / "instrumentation.txt").read_text()
        require(process.returncode == 0 and "OK (1 test)" in text and "FAILURES!!!" not in text, "APP_NATIVE_ASSERTIONS_FAILED")
        collect("done")
        require((out / "done").read_text() == "pass\n", "APP_DONE_MARKER_MISSING")
        collect("responses.jsonl")
        records = [json.loads(line) for line in (out / "responses.jsonl").read_text().splitlines() if line.strip()]
        report["phases"] = validate_runtime(records, audit.events(), args.model, args.allow_question_rejection, args.reviewed_manual_only)
        questions = [item for item in report["phases"] if item["phase"].startswith("question-translation-")]
        report["question_translations_completed"] = sum(item["status"] == "TRANSLATED" for item in questions)
        report["question_translations_rejected"] = sum(item["status"] == "UNAVAILABLE" for item in questions)
        report["generated_translation_quality_passed"] = False  # Functional checks never certify meaning.
        report["app_session_end_asserted"] = True
        for phase in phases:
            collect(phase + ".png")
            require((out / (phase + ".png")).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "INVALID_SCREENSHOT_PNG")
        functional = True
    except Exception as exc:
        code = str(exc) if isinstance(exc, RuntimeError) and re.fullmatch(r"[A-Z0-9_]{1,100}", str(exc)) else "VALIDATION_EXCEPTION"
        report["failure"] = {"type": type(exc).__name__, "code": code}
    finally:
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=10)
            except Exception as exc:
                report["cleanup_errors"].append({"phase": "HOST_PROCESS_WAIT", "type": type(exc).__name__})
                try:
                    process.kill()
                    process.wait(timeout=5)
                except Exception as stop_error:
                    report["cleanup_errors"].append({"phase": "HOST_PROCESS_KILL_WAIT", "type": type(stop_error).__name__})
        if process is not None and not functional:
            try:
                present = set(app("ls", "-1", markers, check=False).splitlines())
                for name in ["responses.jsonl", "done", *[phase + ".png" for phase in phases]]:
                    if name in present and not (out / name).exists():
                        collect(name)
                if (out / "responses.jsonl").is_file():
                    partial = [json.loads(line) for line in (out / "responses.jsonl").read_text().splitlines() if line.strip()]
                    report["partial_phases"] = [{key: value for key, value in row.items() if key != "request_id"}
                                                for row in partial]
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
                report["cleanup_errors"].append({"phase": "CONSOLE_LEASE_CLOSE", "type": type(exc).__name__})
            report["console_session"] = lease.diagnostics()
        if audit is not None:
            try:
                report["audit_events"] = audit.events()
                require(len(report["audit_events"]) == (3 if args.reviewed_manual_only else 6), "FINAL_MODEL_CALL_COUNT_CHANGED")
                if functional:
                    validate_runtime(records, report["audit_events"], args.model,
                                     args.allow_question_rejection, args.reviewed_manual_only)
            except Exception as exc:
                report["cleanup_errors"].append({"phase": "FINAL_AUDIT", "type": type(exc).__name__})
        report["passed"] = bool(functional and not report["cleanup_errors"] and report.get("restored_fixture"))
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["files_sha256"] = {file.name: sha(file) for file in out.iterdir() if file.is_file()}
        (out / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(("PASS functional app checks; semantic review pending: " if report["passed"] else "FAIL app checks: ") + str(out), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
