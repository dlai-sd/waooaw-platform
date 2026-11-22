"""Key Vault credential consumers: a hot-reloaded outbound TLS context and a snapshot-backed inbound authorizer."""

# Implements: ADR-046 Amendment 1 (in-process credential reload) for AIR
# constitutional_basis: C-001, C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import logging
import os
import ssl
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

from employment_auth import DelegatedContext, EmploymentAuthError, EmploymentWorkloadAuth, ReplayStore
from runtime_workload_credentials import CredentialHolder, CredentialSnapshot

logger = logging.getLogger(__name__)

DEFAULT_KEY_TMPFS = "/dev/shm"  # noqa: S108


class HotReloadClientTls:
    """Client SSLContext whose chain and roots follow verified snapshots; the private key touches tmpfs only."""

    def __init__(self, holder: CredentialHolder, key_directory: Path) -> None:
        self.key_directory = key_directory
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        # The peer is matched by workload URI after the handshake, because cloud leaves carry no DNS name.
        self.context.check_hostname = False
        self.context.verify_mode = ssl.CERT_REQUIRED
        self._roots: set[str] = set()
        holder.subscribe(self.install)

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
        logger.info("client_tls certificate_loaded serial_digest=%s", snapshot.serial_digest)


class SnapshotWorkloadAuth:
    """Authorizes one caller workload against the CURRENT snapshot's grants and published delegation keys."""

    def __init__(self, holder: CredentialHolder, caller_workload: str) -> None:
        self._holder = holder
        self._caller = caller_workload
        self._replay_store = ReplayStore()

    def _current(self) -> EmploymentWorkloadAuth:
        snapshot = self._holder.current()
        if snapshot is None:
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED")
        caller_uri = str(snapshot.manifest["workloads"][self._caller]["identity_uri"])
        now = int(time.time())
        keys = {
            identity: entry.public_key
            for identity, entry in snapshot.delegation_keys.items()
            if identity[0] == caller_uri and now >= entry.activate_after
        }
        grants = frozenset(grant for grant in snapshot.grants if grant.caller_uri == caller_uri)
        return EmploymentWorkloadAuth(grants, keys, snapshot.trust_domain, snapshot.audience, self._replay_store)

    def authorize(self, *args: Any, **kwargs: Any) -> DelegatedContext:
        return self._current().authorize(*args, **kwargs)
