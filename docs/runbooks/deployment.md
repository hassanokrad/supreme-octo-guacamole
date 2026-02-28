# Deployment Runbook

## Standard deployment path
1. Merge to `main`.
2. CI workflow validates lint, tests, and Docker build.
3. CD workflow builds and pushes image to GHCR.
4. CD workflow SSHs to production host and runs `docker compose ... up -d --force-recreate`.
5. CD workflow runs health verification against `PROD_HEALTHCHECK_URL`.

## Required secrets
- `PROD_SSH_HOST`
- `PROD_SSH_USER`
- `PROD_SSH_KEY`
- `PROD_HEALTHCHECK_URL`

## Rollback
1. Select prior image tag in GHCR (commit SHA tag).
2. SSH to production host.
3. Run deployment script with previous `IMAGE` tag.
4. Verify `/health` and `/admin/report` endpoints.
