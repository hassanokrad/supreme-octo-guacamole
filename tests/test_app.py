import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import HTTPErrorProcessor, build_opener, urlopen

import main
from config import settings
from http.server import ThreadingHTTPServer
from main import RequestHandler
from store import init_db


class FakeStripeGateway:
    def create_customer(self, email: str) -> str:
        return f"cus_{email.replace('@', '_')}"

    def create_checkout_session(self, customer_id: str, price_id: str, success_url: str, cancel_url: str) -> tuple[str, str]:
        return "cs_test_123", "https://checkout.stripe.test/session/cs_test_123"

    def verify_webhook(self, raw_body: bytes, stripe_signature: str) -> dict:
        return json.loads(raw_body.decode("utf-8"))


class NoRedirect(HTTPErrorProcessor):
    def http_response(self, request, response):
        return response

    https_response = http_response


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = Path(settings.database_url)
        if db_path.exists():
            db_path.unlink()
        init_db()
        main.stripe_gateway = FakeStripeGateway()

        cls.config = AppConfig()
        cls.config.host = "127.0.0.1"
        cls.config.port = 18080
        cls.config.db_path = data / "app.db"
        cls.config.admin_token = "test-token"
        cls.config.seed_path = data / "offers_seed.json"
        cls.config.site_title = "Test Site"

        cls.server = build_server(cls.config)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def test_health(self):
        body = urlopen("http://127.0.0.1:18080/health").read().decode()
        self.assertIn("ok", body)

    def test_subscription_checkout_and_premium_gate(self) -> None:
        conn = HTTPConnection("127.0.0.1", 18080)
        email = "paid@example.com"

        conn.request("GET", f"/premium?email={email}")
        blocked = conn.getresponse()
        self.assertEqual(blocked.status, 402)
        blocked.read()

        conn.request(
            "POST",
            "/signup",
            body=json.dumps({"email": email}),
            headers={"Content-Type": "application/json"},
        )
        signup = conn.getresponse()
        self.assertEqual(signup.status, 201)
        signup.read()

        conn.request(
            "POST",
            "/checkout/session",
            body=json.dumps({"email": email}),
            headers={"Content-Type": "application/json"},
        )
        checkout = conn.getresponse()
        checkout_payload = json.loads(checkout.read().decode("utf-8"))
        self.assertEqual(checkout.status, 200)
        self.assertIn("checkout_url", checkout_payload)

        webhook_event = {
            "id": "evt_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": checkout_payload["session_id"],
                    "customer_details": {"email": email},
                }
            },
        }
        conn.request(
            "POST",
            "/webhooks/stripe",
            body=json.dumps(webhook_event),
            headers={"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=abc"},
        )
        webhook = conn.getresponse()
        self.assertEqual(webhook.status, 200)
        webhook.read()

        conn.request("GET", f"/premium?email={email}")
        allowed = conn.getresponse()
        self.assertEqual(allowed.status, 200)
        payload = json.loads(allowed.read().decode("utf-8"))
        self.assertEqual(payload["feature"], "cohort-retention-insights")

    def test_admin_report_has_metrics(self) -> None:
        conn = HTTPConnection("127.0.0.1", 18080)
        conn.request("GET", "/")
        conn.getresponse().read()

        conn.request("GET", "/admin/report")
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertIn("visits", payload)
        self.assertIn("signup_conversion", payload)
        self.assertIn("mrr_cents", payload)


if __name__ == "__main__":
    unittest.main()
