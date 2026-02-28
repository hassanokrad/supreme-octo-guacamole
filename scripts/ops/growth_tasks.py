import json
import os
import urllib.request

TASKS = {
    "content_publishing": os.getenv("CONTENT_PUBLISH_WEBHOOK", "").strip(),
    "email_campaign": os.getenv("EMAIL_CAMPAIGN_WEBHOOK", "").strip(),
    "lead_follow_up": os.getenv("LEAD_FOLLOWUP_WEBHOOK", "").strip(),
}


def trigger_task(task_name: str, webhook_url: str) -> None:
    payload = json.dumps({"task": task_name, "source": "pulseboard-scheduler"}).encode("utf-8")
    request = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=20):
        return


def main() -> None:
    triggered = 0
    for name, url in TASKS.items():
        if not url:
            print(f"Skipping {name}: webhook not configured")
            continue
        trigger_task(name, url)
        triggered += 1
        print(f"Triggered {name}")

    if triggered == 0:
        print("No growth task webhooks configured; nothing to run")


if __name__ == "__main__":
    main()
