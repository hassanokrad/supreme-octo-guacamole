import json
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

from server import AppConfig, build_server


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        tmp_path = Path(cls.tmp.name)

        seed_path = tmp_path / "offers_seed.json"
        seed_path.write_text(
            json.dumps(
                [
                    {
                        "id": "offer-1",
                        "title": "Starter Deal",
                        "description": "A strong starter offer",
                        "affiliate_url": "https://example.com/deal",
                    }
                ]
            )
        )

        cls.config = AppConfig()
        cls.config.host = "127.0.0.1"
        cls.config.port = 18080
        cls.config.db_path = tmp_path / "app.db"
        cls.config.admin_token = "test-token"
        cls.config.seed_path = seed_path
        cls.config.site_title = "Test Site"

        store.init_db()
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

    def test_refresh_and_offer_redirect(self) -> None:
        conn = HTTPConnection("127.0.0.1", 18080)

        conn.request("POST", "/automation/refresh")
        unauthorized = conn.getresponse()
        self.assertEqual(unauthorized.status, 401)
        unauthorized.read()

        conn.request("POST", "/automation/refresh?token=test-token")
        refreshed = conn.getresponse()
        payload = json.loads(refreshed.read().decode("utf-8"))
        self.assertEqual(refreshed.status, 200)
        self.assertEqual(payload["offers"], 1)

        opener = build_opener(NoRedirect)
        response = opener.open("http://127.0.0.1:18080/go/offer-1")
        self.assertEqual(response.status, 302)
        self.assertEqual(response.headers.get("Location"), "https://example.com/deal")

    def test_admin_report_requires_valid_token(self) -> None:
        conn = HTTPConnection("127.0.0.1", 18080)

        conn.request("GET", "/")
        conn.getresponse().read()

        conn.request("GET", "/admin/report")
        unauthorized = conn.getresponse()
        self.assertEqual(unauthorized.status, 401)
        unauthorized.read()

        conn.request("GET", "/admin/report?token=test-token")
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertIn("views", payload)
        self.assertIn("clicks", payload)
        self.assertIn("ctr_percent", payload)


if __name__ == "__main__":
    unittest.main()
