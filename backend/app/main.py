import asyncio
import hashlib
import json
import os
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from .content import Catalog
from .models import AskRequest, SessionRequest, TranslateRequest
from .provider import Provider
from .storage import Store


def timestamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def create_app(db_path=None, catalog=None, provider=None, mode=None):
    app = FastAPI(title="CarCue", version="0.1.0")
    store = Store(db_path or os.getenv("CARCUE_DB", "carcue.sqlite3"), int(os.getenv("CARCUE_SESSION_MINUTES", "120")))
    catalog = catalog or Catalog()
    provider = provider or Provider()
    mode = mode or os.getenv("CARCUE_MODE", "MOCK")
    if mode not in ("LIVE", "MOCK"):
        raise ValueError("CARCUE_MODE must be LIVE or MOCK")
    locks, quota = {}, []
    app.state.store, app.state.catalog = store, catalog

    async def purge_loop():
        while True:
            await asyncio.sleep(60)
            store.purge()

    @asynccontextmanager
    async def lifespan(_):
        task = asyncio.create_task(purge_loop())
        yield
        task.cancel()
        store.connection.close()

    app.router.lifespan_context = lifespan

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def authorize(session, authorization, profile=None):
        token = authorization.removeprefix("Bearer ") if authorization and authorization.startswith("Bearer ") else ""
        row = store.authorized(session, token)
        if not row:
            raise HTTPException(401, "SESSION_INVALID_OR_EXPIRED")
        if profile is not None and row[1] != profile:
            raise HTTPException(409, "PROFILE_MISMATCH")
        return row

    def validate_locale(locale):
        if not catalog.locale(locale):
            raise HTTPException(422, "LOCALE_NOT_REGISTERED")

    def processing_locale(locale):
        validate_locale(locale)
        if catalog.locale(locale)["ui_status"] == "PLANNED":
            raise HTTPException(422, "LOCALE_PLANNED_CHOOSE_EXPLICIT_FALLBACK")

    def cached(session, request_id, fingerprint):
        with store.transaction() as db:
            row = db.execute("SELECT fingerprint,response FROM results WHERE session=? AND request=?", (session, request_id)).fetchone()
        if row:
            if row[0] != fingerprint:
                raise HTTPException(409, "REQUEST_ID_REUSED_WITH_DIFFERENT_INPUT")
            return json.loads(row[1])

    def reserve(session):
        now = time.time()
        quota[:] = [t for t in quota if t > now - 60]
        with store.transaction() as db:
            count = db.execute("SELECT requests FROM sessions WHERE id=?", (session,)).fetchone()
            if not count:
                raise HTTPException(401, "SESSION_ENDED")
            if count[0] >= int(os.getenv("CARCUE_SESSION_REQUEST_LIMIT", "30")) or len(quota) >= int(os.getenv("CARCUE_GLOBAL_REQUEST_LIMIT", "200")):
                raise HTTPException(429, "REQUEST_LIMIT", headers={"Retry-After": "60"})
            db.execute("UPDATE sessions SET requests=requests+1 WHERE id=?", (session,))
        quota.append(now)

    def save(session, request_id, fingerprint, result, question=None):
        # An end-session DELETE may arrive while awaiting a provider response.
        with store.transaction() as db:
            if not db.execute("SELECT id FROM sessions WHERE id=? AND expires>?", (session, time.time())).fetchone():
                raise HTTPException(401, "SESSION_ENDED")
            db.execute("INSERT INTO results VALUES(?,?,?,?)", (session, request_id, fingerprint, json.dumps(result, ensure_ascii=False)))
            if question:
                db.execute("INSERT INTO history(session,question,answer) VALUES(?,?,?)", (session, question, result["answer"]))
                db.execute("DELETE FROM history WHERE session=? AND position NOT IN (SELECT position FROM history WHERE session=? ORDER BY position DESC LIMIT 3)", (session, session))

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": mode}

    @app.get("/v1/vehicle-profiles")
    def profiles():
        return [p for p in catalog.profiles if mode == "MOCK" or p["verification_status"] == "VERIFIED"]

    @app.get("/v1/vehicle-profiles/{profile_id}")
    def profile(profile_id: str):
        p = catalog.profile(profile_id)
        if not p or (mode == "LIVE" and p["verification_status"] != "VERIFIED"):
            raise HTTPException(404, "PROFILE_NOT_FOUND")
        return p

    @app.get("/v1/locales")
    def locales():
        return catalog.locales

    @app.get("/v1/guides")
    def guides(profile_id: str, locale: str, topic: str | None = None, q: str = ""):
        profile(profile_id)
        validate_locale(locale)
        return catalog.search(profile_id, locale, q[:200], topic)

    @app.get("/v1/guides/{guide_id}")
    def guide(guide_id: str, profile_id: str, locale: str):
        profile(profile_id)
        validate_locale(locale)
        matches = [g for g in catalog.published(profile_id, locale) if g["guide_id"] == guide_id]
        if not matches:
            raise HTTPException(404, "REVIEWED_GUIDE_NOT_FOUND")
        return matches[0]

    @app.post("/v1/sessions", status_code=201)
    def session(request: SessionRequest):
        profile(request.profile_id)
        validate_locale(request.locale)
        sid, token, expires = store.create(request.profile_id, request.locale)
        return {"session_id": sid, "token": token, "profile_id": request.profile_id, "locale": request.locale,
                "expires_at": timestamp(expires), "retention_minutes": store.ttl // 60, "mode": mode}

    @app.delete("/v1/sessions/{session_id}")
    def end(session_id: str, authorization: str | None = Header(default=None)):
        authorize(session_id, authorization)
        store.delete(session_id)
        return {"status": "DELETED"}

    @app.post("/v1/ask")
    async def ask(request: AskRequest, authorization: str | None = Header(default=None)):
        authorize(request.session_id, authorization, request.profile_id)
        processing_locale(request.locale)
        fingerprint = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        lock = locks.setdefault((request.session_id, request.request_id), asyncio.Lock())
        async with lock:
            authorize(request.session_id, authorization, request.profile_id)
            old = cached(request.session_id, request.request_id, fingerprint)
            if old:
                return old
            reserve(request.session_id)
            sources = catalog.retrieve(request)
            result = {"request_id": request.request_id, "status": "NO_RELIABLE_SOURCE", "locale": request.locale,
                "answer": "이 차량의 검수된 자료에서 확인하지 못했어요. 차량 정보를 다시 확인해 주세요." if request.locale.startswith("ko") else "No reviewed source is available for this vehicle. Please confirm the vehicle profile.",
                "citations": [], "follow_up_question": None,
                "actions": [{"kind": "SELECT_PROFILE", "target_id": None}], "mode": mode}
            # MOCK never calls OpenAI and never synthesizes a supposedly sourced answer.
            if sources and mode == "LIVE":
                try:
                    output = await provider.ask(request, sources, store.context(request.session_id))
                    index = {s["source_id"]: (g, s) for g in sources for s in g["sources"]}
                    if any(s not in index for s in output.source_ids):
                        raise ValueError("CITATION_OUTSIDE_RETRIEVAL")
                    if output.status == "ANSWERED" and not output.source_ids:
                        raise ValueError("ANSWER_WITHOUT_CITATION")
                    if output.status == "ANSWERED":
                        quoted = output.answer.strip()
                        cited_guides = [index[sid][0] for sid in output.source_ids]
                        passages = [g["body"] for g in cited_guides] + [step["body"] for g in cited_guides for step in g["steps"]]
                        if not quoted or not any(quoted in passage for passage in passages):
                            raise ValueError("UNSUPPORTED_PARAPHRASE")
                    # Conservative semantic filter; it is not a substitute for human evaluations.
                    if re.search(r"safe to drive|you can drive|고장 원인은|운전해도|주행해도|안전합니다", output.answer, re.I):
                        raise ValueError("UNSAFE_CLAIM")
                    result.update(status=output.status, answer=output.answer, follow_up_question=output.follow_up_question, actions=[])
                    if output.status == "NEED_MORE_INFO" and not output.follow_up_question:
                        raise ValueError("MISSING_FOLLOW_UP")
                    if output.status == "ANSWERED":
                        for sid in dict.fromkeys(output.source_ids):
                            g, s = index[sid]
                            result["citations"].append({"source_id": sid, "guide_id": g["guide_id"], "profile_id": request.profile_id,
                                "manual_set_id": g["manual_set_id"], "source_version": g["source_version"],
                                "title": s["title"], "url": s["url"], "section": s["section"]})
                        result["actions"] = [{"kind": "OPEN_GUIDE", "target_id": result["citations"][0]["guide_id"]},
                                             {"kind": "REFRESH_STATUS", "target_id": "door.position"}]
                except Exception:
                    # Never expose provider details, credentials or a partial unvalidated answer.
                    result.update(status="TEMPORARILY_UNAVAILABLE", answer="지금 답변을 확인할 수 없어요. 저장된 안내를 이용해 주세요." if request.locale.startswith("ko") else "The answer could not be verified. Please use the saved guides.", citations=[], actions=[], follow_up_question=None)
            save(request.session_id, request.request_id, fingerprint, result, request.question)
            return result

    @app.post("/v1/translate")
    async def translate(request: TranslateRequest, authorization: str | None = Header(default=None)):
        authorize(request.session_id, authorization, request.profile_id)
        processing_locale(request.target_locale)
        if request.source_locale != "auto":
            validate_locale(request.source_locale)
        fingerprint = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        lock = locks.setdefault((request.session_id, request.request_id), asyncio.Lock())
        async with lock:
            authorize(request.session_id, authorization, request.profile_id)
            old = cached(request.session_id, request.request_id, fingerprint)
            if old:
                return old
            reserve(request.session_id)
            result = {"request_id": request.request_id, "original_text": request.text,
                "source_locale": request.source_locale, "target_locale": request.target_locale,
                "translated_text": None, "glossary_version": None, "review_status": "UNREVIEWED",
                "status": "TEMPORARILY_UNAVAILABLE", "mode": mode}
            if request.content_kind == "GUIDE":
                match = next((g for g in catalog.published(request.profile_id, request.target_locale)
                              if g["guide_id"] == request.guide_id), None)
                original = next((g for g in catalog.published(request.profile_id)
                                if g["guide_id"] == request.guide_id and g["body"] == request.text
                                and (request.source_locale == "auto" or request.source_locale == g["locale"])), None)
                if match and original and match["source_version"] == original["source_version"] and match["glossary_version"] == original["glossary_version"]:
                    result.update(status="TRANSLATED", translated_text=match["body"], review_status=match["translation_review_status"], glossary_version=match["glossary_version"])
            elif mode == "LIVE":
                try:
                    output = await provider.translate(request)
                    # Number/unit mismatches fail closed; negation/meaning still need human review.
                    tokens = lambda text: re.findall(r"\d+(?:[.,]\d+)?|%|kPa|PSI|kWh|km|°C", text)
                    if sorted(tokens(request.text)) != sorted(tokens(output.translated_text)):
                        raise ValueError("TRANSLATION_NUMBERS_CHANGED")
                    result.update(status="TRANSLATED", source_locale=output.source_locale, translated_text=output.translated_text)
                except Exception:
                    pass
            save(request.session_id, request.request_id, fingerprint, result)
            return result

    return app


app = create_app()
