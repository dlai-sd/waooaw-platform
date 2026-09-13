from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ci_runs_deployment_shaped_business_platform_image_smoke() -> None:
    workflow = (ROOT / ".github/workflows/ci.yaml").read_text()
    smoke = (ROOT / "scripts/smoke_business_platform_image.sh").read_text()

    assert "Smoke Business Platform deployment configuration" in workflow
    assert "scripts/smoke_business_platform_image.sh" in workflow
    assert "--network \"container:$postgres_container\"" in smoke
    assert "--cpus 0.5 --memory 1g" in smoke
    assert "IdentityBrokerRead__AllowedAuthorizedParties__0=waooaw-web" in smoke
    assert "IdentityBrokerRead__AllowedAuthorizedParties__1=waooaw-web-preview" in smoke
    assert "/health/ready" in smoke
    assert "RestartCount" in smoke