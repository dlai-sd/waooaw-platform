import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENTS = ("demo", "uat", "prod")
PROVIDER_IDS = ["GOOGLE", "FACEBOOK", "APPLE", "EMAIL"]
KEYCLOAK_DIGEST = "sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2"
EDGE_DIGEST = "sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10"


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_environment_manifests_are_isolated_strict_and_secret_free() -> None:
    expected_keys = {
        "schemaVersion", "environment", "origins", "keycloak", "clients", "channels",
        "cookie", "identityEdge", "phoneIdentity", "providers",
    }
    for environment in ENVIRONMENTS:
        manifest = load_json(f"infrastructure/identity-config/environments/{environment}.json")
        serialized = json.dumps(manifest)

        assert set(manifest) == expected_keys
        assert manifest["schemaVersion"] == "1.0"
        assert manifest["environment"] == environment
        assert manifest["keycloak"]["audience"] == "waooaw-platform"
        assert manifest["keycloak"]["accessTokenMinutes"] == 15
        assert manifest["keycloak"]["refreshSessionHours"] == 8
        assert [provider["id"] for provider in manifest["providers"]] == PROVIDER_IDS
        assert all("*" not in value for client in manifest["clients"] for value in client["redirectUris"])
        assert all(client["pkceRequired"] for client in manifest["clients"])
        assert all(value.startswith("https://") for value in manifest["origins"].values())
        assert "clientSecret" not in serialized and "privateKey" not in serialized

        expected_host_marker = "waooaw.com" if environment == "prod" else f".{environment}.waooaw.com"
        uri_values = list(manifest["origins"].values())
        uri_values += [value for client in manifest["clients"] for key in (
            "redirectUris", "postLogoutRedirectUris", "allowedOrigins") for value in client[key]]
        assert all(expected_host_marker in value for value in uri_values)


def test_provider_runtime_configuration_is_minimal_and_deferred_providers_are_hidden() -> None:
    realm = load_json("infrastructure/keycloak/waooaw-realm.json")
    providers = {provider["alias"]: provider for provider in realm["identityProviders"]}

    assert set(providers) == {"google", "facebook"}
    assert all(not provider["enabled"] for provider in providers.values())
    assert providers["facebook"]["config"]["defaultScope"] == "email public_profile"
    assert "business_management" not in json.dumps(providers["facebook"])
    assert all(client.get("attributes", {}).get("pkce.code.challenge.method") == "S256"
               for client in realm["clients"] if client["clientId"] in {"waooaw-web", "waooaw-mobile"})

    edge = (ROOT / "infrastructure/identity-edge/nginx.conf.template").read_text(encoding="utf-8")
    assert "(google|facebook)" in edge
    assert "facebook|apple" not in edge
    assert "location /" in edge and 'if ($oidc_route_class = "") { return 404; }' in edge


def test_mobile_conformance_uses_shared_authority_and_forbids_token_upgrade() -> None:
    fixture = load_json("infrastructure/identity-config/conformance/mobile-oidc.json")

    assert fixture["authorizationFlow"] == "authorization_code"
    assert fixture["authorizationServer"] == "KEYCLOAK"
    assert fixture["pkce"] == {"required": True, "codeChallengeMethod": "S256"}
    assert fixture["acceptedAccessTokenAudience"] == "waooaw-platform"
    assert fixture["providerTokensAcceptedByApplication"] is False
    assert fixture["whatsAppProofExchangeAllowed"] is False
    assert {"getIdentityProviders", "getIdentitySession", "startRegistration"}.issubset(
        fixture["businessPlatformOperations"]
    )


def test_release_compose_pins_identity_dependencies_and_exact_audience() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.release.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert services["keycloak"]["image"] == f"quay.io/keycloak/keycloak@{KEYCLOAK_DIGEST}"
    assert services["identity-edge"]["image"] == f"docker.io/library/nginx@{EDGE_DIGEST}"
    assert services["business-platform"]["environment"]["Keycloak__Audience"] == "waooaw-platform"
    assert all("@sha256:" in services[name]["image"] for name in ("keycloak", "identity-edge"))
    assert all(re.fullmatch(r"sha256:[0-9a-f]{64}", services[name]["image"].split("@", 1)[1])
               for name in ("keycloak", "identity-edge"))