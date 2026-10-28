"""Exercise native ARM operation syntax using the pinned Azure CLI against local HTTP."""

import json
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar


class Handler(BaseHTTPRequestHandler):
    seen: ClassVar[list[str]] = []

    def do_POST(self):
        self.seen.append(self.path)
        if "/denied/" in self.path:
            status, body = 403, {"error": {"code": "AuthorizationFailed", "message": "rehearsal denial"}}
        elif "/pending/" in self.path:
            status, body = 202, None
        else:
            status, body = 200, {"properties": {"runningStatus": "Stopped" if "/stop?" in self.path else "Running"}}
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if body is not None:
            self.wfile.write(json.dumps(body).encode())

    def log_message(self, *_args):
        pass


class AzureCLIRehearsal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def request(self, name, operation):
        path = (
            "/subscriptions/2ed11839-6a0f-4eaa-bd94-44ca96ff5d84/resourceGroups/"
            f"waooaw-demo-rg/providers/Microsoft.App/containerApps/{name}/{operation}?api-version=2025-01-01"
        )
        result = subprocess.run(
            [
                "az",
                "rest",
                "--method",
                "post",
                "--url",
                f"http://127.0.0.1:{self.server.server_port}{path}",
                "--skip-authorization-header",
                "--output",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn(path, Handler.seen)
        return result

    def test_native_start_and_stop(self):
        for operation, target in [("start", "Running"), ("stop", "Stopped")]:
            with self.subTest(operation=operation):
                result = self.request("ca-demo-web", operation)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["properties"]["runningStatus"], target)

    def test_async_acceptance_is_not_an_error_or_completion_proof(self):
        result = self.request("pending", "stop")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_authorization_failure_is_nonzero(self):
        result = self.request("denied", "stop")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AuthorizationFailed", result.stderr)


if __name__ == "__main__":
    unittest.main()
