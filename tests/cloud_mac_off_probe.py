"""Public safe pilot: exercise real app, network and tests on hosted Linux.

Run by an isolated GitHub Actions runner; no private application source, secrets,
services, billing actions, or Mac dependencies. Do not deploy this app.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]


def get_json(url):
    with urlopen(url, timeout=15) as res:
        return res.status, json.loads(res.read(8193)), res.headers.get("X-Content-Type-Options")


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("This live network probe is for the isolated cloud runner only")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    # Only a disposable runner process; no deployment or public credentials.
    env = os.environ.copy()
    env["PORT"] = str(port)
    process = subprocess.Popen(
        [sys.executable, "-u", "app.py"], cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        health = None
        for _ in range(50):
            if process.poll() is not None:
                raise RuntimeError("Pilot app exited before HTTP health check")
            try:
                status, health, protection = get_json(f"http://127.0.0.1:{port}/health")
                break
            except (ConnectionError, URLError, TimeoutError):
                time.sleep(0.1)
        if health is None:
            raise AssertionError("Pilot app failed to start on hosted Linux")
        if protection != "nosniff":
            raise AssertionError("Cloud app lacks nosniff response protection")
        if status != 200 or health.get("status") != "ready":
            raise AssertionError("Cloud app HTTP health check failed")
        if health.get("task_execution") is not False:
            raise AssertionError("Pilot unexpectedly permits tasks")
        if health.get("browser_access") is not False:
            raise AssertionError("Pilot incorrectly claims browser control")

        # The running Python app makes a real public HTTPS request; this also
        # checks outbound internet. No login, private repository or data.
        status, public, protection = get_json(f"http://127.0.0.1:{port}/task/1")
        if protection != "nosniff":
            raise AssertionError("Live cloud task response lacks nosniff protection")
        if status != 200 or public.get("status") != "worker_online":
            raise AssertionError("Cloud app could not fetch allowed public GitHub file")
        if public.get("source") != "public_github_file":
            raise AssertionError("Cloud app source was not independently verified")
        if public.get("production_access") is not False:
            raise AssertionError("Pilot incorrectly claims production access")
        print(json.dumps({
            "result": "PASS",
            "runner": "github_hosted_linux",
            "app_http": "PASS",
            "response_security_header": "PASS",
            "outbound_public_https": "PASS",
            "mac_used": False,
            "business_data": False,
            "production_modified": False,
            "github_private_runner_minutes": 0,
            "chatgpt_project_chat_ui_tested": False,
        }, sort_keys=True))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
