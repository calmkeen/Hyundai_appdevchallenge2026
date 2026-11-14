"""Real free-local-model regression for the registered IONIQ 5 closing cautions.

Nine ASK combinations use no fabricated SDK readings. Translations reuse reviewed
content; QUESTION generation is checked as disabled. Tokens stay in memory, and a
new evidence directory preserves every attempt. No paid or remote model fallback.
"""
import argparse
import hashlib
import json
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "ioniq5-ne1-2024-kr"
GUIDE = "ioniq5-door-open-check"
VERSION = "NE1-2024-KR-ko_KR-D202406100040-20240722"
LOCALES = ("ko-KR", "en", "ja-JP")
QUESTIONS = {
    "ko-KR": "문을 닫기 전에 무엇을 확인해야 하나요?",
    "en": "What should I check before closing the indicated door?",
    "ja-JP": "表示されたドアを閉める前に何を確認しますか？",
}
SOURCE_URLS = {
    "hyundai-ne1-2024-kr-door-open-warning": "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/idff13cd5359c.html",
    "hyundai-ne1-2024-kr-door-pinch-caution": "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id0d6d99a8d21.html",
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def published():
    result = {}
    for file in sorted((ROOT / "content/guides").glob("*.json")):
        guide = json.loads(file.read_text())
        if guide.get("guide_id") == GUIDE and guide.get("lifecycle") == "PUBLISHED":
            require(guide["locale"] not in result, "Ambiguous reviewed locale")
            require(guide["profile_ids"] == [PROFILE] and guide["source_version"] == VERSION, "Reviewed scope mismatch")
            result[guide["locale"]] = guide
    require(set(result) == set(LOCALES), "Three reviewed languages required")
    return result


def bundle(guide):
    # Acceptance derives every required manual part independently of backend answer_policy.
    require([s["step_id"] for s in guide["steps"]] == ["check-pinch-area", "check-closure-display"], "Required step sequence missing")
    parts = [guide["body"]]
    for step in guide["steps"]:
        require(step["official_cautions"], "A mandatory caution cannot be empty")
        parts.extend([step["body"], *step["official_cautions"]])
    return "\n".join(parts), parts


def verify_text(text, guide):
    expected, parts = bundle(guide)
    require(text == expected, "Answer omitted/rewrote a reviewed body, caution, negation or sequence")
    position = 0
    for part in parts:
        found = text.find(part, position)
        require(found >= position, "Mandatory manual part missing or out of order")
        position = found + len(part)
    return {"body_and_step_parts": len(parts), "all_step_bodies": True,
            "all_official_cautions": True, "registered_order_preserved": True,
            "answer_sha256": digest(text.encode()), "characters": len(text)}


def validate_model_events(events, request_hashes, model):
    """Pure audit validation, reusable for preserved actual-run evidence.

    Does not invoke a provider. Usage and response digests establish the expected
    recorded local-model calls; this is distinct from independent meaning review.
    """
    expected = set(request_hashes)
    required = {"provider_kind", "operation", "request_id_hash", "model", "outcome", "error_code",
                "http_status", "duration_ms", "prompt_tokens", "output_tokens", "response_digest"}
    allowed = required | {"response_id"}
    require(isinstance(events, list) and len(events) == len(expected) == 9
            and all(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) for value in expected),
            "Exactly nine actual model request hashes required")
    require(all(isinstance(event, dict) and required <= set(event) <= allowed
                and all(value is None or isinstance(value, (str, int, float, bool)) for value in event.values())
                for event in events), "Unsanitized or incomplete model audit")
    require({event["request_id_hash"] for event in events} == expected, "Model audit request correlation failed")
    require(len({event["response_digest"] for event in events}) == 9, "Distinct model response digests required")
    for event in events:
        require(event["provider_kind"] == "OLLAMA_LOCAL" and event["model"] == model
                and event["http_status"] == 200 and event["error_code"] is None
                and event["outcome"] == "STRUCTURED_VALIDATED" and event["operation"] == "LocalPassageSelection"
                and isinstance(event["response_digest"], str) and re.fullmatch(r"[a-f0-9]{64}", event["response_digest"])
                and isinstance(event["duration_ms"], int) and not isinstance(event["duration_ms"], bool)
                and event["duration_ms"] >= 0
                and all(isinstance(event[key], int) and not isinstance(event[key], bool) and event[key] > 0
                        for key in ("prompt_tokens", "output_tokens")), "Invalid actual model provenance or usage")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--audit-file", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8001")
    parser.add_argument("--model", default="qwen3:4b")
    args = parser.parse_args()
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id), "Invalid run ID")
    require(args.backend_url in {"http://127.0.0.1:8001", "http://localhost:8001"}, "Dedicated loopback LIVE backend only")
    for path in (args.audit_file, args.database):
        require(path.resolve().is_relative_to(ROOT / "output/qa") and path.is_file(), "Existing ignored QA runtime evidence required")
    out = ROOT / "output/qa/answer-cautions-20261114" / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    guides = published()
    before = len(args.audit_file.read_text().splitlines())
    report = {"passed": False, "run_id": args.run_id, "started_at": datetime.now(timezone.utc).isoformat(),
              "provider": "OLLAMA_LOCAL", "sdk_tested": False, "vehicle_context_supplied": False,
              "physical_vehicle_tested": False, "paid_ai_called": False, "generated_question_translation_called": False,
              "asks": [], "translations": [], "legacy_rejections": [], "unsupported": [], "question_deferral": [],
              "duplicate_replay": [], "cleanup": [], "semantic_review_status": "PENDING_INDEPENDENT_REVIEW"}
    sessions = []
    request_hashes = set()

    def audit():
        return [json.loads(line) for line in args.audit_file.read_text().splitlines()[before:]]

    with httpx.Client(base_url=args.backend_url, timeout=httpx.Timeout(150, connect=5), trust_env=False) as client:
        def api(path, data=None, session=None, method="POST"):
            headers = {"Authorization": "Bearer " + session["token"]} if session else {}
            response = client.request(method, path, json=data, headers=headers)
            require(response.status_code == (201 if path == "/v1/sessions" and method == "POST" else 200), f"HTTP {response.status_code} at {path.split('/')[2] if len(path.split('/')) > 2 else path}")
            return response.json()

        def payload(session, locale):
            return {"request_id": str(uuid.uuid4()), "session_id": session["session_id"], "profile_id": PROFILE, "locale": locale}

        try:
            require(api("/health", method="GET") == {"status": "ok", "mode": "LIVE"}, "LIVE backend required")
            answers, by_locale = {}, {}
            for locale in LOCALES:
                remote = client.get("/v1/guides", params={"profile_id": PROFILE, "locale": locale})
                require(remote.status_code == 200 and remote.json() == [guides[locale]], "LIVE guide differs from reviewed shipped metadata")
                session = api("/v1/sessions", {"profile_id": PROFILE, "locale": locale})
                sessions.append(session); by_locale[locale] = session
                for step in ("check-pinch-area", "check-closure-display", None):
                    context = {"guide_id": GUIDE, "step_id": step} if step else {"guide_id": None, "step_id": None}
                    data = {**payload(session, locale), "question": QUESTIONS[locale], "guide_context": context, "vehicle_context": []}
                    started = time.monotonic(); response = api("/v1/ask", data, session)
                    require(response.get("status") == "ANSWERED" and response.get("mode") == "LIVE" and response.get("locale") == locale,
                            "Reviewed closing question was not answered in the requested locale")
                    require(response.get("ai_provider") == "OLLAMA_LOCAL" and response.get("ai_model") == args.model, "Real local model provenance required")
                    result = verify_text(response["answer"], guides[locale])
                    citations = response["citations"]
                    require([x["source_id"] for x in citations] == list(SOURCE_URLS), "Exactly both registered sources required")
                    for citation in citations:
                        require(citation["guide_id"] == GUIDE and citation["profile_id"] == PROFILE
                                and citation["manual_set_id"] == guides[locale]["manual_set_id"] and citation["source_version"] == VERSION
                                and citation["url"] == SOURCE_URLS[citation["source_id"]], "Citation scope or URL mismatch")
                    hashed = digest(data["request_id"].encode()); request_hashes.add(hashed)
                    case = {"locale": locale, "step_context": step, "question": QUESTIONS[locale], "request_id_hash": hashed,
                            "elapsed_ms": round((time.monotonic()-started)*1000), "response": response, "checks": result}
                    case["response"] = {k: v for k, v in response.items() if k != "request_id"}
                    report["asks"].append(case); answers[locale] = response["answer"]
                    count = len(audit()); replay = api("/v1/ask", data, session)
                    require(replay == response and len(audit()) == count, "Idempotent answer replay changed or called a model")
                    report["duplicate_replay"].append({"locale": locale, "step_context": step, "additional_model_calls": 0})
                    print("ASK PASS " + locale + "/" + (step or "no-context"), flush=True)

            for source in LOCALES:
                session = by_locale[source]
                for target in LOCALES:
                    if source == target:
                        continue
                    count = len(audit())
                    data = {**payload(session, source), "source_locale": source, "target_locale": target, "text": answers[source], "content_kind": "ANSWER", "guide_id": GUIDE}
                    data.pop("locale")
                    translated = api("/v1/translate", data, session)
                    require(translated["status"] == "TRANSLATED" and translated["ai_provider"] == "STORED_GUIDE"
                            and translated["review_status"] == ("NOT_APPLICABLE" if target == "ko-KR" else "REVIEWED")
                            and translated["source_locale"] == source and translated["target_locale"] == target, "Stored bundle translation required")
                    verify_text(translated["translated_text"], guides[target])
                    require(len(audit()) == count, "Stored translation invoked a model")
                    report["translations"].append({"kind": "ANSWER", "source": source, "target": target, "text": translated["translated_text"], "additional_model_calls": 0})
                target = LOCALES[(LOCALES.index(source)+1) % len(LOCALES)]
                count = len(audit())
                base = {"session_id": session["session_id"], "profile_id": PROFILE, "source_locale": source, "target_locale": target, "guide_id": GUIDE}
                translated = api("/v1/translate", {**base, "request_id": str(uuid.uuid4()), "text": guides[source]["body"], "content_kind": "GUIDE"}, session)
                require(translated["status"] == "TRANSLATED" and translated["translated_text"] == guides[target]["body"]
                        and translated["ai_provider"] == "STORED_GUIDE" and len(audit()) == count, "Original GUIDE translation regressed")
                report["translations"].append({"kind": "GUIDE", "source": source, "target": target, "additional_model_calls": 0})
                legacy = [guides[source]["body"]] + ["\n".join([s["body"], *s["official_cautions"]]) for s in guides[source]["steps"]]
                for index, text in enumerate(legacy):
                    count = len(audit())
                    rejected = api("/v1/translate", {**base, "request_id": str(uuid.uuid4()), "text": text, "content_kind": "ANSWER"}, session)
                    require(rejected["status"] == "TEMPORARILY_UNAVAILABLE" and rejected["translated_text"] is None
                            and rejected["ai_provider"] == "NOT_CALLED" and len(audit()) == count, "Legacy incomplete ANSWER translation was accepted")
                    report["legacy_rejections"].append({"locale": source, "legacy_unit": index, "additional_model_calls": 0})
                disabled = api("/v1/translate", {**base, "request_id": str(uuid.uuid4()), "text": QUESTIONS[source], "content_kind": "QUESTION"}, session)
                require(disabled["status"] == "TEMPORARILY_UNAVAILABLE" and disabled["ai_provider"] == "NOT_CALLED" and len(audit()) == count,
                        "Generated question translation must remain disabled")
                report["question_deferral"].append({"locale": source, "additional_model_calls": 0})

            for locale, question in [("ko-KR", "문이 열려 있을 때 충전해도 되나요?"), ("en", "How do I replace brake fluid?"), ("ja-JP", "ドアを開けたまま充電できますか？")]:
                count = len(audit()); session = by_locale[locale]
                response = api("/v1/ask", {**payload(session, locale), "question": question,
                    "guide_context": {"guide_id": GUIDE, "step_id": "check-closure-display"}, "vehicle_context": []}, session)
                require(response["status"] == "NO_RELIABLE_SOURCE" and response["citations"] == []
                        and response["ai_provider"] == "NOT_CALLED" and len(audit()) == count, "Unsupported topic borrowed the closing bundle")
                report["unsupported"].append({"locale": locale, "question": question, "additional_model_calls": 0})

            events = audit()
            validate_model_events(events, request_hashes, args.model)
            report["model_events"] = events
            report["passed"] = True
        except BaseException as error:
            report["error_type"] = type(error).__name__
            report["error"] = str(error)[:200]
            raise
        finally:
            for session in sessions:
                try:
                    deleted = api("/v1/sessions/" + session["session_id"], session=session, method="DELETE")
                    require(deleted == {"status": "DELETED"}, "Deletion was not confirmed")
                    report["cleanup"].append({"deleted": True})
                except Exception as error:
                    report["passed"] = False
                    report["cleanup"].append({"deleted": False, "error_type": type(error).__name__})
            con = sqlite3.connect("file:" + str(args.database.resolve()) + "?mode=ro", uri=True)
            report["database_counts"] = {table: con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] for table in ("sessions", "results", "history")}; con.close()
            if any(report["database_counts"].values()): report["passed"] = False
            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            (out / "validation-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    require(report["passed"], "Cleanup or validation failed; evidence preserved")
    print("PASS: nine actual ASK cases, six caution-preserving ANSWER translations, no paid calls; SDK not asserted", flush=True)


if __name__ == "__main__":
    main()
