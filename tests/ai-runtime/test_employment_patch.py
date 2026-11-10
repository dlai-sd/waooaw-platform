# Implements: WC-115 R036-R044, R092-R095
# Constitutional basis: C-023, C-049, C-059, C-062, C-076, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115

import hashlib
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import employment_patch
from employment_patch import (
    BoundedContext,
    Contribution,
    EmploymentPatchProposalRequest,
    EmploymentPatchProposalService,
    EmploymentProposalError,
    ImmutableContractReference,
    ProposalInterpretation,
    ProposalOperation,
    SemanticCatalogue,
    configure_employment_patch,
    router,
)
from employment_auth import EmploymentWorkloadAuth, request_digest


def _reference(name: str) -> ImmutableContractReference:
    return ImmutableContractReference(ref=name, version="1", digest="a" * 64)


def _request() -> EmploymentPatchProposalRequest:
    request = EmploymentPatchProposalRequest(
        schemaVersion="1.0",
        protocolVersion="1.0-candidate",
        relationshipRef="relationship-1",
        contributionRef="contribution-1",
        agentType="neutral-professional",
        agentVersion="1",
        manifestVersion="1",
        semanticCatalogue=_reference("catalogue"),
        promptPolicy=_reference("prompt"),
        modelPolicy=_reference("model"),
        patchType="GOAL",
        contribution=Contribution(text="Increase qualified enquiries.", locale="en-IN"),
        requestDigest="0" * 64,
        boundedContext=BoundedContext(currentPlanVersion="plan-1"),
    )
    return request.model_copy(update={"request_digest": EmploymentPatchProposalService.request_digest(request)})


def _service(interpreter) -> EmploymentPatchProposalService:
    catalogue = SemanticCatalogue(
        _reference("catalogue"),
        {"GOAL": frozenset({"/goals/0/outcome"})},
    )
    return EmploymentPatchProposalService((catalogue,), interpreter)


def test_pr_unicode_proposal_digests_match_normalized_air_contract() -> None:
    wire = _request().model_dump(mode="json", by_alias=True)
    wire["contribution"] = {"text": "नमस्ते café", "locale": "en-IN"}
    wire["boundedContext"] = None
    content = {key: value for key, value in wire.items() if key != "requestDigest"}
    wire["requestDigest"] = hashlib.sha256(
        json.dumps(content, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()

    parsed = EmploymentPatchProposalRequest.model_validate(wire)
    assert EmploymentPatchProposalService.request_digest(parsed) == wire["requestDigest"]
    signed_bytes = json.dumps(wire, separators=(",", ":"), sort_keys=True).encode()
    assert request_digest(parsed.model_dump(mode="json", by_alias=True)) == hashlib.sha256(signed_bytes).hexdigest()


def test_cew_fit_05_proposal_is_replayed_and_never_executes_a_command() -> None:
    service = _service(
        lambda _request: ProposalInterpretation(
            operations=(
                ProposalOperation(
                    op="ADD",
                    semanticPath="/goals/0/outcome",
                    value="Increase qualified enquiries.",
                    sourceRefs=("contribution-1",),
                ),
            ),
            confidence=0.9,
            sourceRefs=("contribution-1",),
            modelDecisionRef="decision-1",
        )
    )
    request = _request()
    idempotency_key = uuid4()

    receipt, replayed = service.propose("professional-runtime", idempotency_key, request)
    proposal, replayed_again = service.propose("professional-runtime", idempotency_key, request)

    assert replayed is False
    assert replayed_again is True
    assert proposal.state == "PROPOSED"
    assert proposal.proposal_id == receipt.proposal_id
    assert proposal.operations[0].semantic_path == "/goals/0/outcome"


def test_proposal_idempotency_is_scoped_to_the_tenant() -> None:
    service = _service(
        lambda _request: ProposalInterpretation(
            operations=(
                ProposalOperation(
                    op="ADD",
                    semanticPath="/goals/0/outcome",
                    value="Increase qualified enquiries.",
                ),
            ),
            confidence=0.9,
            modelDecisionRef="decision-1",
        )
    )
    request = _request()
    key = uuid4()
    first, first_replayed = service.propose("professional-runtime", key, request, tenant_id="tenant-a")
    second, second_replayed = service.propose("professional-runtime", key, request, tenant_id="tenant-b")
    replay, replayed = service.propose("professional-runtime", key, request, tenant_id="tenant-a")

    assert not first_replayed
    assert not second_replayed
    assert replayed
    assert first.proposal_id != second.proposal_id
    assert replay.proposal_id == first.proposal_id
    with pytest.raises(EmploymentProposalError, match="AIR_EMPLOYMENT_NOT_FOUND"):
        service.get(first.proposal_id, "tenant-b")


def test_material_uncertainty_returns_no_operations() -> None:
    service = _service(
        lambda _request: ProposalInterpretation(
            confidence=0.2,
            unresolvedQuestions=("Which outcome is authoritative?",),
            modelDecisionRef="decision-2",
        )
    )

    receipt, _ = service.propose("professional-runtime", uuid4(), _request())
    proposal = service.get(receipt.proposal_id)

    assert proposal.state == "UNREPRESENTABLE"
    assert proposal.operations == ()
    assert proposal.reason_code == "MATERIAL_UNCERTAINTY"


def test_disabled_interpreter_reports_model_unavailability_not_customer_uncertainty() -> None:
    service = _service(employment_patch._unavailable_interpreter)
    receipt, _ = service.propose("professional-runtime", uuid4(), _request())
    proposal = service.get(receipt.proposal_id)
    assert proposal.state == "UNREPRESENTABLE"
    assert proposal.operations == ()
    assert proposal.reason_code == "MODEL_UNAVAILABLE"
    assert service.recovery_mode == "DISABLED_INTERPRETER_V1"


def test_cew_neg_011_unlisted_readiness_path_fails_closed() -> None:
    service = _service(
        lambda _request: ProposalInterpretation(
            operations=(
                ProposalOperation(
                    op="REPLACE",
                    semanticPath="/authority/grant",
                    value="expanded",
                ),
            ),
            confidence=1,
            modelDecisionRef="decision-3",
        )
    )

    with pytest.raises(EmploymentProposalError, match="AIR_EMPLOYMENT_UNREPRESENTABLE"):
        service.propose("professional-runtime", uuid4(), _request())


def test_application_configuration_is_digest_bound_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application = FastAPI()
    monkeypatch.setenv(
        "EMPLOYMENT_SEMANTIC_CATALOGUE_JSON",
        """
        {
          "reference": {
            "ref": "catalogue",
            "version": "1",
            "digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
          },
          "allowedPathsByPatchType": {
            "GOAL": ["/goals/0/outcome"]
          }
        }
        """,
    )

    configure_employment_patch(application)
    service = application.state.employment_patch_service
    receipt, _ = service.propose("professional-runtime", uuid4(), _request())
    proposal = service.get(receipt.proposal_id)

    assert proposal.state == "UNREPRESENTABLE"
    assert proposal.operations == ()


@pytest.mark.asyncio
async def test_http_boundary_persists_replays_and_recovers_proposals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(
        lambda _request: ProposalInterpretation(
            operations=(
                ProposalOperation(
                    op="ADD",
                    semanticPath="/goals/0/outcome",
                    value="Increase qualified enquiries.",
                ),
            ),
            confidence=0.9,
            modelDecisionRef="decision-1",
        )
    )

    class Repository:
        stored = None
        claim = None

        @asynccontextmanager
        async def serialize_proposal(self, *_args):
            yield self

        async def find_by_idempotency(self, *_args):
            return self.stored

        async def claim_dispatch(self, _tenant, _relationship, _key, digest, mode):
            if self.claim is not None:
                return False, *self.claim
            self.claim = (digest, mode)
            return True, digest, mode

        async def save(
            self,
            tenant_id,
            relationship_ref,
            idempotency_key,
            request_digest,
            receipt,
            proposal,
        ):
            self.stored = SimpleNamespace(
                tenant_id=tenant_id,
                relationship_ref=relationship_ref,
                proposal_id=proposal["proposalId"],
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                proposal_json=proposal,
            )

        async def get(self, tenant_id, proposal_id):
            if self.stored is not None and self.stored.tenant_id == tenant_id and self.stored.proposal_id == str(proposal_id):
                return self.stored
            return None

    repository = Repository()
    context = SimpleNamespace(
        issuer_uri="spiffe://waooaw.test/workload/professional-runtime",
        tenant_id="00000000-0000-0000-0000-000000000001",
        relationship_id="relationship-1",
    )
    monkeypatch.setattr(employment_patch, "_authorize", lambda *_args: context)
    monkeypatch.setattr(employment_patch, "_repository", lambda _request: repository)
    application = FastAPI()
    application.state.employment_patch_service = service
    application.include_router(router)
    payload = _request().model_dump(mode="json", by_alias=True)
    headers = {
        "Idempotency-Key": "00000000-0000-0000-0000-000000000009",
        "X-Correlation-Id": "00000000-0000-0000-0000-000000000007",
    }

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://air",
    ) as client:
        created = await client.post(
            "/internal/v1/employment-patch-proposals",
            json=payload,
            headers=headers,
        )
        replay = await client.post(
            "/internal/v1/employment-patch-proposals",
            json=payload,
            headers=headers,
        )
        proposal_id = replay.json()["proposalId"]
        context.relationship_id = "relationship-2"
        foreign_memory = await client.get(
            f"/internal/v1/employment-patch-proposals/{proposal_id}",
            headers={"X-Correlation-Id": headers["X-Correlation-Id"]},
        )
        application.state.employment_patch_service = _service(
            lambda _request: ProposalInterpretation(
                confidence=0,
                unresolvedQuestions=("unavailable",),
                modelDecisionRef="decision-2",
            )
        )
        foreign_persisted = await client.get(
            f"/internal/v1/employment-patch-proposals/{proposal_id}",
            headers={"X-Correlation-Id": headers["X-Correlation-Id"]},
        )
        context.relationship_id = "relationship-1"
        recovered = await client.get(
            f"/internal/v1/employment-patch-proposals/{proposal_id}",
            headers={"X-Correlation-Id": headers["X-Correlation-Id"]},
        )

    assert created.status_code == 202
    assert replay.status_code == 200
    assert foreign_memory.status_code == 404
    assert foreign_persisted.status_code == 404
    assert "Increase qualified enquiries." not in foreign_memory.text
    assert "Increase qualified enquiries." not in foreign_persisted.text
    assert recovered.status_code == 200
    assert recovered.json()["state"] == "PROPOSED"


@pytest.mark.asyncio
async def test_crash_after_interpretation_fails_closed_without_reinterpreting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def interpreter(_request):
        nonlocal calls
        calls += 1
        return ProposalInterpretation(
            operations=(ProposalOperation(op="ADD", semanticPath="/goals/0/outcome", value="Goal"),),
            confidence=0.9,
            modelDecisionRef="decision",
        )

    class Repository:
        claim = None

        @asynccontextmanager
        async def serialize_proposal(self, *_args):
            yield self

        async def find_by_idempotency(self, *_args):
            return None

        async def claim_dispatch(self, _tenant, _relationship, _key, digest, mode):
            if self.claim is not None:
                return False, *self.claim
            self.claim = (digest, mode)
            return True, digest, mode

        async def save(self, *_args):
            raise RuntimeError("simulated persistence failure")

    repository = Repository()
    context = SimpleNamespace(
        issuer_uri="spiffe://waooaw.test/workload/professional-runtime",
        tenant_id="00000000-0000-0000-0000-000000000001",
        relationship_id="relationship-1",
    )
    monkeypatch.setattr(employment_patch, "_authorize", lambda *_args: context)
    monkeypatch.setattr(employment_patch, "_repository", lambda _request: repository)
    application = FastAPI()
    application.state.employment_patch_service = _service(interpreter)
    application.include_router(router)
    headers = {
        "Idempotency-Key": "00000000-0000-0000-0000-000000000009",
        "X-Correlation-Id": "00000000-0000-0000-0000-000000000007",
    }
    payload = _request().model_dump(mode="json", by_alias=True)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://air") as client:
        with pytest.raises(RuntimeError, match="simulated persistence failure"):
            await client.post("/internal/v1/employment-patch-proposals", json=payload, headers=headers)
        application.state.employment_patch_service = _service(interpreter)
        retry = await client.post("/internal/v1/employment-patch-proposals", json=payload, headers=headers)

    assert retry.status_code == 503
    assert retry.json()["code"] == "AIR_EMPLOYMENT_RECONCILIATION_REQUIRED"
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("old_claim,changed_interpreter", [(False, False), (True, False), (False, True)])
async def test_restart_recovery_only_replays_proven_disabled_interpreter(
    monkeypatch: pytest.MonkeyPatch, old_claim: bool, changed_interpreter: bool
) -> None:
    class Repository:
        claim = None
        stored = None
        fail_save = True

        @asynccontextmanager
        async def serialize_proposal(self, *_args):
            yield self

        async def find_by_idempotency(self, *_args):
            return self.stored

        async def claim_dispatch(self, _tenant, _relationship, _key, digest, mode):
            if self.claim is not None:
                return False, *self.claim
            self.claim = (digest, mode)
            return True, digest, mode

        async def save(self, _tenant, _relationship, _key, digest, _receipt, proposal):
            if self.fail_save:
                raise RuntimeError("simulated storage outage")
            self.stored = SimpleNamespace(request_digest=digest, proposal_json=proposal)

    repository = Repository()
    context = SimpleNamespace(
        issuer_uri="spiffe://waooaw.test/workload/professional-runtime",
        tenant_id="00000000-0000-0000-0000-000000000001",
        relationship_id="relationship-1",
    )
    monkeypatch.setattr(employment_patch, "_authorize", lambda *_args: context)
    monkeypatch.setattr(employment_patch, "_repository", lambda _request: repository)
    application = FastAPI()
    application.state.employment_patch_service = _service(employment_patch._unavailable_interpreter)
    application.include_router(router)
    headers = {
        "Idempotency-Key": "00000000-0000-0000-0000-000000000009",
        "X-Correlation-Id": "00000000-0000-0000-0000-000000000007",
    }
    payload = _request().model_dump(mode="json", by_alias=True)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://air") as client:
        with pytest.raises(RuntimeError, match="simulated storage outage"):
            await client.post("/internal/v1/employment-patch-proposals", json=payload, headers=headers)
        if old_claim:
            repository.claim = (repository.claim[0], "UNKNOWN")
        interpreter = (
            (lambda _request: pytest.fail("Unknown interpreter must not be invoked"))
            if changed_interpreter
            else employment_patch._unavailable_interpreter
        )
        application.state.employment_patch_service = _service(interpreter)
        repository.fail_save = False
        retry = await client.post("/internal/v1/employment-patch-proposals", json=payload, headers=headers)

    if old_claim or changed_interpreter:
        assert retry.status_code == 503
        assert retry.json()["code"] == "AIR_EMPLOYMENT_RECONCILIATION_REQUIRED"
        assert repository.stored is None
    else:
        assert retry.status_code == 202
        assert repository.stored.proposal_json["state"] == "UNREPRESENTABLE"
        assert repository.stored.proposal_json["operations"] == []
        assert repository.stored.proposal_json["reasonCode"] == "MODEL_UNAVAILABLE"


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["persisted", "unknown", "conflict", "stopped"])
async def test_keyed_reconciliation_never_interprets_or_claims(monkeypatch: pytest.MonkeyPatch, outcome: str) -> None:
    payload = _request()
    service = _service(
        lambda _request: ProposalInterpretation(
            operations=(ProposalOperation(op="ADD", semanticPath="/goals/0/outcome", value="Goal"),),
            confidence=0.9,
            modelDecisionRef="decision",
        )
    )
    receipt, _ = service.propose("pr", uuid4(), payload, tenant_id="tenant")
    proposal = service.get(receipt.proposal_id, "tenant")
    key = uuid4()
    context = SimpleNamespace(tenant_id="tenant", relationship_id="relationship-1")

    class Repository:
        async def find_by_idempotency(self, tenant, relationship, actual_key):
            assert (tenant, relationship, actual_key) == ("tenant", "relationship-1", key)
            if outcome == "stopped":
                raise employment_patch.EmploymentDispatchStoppedError("stopped")
            if outcome == "unknown":
                return None
            return SimpleNamespace(
                request_digest="b" * 64 if outcome == "conflict" else payload.request_digest,
                proposal_json=proposal.model_dump(mode="json", by_alias=True),
            )

    monkeypatch.setattr(employment_patch, "_authorize", lambda *_args: context)
    monkeypatch.setattr(employment_patch, "_repository", lambda _request: Repository())
    application = FastAPI()
    application.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://air") as client:
        response = await client.post(
            "/internal/v1/employment-patch-proposals/reconcile",
            json=payload.model_dump(mode="json", by_alias=True),
            headers={"Idempotency-Key": str(key), "X-Correlation-Id": str(uuid4())},
        )
    assert response.status_code == {"persisted": 200, "unknown": 503, "conflict": 409, "stopped": 423}[outcome]
    if outcome == "persisted":
        assert response.json()["proposalId"] == str(receipt.proposal_id)


@pytest.mark.asyncio
async def test_stop_during_interpretation_prevents_result_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    service = _service(
        lambda _request: (
            calls.append(True)
            or ProposalInterpretation(
                operations=(ProposalOperation(op="ADD", semanticPath="/goals/0/outcome", value="Goal"),),
                confidence=0.9,
                modelDecisionRef="decision",
            )
        )
    )

    class Repository:
        @asynccontextmanager
        async def serialize_proposal(self, *_args):
            yield self

        async def find_by_idempotency(self, *_args):
            return None

        async def claim_dispatch(self, _tenant, _relationship, _key, digest, mode):
            return True, digest, mode

        async def save(self, *_args):
            raise employment_patch.EmploymentDispatchStoppedError("Stop committed during interpretation")

    monkeypatch.setattr(
        employment_patch,
        "_authorize",
        lambda *_args: SimpleNamespace(
            tenant_id="tenant",
            relationship_id="relationship-1",
            issuer_uri="pr",
        ),
    )
    monkeypatch.setattr(employment_patch, "_repository", lambda _request: Repository())
    application = FastAPI()
    application.state.employment_patch_service = service
    application.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://air") as client:
        response = await client.post(
            "/internal/v1/employment-patch-proposals",
            json=_request().model_dump(mode="json", by_alias=True),
            headers={"Idempotency-Key": str(uuid4()), "X-Correlation-Id": str(uuid4())},
        )
    assert response.status_code == 423
    assert calls == [True]
    assert response.json()["code"] == "AIR_EMPLOYMENT_STOPPED"
    assert "Goal" not in response.text


@pytest.mark.asyncio
async def test_same_process_recovers_cached_proposal_after_storage_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def interpreter(_request):
        nonlocal calls
        calls += 1
        return ProposalInterpretation(
            operations=(ProposalOperation(op="ADD", semanticPath="/goals/0/outcome", value="Goal"),),
            confidence=0.9,
            modelDecisionRef="decision",
        )

    class Repository:
        claim = None
        stored = None
        save_attempts = 0

        @asynccontextmanager
        async def serialize_proposal(self, *_args):
            yield self

        async def find_by_idempotency(self, *_args):
            return self.stored

        async def claim_dispatch(self, _tenant, _relationship, _key, digest, mode):
            if self.claim is not None:
                return False, *self.claim
            self.claim = (digest, mode)
            return True, digest, mode

        async def save(self, tenant, relationship, key, digest, _receipt, proposal):
            self.save_attempts += 1
            if self.save_attempts == 1:
                raise RuntimeError("simulated storage outage")
            self.stored = SimpleNamespace(
                tenant_id=tenant,
                relationship_ref=relationship,
                idempotency_key=key,
                request_digest=digest,
                proposal_json=proposal,
            )

    repository = Repository()
    context = SimpleNamespace(
        issuer_uri="spiffe://waooaw.test/workload/professional-runtime",
        tenant_id="00000000-0000-0000-0000-000000000001",
        relationship_id="relationship-1",
    )
    monkeypatch.setattr(employment_patch, "_authorize", lambda *_args: context)
    monkeypatch.setattr(employment_patch, "_repository", lambda _request: repository)
    application = FastAPI()
    application.state.employment_patch_service = _service(interpreter)
    application.include_router(router)
    headers = {
        "Idempotency-Key": "00000000-0000-0000-0000-000000000009",
        "X-Correlation-Id": "00000000-0000-0000-0000-000000000007",
    }
    payload = _request().model_dump(mode="json", by_alias=True)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://air") as client:
        with pytest.raises(RuntimeError, match="simulated storage outage"):
            await client.post("/internal/v1/employment-patch-proposals", json=payload, headers=headers)
        recovered = await client.post("/internal/v1/employment-patch-proposals", json=payload, headers=headers)
        replay = await client.post("/internal/v1/employment-patch-proposals", json=payload, headers=headers)

    assert recovered.status_code == 200
    assert replay.status_code == 200
    assert recovered.json()["proposalId"] == replay.json()["proposalId"]
    assert calls == 1
    assert repository.save_attempts == 2


@pytest.mark.asyncio
async def test_get_does_not_expose_unpersisted_cached_proposal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(
        lambda _request: ProposalInterpretation(
            operations=(ProposalOperation(op="ADD", semanticPath="/goals/0/outcome", value="Goal"),),
            confidence=0.9,
            modelDecisionRef="decision",
        )
    )
    tenant = "00000000-0000-0000-0000-000000000001"
    issuer = "spiffe://waooaw.test/workload/professional-runtime"
    receipt, _ = service.propose(issuer, uuid4(), _request(), tenant_id=tenant)

    class Repository:
        async def get(self, tenant_id, proposal_id):
            assert tenant_id == tenant
            assert proposal_id == receipt.proposal_id
            return None

    monkeypatch.setattr(
        employment_patch,
        "_authorize",
        lambda *_args: SimpleNamespace(tenant_id=tenant, relationship_id="relationship-1"),
    )
    monkeypatch.setattr(employment_patch, "_repository", lambda _request: Repository())
    application = FastAPI()
    application.state.employment_patch_service = service
    application.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://air") as client:
        response = await client.get(
            f"/internal/v1/employment-patch-proposals/{receipt.proposal_id}",
            headers={"X-Correlation-Id": str(uuid4())},
        )
    assert response.status_code == 404
    assert response.json()["code"] == "AIR_EMPLOYMENT_NOT_FOUND"


def test_http_dependencies_fail_closed_without_composed_security_and_storage() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    with pytest.raises(EmploymentProposalError, match="AIR_EMPLOYMENT_UNAVAILABLE"):
        employment_patch._service(request)
    with pytest.raises(EmploymentProposalError, match="AIR_EMPLOYMENT_UNAVAILABLE"):
        employment_patch._repository(request)
    with pytest.raises(EmploymentProposalError, match="AIR_EMPLOYMENT_UNAVAILABLE"):
        employment_patch._authorize(
            request,
            "/internal/v1/employment-patch-proposals",
            "proposeEmploymentPatch",
            "a" * 64,
            "relationship-1",
            uuid4(),
        )


def test_http_authorization_maps_verifier_denial_without_details() -> None:
    application = SimpleNamespace(
        state=SimpleNamespace(
            employment_workload_auth=EmploymentWorkloadAuth(
                frozenset(),
                {},
                "waooaw.test",
                "urn:waooaw:service:ai-runtime",
            )
        )
    )
    request = SimpleNamespace(app=application, scope={"state": {}}, headers={})
    with pytest.raises(EmploymentProposalError, match="AIR_EMPLOYMENT_UNAUTHORIZED"):
        employment_patch._authorize(
            request,
            "/internal/v1/employment-patch-proposals",
            "proposeEmploymentPatch",
            "a" * 64,
            "relationship-1",
            uuid4(),
        )


def test_tenant_mismatch_is_indistinguishable_from_missing_proposal() -> None:
    service = _service(
        lambda _request: ProposalInterpretation(
            confidence=0,
            unresolvedQuestions=("unavailable",),
            modelDecisionRef="decision-2",
        )
    )
    receipt, _ = service.propose(
        "professional-runtime",
        uuid4(),
        _request(),
        tenant_id="tenant-1",
    )
    with pytest.raises(EmploymentProposalError, match="AIR_EMPLOYMENT_NOT_FOUND"):
        service.get(receipt.proposal_id, "tenant-2")


def test_model_policy_fields_preserve_real_pydantic_method_protection() -> None:
    assert employment_patch.EmploymentModel.model_config["protected_namespaces"] == ("model_validate", "model_dump")
