"""
GET /api/status
Response: { "status": "ok", "server": "VN", "version": "1.0" }
"""
import json
from http.server import BaseHTTPRequestHandler
from datetime import datetime

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self._json(200, {
            "status":  "ok",
            "server":  "VN",
            "version": "1.0",
            "time":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "region":  "Việt Nam",
        })

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, *args): pass
