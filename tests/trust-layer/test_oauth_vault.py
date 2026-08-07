# Implements: work-contracts/WC-038-trust-layer-s2-provider-registry-oauth-vault.md §WC038-07
# constitutional_basis: C-076 (≥90% test coverage), ADR-014 (no token in logs), ADR-021

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add src/trust-layer to path so oauth_vault is importable (matches ai-runtime test convention)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "trust-layer"))

# Patch Azure SDK at module level before importing oauth_vault — prevents real AKV connections.
with patch("azure.identity.DefaultAzureCredential"), \
     patch("azure.keyvault.secrets.SecretClient"):
    from oauth_vault.main import app
    from oauth_vault.models import TokenData

from oauth_vault.vault_client import VaultClient
from oauth_vault.refresh_scheduler import RefreshScheduler

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_token_data(
    access_token: str = "tok_abc123",
    refresh_token: str | None = "ref_xyz",
    expires_at: datetime | None = None,
    provider_name: str = "meta",
    contract_id: str = "ctr-001",
) -> TokenData:
    return TokenData(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at or datetime.now(tz=timezone.utc) + timedelta(hours=8),
        provider_name=provider_name,
        contract_id=contract_id,
    )


def _inject(vault=None, ce=None, scheduler=None) -> None:
    """Inject test doubles into the module-level app.state."""
    if vault is not None:
        app.state.vault_client = vault
    if ce is not None:
        app.state.ce_client = ce
    if scheduler is not None:
        app.state.scheduler = scheduler


def _reset() -> None:
    """Clear injected state between tests."""
    for attr in ("vault_client", "ce_client", "scheduler"):
        if hasattr(app.state, attr):
            delattr(app.state, attr)


# ─── CCT-VAULT-01: Token value absent from all log output ─────────────────────


class TestCCTVault01TokenNotInLogs:
    """
    CCT-VAULT-01: ADR-014 — the raw token value (access_token, refresh_token) must NEVER
    appear in any log record on store, retrieve, or error paths.
    """

    def test_store_does_not_log_access_token(self, caplog):
        vault_mock = MagicMock()
        vault_mock.store_token = AsyncMock(return_value=None)
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            with caplog.at_level(logging.DEBUG):
                resp = client.post(
                    "/tokens/ctr-001/meta",
                    json={
                        "access_token": "SUPER_SECRET_TOKEN_12345",
                        "refresh_token": "SUPER_REFRESH_TOKEN_67890",
                    },
                )
        _reset()

        assert resp.status_code == 201
        full_log = " ".join(r.getMessage() for r in caplog.records)
        assert "SUPER_SECRET_TOKEN_12345" not in full_log, \
            "access_token must never appear in logs (ADR-014, OWASP A02)"
        assert "SUPER_REFRESH_TOKEN_67890" not in full_log, \
            "refresh_token must never appear in logs (ADR-014)"

    def test_retrieve_does_not_log_access_token(self, caplog):
        token_data = _make_token_data(access_token="RETRIEVE_SECRET_999")
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=token_data)
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            with caplog.at_level(logging.DEBUG):
                resp = client.get("/tokens/ctr-001/meta")
        _reset()

        assert resp.status_code == 200
        full_log = " ".join(r.getMessage() for r in caplog.records)
        assert "RETRIEVE_SECRET_999" not in full_log, \
            "retrieved access_token must not appear in any log record (ADR-014)"

    def test_error_path_does_not_log_token(self, caplog):
        """Exception handler must not log token fragments from stack traces."""
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(side_effect=RuntimeError("tok=LEAKED_SECRET_abc"))
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            with caplog.at_level(logging.DEBUG):
                resp = client.get("/tokens/ctr-001/meta")
        _reset()

        # Global handler returns sanitised error — raw exception not surfaced to caller.
        assert resp.status_code == 500
        assert resp.json() == {"error": "VAULT_ERROR", "code": "TOKEN_UNAVAILABLE"}
        full_log = " ".join(r.getMessage() for r in caplog.records)
        assert "LEAKED_SECRET_abc" not in full_log, \
            "exception message with token fragment must not appear in logs (ADR-014)"


# ─── CCT-VAULT-02: Revoke calls CE before AKV delete ─────────────────────────


class TestCCTVault02RevokeCEFirst:
    """
    CCT-VAULT-02: C-003 (authority licensed) — DELETE /tokens/{c}/{p} must call CE
    evidence recording BEFORE calling AKV delete. Reversed order is a constitutional violation.
    """

    def test_revoke_calls_ce_before_akv_delete(self):
        call_order: list[str] = []

        class FakeCEClient:
            async def record_revocation(self, contract_id: str, provider_name: str) -> bool:
                call_order.append("CE")
                return True

        vault_mock = MagicMock()

        async def _delete_side_effect(path: str) -> None:
            call_order.append("AKV")

        vault_mock.delete_token = AsyncMock(side_effect=_delete_side_effect)
        _inject(vault=vault_mock, ce=FakeCEClient())

        with TestClient(app) as client:
            resp = client.delete("/tokens/ctr-001/meta")
        _reset()

        assert resp.status_code == 200
        assert call_order == ["CE", "AKV"], \
            "CE must be called before AKV delete (C-003 Evidence First requirement)"

    def test_revoke_blocked_when_ce_unavailable(self):
        """Revoke must fail with 503 if CE cannot record evidence (C-003 non-negotiable)."""

        class FailingCEClient:
            async def record_revocation(self, contract_id: str, provider_name: str) -> bool:
                return False

        vault_mock = MagicMock()
        vault_mock.delete_token = AsyncMock(return_value=None)
        _inject(vault=vault_mock, ce=FailingCEClient())

        with TestClient(app) as client:
            resp = client.delete("/tokens/ctr-001/meta")
        _reset()

        assert resp.status_code == 503
        assert resp.json()["detail"]["error"] == "CE_UNAVAILABLE"
        # AKV delete must NOT have been called.
        vault_mock.delete_token.assert_not_called()


# ─── CCT-VAULT-03: EXPIRING_SOON triggers refresh ─────────────────────────────


class TestCCTVault03RefreshTriggered:
    """
    CCT-VAULT-03: ADR-021 §3 — When a token has status EXPIRING_SOON, the refresh
    scheduler must call the provider's token refresh endpoint.
    """

    @pytest.mark.asyncio
    async def test_expiring_soon_triggers_provider_refresh(self):
        expiring_token = _make_token_data(
            access_token="old_tok",
            refresh_token="valid_refresh",
            expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1),  # < 2h = EXPIRING_SOON
        )

        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=expiring_token)
        vault_mock.store_token = AsyncMock(return_value=None)

        refresh_called = False

        async def mock_post(url, **kwargs):
            nonlocal refresh_called
            refresh_called = True
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "access_token": "new_tok_refreshed",
                "refresh_token": "new_refresh",
                "expires_in": 3600,
            }
            return response

        from oauth_vault.refresh_scheduler import RefreshScheduler

        scheduler = RefreshScheduler(
            vault_alias="test-vault",
            pr_internal_url="http://pr:5003",
        )
        scheduler._vault = vault_mock
        scheduler.register("ctr-001", "meta")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_client_cls.return_value = mock_client

            await scheduler.run_once()

        assert refresh_called, \
            "Provider refresh endpoint must be called for EXPIRING_SOON token (ADR-021 §3)"
        vault_mock.store_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_failure_notifies_pr(self):
        """On refresh failure, PR must receive PLATFORM_TOKEN_EXPIRED event."""
        expiring_token = _make_token_data(
            expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1),
        )

        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=expiring_token)
        vault_mock.store_token = AsyncMock(return_value=None)

        pr_notified = False

        async def mock_post(url, **kwargs):
            nonlocal pr_notified
            if "events" in url:
                pr_notified = True
                r = MagicMock()
                r.status_code = 202
                return r
            # provider refresh fails
            r = MagicMock()
            r.status_code = 401
            return r

        from oauth_vault.refresh_scheduler import RefreshScheduler

        scheduler = RefreshScheduler(
            vault_alias="test-vault",
            pr_internal_url="http://pr:5003",
        )
        scheduler._vault = vault_mock
        scheduler.register("ctr-001", "meta")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_client_cls.return_value = mock_client

            await scheduler.run_once()

        assert pr_notified, "PR must be notified with PLATFORM_TOKEN_EXPIRED on refresh failure"


# ─── CCT-TOKEN-HEALTH-01: Health returns correct status ───────────────────────


class TestCCTTokenHealth01:
    """
    CCT-TOKEN-HEALTH-01: GET /tokens/health/{c}/{p} returns correct status for each state.
    """

    def test_health_valid(self):
        token_data = _make_token_data(
            expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=8),
        )
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=token_data)
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            resp = client.get("/tokens/health/ctr-001/meta")
        _reset()

        assert resp.status_code == 200
        assert resp.json()["status"] == "VALID"

    def test_health_expiring_soon(self):
        token_data = _make_token_data(
            expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1),
        )
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=token_data)
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            resp = client.get("/tokens/health/ctr-001/meta")
        _reset()

        assert resp.status_code == 200
        assert resp.json()["status"] == "EXPIRING_SOON"

    def test_health_expired(self):
        token_data = _make_token_data(
            expires_at=datetime.now(tz=timezone.utc) - timedelta(hours=1),
        )
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=token_data)
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            resp = client.get("/tokens/health/ctr-001/meta")
        _reset()

        assert resp.status_code == 200
        assert resp.json()["status"] == "EXPIRED"

    def test_health_not_connected(self):
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=None)
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            resp = client.get("/tokens/health/ctr-001/meta")
        _reset()

        assert resp.status_code == 200
        assert resp.json()["status"] == "NOT_CONNECTED"

    def test_health_api_key_no_expiry_is_valid(self):
        """API_KEY tokens with no expiry are always VALID (ADR-021 §1)."""
        token_data = _make_token_data(
            expires_at=None,
            provider_name="openai",
        )
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=token_data)
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            resp = client.get("/tokens/health/ctr-001/openai")
        _reset()

        assert resp.status_code == 200
        assert resp.json()["status"] == "VALID"


# ─── VaultClient unit tests (C-076 coverage — vault_client.py) ───────────────


class TestVaultClientUnit:
    """Direct unit tests for VaultClient methods. Mocks Azure SDK at the instance level."""

    def _make_vault_client(self) -> VaultClient:
        with patch("azure.identity.DefaultAzureCredential"), \
             patch("azure.keyvault.secrets.SecretClient"):
            return VaultClient("test-kv")

    @pytest.mark.asyncio
    async def test_store_token_calls_set_secret(self):
        vc = self._make_vault_client()
        vc._client.set_secret = MagicMock(return_value=None)
        await vc.store_token("providers/ctr-001/meta", _make_token_data())
        vc._client.set_secret.assert_called_once()
        args = vc._client.set_secret.call_args[0]
        assert "access_token" in args[1]  # payload JSON contains field name, not value

    @pytest.mark.asyncio
    async def test_retrieve_token_success(self):
        vc = self._make_vault_client()
        secret_mock = MagicMock()
        secret_mock.value = json.dumps({
            "access_token": "tok_unit", "refresh_token": None,
            "expires_at": None, "provider_name": "meta",
            "contract_id": "ctr-001", "extra_data": {},
        })
        vc._client.get_secret = MagicMock(return_value=secret_mock)
        result = await vc.retrieve_token("providers/ctr-001/meta")
        assert result is not None
        assert result.access_token == "tok_unit"

    @pytest.mark.asyncio
    async def test_retrieve_token_not_found_returns_none(self):
        vc = self._make_vault_client()
        vc._client.get_secret = MagicMock(side_effect=Exception("ResourceNotFound"))
        result = await vc.retrieve_token("providers/ctr-001/meta")
        assert result is None

    @pytest.mark.asyncio
    async def test_retrieve_token_corrupt_payload_returns_none(self):
        vc = self._make_vault_client()
        secret_mock = MagicMock()
        secret_mock.value = "not-valid-json{"
        vc._client.get_secret = MagicMock(return_value=secret_mock)
        result = await vc.retrieve_token("providers/ctr-001/meta")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_token_calls_begin_delete_secret(self):
        vc = self._make_vault_client()
        vc._client.begin_delete_secret = MagicMock(return_value=None)
        await vc.delete_token("providers/ctr-001/meta")
        vc._client.begin_delete_secret.assert_called_once()


# ─── Retrieve path coverage (tokens.py: expired, inline refresh) ─────────────


class TestTokensRetrievePaths:
    """Covers retrieve_token expired/EXPIRING_SOON paths and _try_refresh. C-076."""

    def test_retrieve_expired_returns_410(self):
        token = _make_token_data(expires_at=datetime.now(tz=timezone.utc) - timedelta(hours=1))
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=token)
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            resp = client.get("/tokens/ctr-001/meta")
        _reset()

        assert resp.status_code == 410
        assert resp.json()["detail"]["error"] == "TOKEN_EXPIRED"

    def test_retrieve_not_found_returns_404(self):
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=None)
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            resp = client.get("/tokens/ctr-001/meta")
        _reset()

        assert resp.status_code == 404

    def test_retrieve_expiring_soon_inline_refresh_success(self):
        """EXPIRING_SOON + refresh_token → _try_refresh called; response has new token."""
        expiring = _make_token_data(
            access_token="old_tok",
            refresh_token="ref_xyz",
            expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1),
        )
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=expiring)
        vault_mock.store_token = AsyncMock(return_value=None)
        _inject(vault=vault_mock)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            resp_mock = MagicMock()
            resp_mock.status_code = 200
            resp_mock.json.return_value = {"access_token": "new_tok", "expires_in": 86400}
            mock_client.post = AsyncMock(return_value=resp_mock)
            mock_cls.return_value = mock_client

            with TestClient(app) as client:
                resp = client.get("/tokens/ctr-001/meta")
        _reset()

        assert resp.status_code == 200
        assert resp.json()["access_token"] == "new_tok"
        vault_mock.store_token.assert_called_once()

    def test_retrieve_expiring_soon_no_refresh_token_returns_expiring_soon(self):
        """No refresh_token → returns EXPIRING_SOON without attempting refresh."""
        expiring = _make_token_data(
            refresh_token=None,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1),
        )
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=expiring)
        _inject(vault=vault_mock)

        with TestClient(app) as client:
            resp = client.get("/tokens/ctr-001/meta")
        _reset()

        assert resp.status_code == 200
        assert resp.json()["status"] == "EXPIRING_SOON"

    def test_revoke_unregisters_from_scheduler(self):
        """Successful revoke must unregister token from scheduler (ADR-021 §3)."""
        vault_mock = MagicMock()
        vault_mock.delete_token = AsyncMock(return_value=None)
        scheduler_mock = MagicMock()

        class OKCEClient:
            async def record_revocation(self, *_: object) -> bool:
                return True

        _inject(vault=vault_mock, ce=OKCEClient())

        with TestClient(app) as client:
            app.state.scheduler = scheduler_mock  # inject after lifespan runs
            resp = client.delete("/tokens/ctr-001/meta")
        _reset()

        assert resp.status_code == 200
        scheduler_mock.unregister.assert_called_once_with("ctr-001", "meta")

    def test_revoke_ce_http_fallback_503_when_ce_unreachable(self):
        """Without injected ce_client, HTTP fallback to CE → unreachable → 503 (ADR-031 fail-safe)."""
        vault_mock = MagicMock()
        vault_mock.delete_token = AsyncMock(return_value=None)
        _inject(vault=vault_mock)  # no ce_client → triggers HTTP fallback path

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("ConnectionRefused"))
            mock_cls.return_value = mock_client

            with TestClient(app) as client:
                resp = client.delete("/tokens/ctr-001/meta")
        _reset()

        assert resp.status_code == 503
        vault_mock.delete_token.assert_not_called()


# ─── Scheduler edge-case coverage (refresh_scheduler.py) ─────────────────────



class TestSchedulerEdgeCases:
    """Edge-case coverage for RefreshScheduler. C-076."""

    def _make_scheduler(self) -> RefreshScheduler:
        return RefreshScheduler("test-kv", "http://pr:5003")

    @pytest.mark.asyncio
    async def test_valid_token_not_refreshed(self):
        """Scheduler skips tokens with VALID status — no store_token call."""
        valid_token = _make_token_data(
            expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=8),
        )
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=valid_token)
        vault_mock.store_token = AsyncMock(return_value=None)

        scheduler = self._make_scheduler()
        scheduler._vault = vault_mock
        scheduler.register("ctr-001", "meta")

        await scheduler.run_once()

        vault_mock.store_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_expired_no_refresh_token_notifies_pr(self):
        """EXPIRED token with no refresh_token → PR notified directly."""
        expired_token = _make_token_data(
            refresh_token=None,
            expires_at=datetime.now(tz=timezone.utc) - timedelta(hours=1),
        )
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=expired_token)

        pr_notified = False

        async def _mock_post(url: str, **_: object) -> MagicMock:
            nonlocal pr_notified
            if "events" in url:
                pr_notified = True
            r = MagicMock()
            r.status_code = 202
            return r

        scheduler = self._make_scheduler()
        scheduler._vault = vault_mock
        scheduler.register("ctr-001", "meta")

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=_mock_post)
            mock_cls.return_value = mock_client

            await scheduler.run_once()

        assert pr_notified, "PR must receive PLATFORM_TOKEN_EXPIRED for expired token"

    @pytest.mark.asyncio
    async def test_notify_pr_exception_is_non_fatal(self):
        """PR notification failure must be caught and logged, never propagate."""
        expired_token = _make_token_data(
            refresh_token=None,
            expires_at=datetime.now(tz=timezone.utc) - timedelta(hours=1),
        )
        vault_mock = MagicMock()
        vault_mock.retrieve_token = AsyncMock(return_value=expired_token)

        scheduler = self._make_scheduler()
        scheduler._vault = vault_mock
        scheduler.register("ctr-001", "meta")

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("PR down"))
            mock_cls.return_value = mock_client

            await scheduler.run_once()  # must not raise
