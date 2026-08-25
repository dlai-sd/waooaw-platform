"""Azure resource ID contracts for GOAL-006 Terraform imports."""

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from goal006_azure_resource_id import canonical_container_app_id  # noqa: E402


FAILED_RUN_ID = (
    "/subscriptions/2ed11839-6a0f-4eaa-bd94-44ca96ff5d84/"
    "resourceGroups/waooaw-demo-rg/providers/Microsoft.App/"
    "containerapps/ca-demo-identity-edge"
)


@pytest.mark.parametrize("environment", ("demo", "uat", "prod"))
def test_container_app_id_uses_azurerm_canonical_type_casing(environment: str) -> None:
    resource_id = FAILED_RUN_ID.replace("demo", environment)

    assert canonical_container_app_id(
        resource_id,
        expected_resource_group=f"waooaw-{environment}-rg",
        expected_name=f"ca-{environment}-identity-edge",
    ) == resource_id.replace(
        "/containerapps/", "/containerApps/"
    )


@pytest.mark.parametrize(
    "resource_id",
    (
        "",
        "/subscriptions//resourceGroups/rg/providers/Microsoft.App/containerApps/app",
        "/subscriptions/sub/resourceGroups//providers/Microsoft.App/containerApps/app",
        "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Web/containerApps/app",
        "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/jobs/app",
        "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/app/revisions/rev",
    ),
)
def test_container_app_id_rejects_malformed_or_wrong_resource_ids(
    resource_id: str,
) -> None:
    with pytest.raises(ValueError):
        canonical_container_app_id(
            resource_id,
            expected_resource_group="rg",
            expected_name="app",
        )


@pytest.mark.parametrize(
    ("resource_group", "name"),
    (("other-rg", "ca-demo-identity-edge"), ("waooaw-demo-rg", "other-app")),
)
def test_container_app_id_rejects_an_unexpected_identity(
    resource_group: str, name: str
) -> None:
    with pytest.raises(ValueError):
        canonical_container_app_id(
            FAILED_RUN_ID,
            expected_resource_group=resource_group,
            expected_name=name,
        )