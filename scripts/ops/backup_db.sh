#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${DATABASE_URL:-./data/pulseboard.db}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "${BACKUP_DIR}"

BACKUP_FILE="${BACKUP_DIR}/pulseboard-${TIMESTAMP}.db"
MANIFEST_FILE="${BACKUP_DIR}/manifest-${TIMESTAMP}.txt"

python3 - <<PY
import sqlite3
src = sqlite3.connect(r"${DB_PATH}")
dst = sqlite3.connect(r"${BACKUP_FILE}")
with dst:
    src.backup(dst)
src.close()
dst.close()
PY

sha256sum "${BACKUP_FILE}" > "${MANIFEST_FILE}"

echo "Backup created: ${BACKUP_FILE}"
