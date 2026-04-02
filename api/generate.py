"""
POST /api/generate
Body: { "auto_activate": true }
Response: { "success": true, "account": {...} }
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from http.server import BaseHTTPRequestHandler
from _core import create_one_account

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length) or b"{}") if length else {}
            auto_activate = body.get("auto_activate", True)

            acc = create_one_account(auto_activate=auto_activate)

            if acc:
                # Không trả jwt_token ra ngoài vì bảo mật
                safe = {k: v for k, v in acc.items() if k != "jwt_token"}
                self._json(200, {"success": True, "account": safe})
            else:
                self._json(200, {"success": False, "error": "Tạo acc thất bại, thử lại"})

        except Exception as e:
            self._json(500, {"success": False, "error": str(e)})

    def do_GET(self):
        self._json(200, {"status": "ok", "endpoint": "POST /api/generate"})

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
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, *args): pass
