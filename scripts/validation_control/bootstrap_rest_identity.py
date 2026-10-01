#!/usr/bin/env python3
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def require_http_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must use HTTP or HTTPS and include a hostname")
    return url


def request_json(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict[str, str] | None = None,
    idempotency_key: uuid.UUID | None = None,
) -> tuple[int, dict[str, object]]:
    headers = {"Accept": "application/json"}
    body = None
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if idempotency_key is not None:
        headers["Idempotency-Key"] = str(idempotency_key)
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, separators=(",", ":")).encode()
    request = urllib.request.Request(  # noqa: S310 - URL scheme is constrained below.
        require_http_url(url), data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        try:
            problem = json.load(error)
        except json.JSONDecodeError:
            problem = {}
        return error.code, problem


def acquire_customer_token(keycloak_url: str, username: str, password: str) -> str:
    body = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "waooaw-web-preview",
            "scope": "openid profile email",
            "username": username,
            "password": password,
        }
    ).encode()
    request = urllib.request.Request(  # noqa: S310 - URL scheme is constrained here.
        require_http_url(f"{keycloak_url}/realms/waooaw/protocol/openid-connect/token"),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        document = json.load(response)
    token = document.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Keycloak did not return an access token")
    return token


def acquire_service_token(keycloak_url: str, client_secret: str) -> str:
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": "waooaw-platform",
            "client_secret": client_secret,
        }
    ).encode()
    request = urllib.request.Request(  # noqa: S310 - URL scheme is constrained here.
        require_http_url(f"{keycloak_url}/realms/waooaw/protocol/openid-connect/token"),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        document = json.load(response)
    token = document.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Keycloak did not return a service access token")
    return token


def expect(
    result: tuple[int, dict[str, object]],
    statuses: set[int],
    operation: str,
) -> dict[str, object]:
    status, document = result
    if status not in statuses:
        code = document.get("code")
        raise RuntimeError(f"{operation} failed with HTTP {status} ({code})")
    return document


def write_token(path: Path, token: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="ascii") as stream:
        stream.write(token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--business-platform-url", default="http://business-platform:5001")
    parser.add_argument("--keycloak-url", default="http://keycloak:8080")
    parser.add_argument("--customer-token-file", type=Path, required=True)
    parser.add_argument("--service-token-file", type=Path, required=True)
    args = parser.parse_args()

    username = os.environ.get("REST_TEST_USERNAME", "dev@waooaw.local")
    password = os.environ.get("DEV_TEST_PASSWORD", "Waooaw-local-dev-only-1!")
    token = acquire_customer_token(args.keycloak_url, username, password)
    service_token = acquire_service_token(
        args.keycloak_url,
        os.environ.get("REST_TEST_SERVICE_CLIENT_SECRET", "${KEYCLOAK_CLIENT_SECRET}"),
    )
    write_token(args.service_token_file, service_token)
    session = request_json(f"{args.business_platform_url}/api/v1/identity/session", token=token)
    if session[0] == 200:
        write_token(args.customer_token_file, token)
        return
    problem = expect(session, {409}, "read unprovisioned identity session")
    if problem.get("code") != "REGISTRATION_REQUIRED":
        raise RuntimeError("identity session did not require registration")

    registration = expect(
        request_json(
            f"{args.business_platform_url}/api/v1/identity/registrations",
            method="POST",
            token=token,
            payload={"languagePreference": "en"},
            idempotency_key=uuid.UUID("10000000-0000-4000-8000-000000000001"),
        ),
        {200, 201},
        "start identity registration",
    )
    registration_id = registration.get("registrationId")
    if not isinstance(registration_id, str):
        raise RuntimeError("registration response omitted registrationId")

    expect(
        request_json(
            f"{args.business_platform_url}/api/v1/identity/registrations/{registration_id}/profile",
            method="PUT",
            token=token,
            payload={
                "displayName": "REST Contract Customer",
                "businessName": "REST Contract Workspace",
                "businessDomain": "Contract validation",
                "languagePreference": "en",
            },
            idempotency_key=uuid.UUID("10000000-0000-4000-8000-000000000002"),
        ),
        {200},
        "complete identity profile",
    )
    expect(
        request_json(
            f"{args.business_platform_url}/api/v1/identity/registrations/{registration_id}/complete",
            method="POST",
            token=token,
            idempotency_key=uuid.UUID("10000000-0000-4000-8000-000000000003"),
        ),
        {200},
        "complete identity registration",
    )
    expect(
        request_json(f"{args.business_platform_url}/api/v1/identity/session", token=token),
        {200},
        "read provisioned identity session",
    )
    write_token(args.customer_token_file, token)


if __name__ == "__main__":
    main()
