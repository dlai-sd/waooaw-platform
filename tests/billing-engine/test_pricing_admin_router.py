# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
# Constitutional basis: C-059, C-063, C-088, C-089, C-091
"""WBE pricing admin routes: delegated-context binding, role matrix, step-up, replay and problem mapping.

The route coroutines are called directly with a request double; only the workload-identity verifier is
replaced (its own tests live with ADR-046), so the binding predicate each route supplies is exercised.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import pricing_admin  # noqa: E402
from pricing.body_adapter import to_public  # noqa: E402
from pricing.declarations import ManifestDeclarationSource  # noqa: E402
from pricing.export_import import BundleSigner  # noqa: E402
from pricing.models import PricingBelowFloor, PricingKind, PricingVersionNotFound, Violation  # noqa: E402
from pricing_admin import IdempotencyStore, PricingRuntime, etag_of, problem_for  # noqa: E402
from pricing_support import budget_body, dma_package_body, make_harness  # noqa: E402
from workload_identity import ServiceAuthError  # noqa: E402

CORRELATION = "8f6c1d2e-3a4b-4c5d-8e6f-0a1b2c3d4e5f"
CEILING = {"schemaVersion": "1.0", "kind": "BUDGET", "subjectKey": "budget:ENVIRONMENT_CEILING|demo"}


class _Session:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *_):
        return False


class Env:
    def __init__(self, monkeypatch) -> None:
        self.harness = make_harness()
        self.state = SimpleNamespace(
            role="founder", purpose="PRICING_ADMIN_STEP_UP", actor="founder-1", deny=False, context_key=None, seen=[]
        )
        self.runtime = PricingRuntime(
            declarations=ManifestDeclarationSource([]),
            signer=BundleSigner("test-key", b"test-secret-value"),
            store=IdempotencyStore(),
            clock=self.harness.clock,
        )
        self.runtime.service_for = lambda session: self.harness.service  # type: ignore[method-assign]
        monkeypatch.setattr(pricing_admin, "get_session_factory", lambda: (lambda: _Session()))
        monkeypatch.setattr(pricing_admin, "_verify", self._verify)
        self.counter = 0

    def _verify(self, request, route, operation, digest, predicate):
        self.state.seen.append((route, operation, digest))
        if self.state.deny:
            raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
        key = request.headers.get("Idempotency-Key") if self.state.context_key is None else self.state.context_key
        context = SimpleNamespace(
            actor_subject=self.state.actor,
            effective_role=self.state.role,
            purpose=self.state.purpose,
            correlation_id=request.headers.get("X-Correlation-ID", ""),
            idempotency_key=key,
        )
        if not predicate(context):
            raise ServiceAuthError("DELEGATED_CONTEXT_MISMATCH")
        return context

    def request(self, body: Any = None, *, key: str | None = None, query: dict[str, str] | None = None):
        raw = b"" if body is None else json.dumps(body).encode()
        headers = {"X-Correlation-ID": CORRELATION}
        if key is not None:
            headers["Idempotency-Key"] = key
        elif body is not None:
            self.counter += 1
            headers["Idempotency-Key"] = f"key-{self.counter}"
        async def read():
            return raw

        return SimpleNamespace(
            headers=headers,
            method="POST" if body is not None else "GET",
            scope={},
            query_params=query or {},
            body=read,
            app=SimpleNamespace(state=SimpleNamespace(pricing_runtime=self.runtime)),
        )

    async def call(self, handler, body: Any = None, *args, key: str | None = None, query=None):
        response = await handler(*args, self.request(body, key=key, query=query))
        return response.status_code, json.loads(response.body), response


@pytest.fixture
def env(monkeypatch):
    return Env(monkeypatch)


def _etag(payload: dict[str, Any]) -> str:
    return f"{payload['versionNo']}:{payload['state']}:{payload['bodyDigest'][:16]}"


def _ceiling_request(maximum: int = 40000, **extra: Any) -> dict[str, Any]:
    return {
        **CEILING,
        "body": {"scope": "ENVIRONMENT_CEILING", "ref": "demo", "maximumPaise": maximum},
        "deployTimeMaximumPaise": 50000,
        **extra,
    }


async def _submitted(env: Env, maximum: int = 40000) -> dict[str, Any]:
    status, created, _ = await env.call(pricing_admin.wbe_create_pricing_draft, _ceiling_request(maximum))
    assert status == 201
    draft = created["versionId"]
    status, simulated, _ = await env.call(
        pricing_admin.wbe_simulate_pricing_draft,
        {"schemaVersion": "1.0", "expectedVersion": _etag(created), "deployTimeMaximumPaise": 50000},
        draft,
    )
    assert status == 200 and simulated["draftId"] == draft
    version = await env.harness.service.get_version(UUID(draft))
    status, submitted, _ = await env.call(
        pricing_admin.wbe_submit_pricing_draft,
        {"schemaVersion": "1.0", "expectedVersion": etag_of(version), "deployTimeMaximumPaise": 50000},
        draft,
    )
    assert status == 200 and submitted["state"] == "SUBMITTED"
    return submitted


async def test_the_signed_digest_is_the_sha256_of_the_exact_bytes_and_the_route_is_the_grant_template(env):
    request = env.request(_ceiling_request())
    raw = await request.body()

    response = await pricing_admin.wbe_create_pricing_draft(request)

    route, operation, digest = env.state.seen[-1]
    assert (route, operation) == ("/internal/v1/pricing/drafts", "wbeCreatePricingDraft")
    assert digest == hashlib.sha256(raw).hexdigest()
    assert response.status_code == 201
    assert response.headers["ETag"].strip('"') == _etag(json.loads(response.body))


async def test_every_published_operation_has_a_route_with_a_grant_template():
    handlers = {
        name
        for name, member in vars(pricing_admin).items()
        if name.startswith("wbe_") and callable(member) and hasattr(member, "__call__")
    }
    assert len(pricing_admin.OPERATIONS) == 18
    assert len(handlers) == 18
    founder_only = {name for name, spec in pricing_admin.OPERATIONS.items() if spec.roles == pricing_admin.ROLES_FOUNDER}
    assert founder_only == {"wbeAuthorizePricingDraft", "wbeActivatePackageForSale"}


def test_the_router_implements_exactly_the_wbe_slice_and_its_workload_grants():
    import yaml

    root = Path(__file__).resolve().parents[2]
    spec = yaml.safe_load((root / "architecture/reference/api-specs/wbe-pricing-admin.openapi.yaml").read_text("utf-8"))
    registry = yaml.safe_load((root / "infrastructure/workload-identity/registry.yaml").read_text("utf-8"))
    declared = {
        (method.upper(), route, operation["operationId"])
        for route, item in spec["paths"].items()
        for method, operation in item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    }
    implemented = {(item.method, item.route, item.operation) for item in pricing_admin.OPERATIONS.values()}
    granted = {
        (grant["method"], grant["route"], grant["operation"])
        for grant in registry["route_grants"]
        if grant["target"] == "billing-engine" and grant["route"].startswith("/internal/v1/pricing/")
    }

    assert implemented == declared == granted
    assert {item.operation for item in pricing_admin.OPERATIONS.values() if item.writes} == {
        operation["operationId"]
        for item in spec["paths"].values()
        for method, operation in item.items()
        if method in {"post", "put", "patch", "delete"}
    }


async def test_create_replays_with_the_same_key_and_conflicts_with_another_body(env):
    body = _ceiling_request()

    first_status, first, _ = await env.call(pricing_admin.wbe_create_pricing_draft, body, key="replay-1")
    replay_status, replay, _ = await env.call(pricing_admin.wbe_create_pricing_draft, body, key="replay-1")
    conflict_status, conflict, response = await env.call(
        pricing_admin.wbe_create_pricing_draft, _ceiling_request(30000), key="replay-1"
    )

    assert (first_status, replay_status) == (201, 200)
    assert replay == first
    assert len(await env.harness.service.list_versions(kind=PricingKind.BUDGET)) == 1
    assert (conflict_status, conflict["code"]) == (409, "PRICING_IDEMPOTENCY_CONFLICT")
    assert response.media_type == "application/problem+json"


async def test_a_subject_key_that_does_not_match_the_body_is_refused(env):
    status, problem, _ = await env.call(
        pricing_admin.wbe_create_pricing_draft, {**_ceiling_request(), "subjectKey": "budget:ENVIRONMENT_CEILING|other"}
    )

    assert (status, problem["code"]) == (422, "PRICING_DRAFT_INVALID")
    assert problem["violations"][0]["code"] == "PRICING_SUBJECT_MISMATCH"
    assert problem["correlationId"] == CORRELATION


@pytest.mark.parametrize(
    ("role", "purpose", "expected"),
    [("customer", "PRICING_ADMIN", 401), ("", "PRICING_ADMIN", 401), ("pricing_admin", "OTHER", 401)],
)
async def test_a_context_that_does_not_bind_is_refused_as_unauthorized(env, role, purpose, expected):
    env.state.role, env.state.purpose = role, purpose

    status, problem, _ = await env.call(pricing_admin.wbe_get_pricing_live_margin)

    assert (status, problem["code"]) == (expected, "PRICING_FORBIDDEN")


async def test_a_denied_service_assertion_is_unauthorized(env):
    env.state.deny = True

    status, problem, _ = await env.call(pricing_admin.wbe_list_pricing_versions)

    assert (status, problem["code"]) == (401, "PRICING_FORBIDDEN")


@pytest.mark.parametrize(
    "handler",
    [
        pricing_admin.wbe_get_pricing_funding_dashboard,
        pricing_admin.wbe_get_pricing_margin_dashboard,
        pricing_admin.wbe_get_pricing_live_margin,
        pricing_admin.wbe_export_pricing_versions,
    ],
)
async def test_the_reports_and_export_are_closed_to_a_customer_role_and_open_to_an_administrator(env, handler):
    env.state.role = "customer"
    refused, _, _ = await env.call(handler)
    env.state.role, env.state.purpose = "pricing_admin", "PRICING_ADMIN"
    env.runtime.signer = BundleSigner("test-key", b"test-secret-value")

    allowed, _, _ = await env.call(handler)

    assert refused == 401
    assert allowed not in (401, 403)


async def test_a_write_needs_an_idempotency_key_that_equals_the_signed_one(env):
    env.state.context_key = "signed-key"
    mismatch, _, _ = await env.call(pricing_admin.wbe_create_pricing_draft, _ceiling_request(), key="other-key")
    env.state.context_key = None
    missing = env.request(_ceiling_request())
    del missing.headers["Idempotency-Key"]

    absent = await pricing_admin.wbe_create_pricing_draft(missing)

    assert mismatch == 401
    assert absent.status_code == 401
    assert await env.harness.service.list_versions(kind=PricingKind.BUDGET) == []


async def test_an_oversized_body_is_refused_before_verification(env):
    huge = {"schemaVersion": "1.0", "padding": "x" * (pricing_admin.MAXIMUM_BODY_BYTES + 1)}

    status, problem, _ = await env.call(pricing_admin.wbe_create_pricing_draft, huge)

    assert (status, problem["code"]) == (400, "PRICING_REQUEST_INVALID")
    assert env.state.seen == []


@pytest.mark.parametrize("operation", ["wbeAuthorizePricingDraft", "wbeActivatePackageForSale"])
async def test_an_administrator_cannot_authorize_or_activate(env, operation):
    env.state.role = "pricing_admin"
    env.state.purpose = "PRICING_ADMIN"
    handler = {
        "wbeAuthorizePricingDraft": pricing_admin.wbe_authorize_pricing_draft,
        "wbeActivatePackageForSale": pricing_admin.wbe_activate_package_for_sale,
    }[operation]

    status, problem, _ = await env.call(
        handler, {"schemaVersion": "1.0", "expectedVersion": "1:DRAFT:0000"}, "00000000-0000-4000-8000-000000000001"
    )

    assert (status, problem["code"]) == (403, "PRICING_FORBIDDEN")


async def test_an_administrator_drafts_and_a_founder_authorizes_with_step_up_only(env):
    env.state.role, env.state.purpose, env.state.actor = "pricing_admin", "PRICING_ADMIN", "admin-1"
    submitted = await _submitted(env)
    authorize = {"schemaVersion": "1.0", "expectedVersion": _etag(submitted), "deployTimeMaximumPaise": 50000}

    env.state.role, env.state.actor = "founder", "founder-1"
    env.state.purpose = "PRICING_ADMIN"
    no_step_up, refused, _ = await env.call(
        pricing_admin.wbe_authorize_pricing_draft, authorize, submitted["versionId"]
    )
    env.state.purpose = "PRICING_ADMIN_STEP_UP"
    stale, conflict, _ = await env.call(
        pricing_admin.wbe_authorize_pricing_draft,
        {**authorize, "expectedVersion": "9:DRAFT:deadbeef"},
        submitted["versionId"],
    )
    status, authorized, _ = await env.call(pricing_admin.wbe_authorize_pricing_draft, authorize, submitted["versionId"])

    assert (no_step_up, refused["code"]) == (403, "PRICING_STEP_UP_REQUIRED")
    assert (stale, conflict["code"]) == (409, "PRICING_VERSION_CONFLICT")
    assert status == 200 and authorized["state"] in ("AUTHORIZED", "EFFECTIVE")
    assert authorized["authorizedBy"] == "founder-1"
    assert authorized["createdBy"] == "admin-1"
    assert authorized["body"] == {"scope": "ENVIRONMENT_CEILING", "ref": "demo", "maximumPaise": 40000}


async def test_a_ceiling_above_the_deploy_maximum_is_refused_with_its_own_code(env):
    created_status, created, _ = await env.call(
        pricing_admin.wbe_create_pricing_draft, _ceiling_request(60000)
    )
    await env.call(
        pricing_admin.wbe_simulate_pricing_draft,
        {"schemaVersion": "1.0", "expectedVersion": _etag(created), "deployTimeMaximumPaise": 50000},
        created["versionId"],
    )
    version = await env.harness.service.get_version(UUID(created["versionId"]))

    status, problem, _ = await env.call(
        pricing_admin.wbe_submit_pricing_draft,
        {"schemaVersion": "1.0", "expectedVersion": etag_of(version), "deployTimeMaximumPaise": 50000},
        created["versionId"],
    )

    assert created_status == 201
    assert (status, problem["code"]) == (422, "PRICING_CEILING_ABOVE_MAXIMUM")
    assert problem["violations"]


async def test_discarding_a_draft_marks_it_discarded_and_an_unknown_draft_is_not_found(env):
    _, created, _ = await env.call(pricing_admin.wbe_create_pricing_draft, _ceiling_request())

    status, discarded, _ = await env.call(
        pricing_admin.wbe_discard_pricing_draft,
        {"schemaVersion": "1.0", "expectedVersion": _etag(created), "reason": "Superseded by a new plan"},
        created["versionId"],
    )
    missing_status, missing, _ = await env.call(
        pricing_admin.wbe_get_pricing_draft, None, "00000000-0000-4000-8000-0000000000ff"
    )
    bad_status, bad, _ = await env.call(pricing_admin.wbe_get_pricing_draft, None, "not-a-uuid")

    assert (status, discarded["state"]) == (200, "DISCARDED")
    assert (missing_status, missing["code"]) == (404, "PRICING_NOT_FOUND")
    assert (bad_status, bad["code"]) == (400, "PRICING_REQUEST_INVALID")


async def test_lists_are_paged_by_an_opaque_cursor_and_filtered_by_state(env):
    for maximum in (10000, 20000, 30000):
        await env.call(pricing_admin.wbe_create_pricing_draft, {
            **_ceiling_request(maximum),
            "subjectKey": f"budget:ACQUISITION_TENANT|tenant-{maximum}",
            "body": {"scope": "ACQUISITION_TENANT", "ref": f"tenant-{maximum}", "maximumPaise": maximum},
        })

    _, first, _ = await env.call(pricing_admin.wbe_list_pricing_drafts, query={"limit": "2"})
    _, second, _ = await env.call(
        pricing_admin.wbe_list_pricing_drafts, query={"limit": "2", "cursor": first["nextCursor"]}
    )
    bad_limit, problem, _ = await env.call(pricing_admin.wbe_list_pricing_drafts, query={"limit": "500"})
    _, effective, _ = await env.call(pricing_admin.wbe_list_pricing_versions, query={"state": "EFFECTIVE"})

    assert len(first["items"]) == 2 and len(second["items"]) == 1 and "nextCursor" not in second
    assert {item["versionId"] for item in first["items"]}.isdisjoint(item["versionId"] for item in second["items"])
    assert (bad_limit, problem["code"]) == (400, "PRICING_REQUEST_INVALID")
    assert [item["kind"] for item in effective["items"]] == ["POLICY"]


async def test_safety_operations_are_immediate_for_an_administrator_and_report_the_direction(env):
    env.harness.repository.seed(PricingKind.BUDGET, "budget:ENVIRONMENT_CEILING|demo", budget_body(50000))
    env.state.role, env.state.purpose, env.state.actor = "pricing_admin", "PRICING_ADMIN", "admin-1"

    status, lowered, _ = await env.call(
        pricing_admin.wbe_lower_pricing_ceiling,
        {"schemaVersion": "1.0", "scope": "ENVIRONMENT_CEILING", "ref": "demo", "newMaximumPaise": 20000, "reason": "Spend spike"},
    )
    raise_status, raised, _ = await env.call(
        pricing_admin.wbe_lower_pricing_ceiling,
        {"schemaVersion": "1.0", "scope": "ENVIRONMENT_CEILING", "ref": "demo", "newMaximumPaise": 90000, "reason": "Not a lowering"},
    )

    assert status == 200
    assert (lowered["direction"], lowered["state"], lowered["founderNotified"]) == ("SAFETY", "EFFECTIVE", True)
    current = await env.harness.service.effective_version(PricingKind.BUDGET, "budget:ENVIRONMENT_CEILING|demo")
    assert current.body["maximumPaise"] == 20000
    assert (raise_status, raised["code"]) == (422, "PRICING_DRAFT_INVALID")
    assert raised["violations"][0]["code"] == "SAFETY_NOT_A_REDUCTION"


async def test_the_live_margin_report_lists_no_breach_for_an_empty_catalogue(env):
    status, report, _ = await env.call(pricing_admin.wbe_get_pricing_live_margin)

    assert status == 200
    assert (report["packagesChecked"], report["breaches"]) == (0, [])


async def test_the_dashboards_pass_the_period_and_refuse_an_inverted_one(env, monkeypatch):
    seen: list[dict[str, Any]] = []

    async def funding(session, service, **kwargs):
        seen.append(kwargs)
        return {"schemaVersion": "1.0"}

    monkeypatch.setattr(pricing_admin.dashboard_reports, "funding_dashboard", funding)

    status, _, _ = await env.call(
        pricing_admin.wbe_get_pricing_funding_dashboard, query={"from": "2026-02-01", "to": "2026-02-28"}
    )
    inverted, problem, _ = await env.call(
        pricing_admin.wbe_get_pricing_funding_dashboard, query={"from": "2026-03-01", "to": "2026-02-01"}
    )

    assert status == 200
    assert (seen[0]["period_from"].isoformat(), seen[0]["period_to"].isoformat()) == ("2026-02-01", "2026-02-28")
    assert (inverted, problem["code"]) == (400, "PRICING_REQUEST_INVALID")


async def test_an_unexpected_failure_is_reported_as_unavailable_without_its_detail(env, monkeypatch):
    async def broken(*_a, **_k):
        raise RuntimeError("connection string postgres://secret")

    monkeypatch.setattr(env.harness.service, "list_versions", broken)

    status, problem, _ = await env.call(pricing_admin.wbe_list_pricing_versions)

    assert (status, problem["code"]) == (503, "PRICING_UNAVAILABLE")
    assert "secret" not in json.dumps(problem)


def test_problem_mapping_names_the_minimum_price_and_renames_the_not_found_code():
    below = PricingBelowFloor(
        [
            Violation(
                code="PRICING_BELOW_FLOOR",
                field="priceInclGstPaise",
                message="Below the floor.",
                details={"minimumCompliantPricePaise": 123456},
            )
        ]
    )

    mapped = problem_for(below)
    missing = problem_for(PricingVersionNotFound("No such version."))

    assert (mapped.status, mapped.code, mapped.extra["minimumCompliantPricePaise"]) == (422, "PRICING_BELOW_FLOOR", 123456)
    assert mapped.extra["violations"][0]["path"] == "priceInclGstPaise"
    assert (missing.status, missing.code) == (404, "PRICING_NOT_FOUND")


class _IdempotencyDatabase:
    """Interprets the three statements of SqlIdempotencyStore against a dict, one 'transaction' per session."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str, str], tuple[str, int, str, Any]] = {}
        self.commits = 0

    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def commit(self) -> None:
        self.commits += 1

    async def execute(self, statement, params):
        sql = str(statement)
        if sql.lstrip().startswith("SELECT"):
            row = self.rows.get((params["actor"], params["operation"], params["key"]))
            found = row is not None and row[3] >= params["expiry"]
            return SimpleNamespace(first=lambda: (row[0], row[1], row[2]) if found else None)
        if sql.lstrip().startswith("DELETE"):
            self.rows = {key: row for key, row in self.rows.items() if row[3] >= params["expiry"]}
        else:
            self.rows.setdefault(
                (params["actor"], params["operation"], params["key"]),
                (params["digest"], params["status"], params["payload"], params["now"]),
            )
        return SimpleNamespace(first=lambda: None)


async def test_the_sql_idempotency_store_replays_across_instances_expires_and_conflicts(monkeypatch):
    from datetime import datetime, timedelta, timezone

    database = _IdempotencyDatabase()
    monkeypatch.setattr(pricing_admin, "get_session_factory", lambda: database)
    now = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    first = pricing_admin.SqlIdempotencyStore(lambda: now[0])
    other_replica = pricing_admin.SqlIdempotencyStore(lambda: now[0])
    digest = "d" * 64

    assert await first.lookup("actor", "op", "k1", digest) is None
    await first.remember("actor", "op", "k1", digest, 201, {"versionNo": 1})
    assert database.commits == 1
    assert await other_replica.lookup("actor", "op", "k1", digest) == (201, {"versionNo": 1})
    with pytest.raises(pricing_admin.ProblemError) as conflict:
        await other_replica.lookup("actor", "op", "k1", "e" * 64)
    assert (conflict.value.status, conflict.value.code) == (409, "PRICING_IDEMPOTENCY_CONFLICT")
    with pytest.raises(pricing_admin.ProblemError) as too_long:
        await first.lookup("actor", "op", "k" * 129, digest)
    assert too_long.value.status == 400
    now[0] += timedelta(seconds=pricing_admin.IDEMPOTENCY_TTL_SECONDS + 1)
    assert await other_replica.lookup("actor", "op", "k1", "e" * 64) is None
    await other_replica.remember("actor", "op", "k2", digest, 200, {})
    assert list(database.rows) == [("actor", "op", "k2")]


def test_the_public_package_body_carries_the_gst_rate_and_the_component_top_up_flag():
    stored = dma_package_body()
    del stored["gstRatePercent"]

    public = to_public(PricingKind.PACKAGE, stored)

    assert public["gstRatePercent"] == 18
    assert all(component["topupAllowed"] is False for component in public["components"])


# WC-169 R017 to R019: the new package fields travel through the public/stored conversion and the build-up is published.
def test_the_package_description_and_target_margin_survive_both_body_conversions():
    from pricing.body_adapter import to_internal

    body = {**dma_package_body(), "description": "For a business new to digital marketing.", "targetMarginPct": 40}
    published = {**body, "taxTreatment": "GST_INCLUSIVE"}
    stored = to_internal(PricingKind.PACKAGE, published)
    assert stored["description"] == body["description"] and stored["targetMarginPct"] == 40
    assert "taxTreatment" not in stored
    assert to_public(PricingKind.PACKAGE, stored)["description"] == body["description"]
    # A package stored before this change has neither field and does not gain them.
    legacy = to_public(PricingKind.PACKAGE, dma_package_body())
    assert "description" not in legacy and "targetMarginPct" not in legacy


def test_the_simulation_publishes_the_build_up_with_unknown_costs_left_out_and_a_status():
    from markup.package_engine import parse_package_body, project_package
    from pricing_support import dma_rates

    rates = dma_rates(proactive_authorized=True, proactive_cost=100)
    del rates["llm_pro"]
    projection = project_package(parse_package_body({**dma_package_body(), "targetMarginPct": 40}), rates, 55)
    build_up = pricing_admin._build_up(projection)
    assert build_up["suggestionStatus"] == "INCOMPLETE" and build_up["targetMarginPercent"] == 40.0
    assert "llm_pro" in build_up["unauthorizedThreadIds"]
    unknown = next(line for line in build_up["costLines"] if line["threadId"] == "llm_pro")
    assert "unitCostPaise" not in unknown and "lineCostPaise" not in unknown and unknown["authorized"] is False
    assert build_up["infrastructureSharePaise"] == projection.infrastructure_share_paise
    assert build_up["suggestedPriceInclGstPaise"] % 100 == 0
