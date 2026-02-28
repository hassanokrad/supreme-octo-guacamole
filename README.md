# PulseBoard — Product Spec & Runbook

## One-page product scope
**Product type:** API SaaS (usage analytics micro-service).

**Problem:** Small product teams need a dead-simple endpoint they can call to track hits without integrating a full analytics suite.

**Target users:** Indie hackers, early-stage SaaS teams, internal tools teams.

**Core value proposition:** A tiny HTTP API that records events and returns a live counter with near-zero setup.

**MVP features (this repo):**
1. `GET /health` for uptime checks.
2. `GET /` returns service metadata and increments a persisted request counter.
3. SQLite persistence so data survives process restarts.
4. `.env`-driven config for local + container deployments.

**Out of scope (future):** Multi-tenant API keys, per-route metrics, dashboard UI, billing, and retention policies.

---

## Project structure

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

## Run locally

1. Create env file:
   ```bash
   cp .env.example .env
   ```
2. Start app:
   ```bash
   make run
   ```
3. Verify endpoints:
   - `http://127.0.0.1:8000/health`
   - `http://127.0.0.1:8000/`

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
