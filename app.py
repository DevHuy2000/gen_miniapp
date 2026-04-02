"""
app.py — Entrypoint cho Vercel Python runtime
Dùng Flask để serve cả static file lẫn API
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime

app = Flask(__name__, static_folder="public", static_url_path="")

# ── CORS middleware
@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

# ── Serve Mini App HTML
@app.route("/")
def index():
    return send_from_directory("public", "index.html")

# ── GET /api/status
@app.route("/api/status", methods=["GET", "OPTIONS"])
def status():
    if request.method == "OPTIONS":
        return "", 200
    return jsonify({
        "status":  "ok",
        "server":  "VN",
        "version": "1.0",
        "time":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "region":  "Việt Nam",
    })

# ── POST /api/generate
@app.route("/api/generate", methods=["POST", "OPTIONS"])
def generate():
    if request.method == "OPTIONS":
        return "", 200
    try:
        from api._core import create_one_account
        body = request.get_json(silent=True) or {}
        auto_activate = body.get("auto_activate", True)

        acc = create_one_account(auto_activate=auto_activate)

        if acc:
            safe = {k: v for k, v in acc.items() if k != "jwt_token"}
            return jsonify({"success": True, "account": safe})
        else:
            return jsonify({"success": False, "error": "Tạo acc thất bại, thử lại"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Local dev
if __name__ == "__main__":
    app.run(debug=True, port=3000)
