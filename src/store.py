import json
import sqlite3
import time
from pathlib import Path

from src.config import settings


def _db_path() -> Path:
    path = Path(settings.database_url)
    if path.parent.as_posix() not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> int:
    return int(time.time())


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_metrics (
                metric_name TEXT PRIMARY KEY,
                metric_value INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                stripe_customer_id TEXT,
                is_paid INTEGER NOT NULL DEFAULT 0,
                plan TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkout_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                stripe_session_id TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                stripe_event_id TEXT,
                stripe_session_id TEXT,
                amount_cents INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                email TEXT,
                event_payload TEXT,
                created_at INTEGER NOT NULL
            )
            """
        )


def _upsert_metric(conn: sqlite3.Connection, metric_name: str, delta: int = 1) -> int:
    cur = conn.execute(
        "SELECT metric_value FROM service_metrics WHERE metric_name = ?", (metric_name,)
    )
    row = cur.fetchone()
    if row is None:
        value = delta
        conn.execute(
            "INSERT INTO service_metrics(metric_name, metric_value) VALUES(?, ?)",
            (metric_name, value),
        )
    else:
        value = row["metric_value"] + delta
        conn.execute(
            "UPDATE service_metrics SET metric_value = ? WHERE metric_name = ?",
            (value, metric_name),
        )
    return value


def increment_root_hits() -> int:
    with _connect() as conn:
        value = _upsert_metric(conn, "root_hits", 1)
    return value


def track_event(event_name: str, email: str | None = None, payload: dict | None = None) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO analytics_events(event_name, email, event_payload, created_at) VALUES(?, ?, ?, ?)",
            (event_name, email, json.dumps(payload or {}), _now()),
        )


def upsert_user(email: str, stripe_customer_id: str | None = None) -> None:
    with _connect() as conn:
        ts = _now()
        conn.execute(
            """
            INSERT INTO users(email, stripe_customer_id, created_at, updated_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                stripe_customer_id = COALESCE(excluded.stripe_customer_id, users.stripe_customer_id),
                updated_at = excluded.updated_at
            """,
            (email, stripe_customer_id, ts, ts),
        )


def get_user(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def create_checkout_session(email: str, stripe_session_id: str) -> None:
    with _connect() as conn:
        ts = _now()
        conn.execute(
            """
            INSERT INTO checkout_sessions(email, stripe_session_id, status, created_at, updated_at)
            VALUES(?, ?, 'created', ?, ?)
            """,
            (email, stripe_session_id, ts, ts),
        )


def update_checkout_session_status(stripe_session_id: str, status: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE checkout_sessions SET status = ?, updated_at = ? WHERE stripe_session_id = ?",
            (status, _now(), stripe_session_id),
        )


def save_payment(
    *,
    email: str,
    stripe_event_id: str | None,
    stripe_session_id: str | None,
    amount_cents: int,
    status: str,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO payments(email, stripe_event_id, stripe_session_id, amount_cents, status, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (email, stripe_event_id, stripe_session_id, amount_cents, status, _now()),
        )


def set_paid_status(email: str, is_paid: bool, plan: str = "pro-monthly") -> None:
    with _connect() as conn:
        ts = _now()
        conn.execute(
            """
            UPDATE users
            SET is_paid = ?, plan = ?, updated_at = ?
            WHERE email = ?
            """,
            (1 if is_paid else 0, plan if is_paid else None, ts, email),
        )


def admin_report() -> dict:
    with _connect() as conn:
        visits = conn.execute(
            "SELECT COUNT(*) AS c FROM analytics_events WHERE event_name = 'visit'"
        ).fetchone()["c"]
        signups = conn.execute(
            "SELECT COUNT(*) AS c FROM analytics_events WHERE event_name = 'signup'"
        ).fetchone()["c"]
        checkouts = conn.execute(
            "SELECT COUNT(*) AS c FROM analytics_events WHERE event_name = 'checkout_created'"
        ).fetchone()["c"]
        paid_users = conn.execute("SELECT COUNT(*) AS c FROM users WHERE is_paid = 1").fetchone()["c"]
        mrr_cents = conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) AS c FROM payments WHERE status = 'paid'"
        ).fetchone()["c"]

    signup_conversion = (signups / visits) if visits else 0
    checkout_conversion = (checkouts / signups) if signups else 0

    return {
        "visits": visits,
        "signups": signups,
        "checkout_sessions": checkouts,
        "paid_users": paid_users,
        "signup_conversion": round(signup_conversion, 4),
        "checkout_conversion": round(checkout_conversion, 4),
        "mrr_cents": mrr_cents,
    }
