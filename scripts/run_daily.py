#!/usr/bin/env python3
import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DB_PATH = ROOT / "data/app.db"
SEED_PATH = ROOT / "data/offers_seed.json"

if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

DB_PATH = ROOT / os.getenv("DB_PATH", "data/app.db")

conn = sqlite3.connect(DB_PATH)
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS offers (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT NOT NULL,
      affiliate_url TEXT NOT NULL,
      active INTEGER NOT NULL DEFAULT 1,
      updated_at TEXT NOT NULL
    )
    """
)

offers = json.loads(SEED_PATH.read_text())
for offer in offers:
    conn.execute(
        """
        INSERT INTO offers (id, title, description, affiliate_url, active, updated_at)
        VALUES (?, ?, ?, ?, 1, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
          title=excluded.title,
          description=excluded.description,
          affiliate_url=excluded.affiliate_url,
          active=1,
          updated_at=datetime('now')
        """,
        (offer["id"], offer["title"], offer["description"], offer["affiliate_url"]),
    )
conn.commit()
print(f"Daily refresh complete: {len(offers)} offers active")
