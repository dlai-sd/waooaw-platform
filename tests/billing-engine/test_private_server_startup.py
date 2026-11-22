# Implements: WC-150 R002
# constitutional_basis: C-059, C-076, ADR-046

"""Start the billing private listener on a real uvicorn.Config; only the final network serve is replaced."""

from __future__ import annotations

import ssl
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

import private_server


async def stand_in_app(scope, receive, send) -> None:  # pragma: no cover - never served
    raise AssertionError("the network serve is replaced in this test")


def write_credentials(root: Path, workload: str) -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, workload)])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    pem = certificate.public_bytes(serialization.Encoding.PEM)
    (root / "workloads" / workload).mkdir(parents=True)
    (root / "trust").mkdir()
    (root / "workloads" / workload / "tls-cert.pem").write_bytes(pem)
    (root / "workloads" / workload / "tls-key.pem").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
    )
    (root / "trust" / "ca-bundle.pem").write_bytes(pem)


def test_billing_private_listener_starts_from_the_credential_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    write_credentials(tmp_path, "billing-engine")
    monkeypatch.setitem(sys.modules, "main", SimpleNamespace(create_app=lambda: stand_in_app))
    monkeypatch.setenv("WAOOAW_WID_SOURCE", "directory")
    monkeypatch.setenv("WAOOAW_WORKLOAD_CREDENTIALS", str(tmp_path))
    configs: list[uvicorn.Config] = []
    monkeypatch.setattr(uvicorn.Server, "run", lambda self, sockets=None: configs.append(self.config))

    private_server.main()

    assert len(configs) == 1
    assert isinstance(configs[0].ssl, ssl.SSLContext)
    assert configs[0].ssl.minimum_version == ssl.TLSVersion.TLSv1_2
    assert configs[0].ssl.verify_mode == ssl.CERT_REQUIRED
