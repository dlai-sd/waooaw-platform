import json
import os
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from scripts.verify_google_deployment import verify

pytestmark = pytest.mark.skipif(os.environ.get("WC085_RECONSTRUCTION") != "true", reason="Docker reconstruction fixture only")
BASE = "https://ca-demo-identity-edge.local.waooaw.test"
ISSUER = BASE + "/realms/waooaw"


def test_fresh_import_recreates_google_client_flow_and_default_role() -> None:
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
    assert clients[0]["redirectUris"] == ["https://ca-demo-web.local.waooaw.test/api/auth/callback/keycloak"]
    assert clients[0]["attributes"]["pkce.code.challenge.method"] == "S256"
    admin("users", {"username": "synthetic-new-customer", "enabled": True})
    customer = admin("users?username=synthetic-new-customer&exact=true")[0]
    roles = admin("users/" + customer["id"] + "/role-mappings/realm/composite")
    assert "customer" in {role["name"] for role in roles}
    assert "founder" not in {role["name"] for role in roles}
    evidence = verify(ISSUER, "https://ca-demo-web.local.waooaw.test")
    evidence.update(fresh_import=True, default_customer_role_verified=True, credentials="synthetic")
    Path("/evidence/generation-" + os.environ["WC085_GENERATION"] + ".json").write_text(json.dumps(evidence, indent=2) + "\n")