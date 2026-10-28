"""Credential-free GitHub-to-cloud proof; NOT a general browser or command worker."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json
from json import JSONDecodeError
import os
import re

ISSUE_URL = "https://api.github.com/repos/scot1996/cjh-free-connectivity-pilot/issues/1"
EXPECTED = {
    "schema": "cjh.ping.v1",
    "request_id": "pilot-20261028-001",
    "job_type": "ping",
    "target": "render-free-web",
    "read_only": True,
    "execution_enabled": True,
}

def validate_issue(issue):
    if not isinstance(issue, dict):
        raise ValueError("malformed")
    if issue.get("number") != 1 or issue.get("state") != "open":
        raise ValueError("issue_state")
    if issue.get("user", {}).get("login") != "scot1996":
        raise ValueError("author")
    if issue.get("title") != "Connectivity pilot: safe ping request":
        raise ValueError("title")
    match = re.search(r"```json\s*(\{.*?\})\s*```", str(issue.get("body", "")), re.S)
    if not match:
        raise ValueError("envelope")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict) or set(payload) != set(EXPECTED):
        raise ValueError("fields")
    for key, expected_value in EXPECTED.items():
        if type(payload[key]) is not type(expected_value) or payload[key] != expected_value:
            raise ValueError("property")
    return payload

def check_github():
    request = Request(
        ISSUE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "cjh-connectivity-pilot"},
    )
    with urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise ValueError("github")
        data = response.read(16385)
    if len(data) > 16384:
        raise ValueError("size")
    issue = json.loads(data)
    task = validate_issue(issue)
    return {
        "service": "cjh-isolated-controller-pilot",
        "status": "worker_online",
        "request_id": task["request_id"],
        "source": "public_github_issue_1",
        "task_execution": "constant_ping_only",
        "browser_access": False,
        "production_access": False,
        "github_actions": False,
    }

class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, value):
        data = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/health"):
            self.send_json(200, {
                "service": "cjh-isolated-controller-pilot",
                "status": "ready", "mode": "connectivity-only",
                "task_execution": False, "browser_access": False, "github_actions": False
            })
        elif self.path == "/task/1":
            try:
                self.send_json(200, check_github())
            except (ValueError, JSONDecodeError, HTTPError, URLError, TimeoutError, OSError) as exc:
                self.send_json(503, {"status": "not_verified", "reason": type(exc).__name__})
        else:
            self.send_json(404, {"status": "not_found"})

    def log_message(self, fmt, *args):
        return

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), Handler).serve_forever()
