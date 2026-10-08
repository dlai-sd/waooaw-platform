from __future__ import annotations

import ssl
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

import main
import private_server
from employment_auth import PEER_CERTIFICATE_STATE_KEY
from mtls_protocol import MutualTlsH11Protocol


def _protocol(application):
    protocol = object.__new__(MutualTlsH11Protocol)
    protocol.app = application
    protocol.connections = set()
    protocol.logger = Mock(level=100)
    return protocol


@pytest.mark.asyncio
async def test_air_private_transport_injects_authenticated_peer_certificate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_scope = None

    async def application(scope, _receive, _send) -> None:
        nonlocal observed_scope
        observed_scope = scope

    ssl_object = Mock()
    ssl_object.getpeercert.return_value = b"authenticated-der"
    transport = Mock()
    transport.get_extra_info.side_effect = lambda name: ssl_object if name == "ssl_object" else None
    protocol = _protocol(application)
    monkeypatch.setattr(
        "mtls_protocol.H11Protocol.connection_made",
        lambda _self, _transport: None,
    )

    protocol.connection_made(transport)
    await protocol.app({"type": "http", "state": {}}, Mock(), Mock())

    assert observed_scope["state"][PEER_CERTIFICATE_STATE_KEY] == b"authenticated-der"
    transport.close.assert_not_called()


@pytest.mark.parametrize(
    "ssl_object",
    [None, SimpleNamespace(getpeercert=lambda binary_form: None)],
)
def test_air_private_transport_rejects_unauthenticated_connections(
    monkeypatch: pytest.MonkeyPatch,
    ssl_object,
) -> None:
    transport = Mock()
    transport.get_extra_info.side_effect = lambda name: ssl_object if name == "ssl_object" else None
    protocol = _protocol(Mock())
    parent_connection = Mock()
    monkeypatch.setattr("mtls_protocol.H11Protocol.connection_made", parent_connection)

    protocol.connection_made(transport)

    transport.close.assert_called_once_with()
    parent_connection.assert_not_called()


def test_air_private_listener_uses_air_identity_and_mandatory_mtls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    credentials = tmp_path / "credentials"
    monkeypatch.setenv("WAOOAW_WORKLOAD_CREDENTIALS", str(credentials))

    config = private_server.private_listener_config()

    assert config.http is MutualTlsH11Protocol
    assert config.ssl_cert_reqs == ssl.CERT_REQUIRED
    assert config.ssl_keyfile == str(credentials / "workloads/ai-runtime/tls-key.pem")
    assert config.ssl_certfile == str(credentials / "workloads/ai-runtime/tls-cert.pem")
    assert config.ssl_ca_certs == str(credentials / "trust/ca-bundle.pem")


def test_air_private_listener_main_enforces_tls_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tls = MagicMock()
    config = MagicMock(ssl=tls)
    server = MagicMock()
    monkeypatch.setattr(private_server, "private_listener_config", lambda: config)
    monkeypatch.setattr(private_server.uvicorn, "Server", MagicMock(return_value=server))

    private_server.main()

    assert tls.minimum_version == ssl.TLSVersion.TLSv1_2
    config.load.assert_not_called()
    server.run.assert_called_once_with()


@pytest.mark.asyncio
async def test_air_lifespan_owns_repository_startup_and_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[bool] = []

    async def close() -> None:
        closed.append(True)

    repository = SimpleNamespace(close=close)

    async def connect(database_url: str):
        assert database_url.endswith("/waooaw")
        return repository

    monkeypatch.setenv("DATABASE_URL", "postgresql://air@postgres/waooaw")
    monkeypatch.setattr(main.EmploymentPatchRepository, "connect", connect)
    application = SimpleNamespace(state=SimpleNamespace())

    async with main.lifespan(application):
        assert application.state.employment_patch_repository is repository

    assert application.state.employment_patch_repository is None
    assert closed == [True]


@pytest.mark.asyncio
async def test_air_lifespan_without_database_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    application = SimpleNamespace(state=SimpleNamespace())

    async with main.lifespan(application):
        assert application.state.employment_patch_repository is None


def test_air_private_listener_rejects_missing_tls_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = MagicMock(ssl=None)
    monkeypatch.setattr(private_server, "private_listener_config", lambda: config)

    with pytest.raises(RuntimeError, match="requires TLS"):
        private_server.main()

    config.load.assert_called_once_with()


def test_air_private_listener_accepts_tls_loaded_on_demand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tls = MagicMock()
    config = MagicMock(ssl=None)
    config.load.side_effect = lambda: setattr(config, "ssl", tls)
    server = MagicMock()
    monkeypatch.setattr(private_server, "private_listener_config", lambda: config)
    monkeypatch.setattr(private_server.uvicorn, "Server", MagicMock(return_value=server))

    private_server.main()

    config.load.assert_called_once_with()
    assert tls.minimum_version == ssl.TLSVersion.TLSv1_2
    server.run.assert_called_once_with()
