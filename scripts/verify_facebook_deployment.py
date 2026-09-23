"""Verify the public Facebook broker redirect without exchanging codes or reading secrets."""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.cookiejar
import json
import secrets
from http.client import RemoteDisconnected
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, build_opener


META_APP_ID = "2590813568086235"
META_AUTHORIZATION_HOSTS = {"graph.facebook.com", "www.facebook.com", "web.facebook.com"}
BROWSER_HEADERS = [
    ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
    ("User-Agent", "Mozilla/5.0 AppleWebKit/537.36 Chrome/124.0 Safari/537.36"),
]


class VerificationError(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def redirect_failure_reason(location: str, issuer: str) -> str | None:
    parsed = urlsplit(location)
    query = parse_qs(parsed.query)
    scopes = set(query.get("scope", [""])[0].split())
    checks = (
        (parsed.scheme == "https", "non_https_redirect"),
        (parsed.hostname in META_AUTHORIZATION_HOSTS, "untrusted_authorization_host"),
        (parsed.port in (None, 443), "unexpected_authorization_port"),
        (parsed.username is None and parsed.password is None, "redirect_contains_credentials"),
        (query.get("client_id") == [META_APP_ID], "meta_app_id_mismatch"),
        (query.get("redirect_uri") == [issuer + "/broker/facebook/endpoint"], "broker_callback_mismatch"),
        (query.get("response_type") == ["code"], "response_type_mismatch"),
        ({"email", "public_profile"}.issubset(scopes), "required_scope_missing"),
        (bool(query.get("state", [""])[0]), "state_missing"),
    )
    return next((reason for passed, reason in checks if not passed), None)


def validate_redirect(location: str, issuer: str) -> bool:
    return redirect_failure_reason(location, issuer) is None


def provider_failure_reason(status: int, body: bytes) -> str:
    try:
        payload = json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and str(error.get("code")) == "191":
            return "facebook_oauth_191_domain_configuration"
    text = body.decode("utf-8", errors="replace").lower()
    if status == 400 and "191" in text and "domain" in text:
        return "facebook_oauth_191_domain_configuration"
    return f"broker_http_{status}"


def verify_redirect_chain(issuer: str, target: str) -> None:
    opener = build_opener(NoRedirect(), HTTPCookieProcessor(http.cookiejar.CookieJar()))
    opener.addheaders = BROWSER_HEADERS
    for _attempt in range(5):
        if urlsplit(target).scheme != "https":
            raise ValueError("Broker requests require HTTPS")
        try:
            with opener.open(target, timeout=30):
                raise VerificationError("authorization_html_response")
        except HTTPError as error:
            if error.code not in (301, 302, 303, 307, 308):
                raise VerificationError(provider_failure_reason(error.code, error.read(65536))) from None
            target = urljoin(target, error.headers.get("Location", ""))
        if validate_redirect(target, issuer):
            break
        parsed = urlsplit(target)
        if parsed.scheme != "https" or parsed.netloc != urlsplit(issuer).netloc:
            raise VerificationError(redirect_failure_reason(target, issuer) or "unexpected_redirect_destination")
    else:
        raise VerificationError("broker_redirect_limit_exceeded")


def verify(issuer: str, web_url: str) -> dict[str, object]:
    if any(urlsplit(value).scheme != "https" or urlsplit(value).query or urlsplit(value).fragment for value in (issuer, web_url)):
        raise ValueError("Verification requires exact HTTPS endpoints")
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    target = (
        issuer
        + "/protocol/openid-connect/auth?"
        + urlencode(
            {
                "client_id": "waooaw-web",
                "redirect_uri": web_url + "/api/auth/callback/keycloak-facebook",
                "response_type": "code",
                "scope": "openid email profile",
                "kc_idp_hint": "facebook",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": secrets.token_urlsafe(24),
                "nonce": secrets.token_urlsafe(24),
            }
        )
    )
    for initiation_attempt in range(3):
        try:
            verify_redirect_chain(issuer, target)
            break
        except (RemoteDisconnected, TimeoutError, URLError) as error:
            if initiation_attempt == 2:
                raise VerificationError("broker_transport_retries_exhausted") from error
    return {
        "provider": "FACEBOOK",
        "issuer": issuer,
        "callback": issuer + "/broker/facebook/endpoint",
        "web_callback": web_url + "/api/auth/callback/keycloak-facebook",
        "redirect_verified": True,
        "real_user_sign_in_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--web-url", required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--keycloak-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence: dict[str, object]
    try:
        evidence = verify(args.issuer.rstrip("/"), args.web_url.rstrip("/"))
    except VerificationError as error:
        evidence = {
            "provider": "FACEBOOK",
            "redirect_verified": False,
            "real_user_sign_in_verified": False,
            "failure_reason": error.reason,
        }
        evidence.update(release_sha=args.release_sha, keycloak_revision=args.keycloak_revision)
        args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print("Facebook deployment verification failed: " + error.reason)
        return 1
    evidence.update(release_sha=args.release_sha, keycloak_revision=args.keycloak_revision)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("Facebook redirect verified; real-account acceptance remains separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
