"""Run real loopback guide/stored-translation checks with an owned, AI-disabled server.

Never starts AVD/Ollama or reuses an existing backend/DB. Session credentials stay
in memory; report hashes and scope only. Run using the backend Python environment.
"""
import argparse
import hashlib
import itertools
import json
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.answer_policy import answer_units
from app.content import Catalog

PROFILE = "ioniq5-ne1-2024-kr"
LOCALES = ("ko-KR", "en", "ja-JP")
IDS = ("ioniq5-ac-charging-check", "ioniq5-seat-mirror-before-driving", "ioniq5-cluster-display-check")
UNSUPPORTED = {
    "ko-KR": ("충전 종료 후 커넥터 분리 방법", "좌석 통풍 사용 방법", "계기판 상향등 의미"),
    "en": ("How do I disconnect the charging connector?", "How do I use DCM mirrors?", "What does the high beam indicator mean?"),
    "ja-JP": ("充電終了後にコネクターを取り外す方法は？", "シートのベンチレーションは？", "ハイビーム表示灯の意味は？"),
}


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def validate(output):
    require(not output.exists(), "NEW_EVIDENCE_DIRECTORY_REQUIRED")
    output.mkdir(parents=True)
    db = output / "sessions.sqlite3"
    catalog = Catalog()
    guides = {(identifier, locale): next(g for g in catalog.published(PROFILE, locale)
              if g["guide_id"] == identifier) for identifier in IDS for locale in LOCALES}
    units = {key: answer_units([guide]) for key, guide in guides.items()}
    require(all(len(value) == 1 for value in units.values()), "COMPLETE_REGISTERED_UNITS_REQUIRED")
    units = {key: value[0] for key, value in units.items()}
    reserved = socket.socket()
    reserved.bind(("127.0.0.1", 0))
    reserved.listen(128)
    port = reserved.getsockname()[1]
    env = {**os.environ, "CARCUE_MODE": "LIVE", "CARCUE_AI_PROVIDER": "DISABLED",
           "OPENAI_API_KEY": "", "OPENAI_MODEL": "", "CARCUE_DB": str(db)}
    report = {"passed": False, "started_at": datetime.now(timezone.utc).isoformat(),
              "transport": "REAL_LOOPBACK_HTTP", "server_mode": "LIVE", "configured_provider": "DISABLED",
              "new_topic_sensor_connected": False, "sdk_called": False, "avd_started": False,
              "actual_model_called": False, "paid_ai_called": False,
              "existing_backend_restarted": False, "existing_database_used": False,
              "guides": [], "translations": [], "unsupported": [], "cleanup_errors": []}
    process = None
    protocol_passed = False
    error = None
    sessions = []
    with (output / "server.log").open("wb") as log, httpx.Client(timeout=5, trust_env=False) as client:
        base = f"http://127.0.0.1:{port}"
        try:
            try:
                process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", str(ROOT / "backend"),
                    "--fd", str(reserved.fileno()), "--no-access-log"],
                    cwd=ROOT, env=env, pass_fds=(reserved.fileno(),), stdout=log, stderr=subprocess.STDOUT)
            finally:
                reserved.close()  # The child inherits the bound socket; no release/rebind ownership race.
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                require(process.poll() is None, "OWNED_SERVER_EXITED_BEFORE_READY")
                try:
                    if client.get(base + "/health").json() == {"status": "ok", "mode": "LIVE"}:
                        break
                except (httpx.HTTPError, ValueError):
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("OWNED_SERVER_READY_TIMEOUT")
            for locale in LOCALES:
                response = client.get(base + "/v1/guides", params={"profile_id": PROFILE, "locale": locale})
                response.raise_for_status()
                require({g["guide_id"] for g in response.json()} == set(IDS) | {"ioniq5-door-open-check"}, "EXACT_PUBLISHED_CORPUS_REQUIRED")
                for identifier in IDS:
                    response = client.get(base + "/v1/guides/" + identifier,
                        params={"profile_id": PROFILE, "locale": locale})
                    response.raise_for_status()
                    require(response.json() == guides[identifier, locale], "HTTP_GUIDE_DIFFERS_FROM_REVIEWED_RECORD")
                    report["guides"].append({"guide_id": identifier, "locale": locale,
                        "bundle_sha256": digest(units[identifier, locale]["text"]), "full_bundle_characters": len(units[identifier, locale]["text"])})
                response = client.post(base + "/v1/sessions", json={"profile_id": PROFILE, "locale": locale})
                response.raise_for_status()
                session = response.json()
                sessions.append((session["session_id"], session["token"]))
                sid, token = sessions[-1]
                headers = {"Authorization": "Bearer " + token}
                for identifier, target, kind in itertools.product(IDS, [tag for tag in LOCALES if tag != locale], ("GUIDE", "ANSWER")):
                    source = guides[identifier, locale]["body"] if kind == "GUIDE" else units[identifier, locale]["text"]
                    expected = guides[identifier, target]["body"] if kind == "GUIDE" else units[identifier, target]["text"]
                    response = client.post(base + "/v1/translate", headers=headers, json={
                        "request_id": uuid4().hex, "session_id": sid, "profile_id": PROFILE,
                        "source_locale": locale, "target_locale": target, "content_kind": kind,
                        "guide_id": identifier, "text": source})
                    response.raise_for_status()
                    result = response.json()
                    require(result["status"] == "TRANSLATED" and result["ai_provider"] == "STORED_GUIDE"
                            and result["ai_model"] is None and result["translated_text"] == expected
                            and result["source_locale"] == locale and result["target_locale"] == target,
                            "EXACT_STORED_TRANSLATION_REQUIRED")
                    report["translations"].append({"guide_id": identifier, "source_locale": locale,
                        "target_locale": target, "content_kind": kind, "sha256": digest(expected), "ai_provider": "STORED_GUIDE"})
                for question in UNSUPPORTED[locale]:
                    response = client.post(base + "/v1/ask", headers=headers, json={
                        "request_id": uuid4().hex, "session_id": sid, "profile_id": PROFILE, "locale": locale,
                        "question": question, "guide_context": {}, "vehicle_context": []})
                    response.raise_for_status()
                    result = response.json()
                    require(result["status"] == "NO_RELIABLE_SOURCE" and result["ai_provider"] == "NOT_CALLED"
                            and not result["citations"], "OUTSIDE_SCOPE_MUST_NOT_CALL_PROVIDER")
                    report["unsupported"].append({"locale": locale, "question_sha256": digest(question), "provider_called": False})
            protocol_passed = True
        except Exception as exc:
            error = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        finally:
            for sid, token in sessions:
                try:
                    response = client.delete(base + "/v1/sessions/" + sid, headers={"Authorization": "Bearer " + token})
                    require(response.status_code == 200 and response.json().get("status") == "DELETED", "SESSION_DELETE_NOT_CONFIRMED")
                except Exception:
                    report["cleanup_errors"].append("SESSION_DELETE_NOT_CONFIRMED")
            if process is not None:
                process.terminate()  # Only the process created above; never a pre-existing backend.
                try:
                    report["owned_server_exit_code"] = process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    report["owned_server_exit_code"] = process.wait(timeout=5)
                    report["cleanup_errors"].append("OWNED_SERVER_REQUIRED_KILL")
    if db.exists():
        with sqlite3.connect(db) as connection:
            report["final_database_counts"] = {table: connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                                               for table in ("sessions", "results", "history")}
    # Pinned Uvicorn 0.34 re-raises SIGTERM after its graceful shutdown. Keep the
    # observed exit code and require the actual shutdown log, rather than calling -15 a crash.
    report["owned_server_shutdown_confirmed"] = report.get("owned_server_exit_code") in (0, -signal.SIGTERM) and "Application shutdown complete." in (output / "server.log").read_text()
    report["passed"] = protocol_passed and not report["cleanup_errors"] and report["owned_server_shutdown_confirmed"] and report.get("final_database_counts") == {"sessions": 0, "results": 0, "history": 0}
    report["guide_count"] = len(report["guides"])
    report["stored_translation_count"] = len(report["translations"])
    report["unsupported_count"] = len(report["unsupported"])
    report["error"] = error
    (output / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("passed", "guide_count", "stored_translation_count", "unsupported_count", "error")}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(validate(args.output_dir.resolve()))
