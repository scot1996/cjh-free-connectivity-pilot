"""Standard-library unit tests; no network or private credentials required."""
import io
import json
import unittest
from unittest.mock import patch

import app


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, max_bytes):
        return self.body[:max_bytes]


class CloudPilotContracts(unittest.TestCase):
    def test_health_rejects_arbitrary_cloud_commands(self):
        self.assertEqual(app.EXPECTED["job_type"], "ping")
        self.assertTrue(app.EXPECTED["read_only"])

    def test_hardcoded_public_https_only(self):
        self.assertTrue(app.PING_URL.startswith("https://raw.githubusercontent.com/"))
        self.assertNotIn("token=", app.PING_URL)

    def test_fixed_public_payload_is_accepted(self):
        body = json.dumps(app.EXPECTED).encode("utf-8")
        with patch.object(app, "urlopen", return_value=FakeResponse(body)):
            outcome = app.check_github()
        self.assertEqual(outcome["status"], "worker_online")
        self.assertFalse(outcome["production_access"])
        self.assertFalse(outcome["browser_access"])

    def test_unrecognised_field_fails_closed(self):
        data = {**app.EXPECTED, "shell": "anything"}
        with patch.object(app, "urlopen", return_value=FakeResponse(json.dumps(data).encode())):
            with self.assertRaises(ValueError):
                app.check_github()

    def test_fake_job_is_rejected(self):
        data = {**app.EXPECTED, "job_type": "deploy"}
        with patch.object(app, "urlopen", return_value=FakeResponse(json.dumps(data).encode())):
            with self.assertRaises(ValueError):
                app.check_github()

    def test_oversized_response_fails_closed(self):
        with patch.object(app, "urlopen", return_value=FakeResponse(b"X" * 8193)):
            with self.assertRaises(ValueError):
                app.check_github()


if __name__ == "__main__":
    unittest.main()
