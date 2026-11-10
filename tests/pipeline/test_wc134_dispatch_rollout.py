from __future__ import annotations

import copy

import pytest

from scripts.wc134_dispatch_rollout import MEMBERS, quiesce


def test_rollout_drains_old_replicas_and_preserves_exact_candidate() -> None:
    images = {member: f"registry/{member}@sha256:" + "a" * 64 for member in MEMBERS}
    app = "ca-demo-ai-runtime"
    revisions = [
        {"name": "old", "properties": {"active": True, "replicas": 1,
         "template": {"containers": [{"image": "registry/air@sha256:" + "b" * 64}]}}},
        {"name": "candidate", "properties": {"active": True, "replicas": 1,
         "template": {"containers": [{"image": images["ai-runtime"]}]}}},
    ]
    deactivated = []

    def run_az(args):
        if args[:2] == ["containerapp", "list"]:
            return [app]
        if args[2] == "list":
            return copy.deepcopy(revisions)
        if args[2] == "deactivate":
            name = args[args.index("--revision") + 1]
            deactivated.append(name)
            revisions[0]["properties"].update(active=False, replicas=0)
            return None
        if args[2] == "show":
            return copy.deepcopy(revisions[0])
        pytest.fail(f"Unexpected command: {args}")

    result = quiesce("waooaw-demo-rg", images, run_az=run_az)
    assert result["status"] == "passed"
    assert deactivated == ["old"]
    assert revisions[1]["properties"]["active"]


def test_rollout_refuses_missing_digests_and_wrong_environment_before_mutation() -> None:
    def forbidden(_args):
        pytest.fail("No cloud operations permitted for invalid rollout input")

    with pytest.raises(ValueError, match="restricted"):
        quiesce("waooaw-uat-rg", {}, run_az=forbidden)
    images = {member: f"registry/{member}:latest" for member in MEMBERS}
    with pytest.raises(ValueError, match="exact candidate"):
        quiesce("waooaw-demo-rg", images, run_az=forbidden)
    with pytest.raises(ValueError, match="exact candidate"):
        quiesce("waooaw-demo-rg", {}, run_az=forbidden)


def test_rollout_does_not_claim_completion_until_old_replica_count_is_zero() -> None:
    images = {member: f"registry/{member}@sha256:" + "a" * 64 for member in MEMBERS}
    revision = {"name": "old", "properties": {"active": False, "replicas": 1,
                "template": {"containers": [{"image": "registry/air@sha256:" + "b" * 64}]}}}

    def run_az(args):
        if args[:2] == ["containerapp", "list"]:
            return ["ca-demo-ai-runtime"]
        if args[2] == "list":
            return [revision]
        if args[2] == "deactivate":
            return None
        if args[2] == "show":
            return revision
        pytest.fail(f"Unexpected command: {args}")

    with pytest.raises(RuntimeError, match="did not drain"):
        quiesce("waooaw-demo-rg", images, run_az=run_az, timeout_seconds=0)


@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("replicas", [None, -1, "0", False])
def test_rollout_refuses_unknown_replica_state_before_mutation(active, replicas) -> None:
    images = {member: f"registry/{member}@sha256:" + "a" * 64 for member in MEMBERS}
    revision = {"name": "unknown", "properties": {"active": active, "replicas": replicas,
                "template": {"containers": [{"image": images["ai-runtime"]}]}}}
    if replicas is None:
        del revision["properties"]["replicas"]

    def run_az(args):
        if args[:2] == ["containerapp", "list"]:
            return ["ca-demo-ai-runtime"]
        if args[2] == "list":
            return [revision]
        pytest.fail("Invalid inventory must not cause a revision mutation")

    with pytest.raises(ValueError, match="replica count"):
        quiesce("waooaw-demo-rg", images, run_az=run_az)


def test_rollout_rechecks_app_inventory_for_concurrent_old_revisions() -> None:
    images = {member: f"registry/{member}@sha256:" + "a" * 64 for member in MEMBERS}
    listings = 0

    def run_az(args):
        nonlocal listings
        if args[:2] == ["containerapp", "list"]:
            listings += 1
            return [] if listings == 1 else ["ca-demo-ai-runtime"]
        if args[2] == "list":
            return [{"name": "concurrent-old", "properties": {"active": True, "replicas": 1,
                     "template": {"containers": [{"image": "registry/air:old"}]}}}]
        pytest.fail(f"Unexpected command: {args}")

    with pytest.raises(RuntimeError, match="appeared"):
        quiesce("waooaw-demo-rg", images, run_az=run_az)


def test_rollout_does_not_mistake_candidate_sidecar_for_candidate_application() -> None:
    images = {member: f"registry/{member}@sha256:" + "a" * 64 for member in MEMBERS}

    def run_az(args):
        if args[:2] == ["containerapp", "list"]:
            return ["ca-demo-ai-runtime"]
        if args[2] == "list":
            return [{"name": "mixed", "properties": {"active": True, "replicas": 1,
                     "template": {"containers": [
                         {"image": "registry/air:old"}, {"image": images["ai-runtime"]},
                     ]}}}]
        pytest.fail("Mixed application inventory must be rejected before mutation")

    with pytest.raises(ValueError, match="exactly one"):
        quiesce("waooaw-demo-rg", images, run_az=run_az)
