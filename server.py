import http.server
import json
import logging
import os
import sys
import threading
import urllib.parse
from zoneinfo import ZoneInfo
from datetime import datetime

# Fix stdout encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TrackerServer")

import run_tracker

PORT = 5005
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")
DATA_DIR = os.path.join(BASE_DIR, "data")

class TrackerRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # Route / or /index.html directly to dashboard
        if parsed.path in ["/", "/index.html"]:
            self.send_response(302)
            self.send_header("Location", "/dashboard/index.html")
            self.end_headers()
            return

        # API Route: /api/sync -> triggers live scraper and returns updated JSON
        if parsed.path == "/api/sync":
            try:
                logger.info("Received manual sync request from dashboard...")
                updated_data = run_tracker.run()

                response_bytes = json.dumps(updated_data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)
            except Exception as e:
                logger.error(f"Sync error: {e}")
                err_payload = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(err_payload)
            return

        # Serve static files as usual
        return super().do_GET()

def start_server():
    server_address = ("127.0.0.1", PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, TrackerRequestHandler)
    print("=" * 70)
    print("🏀 Deni Avdija & Channel 5 Tracker Web Server")
    print(f"🌐 Dashboard is LIVE at: http://localhost:{PORT}")
    print("=" * 70)
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    start_server()
