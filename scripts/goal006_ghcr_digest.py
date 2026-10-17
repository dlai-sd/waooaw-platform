#!/usr/bin/env python3
"""Resolve a public GHCR manifest reference to its immutable digest."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

GHCR_AUTH_URL = "https://ghcr.io/token"
GHCR_REGISTRY_URL = "https://ghcr.io"
MANIFEST_ACCEPT = ", ".join(
    (
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
    )
)
REPOSITORY = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)+")
REFERENCE = re.compile(r"(?:sha256:[0-9a-f]{64}|[A-Za-z0-9_][A-Za-z0-9._-]{0,127})")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


class RegistryResolutionError(RuntimeError):
    """Raised when GHCR does not provide a complete immutable binding."""


def _read_json(
    request: urllib.request.Request,
    *,
    opener: Callable[..., Any],
) -> dict[str, Any]:
    with opener(request, timeout=15) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise RegistryResolutionError("GHCR token response is not an object")
    return payload


def resolve_digest(
    repository: str,
    reference: str,
    *,
    expected_digest: str | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> str:
    if REPOSITORY.fullmatch(repository) is None:
        raise RegistryResolutionError("GHCR repository is invalid")
    if REFERENCE.fullmatch(reference) is None:
        raise RegistryResolutionError("GHCR manifest reference is invalid")
    if expected_digest is not None and DIGEST.fullmatch(expected_digest) is None:
        raise RegistryResolutionError("expected GHCR digest is invalid")

    token_query = urllib.parse.urlencode(
        {
            "service": "ghcr.io",
            "scope": f"repository:{repository}:pull",
        }
    )
    token_request = urllib.request.Request(f"{GHCR_AUTH_URL}?{token_query}")  # noqa: S310
    token_response = _read_json(token_request, opener=opener)
    token = str(token_response.get("token", ""))
    if not token:
        raise RegistryResolutionError("GHCR pull token is missing")

    manifest_request = urllib.request.Request(  # noqa: S310
        f"{GHCR_REGISTRY_URL}/v2/{repository}/manifests/{reference}",
        method="HEAD",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": MANIFEST_ACCEPT,
        },
    )
    with opener(manifest_request, timeout=15) as response:
        digest = str(response.headers.get("Docker-Content-Digest", "")).lower()
    if DIGEST.fullmatch(digest) is None:
        raise RegistryResolutionError("GHCR manifest digest is missing or invalid")
    if expected_digest is not None and digest != expected_digest:
        raise RegistryResolutionError("GHCR manifest digest differs from the expected digest")
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--expected-digest")
    arguments = parser.parse_args()
    try:
        digest = resolve_digest(
            arguments.repository,
            arguments.reference,
            expected_digest=arguments.expected_digest,
        )
    except (RegistryResolutionError, json.JSONDecodeError, OSError) as error:
        parser.error(str(error))
    print(digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
