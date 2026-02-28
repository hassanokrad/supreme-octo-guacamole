# Backup + Restore Runbook

## Automated process
- `scripts/ops/backup_db.sh` creates SQLite backup snapshots and SHA256 manifests.
- `scripts/ops/restore_validate.sh` restores latest backup and runs SQLite integrity checks.
- Operations workflow runs this daily and uploads backup artifacts.

## Manual backup
```bash
DATABASE_URL=./data/pulseboard.db BACKUP_DIR=./backups bash scripts/ops/backup_db.sh
```

## Manual restore validation
```bash
BACKUP_DIR=./backups bash scripts/ops/restore_validate.sh
```

## Disaster restore
1. Stop app process/container.
2. Copy chosen backup file over active database path.
3. Start service.
4. Validate `/health` and `/admin/report`.
