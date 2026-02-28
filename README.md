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

**Success criteria (MVP):**
- Runs locally in <5 minutes.
- Deployable as a container.
- CI validates lint + tests + build on every push.

---

## Project structure

```text
src/
  main.py          # app entrypoint + HTTP routes
  config.py        # env/config loading
  store.py         # sqlite persistence layer
  app/             # compatibility package
tests/
  test_app.py      # endpoint and counter tests
infra/
  docker-compose.prod.yml
.github/workflows/
  ci.yml           # lint + test + docker build
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

## Deploy

### Option A: Docker

```bash
docker build -t pulseboard:latest .
docker run --rm -p 8000:8000 --env-file .env pulseboard:latest
```

### Option B: Docker Compose

```bash
docker compose -f infra/docker-compose.prod.yml up --build -d
```

## CI behavior

On each push, GitHub Actions runs:
1. Lint (`py_compile` syntax check)
2. Tests (`unittest`)
3. Docker image build
