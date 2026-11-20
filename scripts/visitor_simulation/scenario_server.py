# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C7-01, C7-02
# Constitutional basis: C-048, C-049, C-059, C-063
"""Loopback JSON server that hosts a scenario fake (funding or pricing) on 127.0.0.1 only."""

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

AppHandler = Callable[[str, str, dict[str, str], dict[str, Any] | None], tuple[int, dict[str, str], dict[str, Any]]]


class ScenarioServer:
    """Serves ``handle(method, path, headers, body)`` over HTTP; the port is chosen by the operating system."""

    def __init__(self, handle: AppHandler) -> None:
        self._handle = handle
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def base_url(self) -> str:
        assert self._httpd is not None, "server not started"
        return f"http://127.0.0.1:{self._httpd.server_address[1]}"

    def start(self) -> "ScenarioServer":
        app = self

        class Handler(BaseHTTPRequestHandler):
            def _serve(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = {"$invalid": True}
                with app._lock:  # one step at a time keeps the fake deterministic
                    status, headers, payload = app._handle(self.command, self.path, dict(self.headers.items()), body)
                data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = _serve  # noqa: N815
            do_POST = _serve  # noqa: N815

            def log_message(self, format: str, *args: Any) -> None:
                return

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._httpd.daemon_threads = True
        self._thread = threading.Thread(target=self._httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> "ScenarioServer":
        return self if self._httpd is not None else self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
