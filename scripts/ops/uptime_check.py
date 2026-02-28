import json
import os
import urllib.request

from notify import main as notify_main


def main() -> None:
    url = os.getenv("HEALTHCHECK_URL", "").strip()
    if not url:
        raise SystemExit("HEALTHCHECK_URL is required")

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if response.status != 200 or payload.get("status") != "ok":
                raise RuntimeError(f"Unexpected health payload: {payload}")
        print("Uptime check passed")
    except Exception as exc:  # noqa: BLE001
        os.environ["NOTIFICATION_TEXT"] = f"PulseBoard uptime check failed for {url}: {exc}"
        notify_main()
        raise


if __name__ == "__main__":
    main()
