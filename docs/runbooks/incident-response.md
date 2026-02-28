# Incident Response Runbook

## Alert channels
1. Slack webhook (`SLACK_WEBHOOK_URL`) for broad visibility.
2. PagerDuty Events API (`PAGERDUTY_ROUTING_KEY`) for on-call paging.
3. SMTP (`SMTP_*` and `ALERT_EMAIL_*`) for email escalation.

Automation sends fan-out notifications via `scripts/ops/notify.py`.

## Severity matrix
- **SEV-1**: Production down, checkout unavailable, or data corruption risk.
- **SEV-2**: Intermittent errors > threshold, elevated resource pressure.
- **SEV-3**: Non-critical automation failure (reporting, growth jobs).

## First 15 minutes checklist
1. Acknowledge incident in Slack/PagerDuty.
2. Confirm current health endpoint response (`/health`).
3. Check latest deploy and rollback if incident correlates with release.
4. Validate backup freshness (`backups/manifest-*`).
5. Open incident document with timeline and owner.

## Mitigation playbook
- **Service outage**: restart service and re-check `/health`.
- **High error rate**: inspect Stripe webhook path, external dependencies, and latest logs.
- **Resource saturation**: scale host or recycle workload, verify disk utilization.
- **Backup/restore failed**: rerun backup workflow, execute restore validation manually.

## Closeout
1. Resolve monitor alerts and confirm KPI jobs continue.
2. Write postmortem with root cause, blast radius, and prevention actions.
3. Create follow-up tasks with owners and due dates.
