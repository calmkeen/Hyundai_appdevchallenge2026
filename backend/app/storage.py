"""Short-lived sessions; no vehicle raw data, request bodies or credentials in logs."""
import hashlib
import hmac
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager


class Store:
    def __init__(self, path: str, ttl_minutes: int = 120):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.execute("PRAGMA secure_delete=ON")
        self.lock = threading.RLock()
        self.ttl = ttl_minutes * 60
        with self.transaction() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, profile TEXT NOT NULL,
              locale TEXT NOT NULL, expires REAL NOT NULL, requests INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS results (
              session TEXT, request TEXT, fingerprint TEXT, response TEXT,
              PRIMARY KEY(session,request));
            CREATE TABLE IF NOT EXISTS history (
              session TEXT, position INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT);
            """)

    @contextmanager
    def transaction(self):
        with self.lock, self.connection:
            yield self.connection

    def purge(self):
        with self.transaction() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM sessions WHERE expires<=?", (time.time(),))]
            for session in ids:
                self.delete(session)

    def create(self, profile: str, locale: str):
        self.purge()
        session, token = secrets.token_urlsafe(24), secrets.token_urlsafe(32)
        expires = time.time() + self.ttl
        with self.transaction() as db:
            db.execute("INSERT INTO sessions(id,token_hash,profile,locale,expires) VALUES(?,?,?,?,?)",
                       (session, hashlib.sha256(token.encode()).hexdigest(), profile, locale, expires))
        return session, token, expires

    def authorized(self, session: str, token: str):
        self.purge()
        with self.transaction() as db:
            row = db.execute("SELECT token_hash,profile,locale,expires,requests FROM sessions WHERE id=?", (session,)).fetchone()
        if not row or not hmac.compare_digest(row[0], hashlib.sha256(token.encode()).hexdigest()):
            return None
        return row

    def delete(self, session: str):
        with self.transaction() as db:
            for table in ("results", "history", "sessions"):
                column = "id" if table == "sessions" else "session"
                db.execute(f"DELETE FROM {table} WHERE {column}=?", (session,))

    def context(self, session: str):
        with self.transaction() as db:
            return list(reversed(db.execute("SELECT question,answer FROM history WHERE session=? ORDER BY position DESC LIMIT 3", (session,)).fetchall()))
