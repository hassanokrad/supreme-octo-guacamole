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

Open `http://localhost:8080`.

## Configuration

Copy `.env.example` to `.env` and edit values.

- `HOST` / `PORT`: bind settings.
- `ADMIN_TOKEN`: required to access automation and reporting endpoints.
- `SITE_TITLE`: site heading.

## Endpoints

- `GET /` landing page
- `GET /health` health check
- `GET /go/<offer_id>` tracked redirect to affiliate URL
- `POST /automation/refresh?token=<ADMIN_TOKEN>` refreshes offers from seed file
- `GET /admin/report?token=<ADMIN_TOKEN>` funnel report (views/clicks/CTR)

## Automation

Daily refresh and metrics task:

```bash
make daily
```

For unattended operation, schedule:

```cron
0 4 * * * cd /path/to/repo && /usr/bin/make daily >> /var/log/autonomous-revenue.log 2>&1
```

## Testing

```bash
make test
```
