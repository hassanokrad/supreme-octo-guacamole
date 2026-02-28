import argparse
import calendar
import sqlite3
from datetime import datetime, timezone


def date_window(reference: datetime) -> tuple[str, str]:
    year = reference.year
    month = reference.month
    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59, tzinfo=timezone.utc)
    return start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")


def count(conn: sqlite3.Connection, query: str, params: tuple = ()) -> int:
    value = conn.execute(query, params).fetchone()[0]
    return int(value or 0)


def generate_report(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc)
    start, end = date_window(now)

    revenue_cents = count(
        conn,
        """
        SELECT COALESCE(SUM(amount_cents), 0)
        FROM payments
        WHERE status = 'paid' AND created_at BETWEEN ? AND ?
        """,
        (start, end),
    )
    new_paid = count(
        conn,
        """
        SELECT COUNT(*) FROM users
        WHERE is_paid = 1 AND created_at BETWEEN ? AND ?
        """,
        (start, end),
    )
    churned = count(
        conn,
        """
        SELECT COUNT(*) FROM users
        WHERE is_paid = 0 AND updated_at BETWEEN ? AND ?
        """,
        (start, end),
    )
    visits = count(
        conn,
        """
        SELECT COUNT(*) FROM analytics_events
        WHERE event_name = 'visit' AND created_at BETWEEN ? AND ?
        """,
        (start, end),
    )
    signups = count(
        conn,
        """
        SELECT COUNT(*) FROM analytics_events
        WHERE event_name = 'signup' AND created_at BETWEEN ? AND ?
        """,
        (start, end),
    )
    checkouts = count(
        conn,
        """
        SELECT COUNT(*) FROM analytics_events
        WHERE event_name = 'checkout_created' AND created_at BETWEEN ? AND ?
        """,
        (start, end),
    )
    conn.close()

    signup_rate = (signups / visits) if visits else 0.0
    checkout_rate = (checkouts / signups) if signups else 0.0
    churn_rate = (churned / (new_paid + churned)) if (new_paid + churned) else 0.0

    return f"""# PulseBoard KPI Report ({start} to {end})

## Revenue
- Revenue: ${revenue_cents / 100:.2f}
- New paid users: {new_paid}
- Churned users: {churned}
- Churn rate: {churn_rate:.2%}

## Funnel
- Visits: {visits}
- Signups: {signups}
- Checkout starts: {checkouts}
- Visit → Signup: {signup_rate:.2%}
- Signup → Checkout: {checkout_rate:.2%}
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="./data/pulseboard.db")
    parser.add_argument("--output", default="kpi-report.md")
    args = parser.parse_args()

    report = generate_report(args.db_path)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(report)
    print(f"Wrote KPI report to {args.output}")


if __name__ == "__main__":
    main()
