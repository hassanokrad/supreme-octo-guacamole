import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def load_env():
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class AppConfig:
    def __init__(self):
        load_env()
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8080"))
        self.db_path = ROOT / os.getenv("DB_PATH", "data/app.db")
        self.admin_token = os.getenv("ADMIN_TOKEN", "change-me")
        self.site_title = os.getenv("SITE_TITLE", "Smart Deals Daily")
        self.seed_path = ROOT / "data/offers_seed.json"


class Store:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS offers (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    affiliate_url TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    offer_id TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def upsert_offers(self, offers):
        with self._lock, self._conn() as conn:
            now = utc_now()
            for offer in offers:
                conn.execute(
                    """
                    INSERT INTO offers (id, title, description, affiliate_url, active, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      title=excluded.title,
                      description=excluded.description,
                      affiliate_url=excluded.affiliate_url,
                      active=1,
                      updated_at=excluded.updated_at
                    """,
                    (offer["id"], offer["title"], offer["description"], offer["affiliate_url"], now),
                )

    def list_offers(self):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, title, description, affiliate_url FROM offers WHERE active=1 ORDER BY updated_at DESC"
            ).fetchall()
        return [
            {"id": r[0], "title": r[1], "description": r[2], "affiliate_url": r[3]}
            for r in rows
        ]

    def get_offer(self, offer_id):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, title, description, affiliate_url FROM offers WHERE id=? AND active=1",
                (offer_id,),
            ).fetchone()
        if not row:
            return None
        return {"id": row[0], "title": row[1], "description": row[2], "affiliate_url": row[3]}

    def log_event(self, event_type, offer_id=None):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO events (event_type, offer_id, created_at) VALUES (?, ?, ?)",
                (event_type, offer_id, utc_now()),
            )

    def report(self):
        with self._conn() as conn:
            views = conn.execute("SELECT COUNT(*) FROM events WHERE event_type='page_view'").fetchone()[0]
            clicks = conn.execute("SELECT COUNT(*) FROM events WHERE event_type='offer_click'").fetchone()[0]
        ctr = (clicks / views * 100.0) if views else 0.0
        return {"views": views, "clicks": clicks, "ctr_percent": round(ctr, 2)}


class RevenueHandler(BaseHTTPRequestHandler):
    store = None
    config = None

    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, status, html):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _is_authorized(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        return params.get("token", [""])[0] == self.config.admin_token

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self._json(HTTPStatus.OK, {"status": "ok"})

        if parsed.path == "/":
            self.store.log_event("page_view")
            offers = self.store.list_offers()
            cards = "".join(
                f"<article><h3>{o['title']}</h3><p>{o['description']}</p><a href='/go/{o['id']}'>View Deal</a></article>"
                for o in offers
            )
            html = f"""
                <html><head><title>{self.config.site_title}</title>
                <style>body{{font-family:Arial;max-width:900px;margin:2rem auto;padding:1rem;}}
                article{{border:1px solid #ddd;padding:1rem;border-radius:8px;margin-bottom:1rem;}}
                a{{display:inline-block;background:#111;color:#fff;padding:.5rem .75rem;border-radius:6px;text-decoration:none;}}</style>
                </head><body>
                <h1>{self.config.site_title}</h1>
                <p>Automated offer recommendations updated daily.</p>
                {cards or '<p>No offers yet. Trigger automation refresh.</p>'}
                </body></html>
            """
            return self._html(HTTPStatus.OK, html)

        if parsed.path.startswith("/go/"):
            offer_id = parsed.path.replace("/go/", "", 1)
            offer = self.store.get_offer(offer_id)
            if not offer:
                return self._json(HTTPStatus.NOT_FOUND, {"error": "offer_not_found"})
            self.store.log_event("offer_click", offer_id)
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", offer["affiliate_url"])
            self.end_headers()
            return

        if parsed.path == "/admin/report":
            if not self._is_authorized():
                return self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return self._json(HTTPStatus.OK, self.store.report())

        return self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/automation/refresh":
            if not self._is_authorized():
                return self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            offers = json.loads(self.config.seed_path.read_text())
            self.store.upsert_offers(offers)
            return self._json(HTTPStatus.OK, {"status": "refreshed", "offers": len(offers)})

        return self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})


def build_server(config=None):
    config = config or AppConfig()
    store = Store(config.db_path)
    store.init_db()
    if not store.list_offers() and config.seed_path.exists():
        store.upsert_offers(json.loads(config.seed_path.read_text()))

    RevenueHandler.store = store
    RevenueHandler.config = config
    return ThreadingHTTPServer((config.host, config.port), RevenueHandler)


def main():
    server = build_server()
    print(f"Server running on http://{AppConfig().host}:{AppConfig().port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
