import json
import os
import urllib.request

from notify import main as notify_main


def main() -> None:
    log_url = os.getenv("ERROR_LOG_URL", "").strip()
    if not log_url:
        print("ERROR_LOG_URL not configured; skipping external error log polling")
        return

    threshold = float(os.getenv("ERROR_RATE_THRESHOLD", "0.05"))
    with urllib.request.urlopen(log_url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    error_rate = float(payload.get("error_rate", 0.0))
    if error_rate >= threshold:
        os.environ["NOTIFICATION_TEXT"] = (
            f"PulseBoard error-rate alert: {error_rate:.2%} exceeded threshold {threshold:.2%}."
        )
        notify_main()
        raise SystemExit(1)

    print(f"Error tracking check passed (error_rate={error_rate:.2%})")


if __name__ == "__main__":
    main()
