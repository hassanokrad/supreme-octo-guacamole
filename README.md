# PulseBoard

A minimal, self-hostable Python service for subscription analytics with Stripe-backed checkout.

## What it does

- Serves core API endpoints for health, signup, checkout, premium access, and reporting.
- Persists user, checkout, payment, and analytics data in SQLite.
- Verifies Stripe webhooks and updates paid subscription state.
- Includes lightweight scripts for initialization, operations checks, and daily automation.

## Quickstart

```bash
make init-db
make run
```

## Architecture

PulseBoard is standardized on a single server implementation:

- **Canonical app module:** `src/main.py`
- **Config module:** `src/config.py`
- **Persistence module:** `src/store.py`
- **Legacy compatibility wrappers:** `src/server.py` and `src/app/*` (deprecated)

```text
src/
  main.py          # canonical app entrypoint + HTTP routes
  config.py        # env/config loading
  store.py         # sqlite persistence layer
  server.py        # deprecated compatibility entrypoint
  app/             # deprecated compatibility wrappers
scripts/ops/
  *.py|*.sh        # monitoring, backup, KPI, growth, notifications
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service metadata and root hit counter |
| GET | `/health` | Health check and environment |
| GET | `/pricing` | Subscription pricing page |
| POST | `/signup` | Create/update user by email |
| POST | `/checkout/session` | Create Stripe checkout session |
| POST | `/webhooks/stripe` | Process Stripe webhook events |
| GET | `/premium?email=<email>` | Premium feature access gate |
| GET | `/admin/report` | Funnel + revenue summary |

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
