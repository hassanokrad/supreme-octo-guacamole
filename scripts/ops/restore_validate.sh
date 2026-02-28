#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
LATEST_BACKUP="$(ls -1 "${BACKUP_DIR}"/pulseboard-*.db | tail -n1)"
RESTORE_FILE="${BACKUP_DIR}/restore-validation.db"
cp "${LATEST_BACKUP}" "${RESTORE_FILE}"

python3 - <<PY
import sqlite3
conn = sqlite3.connect(r"${RESTORE_FILE}")
result = conn.execute("PRAGMA integrity_check").fetchone()[0]
if result != "ok":
    raise SystemExit(f"Integrity check failed: {result}")
for table in ["service_metrics", "analytics_events", "users", "payments"]:
    conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
conn.close()
PY

echo "Restore validation succeeded for ${LATEST_BACKUP}"
