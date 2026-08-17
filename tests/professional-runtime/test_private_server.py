# Implements: ADR-046 sections 3.1, 3.2, 4.1, and 10.1
# constitutional_basis: C-026, C-059, C-063, C-076, C-083, C-084, C-085

from __future__ import annotations

import ssl
from unittest.mock import MagicMock

from mtls_protocol import MutualTlsH11Protocol
import private_server
from private_server import private_listener_config


def test_private_listener_requires_peer_certificate_and_custom_protocol(monkeypatch, tmp_path) -> None:
    credentials = tmp_path / "credentials"
    monkeypatch.setenv("WAOOAW_WORKLOAD_CREDENTIALS", str(credentials))

    config = private_listener_config()

    assert config.http is MutualTlsH11Protocol
    assert config.ssl_cert_reqs == ssl.CERT_REQUIRED
    assert config.ssl_keyfile == str(credentials / "workloads/professional-runtime/tls-key.pem")
    assert config.ssl_certfile == str(credentials / "workloads/professional-runtime/tls-cert.pem")
    assert config.ssl_ca_certs == str(credentials / "trust/ca-bundle.pem")


def test_private_listener_main_enforces_tls_floor_and_runs(monkeypatch) -> None:
    tls = MagicMock()
    config = MagicMock(ssl=tls)
    server = MagicMock()
    monkeypatch.setattr(private_server, "private_listener_config", lambda: config)
    monkeypatch.setattr(private_server.uvicorn, "Server", MagicMock(return_value=server))

    private_server.main()

    assert tls.minimum_version == ssl.TLSVersion.TLSv1_2
    config.load.assert_not_called()
    server.run.assert_called_once_with()
