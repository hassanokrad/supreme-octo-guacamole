import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import HTTPErrorProcessor, build_opener, urlopen

from src.server import AppConfig, build_server


class NoRedirect(HTTPErrorProcessor):
    def http_response(self, request, response):
        return response

    https_response = http_response


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        data = root / "data"
        data.mkdir()
        (data / "offers_seed.json").write_text(
            json.dumps([
                {
                    "id": "demo",
                    "title": "Demo Offer",
                    "description": "Great deal",
                    "affiliate_url": "https://example.com/demo",
                }
            ])
        )

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

    def test_report_and_redirect(self):
        urlopen("http://127.0.0.1:18080/")

        resp = urlopen("http://127.0.0.1:18080/admin/report?token=test-token")
        report = json.loads(resp.read().decode())
        self.assertGreaterEqual(report["views"], 1)

        opener = build_opener(NoRedirect)
        redirect_resp = opener.open("http://127.0.0.1:18080/go/demo")
        self.assertEqual(redirect_resp.status, 302)


if __name__ == "__main__":
    unittest.main()
