# Autonomous Revenue Starter

A minimal, self-hostable Python project designed to run continuously and monetize via affiliate links with minimal owner interaction.

## What it does

- Serves a landing page with curated offers.
- Tracks page views and affiliate click-throughs in SQLite.
- Rotates and refreshes offers from a local seed file automatically.
- Exposes a token-protected admin report endpoint for basic revenue-funnel metrics.
- Includes CI checks and scripts for unattended operation.

> This is an automation starter, not a guaranteed income machine. Profit depends on traffic and offer quality.

## Quickstart

```bash
make init-db
make run
```

---

Copy `.env.example` to `.env` and edit values.

```text
src/
  main.py          # app entrypoint + HTTP routes
  config.py        # env/config loading
  store.py         # sqlite persistence layer
  app/             # compatibility package
scripts/ops/
  *.py|*.sh        # monitoring, backup, KPI, growth, notifications
.github/workflows/
  ci.yml           # lint + test + docker build
  cd.yml           # deploy on main after CI succeeds
  operations.yml   # monitoring + backups + growth + KPI schedules
docs/runbooks/
  *.md             # incident, deployment, and backup runbooks
```

## Endpoints

- `GET /` landing page
- `GET /health` health check
- `GET /go/<offer_id>` tracked redirect to affiliate URL
- `POST /automation/refresh?token=<ADMIN_TOKEN>` refreshes offers from seed file
- `GET /admin/report?token=<ADMIN_TOKEN>` funnel report (`200 OK` with metrics JSON)
  - Missing or invalid `token` query value returns `401 Unauthorized` with `{"error":"unauthorized"}`.

## CI/CD

- **CI (`.github/workflows/ci.yml`)** runs lint, unit tests, and container build.
- **CD (`.github/workflows/cd.yml`)** triggers automatically when CI succeeds on `main`, then:
  1. Builds + pushes `ghcr.io/<org>/pulseboard` image tags (`latest` + commit SHA).
  2. Deploys to production host over SSH using Compose.
  3. Runs health verification.

Required repository/environment secrets:
- `PROD_SSH_HOST`, `PROD_SSH_USER`, `PROD_SSH_KEY`
- `PROD_HEALTHCHECK_URL`

## Production monitoring + operations

`operations.yml` drives automation for:
- **Uptime checks** every 5 minutes.
- **Error tracking checks** every 5 minutes.
- **Resource alerts** (CPU/memory/disk) hourly.
- **Backups + restore validation** daily.
- **Growth/revenue jobs** (content publishing, email campaign, lead follow-up) weekdays.
- **Monthly KPI report** for revenue, churn, and funnel metrics.

Notification fan-out is handled by `scripts/ops/notify.py` and supports:
- Slack (`SLACK_WEBHOOK_URL`)
- PagerDuty (`PAGERDUTY_ROUTING_KEY`)
- SMTP email (`SMTP_*`, `ALERT_EMAIL_FROM`, `ALERT_EMAIL_TO`)

## Runbooks

- Incident response: `docs/runbooks/incident-response.md`
- Deployment: `docs/runbooks/deployment.md`
- Backup and restore: `docs/runbooks/backups.md`
