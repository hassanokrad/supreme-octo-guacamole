import sqlite3
from pathlib import Path

from config import settings


def _db_path() -> Path:
    path = Path(settings.database_url)
    if path.parent.as_posix() not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_metrics (
                metric_name TEXT PRIMARY KEY,
                metric_value INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


def increment_root_hits() -> int:
    with sqlite3.connect(_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT metric_value FROM service_metrics WHERE metric_name = ?", ("root_hits",)
        )
        row = cursor.fetchone()

        if row is None:
            value = 1
            cursor.execute(
                "INSERT INTO service_metrics(metric_name, metric_value) VALUES(?, ?)",
                ("root_hits", value),
            )
        else:
            value = row[0] + 1
            cursor.execute(
                "UPDATE service_metrics SET metric_value = ? WHERE metric_name = ?",
                (value, "root_hits"),
            )

        conn.commit()
        return value
