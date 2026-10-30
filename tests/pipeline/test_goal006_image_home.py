"""WC-127 contracts: image_home selection, ACR mirroring, and registry wiring for deployments."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import goal006_image_mirror as mirror
from scripts.goal006_dispatch_inputs import normalize_dispatch_inputs
from scripts.wc124_pgbouncer_preflight_job import BILLING_IMAGE, RUNNER_IMAGE

ROOT = Path(__file__).resolve().parents[2]
CI = yaml.safe_load((ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
DEPLOY = yaml.safe_load((ROOT / ".github/workflows/deploy.yaml").read_text(encoding="utf-8"))
ENVIRONMENT_TEXT = (ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")
ENVIRONMENT = yaml.safe_load(ENVIRONMENT_TEXT)
WORKLOAD_MODULE = (ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text(encoding="utf-8")
FOUNDATION_MODULE = (ROOT / "infrastructure/terraform/phase2/modules/foundation/main.tf").read_text(encoding="utf-8")
MIRROR_CONFIG = json.loads((ROOT / "infrastructure/image-registry/acr-mirrors.json").read_text(encoding="utf-8"))

SERVER = "acrwaooawdemo2ed118.azurecr.io"
PULL_ID = (
    "/subscriptions/2ed11839-6a0f-4eaa-bd94-44ca96ff5d84/resourceGroups/waooaw-demo-rg/providers/"
    "Microsoft.ManagedIdentity/userAssignedIdentities/id-waooaw-demo-image-pull"
)
INDEX = "application/vnd.oci.image.index.v1+json"


def digest(character: str) -> str:
    return "sha256:" + character * 64


IMAGES = {
    "web": f"ghcr.io/dlai-sd/web@{digest('a')}",
    "billing-engine": f"ghcr.io/dlai-sd/billing-engine@{digest('b')}",
}
CHILDREN = {digest("a"): [digest("c"), digest("d")], digest("b"): [digest("e")]}


class FakeRegistry:
    """Emulates docker buildx imagetools and the az/docker login commands against an in-memory ACR."""

    def __init__(self, *, create_failures: int = 0, drop_children: int = 0, fail_login: str = "") -> None:
        self.manifests: dict[str, dict[str, Any]] = {}
        self.create_failures = create_failures
        self.drop_children = drop_children
        self.fail_login = fail_login
        self.calls: list[list[str]] = []
        self.stdin: list[str | None] = []

    def seed(self, image: str, *, children: bool = True) -> None:
        repository, index_digest = mirror.parse_source(image)
        base = f"{SERVER}/{repository}"
        child_digests = CHILDREN[index_digest]
        self.manifests[f"{base}@{index_digest}"] = {
            "mediaType": INDEX,
            "manifests": [{"digest": child} for child in child_digests],
        }
        if children:
            for child in child_digests:
                self.manifests[f"{base}@{child}"] = {"mediaType": "application/vnd.oci.image.manifest.v1+json"}

    def __call__(self, arguments: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        arguments = list(arguments)
        self.calls.append(arguments)
        self.stdin.append(input_text)
        if arguments[:4] == ["docker", "buildx", "imagetools", "inspect"]:
            manifest = self.manifests.get(arguments[-1])
            if manifest is None:
                return subprocess.CompletedProcess(arguments, 1, "", "MANIFEST_UNKNOWN")
            return subprocess.CompletedProcess(arguments, 0, json.dumps(manifest), "")
        if arguments[:4] == ["docker", "buildx", "imagetools", "create"]:
            if self.create_failures:
                self.create_failures -= 1
                return subprocess.CompletedProcess(arguments, 1, "", "error: 503 Service Unavailable")
            tag, source = arguments[5], arguments[6]
            assert tag.startswith(SERVER + "/") and ":sha256-" in tag
            self.seed(source, children=self.drop_children == 0)
            self.drop_children = max(0, self.drop_children - 1)
            return subprocess.CompletedProcess(arguments, 0, "", "")
        if arguments[:2] == ["az", "login"]:
            return subprocess.CompletedProcess(arguments, 1 if self.fail_login == "az" else 0, "", "AADSTS70021")
        if arguments[:3] == ["az", "acr", "login"]:
            return subprocess.CompletedProcess(arguments, 0, "acr-refresh-token\n", "")
        if arguments[:2] == ["docker", "login"]:
            return subprocess.CompletedProcess(arguments, 0, "Login Succeeded", "")
        if arguments in (["az", "logout"],) or arguments[:2] == ["docker", "logout"]:
            return subprocess.CompletedProcess(arguments, 0, "", "")
        raise AssertionError(f"unexpected command {arguments}")


def no_sleep(_: float) -> None:
    return None


def select(image_home: str, registry: FakeRegistry, **overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "image_home": image_home,
        "images": IMAGES,
        "login_server": SERVER,
        "pull_identity_id": PULL_ID,
        "registry_ready": True,
        "run": registry,
        "sleep": no_sleep,
    }
    arguments.update(overrides)
    return mirror.select_image_home(**arguments)


def test_github_home_makes_no_registry_calls() -> None:
    registry = FakeRegistry()
    evidence = select("github", registry)
    assert evidence["effective_image_home"] == "github"
    assert evidence["references"] == IMAGES
    assert registry.calls == []


@pytest.mark.parametrize("image_home", ["azure", "both"])
def test_azure_home_copies_missing_images_and_returns_digest_identical_acr_references(image_home: str) -> None:
    registry = FakeRegistry()
    registry.seed(IMAGES["web"])
    evidence = select(image_home, registry)
    assert evidence["effective_image_home"] == "azure"
    assert evidence["registry_server"] == SERVER
    assert evidence["pull_identity_id"] == PULL_ID
    assert evidence["references"] == {
        "web": f"{SERVER}/dlai-sd/web@{digest('a')}",
        "billing-engine": f"{SERVER}/dlai-sd/billing-engine@{digest('b')}",
    }
    copied = {record["member"]: record["copied"] for record in evidence["mirrored"]}
    assert copied == {"web": False, "billing-engine": True}
    creates = [call for call in registry.calls if call[3] == "create"]
    assert creates == [
        [
            "docker",
            "buildx",
            "imagetools",
            "create",
            "--tag",
            f"{SERVER}/dlai-sd/billing-engine:sha256-{'b' * 64}",
            IMAGES["billing-engine"],
        ]
    ]


def test_index_without_every_child_manifest_is_not_complete() -> None:
    registry = FakeRegistry()
    registry.seed(IMAGES["web"], children=False)
    assert mirror.is_complete(SERVER, IMAGES["web"], registry) is False
    registry.seed(IMAGES["web"])
    assert mirror.is_complete(SERVER, IMAGES["web"], registry) is True


def test_copy_retries_transient_failures_and_incomplete_indexes() -> None:
    registry = FakeRegistry(create_failures=1, drop_children=1)
    sleeps: list[float] = []
    record = mirror.copy_image(SERVER, IMAGES["web"], registry, sleep=sleeps.append)
    assert record["copied"] is True
    assert sleeps == [10, 20]


def test_azure_home_fails_closed_when_copy_never_completes() -> None:
    registry = FakeRegistry(create_failures=10)
    with pytest.raises(mirror.MirrorError, match="503 Service Unavailable"):
        select("azure", registry)


def test_both_home_falls_back_to_github_with_reason() -> None:
    registry = FakeRegistry(create_failures=10)
    evidence = select("both", registry)
    assert evidence["effective_image_home"] == "github"
    assert evidence["references"] == IMAGES
    assert evidence["registry_server"] == ""
    assert "503 Service Unavailable" in evidence["fallback_reason"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"registry_ready": False}, "does not exist yet"),
        ({"login_server": "acrwaooawuat2ed118.azurecr.io"}, "pull identity must be the environment"),
        ({"login_server": "attacker.azurecr.io"}, "login server must be an environment WAOOAW ACR"),
        ({"pull_identity_id": PULL_ID.replace("image-pull", "deployment")}, "pull identity"),
    ],
)
def test_registry_preconditions_fail_azure_and_fall_back_for_both(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(mirror.MirrorError, match=message):
        select("azure", FakeRegistry(), **overrides)
    evidence = select("both", FakeRegistry(), **overrides)
    assert evidence["effective_image_home"] == "github"
    assert message in evidence["fallback_reason"]


def test_only_immutable_ghcr_sources_are_accepted() -> None:
    with pytest.raises(ValueError, match="immutable GHCR digest"):
        select("github", FakeRegistry(), images={"web": "ghcr.io/dlai-sd/web:latest"})
    with pytest.raises(ValueError, match="immutable GHCR digest"):
        select("both", FakeRegistry(), images={"web": f"docker.io/dlai-sd/web@{digest('a')}"})


def test_committed_mirror_config_is_valid_and_skips_unrecorded_publish_identities() -> None:
    tenant_id, targets = mirror.load_mirror_targets(MIRROR_CONFIG)
    assert tenant_id == "0471534c-1bbe-40ab-ae65-3f721b62582c"
    servers = {name: record["login_server"] for name, record in MIRROR_CONFIG["environments"].items()}
    assert servers == {
        "demo": "acrwaooawdemo2ed118.azurecr.io",
        "uat": "acrwaooawuat2ed118.azurecr.io",
        "prod": "acrwaooawprod2ed118.azurecr.io",
    }
    recorded = {name for name, record in MIRROR_CONFIG["environments"].items() if record["publish_client_id"]}
    assert {target["environment"] for target in targets} == recorded


def test_demo_publish_identity_is_recorded_so_ci_fills_the_demo_acr() -> None:
    _, targets = mirror.load_mirror_targets(MIRROR_CONFIG)
    assert targets == [
        {
            "environment": "demo",
            "login_server": "acrwaooawdemo2ed118.azurecr.io",
            "client_id": "8894d1b4-758c-498c-9d25-8bac3de0dc68",
        }
    ]


def configured(**environments: str | None) -> dict[str, Any]:
    config = json.loads(json.dumps(MIRROR_CONFIG))
    for name, client_id in environments.items():
        config["environments"][name]["publish_client_id"] = client_id
    return config


def test_publish_logs_in_with_oidc_copies_and_always_logs_out() -> None:
    registry = FakeRegistry()
    client_id = "11111111-2222-3333-4444-555555555555"
    evidence = mirror.publish_to_mirrors(
        configured(demo=client_id),
        {"web": IMAGES["web"]},
        registry,
        token_source=lambda: "oidc-jwt",
        sleep=no_sleep,
    )
    assert evidence["targets"][0]["status"] == "succeeded"
    assert evidence["targets"][0]["mirrored"][0]["copied"] is True
    login = registry.calls[0]
    assert login[:3] == ["az", "login", "--service-principal"]
    assert login[login.index("--username") + 1] == client_id
    assert login[login.index("--federated-token") + 1] == "oidc-jwt"
    assert "--allow-no-subscriptions" in login
    assert registry.calls[1][:5] == ["az", "acr", "login", "--name", "acrwaooawdemo2ed118"]
    docker_login = registry.calls.index(["docker", "login", SERVER, "--username", mirror.ACR_TOKEN_USER, "--password-stdin"])
    assert registry.stdin[docker_login] == "acr-refresh-token"
    assert registry.calls[-2:] == [["docker", "logout", SERVER], ["az", "logout"]]


def test_publish_failure_in_one_environment_does_not_stop_the_next() -> None:
    registry = FakeRegistry(fail_login="az")
    evidence = mirror.publish_to_mirrors(
        configured(demo="11111111-2222-3333-4444-555555555555", uat="66666666-2222-3333-4444-555555555555"),
        {"web": IMAGES["web"]},
        registry,
        token_source=lambda: "oidc-jwt",
        sleep=no_sleep,
    )
    assert [target["status"] for target in evidence["targets"]] == ["failed", "failed"]
    assert "AADSTS70021" in evidence["targets"][0]["error"]
    assert registry.calls.count(["az", "logout"]) == 2


@pytest.mark.parametrize(
    "mutation",
    [
        lambda config: config.update(schema="other"),
        lambda config: config["environments"]["demo"].update(login_server="acrwaooawuat2ed118.azurecr.io"),
        lambda config: config["environments"]["demo"].update(publish_client_id="not-a-guid"),
        lambda config: config["environments"].update(staging={"login_server": SERVER, "publish_client_id": None}),
    ],
)
def test_mirror_config_rejects_unsafe_targets(mutation: Any) -> None:
    config = configured()
    mutation(config)
    with pytest.raises(ValueError):
        mirror.load_mirror_targets(config)


def test_publish_cli_skips_with_notice_until_a_publish_identity_is_recorded(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps(configured(demo=None)), encoding="utf-8")
    output = tmp_path / "acr-mirror.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/goal006_image_mirror.py",
            "publish",
            "--config",
            str(config),
            "--image",
            f"web={IMAGES['web']}",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "::notice title=ACR mirror skipped::" in result.stdout
    assert json.loads(output.read_text(encoding="utf-8")) == {"targets": []}


def test_dispatch_image_home_defaults_to_github_and_rejects_unknown_values() -> None:
    assert normalize_dispatch_inputs("demo", "plan")["image_home"] == "github"
    assert normalize_dispatch_inputs("demo", "plan", image_home="both")["image_home"] == "both"
    with pytest.raises(ValueError):
        normalize_dispatch_inputs("demo", "plan", image_home="dockerhub")


def test_preflight_accepts_environment_acr_mirror_and_rejects_foreign_registries() -> None:
    runner = "/dlai-sd/goal006-private-runner@" + digest("a")
    billing = "/dlai-sd/billing-engine@" + digest("b")
    for server in ("ghcr.io", SERVER, "acrwaooawuat2ed118.azurecr.io"):
        assert RUNNER_IMAGE.fullmatch(server + runner)
        assert BILLING_IMAGE.fullmatch(server + billing)
    for server in ("attacker.azurecr.io", "docker.io", "acrwaooawdemo2ed118.azurecr.io.evil.example"):
        assert RUNNER_IMAGE.fullmatch(server + runner) is None
        assert BILLING_IMAGE.fullmatch(server + billing) is None


def test_deploy_dispatch_offers_image_home_and_passes_it_to_the_engine() -> None:
    dispatch = DEPLOY[True]["workflow_dispatch"]["inputs"]["image_home"]
    assert dispatch["type"] == "choice"
    assert dispatch["options"] == ["github", "azure", "both"]
    assert dispatch["default"] == "github"
    assert DEPLOY["jobs"]["deploy"]["with"]["image_home"] == "${{ needs.authorize.outputs.image_home }}"
    engine_input = ENVIRONMENT[True]["workflow_call"]["inputs"]["image_home"]
    assert engine_input["type"] == "string"
    assert engine_input["default"] == "github"


def test_engine_selects_image_home_on_github_hosted_broker_before_terraform() -> None:
    broker = ENVIRONMENT["jobs"]["start-broker"]
    assert broker["runs-on"] == "ubuntu-latest"
    assert broker["outputs"]["image_home"] == "${{ steps.image-home.outputs.effective_image_home || 'github' }}"
    names = [step.get("name") for step in broker["steps"]]
    select_index = names.index("Select image home and mirror release images to ACR")
    assert names.index("Azure login with control-plane identity") < select_index
    step = broker["steps"][select_index]
    assert step["if"] == "inputs.apply && inputs.image_home != 'github'"
    assert "goal006_image_mirror.py select" in step["run"]
    assert "goal006-private-runner=ghcr.io/dlai-sd/goal006-private-runner@" in step["run"]
    assert 'docker logout "$login_server"' in step["run"]
    evidence = broker["steps"][select_index + 1]
    assert evidence["name"] == "Retain image home evidence"
    assert evidence["if"] == "always() && steps.image-home.outcome != 'skipped'"
    assert "start-broker" in ENVIRONMENT["jobs"]["terraform"]["needs"]


def test_workload_inputs_receive_registry_only_for_effective_azure_home() -> None:
    step = next(
        step
        for step in ENVIRONMENT["jobs"]["terraform"]["steps"]
        if step.get("name") == "Build workload inputs from trusted foundation outputs"
    )
    assert step["env"]["IMAGE_HOME"] == "${{ needs.start-broker.outputs.image_home }}"
    assert 'if test "${IMAGE_HOME:-github}" = azure; then' in step["run"]
    assert '"${registry_arguments[@]}"' in step["run"]


@pytest.mark.parametrize("image_home", ["github", "azure"])
def test_database_provisioner_job_pulls_from_the_selected_home(tmp_path: Path, image_home: str) -> None:
    step = next(
        step for step in ENVIRONMENT["jobs"]["terraform"]["steps"] if step.get("name") == "Create WC-124 database provisioner"
    )
    expressions = {
        "steps.database-transition.outputs.revocation_verification_required": "false",
        "steps.database-transition.outputs.provisioner_required": "true",
        "inputs.control_sha": "c" * 40,
    }
    script = re.sub(r"\$\{\{\s*([^}]+?)\s*\}\}", lambda match: expressions[match[1]], step["run"])
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/goal006_ghcr_digest.py").write_text(f"print('{digest('f')}')\n", encoding="utf-8")
    az = tmp_path / "az"
    az.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "if args[:3] == ['containerapp', 'job', 'list']:\n"
        "    print('')\n"
        "elif args[:3] == ['containerapp', 'job', 'create']:\n"
        "    Path('created.json').write_text(Path(args[args.index('--yaml') + 1]).read_text())\n"
        "elif args[:3] == ['containerapp', 'job', 'show']:\n"
        "    print(json.dumps(list(json.loads(Path('created.json').read_text())['identity']['userAssignedIdentities'])))\n"
        "else:\n"
        "    sys.exit('unexpected az operation: ' + repr(args))\n",
        encoding="utf-8",
    )
    az.chmod(0o755)
    effective = {"github": ("github", "", ""), "azure": ("azure", SERVER, PULL_ID)}[image_home]
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "BOOTSTRAP_CLIENT_ID": "bootstrap-client",
            "BOOTSTRAP_IDENTITY_ID": "/identities/bootstrap",
            "CONTAINER_APP_ENVIRONMENT_ID": "/environments/demo",
            "DATABASE_PROVISIONER_CLIENT_ID": "provisioner-client",
            "DATABASE_PROVISIONER_IDENTITY_ID": "/identities/provisioner",
            "KEY_VAULT_NAME": "kv-waooaw-demo",
            "POSTGRESQL_SERVER_FQDN": "postgres.example.invalid",
            "RESOURCE_GROUP": "waooaw-demo-rg",
            "TARGET_ENVIRONMENT": "demo",
            "IMAGE_HOME": effective[0],
            "IMAGE_REGISTRY_SERVER": effective[1],
            "IMAGE_PULL_IDENTITY_ID": effective[2],
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    job = json.loads((tmp_path / "created.json").read_text(encoding="utf-8"))
    image = job["properties"]["template"]["containers"][0]["image"]
    identities = set(job["identity"]["userAssignedIdentities"])
    if image_home == "github":
        assert image == f"ghcr.io/dlai-sd/goal006-private-runner@{digest('f')}"
        assert "registries" not in job["properties"]["configuration"]
        assert identities == {"/identities/bootstrap", "/identities/provisioner"}
    else:
        assert image == f"{SERVER}/dlai-sd/goal006-private-runner@{digest('f')}"
        assert job["properties"]["configuration"]["registries"] == [{"server": SERVER, "identity": PULL_ID}]
        assert identities == {"/identities/bootstrap", "/identities/provisioner", PULL_ID}


def test_ci_mirrors_each_image_immediately_after_publish_without_blocking_release() -> None:
    for job_name, member in (("publish", "matrix.service.name"), ("publish-runner-images", "matrix.image.name")):
        steps = CI["jobs"][job_name]["steps"]
        names = [step.get("name") for step in steps]
        mirror_index = next(index for index, name in enumerate(names) if name and name.startswith("Mirror"))
        build_index = next(index for index, step in enumerate(steps) if step.get("id") == "image")
        assert build_index < mirror_index
        assert all("attest" not in (name or "").lower() for name in names[build_index + 1 : mirror_index])
        step = steps[mirror_index]
        assert step["continue-on-error"] is True
        assert "goal006_image_mirror.py publish" in step["run"]
        assert "--config infrastructure/image-registry/acr-mirrors.json" in step["run"]
        assert step["env"]["IMAGE"].endswith("@${{ steps.image.outputs.digest }}")
        assert member in step["env"]["MEMBER"]
        assert CI["jobs"][job_name]["permissions"]["id-token"] == "write"


def test_foundation_creates_private_pull_and_main_only_publish_identities() -> None:
    assert 'resource "azurerm_container_registry" "images"' in FOUNDATION_MODULE
    assert 'sku                           = "Basic"' in FOUNDATION_MODULE or 'sku = "Basic"' in FOUNDATION_MODULE
    assert "admin_enabled                 = false" in FOUNDATION_MODULE or "admin_enabled = false" in FOUNDATION_MODULE
    assert 'role_definition_name = "AcrPull"' in FOUNDATION_MODULE
    assert 'role_definition_name = "AcrPush"' in FOUNDATION_MODULE
    assert 'subject             = "repo:${var.repository_id}:ref:refs/heads/main"' in FOUNDATION_MODULE


def test_workload_rewrites_release_images_to_the_mirror_without_changing_digests() -> None:
    assert '"${var.image_registry_server}/${trimprefix(image, "ghcr.io/")}"' in WORKLOAD_MODULE
    assert "image  = local.image_refs[each.key]" in WORKLOAD_MODULE
    assert 'image   = local.image_refs["billing-engine"]' in WORKLOAD_MODULE
    assert 'image   = local.image_refs["constitutional-engine"]' in WORKLOAD_MODULE
    assert WORKLOAD_MODULE.count('dynamic "registry"') == 3
    assert re.search(r"image\s+=\s+var\.image_digests\[", WORKLOAD_MODULE) is None
