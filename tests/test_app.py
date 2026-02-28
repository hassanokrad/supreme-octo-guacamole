import json
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from http.client import HTTPConnection
from pathlib import Path

import config
import main
import store
from config import Settings
from http.server import ThreadingHTTPServer
from main import RequestHandler


class FakeStripeGateway:
    def create_customer(self, email: str) -> str:
        return f"cus_{email.replace('@', '_')}"

    def create_checkout_session(self, customer_id: str, price_id: str, success_url: str, cancel_url: str) -> tuple[str, str]:
        return "cs_test_123", "https://checkout.stripe.test/session/cs_test_123"

    def verify_webhook(self, raw_body: bytes, stripe_signature: str) -> dict:
        return json.loads(raw_body.decode("utf-8"))


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "test.db"

        test_settings: Settings = replace(config.settings, database_url=str(db_path), admin_token="test-token")
        config.settings = test_settings
        main.settings = test_settings
        store.settings = test_settings

        store.init_db()
        main.stripe_gateway = FakeStripeGateway()

        cls.server = ThreadingHTTPServer(("127.0.0.1", 18080), RequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_health(self):
        conn = HTTPConnection("127.0.0.1", 18080)
        conn.request("GET", "/health")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        self.assertEqual(response.status, 200)
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

    def test_admin_report_requires_valid_token(self) -> None:
        conn = HTTPConnection("127.0.0.1", 18080)

        conn.request("GET", "/admin/report")
        missing_token = conn.getresponse()
        missing_payload = json.loads(missing_token.read().decode("utf-8"))
        self.assertEqual(missing_token.status, 401)
        self.assertEqual(missing_payload["error"], "unauthorized")

        conn.request("GET", "/admin/report?token=wrong-token")
        invalid_token = conn.getresponse()
        invalid_payload = json.loads(invalid_token.read().decode("utf-8"))
        self.assertEqual(invalid_token.status, 401)
        self.assertEqual(invalid_payload["error"], "unauthorized")

        conn.request("GET", "/")
        conn.getresponse().read()

        conn.request("GET", "/admin/report?token=test-token")
        authorized = conn.getresponse()
        payload = json.loads(authorized.read().decode("utf-8"))

        self.assertEqual(authorized.status, 200)
        self.assertIn("visits", payload)
        self.assertIn("signup_conversion", payload)
        self.assertIn("mrr_cents", payload)


if __name__ == "__main__":
    unittest.main()
