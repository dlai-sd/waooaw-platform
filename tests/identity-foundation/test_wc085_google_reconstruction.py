import base64
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from scripts.verify_google_deployment import verify

pytestmark = pytest.mark.skipif(os.environ.get("WC085_RECONSTRUCTION") != "true", reason="Docker reconstruction fixture only")
BASE = "https://ca-demo-identity-edge.local.waooaw.test"
ISSUER = BASE + "/realms/waooaw"


def test_fresh_import_recreates_google_client_flow_and_default_role() -> None:
    runtime = json.loads(json.loads(Path("/fixture/identity-runtime.json").read_text()))
    manifest = json.loads((Path(__file__).resolve().parents[2] /
        "infrastructure/identity-config/environments/demo.json").read_text())

    def check_environment(value: object, prefix: str) -> None:
        if isinstance(value, dict):
            for name, child in value.items():
                check_environment(child, prefix + "__" + name)
        elif isinstance(value, list):
            for position, child in enumerate(value):
                check_environment(child, prefix + "__" + str(position))
        else:
            expected = str(value).lower() if isinstance(value, bool) else str(value)
            assert runtime[prefix.lower()] == expected

    runtime = {name.lower(): value for name, value in runtime.items()}
    check_environment(manifest, "IdentityEnvironment")
    assert runtime["identityenvironment__providers__3__readinessevidencereference"] == ""
    deadline = time.monotonic() + 120
    while True:
        try:
            with urlopen(ISSUER + "/.well-known/openid-configuration", timeout=5) as response:
                assert json.load(response)["issuer"] == ISSUER
            break
        except URLError:
            if time.monotonic() >= deadline:
                raise

    credentials = urlencode({
        "client_id": "admin-cli", "grant_type": "password", "username": "fixture-admin",
        "password": "Synthetic-Admin-Only-123",
    }).encode()
    with urlopen(BASE + "/realms/master/protocol/openid-connect/token", data=credentials, timeout=10) as response:
        token = json.load(response)["access_token"]

    def admin(path: str, data: object | None = None):
        request = Request(BASE + "/admin/realms/waooaw/" + path, headers={
            "Authorization": "Bearer " + token, "Content-Type": "application/json",
        }, data=json.dumps(data).encode() if data is not None else None)
        with urlopen(request, timeout=10) as response:
            content = response.read()
            return json.loads(content) if content else None

    provider = admin("identity-provider/instances/google")
    assert provider["enabled"] is True
    assert provider["config"]["clientId"] == "synthetic.apps.googleusercontent.com"
    assert provider["config"]["clientSecret"] != "${GOOGLE_CLIENT_SECRET}"
    assert provider["firstBrokerLoginFlowAlias"] == "first broker login"
    clients = admin("clients?clientId=waooaw-web")
    assert clients[0]["redirectUris"] == [
        "https://ca-demo-web.local.waooaw.test/api/auth/callback/keycloak",
        "https://ca-demo-web.local.waooaw.test/api/auth/callback/keycloak-google",
    ]
    assert clients[0]["attributes"]["pkce.code.challenge.method"] == "S256"
    assert admin("")["ssoSessionMaxLifespan"] == 28800
    admin("users", {"username": "synthetic-new-customer", "enabled": True, "emailVerified": True})
    customer = admin("users?username=synthetic-new-customer&exact=true")[0]
    admin("users/" + customer["id"] + "/federated-identity/google", {
        "identityProvider": "google",
        "userId": "Google-Opaque-" + customer["id"],
        "userName": "synthetic-new-customer",
    })
    roles = admin("users/" + customer["id"] + "/role-mappings/realm/composite")
    assert "customer" in {role["name"] for role in roles}
    assert "founder" not in {role["name"] for role in roles}

    reader_client = admin("clients?clientId=waooaw-bp-identity-reader")[0]
    realm_management = admin("clients?clientId=realm-management")[0]
    reader_service_account = admin("clients/" + reader_client["id"] + "/service-account-user")
    assigned_reader_roles = admin(
        "users/" + reader_service_account["id"] + "/role-mappings/clients/" + realm_management["id"]
    )
    assert {role["name"] for role in assigned_reader_roles} == {"view-users"}
    reader_mapper = next(mapper for mapper in reader_client["protocolMappers"]
                         if mapper["name"] == "realm-management-view-users")
    assert reader_mapper["protocolMapper"] == "oidc-hardcoded-role-mapper"
    assert reader_mapper["config"]["role"] == "realm-management.view-users"

    reader_credentials = urlencode({
        "client_id": "waooaw-bp-identity-reader",
        "client_secret": "Synthetic-Reader-Only-123",
        "grant_type": "client_credentials",
    }).encode()
    with urlopen(ISSUER + "/protocol/openid-connect/token", data=reader_credentials, timeout=10) as response:
        reader_token_response = json.load(response)
    assert reader_token_response["token_type"] == "Bearer"
    assert reader_token_response["expires_in"] <= 60
    assert "refresh_token" not in reader_token_response
    reader_token = reader_token_response["access_token"]
    payload_segment = reader_token.split(".")[1]
    payload = json.loads(base64.urlsafe_b64decode(payload_segment + "=" * (-len(payload_segment) % 4)))
    assert payload["exp"] - payload["iat"] <= 60
    assert payload["resource_access"]["realm-management"]["roles"] == ["view-users"]

    def reader(path: str, method: str = "GET", data: object | None = None):
        request = Request(BASE + "/admin/realms/waooaw/" + path, headers={
            "Authorization": "Bearer " + reader_token, "Content-Type": "application/json",
        }, data=json.dumps(data).encode() if data is not None else None, method=method)
        with urlopen(request, timeout=10) as response:
            content = response.read()
            return json.loads(content) if content else None

    assert reader("users/" + customer["id"])["id"] == customer["id"]
    binding = reader("users/" + customer["id"] + "/federated-identity")
    assert binding == [{
        "identityProvider": "google",
        "userId": "Google-Opaque-" + customer["id"],
        "userName": "synthetic-new-customer",
    }]
    forbidden = [
        ("PUT", "users/" + customer["id"], {"enabled": False}),
        ("PUT", "users/" + customer["id"] + "/reset-password", {
            "type": "password", "temporary": False, "value": "Not-Allowed-123!",
        }),
        ("DELETE", "users/" + customer["id"] + "/federated-identity/google", None),
        ("POST", "users/" + customer["id"] + "/role-mappings/realm", [admin("roles/founder")]),
    ]
    for method, path, body in forbidden:
        with pytest.raises(HTTPError) as denied:
            reader(path, method, body)
        assert denied.value.code == 403
        denied.value.close()

    Path("/evidence/reader-actor-id").write_text(customer["id"])
    evidence = verify(ISSUER, "https://ca-demo-web.local.waooaw.test")
    evidence.update(
        fresh_import=True,
        default_customer_role_verified=True,
        reader_exact_gets_verified=True,
        reader_writes_denied=True,
        reader_token_seconds=payload["exp"] - payload["iat"],
        credentials="synthetic",
    )
    Path("/evidence/generation-" + os.environ["WC085_GENERATION"] + ".json").write_text(json.dumps(evidence, indent=2) + "\n")