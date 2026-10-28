"""Public, credential-free reachability pilot. No worker execution, browser or account access."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/health', '/'):
            self.send_error(404)
            return
        data = json.dumps({
            "service": "cjh-isolated-controller-pilot",
            "status": "ready",
            "mode": "connectivity-only",
            "github_actions": False,
            "task_execution": False,
            "browser_access": False
        }, separators=(',', ':')).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, fmt, *args):
        pass

if __name__ == '__main__':
    HTTPServer(('0.0.0.0', int(os.environ.get('PORT','10000'))), Handler).serve_forever()
