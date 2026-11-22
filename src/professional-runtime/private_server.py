"""Start the PR WC-034 F4 private listener with mandatory ADR-046 mTLS."""

# Implements: ADR-046 sections 3.1, 3.2, 4.1, 10.1 and Amendment 1 (cloud credential delivery)
# constitutional_basis: C-001, C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import asyncio
import logging
import os
import ssl
import tempfile
from contextlib import suppress
from pathlib import Path

import uvicorn
from cryptography import x509

from mtls_protocol import MutualTlsH11Protocol
from runtime_workload_credentials import (
    SOURCE_KEYVAULT,
    CredentialHolder,
    CredentialSnapshot,
    authenticate_peer,
    shared_holder,
)

logger = logging.getLogger(__name__)

DEFAULT_KEY_TMPFS = "/dev/shm"  # noqa: S108


def keyvault_source() -> bool:
    return os.getenv("WAOOAW_WID_SOURCE", "directory").strip().lower() == SOURCE_KEYVAULT


class CredentialGatedProtocol(MutualTlsH11Protocol):
    """Refuse every connection unless the current snapshot is live and the peer chains to the CURRENT bundle roots."""

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        holder = shared_holder()
        ssl_object = transport.get_extra_info("ssl_object")
        peer_certificate = ssl_object.getpeercert(binary_form=True) if ssl_object is not None else None
        try:
            if holder is None or not peer_certificate:
                raise ValueError("no credential or peer certificate")
            authenticate_peer(holder, x509.load_der_x509_certificate(peer_certificate))
        except Exception:
            logger.warning("private_listener connection_refused reason=PEER_OR_CREDENTIAL_REJECTED")
            transport.close()
            return
        super().connection_made(transport)


class HotReloadTlsContext:
    """Server SSLContext whose certificate chain is swapped in place from verified snapshots, via tmpfs only."""

    def __init__(self, holder: CredentialHolder, key_directory: Path) -> None:
        self.holder = holder
        self.key_directory = key_directory
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.sni_callback = self._refuse_when_unavailable
        self._roots: set[str] = set()

    def _refuse_when_unavailable(self, _ssl_object: object, _server_name: str | None, _context: object) -> int | None:
        if self.holder.current() is None:
            return ssl.ALERT_DESCRIPTION_HANDSHAKE_FAILURE
        return None

    def install(self, snapshot: CredentialSnapshot) -> None:
        if snapshot.ca_bundle_pem not in self._roots:
            self.context.load_verify_locations(cadata=snapshot.ca_bundle_pem)
            self._roots.add(snapshot.ca_bundle_pem)
        if not self.key_directory.is_dir():
            raise RuntimeError("private key tmpfs directory is unavailable")
        descriptor, name = tempfile.mkstemp(prefix="wid-", suffix=".pem", dir=self.key_directory)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(snapshot.tls_key_pem)
                handle.write(b"\n")
                handle.write(snapshot.tls_chain_pem.encode("ascii"))
            self.context.load_cert_chain(name)
        finally:
            with suppress(FileNotFoundError):
                Path(name).unlink()
        logger.info("private_listener certificate_loaded serial_digest=%s", snapshot.serial_digest)


def private_listener_config() -> uvicorn.Config:
    host = os.getenv("PR_PRIVATE_HOST", "0.0.0.0")  # noqa: S104
    port = int(os.getenv("PR_PRIVATE_PORT", "5443"))
    if keyvault_source():
        return uvicorn.Config("main:app", host=host, port=port, http=CredentialGatedProtocol)
    credentials = Path(os.environ["WAOOAW_WORKLOAD_CREDENTIALS"])
    workload = credentials / "workloads" / "professional-runtime"
    return uvicorn.Config(
        "main:app",
        host=host,
        port=port,
        http=MutualTlsH11Protocol,
        ssl_keyfile=str(workload / "tls-key.pem"),
        ssl_certfile=str(workload / "tls-cert.pem"),
        ssl_ca_certs=str(credentials / "trust" / "ca-bundle.pem"),
        ssl_cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLS_SERVER,
    )


def main() -> None:
    config = private_listener_config()
    if config.ssl is None:
        config.load()
    if config.ssl is None and keyvault_source():
        holder = shared_holder()
        if holder is None:
            raise RuntimeError("ADR-046 private listener requires a credential holder")
        tls = HotReloadTlsContext(holder, Path(os.getenv("WAOOAW_WID_KEY_TMPFS", DEFAULT_KEY_TMPFS)))
        holder.subscribe(tls.install)
        config.ssl = tls.context
    if config.ssl is None:
        raise RuntimeError("ADR-046 private listener requires TLS")
    config.ssl.minimum_version = ssl.TLSVersion.TLSv1_2
    uvicorn.Server(config).run()


if __name__ == "__main__":
    main()
