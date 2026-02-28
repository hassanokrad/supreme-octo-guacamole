import json
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

from src import main
from src.config import settings
from http.server import ThreadingHTTPServer
from src.main import RequestHandler
from src.store import init_db


class FakeStripeGateway:
    def create_customer(self, email: str) -> str:
        return f"cus_{email.replace('@', '_')}"

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> tuple[str, str]:
        return "cs_test_123", "https://checkout.stripe.test/session/cs_test_123"

    def verify_webhook(self, raw_body: bytes, stripe_signature: str) -> dict:
        return json.loads(raw_body.decode("utf-8"))


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.original_db_url = settings.database_url
        object.__setattr__(settings, "database_url", str(Path(cls.tmp.name) / "test.db"))

        init_db()
        main.stripe_gateway = FakeStripeGateway()

        cls.server = ThreadingHTTPServer(("127.0.0.1", 18080), RequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join(timeout=1)
        object.__setattr__(settings, "database_url", cls.original_db_url)
        cls.tmp.cleanup()

    def test_health(self) -> None:
        conn = HTTPConnection("127.0.0.1", 18080)
        conn.request("GET", "/health")
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("environment", payload)

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
