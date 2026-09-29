"""Serve the public page and a narrow knowledge API; never serve package files."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from knowledge_service import KnowledgeService


def make_handler(root):
    root = Path(root).resolve()
    page = root / "index.html"
    packages = Path(os.environ.get("KNOWLEDGE_DIR", str(root))).resolve()

    class Handler(BaseHTTPRequestHandler):
        def send_bytes(self, status, data, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, status, value):
            self.send_bytes(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self.send_bytes(200, page.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/reports":
                self.send_json(200, KnowledgeService(packages).statuses())
            else:
                self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")

        def do_POST(self):
            if self.path != "/api/answer":
                self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 4096 or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("invalid request")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("invalid request")
                response = KnowledgeService(packages).answer(
                    payload.get("reportKey"), payload.get("question"), payload.get("previousQuestion"))
                self.send_json(200, response)
            except (ValueError, UnicodeError, json.JSONDecodeError):
                self.send_json(400, {"error": "无效的报表或问题"})

    return Handler


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Local KPI knowledge service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    print(f"Serving http://{args.host}:{args.port}/")
    ThreadingHTTPServer((args.host, args.port), make_handler(root)).serve_forever()
