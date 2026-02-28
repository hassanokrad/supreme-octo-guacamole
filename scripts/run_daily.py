#!/usr/bin/env python3
"""Daily maintenance for the canonical PulseBoard app schema."""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import settings
from src.store import init_db


def main() -> None:
    init_db()

    db_path = Path(settings.database_url)
    with sqlite3.connect(db_path) as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        events = conn.execute("SELECT COUNT(*) FROM analytics_events").fetchone()[0]
        payments = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]

    print(
        "Daily maintenance complete "
        f"(db={db_path}, users={users}, analytics_events={events}, payments={payments})"
    )


if __name__ == "__main__":
    main()
