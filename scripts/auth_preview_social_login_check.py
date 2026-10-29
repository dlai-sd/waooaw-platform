#!/usr/bin/env python3
"""Drive Google/Facebook sign-in end to end against the local auth preview (AUTH_PREVIEW_IDP=local).

Steps per provider: CSRF -> provider-start (OIDC transaction reservation) -> Keycloak broker ->
mock provider login -> first-broker-login forms -> web callback -> NextAuth session -> landing page.
Public Codespaces URLs are mapped to the local forwarded ports, so no browser is required.
Credentials, tokens and cookies are never printed.
"""

from __future__ import annotations

import argparse
import html
import http.client
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ENVIRONMENT = ROOT / ".auth-preview/runtime.env"


class SocialLoginCheckError(Exception):
    pass


def runtime_settings() -> dict[str, str]:
    if not RUNTIME_ENVIRONMENT.exists():
        raise SocialLoginCheckError("no prepared preview exists; run scripts/run_auth_preview.sh start")
    settings = {}
    for line in RUNTIME_ENVIRONMENT.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        settings[key] = value
    if settings.get("AUTH_PREVIEW_IDP") != "local":
        raise SocialLoginCheckError("verify-social requires AUTH_PREVIEW_IDP=local")
    return settings


class Browser:
    def __init__(self, routes: dict[str, int]) -> None:
        self.routes = routes
        self.jars: dict[str, dict[tuple[str, str], str]] = {origin: {} for origin in routes}

    def request(self, method: str, url: str, form: dict[str, str] | None = None, headers=None):
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self.routes:
            raise SocialLoginCheckError(f"unexpected origin {origin}")
        body = urlencode(form) if form is not None else None
        request_headers = {
            "Host": parts.netloc,
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": parts.netloc,
            "User-Agent": "waooaw-auth-preview-social-check",
        }
        if body is not None:
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        jar = self.jars[origin]
        request_path = parts.path or "/"
        # Honour cookie paths: realms on one host issue same-named cookies scoped per realm path.
        matching = sorted(
            ((name, path, value) for (name, path), value in jar.items() if request_path.startswith(path)),
            key=lambda item: -len(item[1]),
        )
        if matching:
            request_headers["Cookie"] = "; ".join(f"{name}={value}" for name, _, value in matching)
        request_headers.update(headers or {})
        connection = http.client.HTTPConnection("127.0.0.1", self.routes[origin], timeout=30)
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        connection.request(method, path or "/", body=body, headers=request_headers)
        response = connection.getresponse()
        payload = response.read().decode("utf-8", errors="replace")
        for header, value in response.getheaders():
            if header.lower() != "set-cookie":
                continue
            name, _, rest = value.partition("=")
            cookie_value = rest.split(";", 1)[0]
            path_match = re.search(r"(?i);\s*path=([^;]*)", value)
            key = (name.strip(), (path_match.group(1).strip() if path_match else "/") or "/")
            expired = re.search(r"(?i)max-age=0|expires=thu, 01 jan 1970", value)
            if expired or cookie_value == "":
                jar.pop(key, None)
            else:
                jar[key] = cookie_value
        location = response.getheader("Location")
        return response.status, (urljoin(url, location) if location else None), payload


def form_action(page: str) -> tuple[str, dict[str, str]]:
    match = re.search(r'<form[^>]*action="([^"]+)"[^>]*>(.*?)</form>', page, re.S)
    if not match:
        raise SocialLoginCheckError("expected a Keycloak form but none was rendered")
    fields = {}
    for tag in re.findall(r"<input[^>]*>", match.group(2)):
        name = re.search(r'name="([^"]+)"', tag)
        if not name:
            continue
        value = re.search(r'value="([^"]*)"', tag)
        fields[name.group(1)] = html.unescape(value.group(1)) if value else ""
    return html.unescape(match.group(1)), fields


def check(provider: str, settings: dict[str, str], browser: Browser) -> str:
    origin = settings["AUTH_PREVIEW_ORIGIN"]
    idp_origin = settings["AUTH_PREVIEW_IDP_ORIGIN"]

    status, _, payload = browser.request("GET", f"{origin}/api/auth/csrf")
    if status != 200:
        raise SocialLoginCheckError(f"csrf returned {status}")
    csrf = json.loads(payload)["csrfToken"]

    query = "?max_age=0&prompt=select_account" if provider == "google" else ""
    status, _, payload = browser.request(
        "POST",
        f"{origin}/api/auth/signin/keycloak-{provider}{query}",
        form={"csrfToken": csrf, "callbackUrl": f"{origin}/home", "waooawIntent": "LOGIN", "json": "true"},
        headers={"Origin": origin},
    )
    if status != 200:
        raise SocialLoginCheckError(f"provider-start returned {status} {payload[:120]}")
    authorization = json.loads(payload).get("url", "")
    if not authorization.startswith(f"{idp_origin}/realms/waooaw/protocol/openid-connect/auth?"):
        raise SocialLoginCheckError("provider-start did not redirect to the Keycloak authorization endpoint")
    if f"kc_idp_hint={provider}" not in authorization:
        raise SocialLoginCheckError("provider-start redirect lacks the broker hint")
    print(f"  {provider}: provider-start redirected to Keycloak (OIDC transaction reserved)")

    url, method, form = authorization, "GET", None
    logged_in = False
    for _ in range(20):
        status, location, page = browser.request(method, url, form=form)
        if location and location.startswith(f"{origin}/"):
            url = location
            break
        if location:
            url, method, form = location, "GET", None
            continue
        if status != 200:
            raise SocialLoginCheckError(f"identity provider step returned {status} at {urlsplit(url).path}")
        action, fields = form_action(page)
        if "username" in fields and "password" in fields and not logged_in:
            fields.update(username=f"{provider}-customer@waooaw.local", password=settings["AUTH_PREVIEW_IDP_USER_PASSWORD"])
            logged_in = True
        else:
            for name, value in (
                ("email", f"{provider}-customer@waooaw.local"),
                ("firstName", "Preview"),
                ("lastName", provider.title()),
            ):
                if name in fields and not fields[name]:
                    fields[name] = value
        url, method, form = urljoin(url, action), "POST", fields
    else:
        raise SocialLoginCheckError("identity provider flow did not return to the web callback")
    if "/api/auth/callback/" not in url:
        raise SocialLoginCheckError(f"identity provider returned to {urlsplit(url).path} instead of the callback")
    print(f"  {provider}: broker login completed; returned to web callback")

    status, location, _ = browser.request("GET", url)
    if status not in (302, 303, 307) or not location:
        raise SocialLoginCheckError(f"callback returned {status}")
    if "/api/auth/error" in location or "/login" in urlsplit(location).path:
        raise SocialLoginCheckError(f"callback was rejected ({urlsplit(location).path}?{urlsplit(location).query})")
    status, _, payload = browser.request("GET", f"{origin}/api/auth/session")
    session = json.loads(payload or "{}")
    if status != 200 or session.get("authenticated") is not True:
        cookies = sorted({name for name, _ in browser.jars[origin]})
        raise SocialLoginCheckError(
            f"callback to {urlsplit(location).path} did not establish a NextAuth session "
            f"(session status {status}; authenticated={session.get('authenticated')!r}; keys {sorted(session)}; cookies {', '.join(cookies) or 'none'})"
        )
    print(f"  {provider}: callback consumed the OIDC transaction; session established")

    url = location
    for _ in range(8):
        status, location, _ = browser.request("GET", url)
        if not location:
            break
        url = location
    landing = urlsplit(url).path
    if status != 200 or landing.startswith("/login") or "/auth/error" in landing:
        raise SocialLoginCheckError(f"post-login landing {landing} returned {status}")
    print(f"  {provider}: signed-in landing {landing} returned 200")
    return landing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["google", "facebook"], action="append")
    args = parser.parse_args()
    try:
        settings = runtime_settings()
        routes = {
            settings["AUTH_PREVIEW_ORIGIN"]: int(settings["AUTH_PREVIEW_PORT"]),
            settings["AUTH_PREVIEW_IDP_ORIGIN"]: int(settings["AUTH_PREVIEW_IDP_PORT"]),
        }
        for provider in args.provider or ["google", "facebook"]:
            check(provider, settings, Browser(routes))
    except SocialLoginCheckError as failure:
        print(f"auth-preview social sign-in check failed: {failure}", file=sys.stderr)
        return 1
    print("auth-preview social sign-in check: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
