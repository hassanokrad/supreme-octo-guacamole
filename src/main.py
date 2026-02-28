import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from store import increment_root_hits, init_db
from config import settings


class RequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json({"status": "ok", "environment": settings.app_env})
            return
        if self.path == "/":
            hits = increment_root_hits()
            self._send_json(
                {
                    "service": settings.app_name,
                    "message": "PulseBoard API is running",
                    "root_hits": hits,
                }
            )
            return

        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)


def run_server() -> None:
    init_db()
    server = ThreadingHTTPServer((settings.host, settings.port), RequestHandler)
    print(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
