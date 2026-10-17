import urllib.request
from collections.abc import Iterator
from email.message import Message

import pytest

from scripts.goal006_ghcr_digest import RegistryResolutionError, resolve_digest

DIGEST = "sha256:" + "a" * 64


class Response:
    def __init__(self, body: bytes = b"", headers: Message | None = None) -> None:
        self._body = body
        self.headers = headers or Message()

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def opener(responses: Iterator[Response], requests: list[urllib.request.Request]):
    def open_request(request: urllib.request.Request, *, timeout: int) -> Response:
        assert timeout == 15
        requests.append(request)
        return next(responses)

    return open_request


def test_resolves_release_tag_through_anonymous_pull_token() -> None:
    headers = Message()
    headers["Docker-Content-Digest"] = DIGEST.upper()
    requests: list[urllib.request.Request] = []
    digest = resolve_digest(
        "dlai-sd/goal006-private-runner",
        "sha-" + "b" * 40,
        opener=opener(iter((Response(b'{"token":"anonymous-token"}'), Response(headers=headers))), requests),
    )

    assert digest == DIGEST
    assert len(requests) == 2
    assert requests[0].full_url.startswith("https://ghcr.io/token?")
    assert "scope=repository%3Adlai-sd%2Fgoal006-private-runner%3Apull" in requests[0].full_url
    assert requests[1].get_method() == "HEAD"
    assert requests[1].get_header("Authorization") == "Bearer anonymous-token"
    assert requests[1].full_url.endswith("/manifests/sha-" + "b" * 40)


def test_verifies_digest_reference_without_trusting_reference_text() -> None:
    headers = Message()
    headers["Docker-Content-Digest"] = DIGEST
    requests: list[urllib.request.Request] = []

    assert (
        resolve_digest(
            "dlai-sd/web",
            DIGEST,
            expected_digest=DIGEST,
            opener=opener(iter((Response(b'{"token":"anonymous-token"}'), Response(headers=headers))), requests),
        )
        == DIGEST
    )


@pytest.mark.parametrize(
    ("repository", "reference"),
    (
        ("DLai-SD/web", DIGEST),
        ("dlai-sd/web", "latest/../../token"),
    ),
)
def test_rejects_invalid_registry_coordinates(repository: str, reference: str) -> None:
    with pytest.raises(RegistryResolutionError):
        resolve_digest(repository, reference)


def test_rejects_missing_token() -> None:
    with pytest.raises(RegistryResolutionError, match="token is missing"):
        resolve_digest(
            "dlai-sd/web",
            DIGEST,
            opener=opener(iter((Response(b"{}"),)), []),
        )


def test_rejects_digest_mismatch() -> None:
    headers = Message()
    headers["Docker-Content-Digest"] = "sha256:" + "c" * 64
    with pytest.raises(RegistryResolutionError, match="differs"):
        resolve_digest(
            "dlai-sd/web",
            DIGEST,
            expected_digest=DIGEST,
            opener=opener(iter((Response(b'{"token":"anonymous-token"}'), Response(headers=headers))), []),
        )
