import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from billing import StripeGateway
from config import settings
from store import (
    admin_report,
    create_checkout_session,
    get_user,
    increment_root_hits,
    init_db,
    save_payment,
    set_paid_status,
    track_event,
    update_checkout_session_status,
    upsert_user,
)

stripe_gateway = StripeGateway(settings.stripe_api_key, settings.stripe_webhook_secret)


class RequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body)

    def _log_metric(self, event_name: str, email: str | None = None, payload: dict | None = None) -> None:
        entry = {"event": event_name, "email": email, "payload": payload or {}}
        print(json.dumps(entry))
        track_event(event_name, email=email, payload=payload)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json({"status": "ok", "environment": settings.app_env})
            return
        if parsed.path == "/":
            hits = increment_root_hits()
            self._log_metric("visit", payload={"path": "/"})
            self._send_json(
                {
                    "service": settings.app_name,
                    "message": "PulseBoard API is running",
                    "root_hits": hits,
                }
            )
            return
        if parsed.path == "/pricing":
            self._log_metric("visit", payload={"path": "/pricing"})
            self._send_html(self._pricing_html())
            return
        if parsed.path == "/premium":
            email = parse_qs(parsed.query).get("email", [""])[0]
            user = get_user(email) if email else None
            if not user or not user["is_paid"]:
                self._send_json(
                    {
                        "error": "premium feature requires active subscription",
                        "upgrade_url": "/pricing",
                    },
                    status=HTTPStatus.PAYMENT_REQUIRED,
                )
                return
            self._send_json(
                {
                    "feature": "cohort-retention-insights",
                    "insight": "Your highest 7-day retention cohort is from organic traffic.",
                }
            )
            return
        if parsed.path == "/admin/report":
            self._send_json(admin_report())
            return

        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/signup":
            payload = self._read_json_body()
            email = payload.get("email", "").strip().lower()
            if not email:
                self._send_json({"error": "email is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            upsert_user(email)
            self._log_metric("signup", email=email)
            self._send_json({"status": "ok", "email": email}, status=HTTPStatus.CREATED)
            return

        if parsed.path == "/checkout/session":
            payload = self._read_json_body()
            email = payload.get("email", "").strip().lower()
            if not email:
                self._send_json({"error": "email is required"}, status=HTTPStatus.BAD_REQUEST)
                return

            user = get_user(email)
            customer_id = user["stripe_customer_id"] if user else None
            if not customer_id:
                customer_id = stripe_gateway.create_customer(email)

            upsert_user(email, stripe_customer_id=customer_id)
            session_id, checkout_url = stripe_gateway.create_checkout_session(
                customer_id=customer_id,
                price_id=settings.stripe_price_id,
                success_url=f"{settings.app_base_url}/pricing?checkout=success",
                cancel_url=f"{settings.app_base_url}/pricing?checkout=cancel",
            )
            create_checkout_session(email, session_id)
            self._log_metric("checkout_created", email=email, payload={"session_id": session_id})
            self._send_json({"checkout_url": checkout_url, "session_id": session_id})
            return

        if parsed.path == "/webhooks/stripe":
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            signature = self.headers.get("Stripe-Signature", "")

            try:
                event = stripe_gateway.verify_webhook(raw_body, signature)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return

            event_type = event.get("type")
            data = event.get("data", {}).get("object", {})
            customer_email = data.get("customer_details", {}).get("email") or data.get("metadata", {}).get("email")
            session_id = data.get("id")

            if event_type == "checkout.session.completed" and customer_email:
                update_checkout_session_status(session_id, "paid")
                set_paid_status(customer_email, True)
                save_payment(
                    email=customer_email,
                    stripe_event_id=event.get("id"),
                    stripe_session_id=session_id,
                    amount_cents=settings.subscription_amount_cents,
                    status="paid",
                )
                self._log_metric("payment_succeeded", email=customer_email, payload={"session_id": session_id})
            elif event_type == "checkout.session.async_payment_failed" and customer_email:
                update_checkout_session_status(session_id, "failed")
                set_paid_status(customer_email, False)
                save_payment(
                    email=customer_email,
                    stripe_event_id=event.get("id"),
                    stripe_session_id=session_id,
                    amount_cents=settings.subscription_amount_cents,
                    status="failed",
                )
                self._log_metric("payment_failed", email=customer_email, payload={"session_id": session_id})

            self._send_json({"received": True})
            return

        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def _pricing_html(self) -> str:
        return f"""
<!doctype html>
<html>
  <head>
    <title>PulseBoard Pricing</title>
    <style>
      body {{ font-family: sans-serif; max-width: 760px; margin: 2rem auto; line-height: 1.4; }}
      .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }}
      .price {{ font-size: 2rem; font-weight: bold; }}
      button {{ background: #2563eb; color: white; border: 0; border-radius: 6px; padding: 0.6rem 1rem; cursor: pointer; }}
      input {{ padding: 0.6rem; width: 100%; margin-bottom: 0.75rem; }}
      #status {{ margin-top: 0.75rem; }}
    </style>
  </head>
  <body>
    <h1>PulseBoard Pro</h1>
    <div class="card">
      <p class="price">${settings.subscription_amount_cents/100:.2f}/month</p>
      <ul>
        <li>Premium retention insight endpoint</li>
        <li>Priority event ingestion</li>
        <li>Admin revenue reporting</li>
      </ul>
      <input id="email" type="email" placeholder="you@company.com" />
      <button onclick="startCheckout()">Start subscription checkout</button>
      <div id="status"></div>
    </div>

    <script>
      async function startCheckout() {{
        const email = document.getElementById('email').value;
        const status = document.getElementById('status');
        status.textContent = 'Creating customer and checkout session...';

        await fetch('/signup', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ email }})
        }});

        const response = await fetch('/checkout/session', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ email }})
        }});
        const data = await response.json();
        if (!response.ok) {{
          status.textContent = data.error || 'Unable to create checkout';
          return;
        }}
        status.textContent = 'Redirecting to Stripe checkout...';
        window.location.href = data.checkout_url;
      }}
    </script>
  </body>
</html>
"""


def run_server() -> None:
    init_db()
    server = ThreadingHTTPServer((settings.host, settings.port), RequestHandler)
    print(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
