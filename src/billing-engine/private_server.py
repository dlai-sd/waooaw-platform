"""Start the WBE Relationship Workspace private listener with mandatory mTLS."""

# Implements: ADR-046 sections 3.1, 3.2, 4.1, 5.1, 10.1, and 12 (D4, D5)
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

import asyncio
import logging
import os
import shutil
import ssl
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import uvicorn
from mtls_protocol import MutualTlsH11Protocol, validated_protocol
from billing_workload_credentials import (
    MINIMUM_REFRESH_SECONDS,
    SOURCE_KEYVAULT,
    CredentialHolder,
    CredentialSnapshot,
    credential_source,
    keyvault_runtime,
)

logger = logging.getLogger(__name__)

TLS_KEY_DIRECTORY = "/dev/shm"  # noqa: S108 - tmpfs, so private key material never reaches disk
DEFAULT_RELOAD_SECONDS = 30


def private_listener_config() -> uvicorn.Config:
    credentials = Path(os.environ["WAOOAW_WORKLOAD_CREDENTIALS"])
    workload = credentials / "workloads" / "billing-engine"
    return uvicorn.Config(
        "main:create_app", factory=True, host=os.getenv("WBE_PRIVATE_HOST", "0.0.0.0"),  # noqa: S104
        port=int(os.getenv("WBE_PRIVATE_PORT", "5444")), http=MutualTlsH11Protocol,
        ssl_keyfile=str(workload / "tls-key.pem"), ssl_certfile=str(workload / "tls-cert.pem"),
        ssl_ca_certs=str(credentials / "trust" / "ca-bundle.pem"), ssl_cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLS_SERVER)


class WorkloadTlsContext:
    """One long-lived server SSLContext whose certificate chain follows the current verified snapshot."""

    def __init__(self, holder: CredentialHolder, key_directory: str | Path = TLS_KEY_DIRECTORY) -> None:
        self.holder = holder
        self._key_directory = Path(key_directory)
        self._applied: str | None = None
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.sni_callback = self._refuse_when_unavailable

    def _refuse_when_unavailable(self, _ssl_object: Any, _server_name: str | None, _context: ssl.SSLContext) -> int | None:
        return ssl.ALERT_DESCRIPTION_INTERNAL_ERROR if self.holder.current() is None else None

    def _apply(self, snapshot: CredentialSnapshot) -> None:
        if not self._key_directory.is_dir():
            raise RuntimeError("ADR-046 private listener requires a tmpfs key directory")
        directory = Path(tempfile.mkdtemp(prefix="wid-", dir=self._key_directory))
        try:
            paths = (directory / "key.pem", directory / "chain.pem")
            for path, content in zip(paths, (snapshot.tls_key_pem, snapshot.tls_chain_pem), strict=True):
                with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as handle:
                    handle.write(content)
            self.context.load_cert_chain(certfile=paths[1], keyfile=paths[0])
        finally:
            shutil.rmtree(directory, ignore_errors=True)
        self.context.load_verify_locations(cadata=snapshot.ca_bundle_pem.decode("ascii"))
        self._applied = snapshot.digest

    def reload(self) -> bool:
        snapshot = self.holder.current()
        if snapshot is None or snapshot.digest == self._applied:
            return False
        self._apply(snapshot)
        logger.info("private_listener decision=reload serial=%s bundle_version=%s", snapshot.serial_digest, snapshot.bundle_version)
        return True


class ReloadingServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config, tls: WorkloadTlsContext, interval_seconds: int = DEFAULT_RELOAD_SECONDS) -> None:
        super().__init__(config)
        self._tls = tls
        self._interval = interval_seconds

    async def _reload_loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                self._tls.reload()
            except Exception:  # keep serving with the chain already loaded
                logger.error("private_listener decision=reload_failed")

    async def serve(self, sockets: list[Any] | None = None) -> None:
        reloader = asyncio.create_task(self._reload_loop())
        try:
            await super().serve(sockets=sockets)
        finally:
            reloader.cancel()


def keyvault_listener_config(tls: WorkloadTlsContext) -> uvicorn.Config:
    return uvicorn.Config(
        "main:create_app", factory=True, host=os.getenv("WBE_PRIVATE_HOST", "0.0.0.0"),  # noqa: S104
        port=int(os.getenv("WBE_PRIVATE_PORT", "5444")), http=validated_protocol(tls.holder.validate_peer))


def await_first_snapshot(
    refresh: Callable[[], str], holder: CredentialHolder, sleep: Callable[[float], None] = time.sleep
) -> None:
    while holder.current() is None:
        refresh()
        if holder.current() is None:
            sleep(MINIMUM_REFRESH_SECONDS)


def run_keyvault_listener() -> None:
    runtime = keyvault_runtime()
    if runtime.refresher is None:
        raise RuntimeError("ADR-046 private listener requires valid WAOOAW_WID_* configuration")
    await_first_snapshot(runtime.refresher.refresh_once, runtime.holder)
    tls = WorkloadTlsContext(runtime.holder, os.getenv("WBE_TLS_KEY_DIRECTORY", TLS_KEY_DIRECTORY))
    tls.reload()
    config = keyvault_listener_config(tls)
    config.load()
    config.ssl = tls.context
    ReloadingServer(config, tls, int(os.getenv("WBE_TLS_RELOAD_SECONDS", str(DEFAULT_RELOAD_SECONDS)))).run()


def main() -> None:
    if credential_source() == SOURCE_KEYVAULT:
        run_keyvault_listener()
        return
    config = private_listener_config()
    config.load()
    if config.ssl is None:
        raise RuntimeError("ADR-046 private listener requires TLS")
    config.ssl.minimum_version = ssl.TLSVersion.TLSv1_2
    uvicorn.Server(config).run()


if __name__ == "__main__":
    main()