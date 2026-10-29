#!/usr/bin/env python3
"""Generate the local Keycloak realms used by `run_auth_preview.sh` when AUTH_PREVIEW_IDP=local.

The `waooaw` realm mirrors the Demo `waooaw-web-preview` client from Terraform. Google and Facebook
are brokered under their Demo aliases to two mock OIDC realms (`mock-google`, `mock-facebook`) in the
same Keycloak, so the full provider-start -> broker -> callback -> session path runs without
third-party credentials.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_REALM = ROOT / "infrastructure/keycloak/waooaw-realm.json"
INTERNAL_KEYCLOAK = "http://keycloak:8080"
PROVIDERS = {
    "google": {"display": "Continue with Google", "flow": "google verified email first login", "trust": True},
    "facebook": {"display": "Continue with Facebook", "flow": "first broker login", "trust": False},
}


def preview_client(origin: str) -> dict:
    return {
        "clientId": "waooaw-web-preview",
        "name": "WAOOAW Codespaces Authentication Preview (local identity)",
        "enabled": True,
        "publicClient": True,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "redirectUris": [f"{origin}/api/auth/callback/keycloak"]
        + [f"{origin}/api/auth/callback/keycloak-{alias}" for alias in PROVIDERS],
        "webOrigins": [origin],
        "attributes": {"pkce.code.challenge.method": "S256", "post.logout.redirect.uris": f"{origin}/login"},
        "protocolMappers": [
            {
                "name": "tenant_id_mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-hardcoded-claim-mapper",
                "config": {
                    "claim.name": "tenant_id",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true",
                    "claim.value": "00000000-0000-0000-0000-000000000001",
                },
            },
            {
                "name": "audience_mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-audience-mapper",
                "config": {
                    "included.client.audience": "waooaw-platform",
                    "id.token.claim": "false",
                    "access.token.claim": "true",
                },
            },
            {
                "name": "realm_roles_mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-realm-role-mapper",
                "config": {
                    "claim.name": "realm_access.roles",
                    "jsonType.label": "String",
                    "multivalued": "true",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true",
                },
            },
            {
                "name": "identity_provider_session",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usersessionmodel-note-mapper",
                "config": {
                    "user.session.note": "identity_provider",
                    "claim.name": "idp",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "false",
                },
            },
        ],
    }


def broker(alias: str, idp_origin: str, secret: str) -> dict:
    realm = f"mock-{alias}"
    settings = PROVIDERS[alias]
    return {
        "alias": alias,
        "displayName": settings["display"],
        "providerId": "oidc",
        "enabled": True,
        "trustEmail": settings["trust"],
        "storeToken": False,
        "addReadTokenRoleOnCreate": False,
        "firstBrokerLoginFlowAlias": settings["flow"],
        "config": {
            "issuer": f"{idp_origin}/realms/{realm}",
            "authorizationUrl": f"{idp_origin}/realms/{realm}/protocol/openid-connect/auth",
            "tokenUrl": f"{INTERNAL_KEYCLOAK}/realms/{realm}/protocol/openid-connect/token",
            "userInfoUrl": f"{INTERNAL_KEYCLOAK}/realms/{realm}/protocol/openid-connect/userinfo",
            "jwksUrl": f"{INTERNAL_KEYCLOAK}/realms/{realm}/protocol/openid-connect/certs",
            "useJwksUrl": "true",
            "validateSignature": "true",
            "clientAuthMethod": "client_secret_post",
            "clientId": "waooaw-broker",
            "clientSecret": secret,
            "defaultScope": "openid email profile",
            "syncMode": "IMPORT",
        },
    }


def mock_realm(alias: str, idp_origin: str, secret: str, password: str) -> dict:
    return {
        "realm": f"mock-{alias}",
        "displayName": f"Mock {alias.title()} (local auth preview only)",
        "enabled": True,
        "sslRequired": "external",
        "loginWithEmailAllowed": True,
        "clients": [
            {
                "clientId": "waooaw-broker",
                "enabled": True,
                "publicClient": False,
                "secret": secret,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": False,
                "redirectUris": [f"{idp_origin}/realms/waooaw/broker/{alias}/endpoint"],
            }
        ],
        "users": [
            {
                "username": f"{alias}-customer@waooaw.local",
                "email": f"{alias}-customer@waooaw.local",
                "emailVerified": True,
                "firstName": "Preview",
                "lastName": alias.title(),
                "enabled": True,
                "credentials": [{"type": "password", "value": password, "temporary": False}],
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True, help="web preview HTTPS origin")
    parser.add_argument("--idp-origin", required=True, help="local identity HTTPS origin")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    broker_secret = os.environ["AUTH_PREVIEW_IDP_BROKER_SECRET"]
    password = os.environ["AUTH_PREVIEW_IDP_USER_PASSWORD"]

    realm = copy.deepcopy(json.loads(BASE_REALM.read_text(encoding="utf-8")))
    realm["clients"] = [client for client in realm["clients"] if client["clientId"] != "waooaw-web-preview"]
    realm["clients"].append(preview_client(args.origin))
    realm["identityProviders"] = [broker(alias, args.idp_origin, broker_secret) for alias in PROVIDERS]
    realm["identityProviderMappers"] = []

    args.output.mkdir(parents=True, exist_ok=True)
    documents = {"waooaw-realm.json": realm}
    documents.update(
        {f"mock-{alias}-realm.json": mock_realm(alias, args.idp_origin, broker_secret, password) for alias in PROVIDERS}
    )
    for name, document in documents.items():
        target = args.output / name
        target.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        target.chmod(0o644)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
