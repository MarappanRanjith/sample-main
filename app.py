from __future__ import annotations

import json
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from src.framework.data import candles_from_file, load_candles
from src.smc_service import CandleInputError, analyze_candles

ROOT = Path(__file__).resolve().parent


def _analyze_payload(payload: object):
    if not isinstance(payload, dict) or not isinstance(payload.get("candles"), list):
        raise CandleInputError("Request body must contain a 'candles' array.")
    return analyze_candles(payload["candles"], int(payload.get("minimum_score", 2)))


class DashboardHandler(BaseHTTPRequestHandler):
    def _send(self, status: HTTPStatus, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, payload: object):
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        path = unquote(urlparse(self.path).path)
        if path == "/":
            self._send(HTTPStatus.OK, (ROOT / "templates" / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/demo":
            candles = load_candles(ROOT / "data" / "demo_candles.json")
            self._json(HTTPStatus.OK, analyze_candles(candles))
        elif path.startswith("/static/"):
            asset = ROOT / path.removeprefix("/")
            if asset.is_file() and asset.parent == ROOT / "static":
                content_type = "text/css; charset=utf-8" if asset.suffix == ".css" else "text/javascript; charset=utf-8"
                self._send(HTTPStatus.OK, asset.read_bytes(), content_type)
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "Asset not found."})
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            if self.path == "/api/analyze":
                self._json(HTTPStatus.OK, _analyze_payload(json.loads(body)))
                return
            if self.path == "/api/analyze-upload":
                message = BytesParser(policy=policy.default).parsebytes(
                    b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + body
                )
                file_part = next((part for part in message.iter_attachments() if part.get_filename()), None)
                if file_part is None:
                    raise CandleInputError("Choose a JSON or CSV candle file first.")
                contents = (file_part.get_payload(decode=True) or b"").decode("utf-8-sig")
                candles = candles_from_file(contents, file_part.get_filename() or "")
                self._json(HTTPStatus.OK, analyze_candles(candles))
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
        except (CandleInputError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, format, *args):
        return


def create_server(host="127.0.0.1", port=5000):
    return ThreadingHTTPServer((host, port), DashboardHandler)


if __name__ == "__main__":
    server = create_server()
    print("SMC Signal Desk running at http://127.0.0.1:5000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
