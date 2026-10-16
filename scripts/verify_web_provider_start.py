"""Verify that the deployed Web BFF starts an exact provider-neutral OIDC ceremony."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener


PROVIDERS = {
    "google": "keycloak-google",
    "facebook": "keycloak-facebook",
}


def validate_authorization_url(
    target: str,
    issuer: str,
    web_url: str,
    provider: str,
    expected_client_id: str = "waooaw-web",
) -> bool:
    parsed = urlsplit(target)
    issuer_url = urlsplit(issuer)
    query = parse_qs(parsed.query)
    provider_id = PROVIDERS[provider]
    return (
        parsed.scheme == "https"
        and parsed.netloc == issuer_url.netloc
        and parsed.path == issuer_url.path.rstrip("/") + "/protocol/openid-connect/auth"
        and query.get("client_id") == [expected_client_id]
        and query.get("redirect_uri") == [f"{web_url}/api/auth/callback/{provider_id}"]
        and query.get("kc_idp_hint") == [provider]
        and query.get("response_type") == ["code"]
        and bool(query.get("state", [""])[0])
        and bool(query.get("code_challenge", [""])[0])
    )


def verify(
    issuer: str,
    web_url: str,
    provider: str,
    request_url: str | None = None,
    expected_client_id: str = "waooaw-web",
) -> dict[str, object]:
    if provider not in PROVIDERS:
        raise ValueError("Unsupported provider")
    if any(urlsplit(value).scheme != "https" or urlsplit(value).query or urlsplit(value).fragment for value in (issuer, web_url)):
        raise ValueError("Verification requires exact HTTPS endpoints")
    request_origin = request_url or web_url
    request_endpoint = urlsplit(request_origin)
    if (
        request_endpoint.scheme not in ("http", "https")
        or request_endpoint.query
        or request_endpoint.fragment
        or request_endpoint.path not in ("", "/")
    ):
        raise ValueError("Request endpoint must be an exact HTTP(S) origin")

    cookie_policy = http.cookiejar.DefaultCookiePolicy(secure_protocols=("https", "http")) if request_url else None
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar(policy=cookie_policy)))
    with opener.open(f"{request_origin.rstrip('/')}/api/auth/csrf", timeout=30) as response:
        csrf = json.load(response).get("csrfToken")
    if not isinstance(csrf, str) or not csrf:
        raise ValueError("Web CSRF token is unavailable")

    provider_id = PROVIDERS[provider]
    request = Request(  # noqa: S310 - request origin is constrained to an exact HTTP(S) origin above.
        f"{request_origin.rstrip('/')}/api/auth/signin/{provider_id}",
        data=urlencode(
            {
                "csrfToken": csrf,
                "callbackUrl": "/login?returnTo=%2Fhome",
                "waooawIntent": "login",
                "json": "true",
            }
        ).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with opener.open(request, timeout=30) as response:
        result = json.load(response)
    target = result.get("url")
    if not isinstance(target, str) or not validate_authorization_url(
        target,
        issuer,
        web_url,
        provider,
        expected_client_id,
    ):
        raise ValueError("Web provider start did not return the accepted OIDC authorization route")

    return {
        "provider": provider.upper(),
        "web_origin": web_url,
        "request_origin": request_origin,
        "issuer": issuer,
        "client_id": expected_client_id,
        "web_callback": f"{web_url}/api/auth/callback/{provider_id}",
        "provider_start_verified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--web-url", required=True)
    parser.add_argument("--request-url")
    parser.add_argument("--expected-client-id", default="waooaw-web")
    parser.add_argument("--provider", choices=tuple(PROVIDERS), required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        evidence = verify(
            args.issuer.rstrip("/"),
            args.web_url.rstrip("/"),
            args.provider,
            args.request_url.rstrip("/") if args.request_url else None,
            args.expected_client_id,
        )
    except Exception as error:
        print(f"{args.provider.title()} Web provider-start verification failed: {type(error).__name__}")
        return 1
    evidence["release_sha"] = args.release_sha
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"{args.provider.title()} Web provider start verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
