import json
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage


def send_slack(message: str) -> None:
    webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        return
    payload = json.dumps({"text": message}).encode("utf-8")
    request = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10):
        return


def send_pagerduty(summary: str) -> None:
    routing_key = os.getenv("PAGERDUTY_ROUTING_KEY", "").strip()
    if not routing_key:
        return
    event = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": summary,
            "severity": "error",
            "source": "pulseboard-automation",
        },
    }
    body = json.dumps(event).encode("utf-8")
    request = urllib.request.Request(
        "https://events.pagerduty.com/v2/enqueue",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10):
        return


def send_email(message: str) -> None:
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        return

    sender = os.getenv("ALERT_EMAIL_FROM", "alerts@pulseboard.local")
    recipients = [email.strip() for email in os.getenv("ALERT_EMAIL_TO", "").split(",") if email.strip()]
    if not recipients:
        return

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")

    msg = EmailMessage()
    msg["Subject"] = "PulseBoard incident notification"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(message)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=20) as client:
        client.starttls(context=context)
        if username:
            client.login(username, password)
        client.send_message(msg)


def main() -> None:
    message = os.getenv("NOTIFICATION_TEXT", "PulseBoard operations alert")
    send_slack(message)
    send_pagerduty(message)
    send_email(message)
    print("Notification fan-out complete")


if __name__ == "__main__":
    main()
