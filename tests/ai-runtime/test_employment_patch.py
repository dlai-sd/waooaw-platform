# Implements: WC-115 R036-R044, R092-R095
# Constitutional basis: C-023, C-049, C-059, C-062, C-076, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115

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
from employment_auth import EmploymentWorkloadAuth


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

        async def find_by_idempotency(self, *_args):
            return self.stored

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
        application.state.employment_patch_service = _service(
            lambda _request: ProposalInterpretation(
                confidence=0,
                unresolvedQuestions=("unavailable",),
                modelDecisionRef="decision-2",
            )
        )
        recovered = await client.get(
            f"/internal/v1/employment-patch-proposals/{proposal_id}",
            headers={"X-Correlation-Id": headers["X-Correlation-Id"]},
        )

    assert created.status_code == 202
    assert replay.status_code == 200
    assert recovered.status_code == 200
    assert recovered.json()["state"] == "PROPOSED"


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
