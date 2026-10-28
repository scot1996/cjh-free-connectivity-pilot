"""Public, credential-free, allowlisted ping proof. NOT a browser/command executor."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from json import JSONDecodeError
import json
import os

PING_URL = "https://raw.githubusercontent.com/scot1996/cjh-free-connectivity-pilot/main/ping.json"
EXPECTED = {
    "schema": "cjh.ping.v1",
    "request_id": "pilot-20261028-public-file-001",
    "job_type": "ping",
    "target": "render-free-web",
    "read_only": True,
    "execution_enabled": True,
}

def check_github():
    # Only one hardcoded, public, non-secret source may be read.
    req = Request(PING_URL, headers={"User-Agent": "cjh-connectivity-pilot/1.0"})
    with urlopen(req, timeout=10) as response:
        if response.status != 200:
            raise ValueError("github_file")
        body = response.read(8193)
    if len(body) > 8192:
        raise ValueError("size")
    task = json.loads(body)
    if not isinstance(task, dict) or set(task) != set(EXPECTED):
        raise ValueError("task_schema")
    for key, value in EXPECTED.items():
        if type(task[key]) is not type(value) or task[key] != value:
            raise ValueError("task_property")
    return {
        "service": "cjh-isolated-controller-pilot",
        "status": "worker_online",
        "request_id": task["request_id"],
        "source": "public_github_file",
        "action": "fixed_ping_only",
        "browser_access": False,
        "production_access": False,
        "github_actions": False
    }

class Handler(BaseHTTPRequestHandler):
    def answer(self, status, payload):
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/health"):
            self.answer(200, {
                "service": "cjh-isolated-controller-pilot", "status": "ready",
                "mode": "connectivity-only", "task_execution": False,
                "browser_access": False, "github_actions": False
            })
        elif self.path == "/task/1":
            try:
                self.answer(200, check_github())
            except (ValueError, JSONDecodeError, HTTPError, URLError, TimeoutError, OSError) as exc:
                self.answer(503, {"status": "not_verified", "reason": type(exc).__name__})
        else:
            self.answer(404, {"status": "not_found"})

    def log_message(self, fmt, *args):
        return

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), Handler).serve_forever()
