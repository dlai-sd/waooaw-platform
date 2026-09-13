"""Verify the public Facebook broker redirect without exchanging codes or reading secrets."""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.cookiejar
import json
import secrets
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, build_opener


META_APP_ID = "2590813568086235"
META_AUTHORIZATION_HOSTS = {"graph.facebook.com", "www.facebook.com", "web.facebook.com"}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def validate_redirect(location: str, issuer: str) -> bool:
    parsed = urlsplit(location)
    query = parse_qs(parsed.query)
    scopes = set(query.get("scope", [""])[0].split())
    return (
        parsed.scheme == "https"
        and parsed.hostname in META_AUTHORIZATION_HOSTS
        and parsed.port in (None, 443)
        and parsed.username is None
        and parsed.password is None
        and query.get("client_id") == [META_APP_ID]
        and query.get("redirect_uri") == [issuer + "/broker/facebook/endpoint"]
        and query.get("response_type") == ["code"]
        and {"email", "public_profile"}.issubset(scopes)
        and bool(query.get("state", [""])[0])
    )


def verify(issuer: str, web_url: str) -> dict[str, object]:
    if any(urlsplit(value).scheme != "https" or urlsplit(value).query or urlsplit(value).fragment for value in (issuer, web_url)):
        raise ValueError("Verification requires exact HTTPS endpoints")
    opener = build_opener(NoRedirect(), HTTPCookieProcessor(http.cookiejar.CookieJar()))
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    target = issuer + "/protocol/openid-connect/auth?" + urlencode({
        "client_id": "waooaw-web", "redirect_uri": web_url + "/api/auth/callback/keycloak-facebook",
        "response_type": "code", "scope": "openid email profile", "kc_idp_hint": "facebook",
        "code_challenge": challenge, "code_challenge_method": "S256",
        "state": secrets.token_urlsafe(24), "nonce": secrets.token_urlsafe(24),
    })
    for _attempt in range(5):
        if urlsplit(target).scheme != "https":
            raise ValueError("Broker requests require HTTPS")
        try:
            with opener.open(target, timeout=30):
                raise ValueError("Expected a broker redirect, received an HTML response")
        except HTTPError as error:
            if error.code not in (301, 302, 303, 307, 308):
                raise ValueError("Broker returned HTTP " + str(error.code)) from None
            target = urljoin(target, error.headers.get("Location", ""))
        if validate_redirect(target, issuer):
            break
        parsed = urlsplit(target)
        if parsed.scheme != "https" or parsed.netloc != urlsplit(issuer).netloc:
            raise ValueError("Unexpected redirect destination")
    else:
        raise ValueError("Broker redirect limit exceeded")
    return {
        "provider": "FACEBOOK", "issuer": issuer,
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
    try:
        evidence = verify(args.issuer.rstrip("/"), args.web_url.rstrip("/"))
    except Exception as error:
        print("Facebook deployment verification failed: " + type(error).__name__)
        return 1
    evidence.update(release_sha=args.release_sha, keycloak_revision=args.keycloak_revision)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("Facebook redirect verified; real-account acceptance remains separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
