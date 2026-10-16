from __future__ import annotations

import io
import json
from urllib.parse import urlencode

from scripts import verify_web_provider_start


class Response:
    def __init__(self, value: dict[str, object]) -> None:
        self._body = io.BytesIO(json.dumps(value).encode())

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)


class Opener:
    def __init__(self, provider: str) -> None:
        self.provider = provider
        self.requests: list[object] = []

    def open(self, request, timeout: int):
        self.requests.append(request)
        if isinstance(request, str):
            return Response({"csrfToken": "csrf-token"})
        provider_id = verify_web_provider_start.PROVIDERS[self.provider]
        query = urlencode(
            {
                "client_id": "waooaw-web",
                "redirect_uri": f"https://cp.demo.waooaw.com/api/auth/callback/{provider_id}",
                "kc_idp_hint": self.provider,
                "response_type": "code",
                "state": "state",
                "code_challenge": "challenge",
            }
        )
        return Response({"url": "https://auth.demo.waooaw.com/realms/waooaw/protocol/openid-connect/auth?" + query})


def test_verifies_google_and_facebook_through_the_web_bff(monkeypatch) -> None:
    for provider in verify_web_provider_start.PROVIDERS:
        opener = Opener(provider)
        monkeypatch.setattr(
            verify_web_provider_start,
            "build_opener",
            lambda *_handlers, opener=opener: opener,
        )

        evidence = verify_web_provider_start.verify(
            "https://auth.demo.waooaw.com/realms/waooaw",
            "https://cp.demo.waooaw.com",
            provider,
        )

        assert evidence["provider_start_verified"] is True
        assert len(opener.requests) == 2


def test_rejects_a_direct_or_wrong_provider_redirect(monkeypatch) -> None:
    class WrongOpener(Opener):
        def open(self, request, timeout: int):
            if isinstance(request, str):
                return Response({"csrfToken": "csrf-token"})
            return Response({"url": "https://accounts.google.com/o/oauth2/auth?state=state"})

    monkeypatch.setattr(verify_web_provider_start, "build_opener", lambda *_handlers: WrongOpener("google"))

    try:
        verify_web_provider_start.verify(
            "https://auth.demo.waooaw.com/realms/waooaw",
            "https://cp.demo.waooaw.com",
            "google",
        )
    except ValueError as error:
        assert "accepted OIDC authorization route" in str(error)
    else:
        raise AssertionError("wrong redirect was accepted")


def test_allows_internal_transport_while_validating_public_callback(monkeypatch) -> None:
    opener = Opener("google")
    monkeypatch.setattr(verify_web_provider_start, "build_opener", lambda *_handlers: opener)

    evidence = verify_web_provider_start.verify(
        "https://auth.demo.waooaw.com/realms/waooaw",
        "https://cp.demo.waooaw.com",
        "google",
        "http://auth-preview:3000",
    )

    assert evidence["request_origin"] == "http://auth-preview:3000"
    assert opener.requests[0] == "http://auth-preview:3000/api/auth/csrf"


def test_rejects_internal_transport_paths() -> None:
    try:
        verify_web_provider_start.verify(
            "https://auth.demo.waooaw.com/realms/waooaw",
            "https://cp.demo.waooaw.com",
            "google",
            "http://auth-preview:3000/internal",
        )
    except ValueError as error:
        assert "exact HTTP" in str(error)
    else:
        raise AssertionError("request path was accepted")
