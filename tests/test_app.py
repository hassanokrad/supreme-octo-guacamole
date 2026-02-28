import json
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

from config import settings
from main import RequestHandler
from store import init_db
from http.server import ThreadingHTTPServer


class AppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = Path(settings.database_url)
        if db_path.exists():
            db_path.unlink()
        init_db()

        cls.server = ThreadingHTTPServer(("127.0.0.1", 18080), RequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def test_health(self) -> None:
        conn = HTTPConnection("127.0.0.1", 18080)
        conn.request("GET", "/health")
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_root_counter_increments(self) -> None:
        conn = HTTPConnection("127.0.0.1", 18080)
        conn.request("GET", "/")
        first = json.loads(conn.getresponse().read().decode("utf-8"))

        conn.request("GET", "/")
        second = json.loads(conn.getresponse().read().decode("utf-8"))

        self.assertEqual(second["root_hits"], first["root_hits"] + 1)


if __name__ == "__main__":
    unittest.main()
