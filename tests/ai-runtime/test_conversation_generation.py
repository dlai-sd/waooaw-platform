"""WC-134 governed generation, bounded resume and fresh-owner recovery regressions."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import copy
import hashlib
from pathlib import Path

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import ValidationError

from conversation_generation import (
    GenerationInput,
    GenerationRequest,
    GenerationResult,
    GovernedGenerationService,
    InferenceBinding,
    InferencePermit,
    InferenceReceipt,
    GenerationContentRecoveryRequest,
    GenerationContentRecoveryResult,
    ConversationResumeContext,
    canonical,
)
from conversation_generation_provider import InstitutionalOllamaProvider
from conversation_generation_owner import BusinessPlatformGenerationOwner
from conversation_generation_store import ConversationGenerationStore
from employment_auth import DelegatedContext
from employment_persistence import EmploymentDispatchStoppedError


def scenario(professional="digital-marketing-agent"):
    key, tenant, relationship, actor, execution, contribution = (uuid4() for _ in range(6))
    prompt = {"schemaVersion": "1.0", "systemPrompt": "Synthetic admitted skill prompt", "wrapper": "RAW_SYSTEM_DOUBLE_NEWLINE"}
    prompt_digest = "sha256:" + hashlib.sha256(canonical(prompt)).hexdigest()
    rates = {
        "schemaVersion": "1.0",
        "currency": "INR",
        "rounding": "CEIL_COMPONENT_PER_MILLION",
        "inputPaisePerMillion": 1,
        "outputPaisePerMillion": 1,
    }
    binding = InferenceBinding(
        providerId="synthetic-ollama",
        providerIdentityUri="spiffe://waooaw.test/provider/model",
        adapter="OLLAMA_INSTITUTIONAL",
        endpoint="https://model.example.invalid",
        model="synthetic-model",
        modelDigest="sha256:" + "a" * 64,
        tokenizerDigest="sha256:" + "b" * 64,
        tokenizerVersion="1",
        region="test-region",
        tier="LOCAL",
        languages=["en"],
        domains=[professional],
        planTiers=["TEST_PLAN"],
        resolvedPlanTier="TEST_PLAN",
        mandatoryTiers=["LOCAL"],
        residencyRegions=["test-region"],
        institutionalBoundary=True,
        configurationDigest="sha256:" + "c" * 64,
        rateDigest="sha256:" + hashlib.sha256(canonical(rates)).hexdigest(),
        inputPaisePerMillion=1,
        outputPaisePerMillion=1,
        systemPrompt=prompt["systemPrompt"],
        promptVersion="1",
        promptDigest=prompt_digest,
        promptWrapper=prompt["wrapper"],
        modelPolicyDigest="sha256:" + "d" * 64,
        expiresAt=datetime.now(timezone.utc) + timedelta(minutes=2),
        bindingId=uuid4(),
    )
    mandate = {
        "schemaVersion": "1.0",
        "tenantId": str(tenant),
        "relationshipId": str(relationship),
        "actorId": str(actor),
        "actorRole": "EMPLOYER",
        "idempotencyIdentity": str(key),
        "stopped": False,
        "relationshipLifecycle": "ACTIVE",
        "engagementMode": "LIVE",
        "approvalRefs": ["synthetic-confirmed-hire"],
        "agentInstanceId": str(uuid4()),
        "professionalType": professional,
        "skillId": professional + ":specific-skill",
        "permittedActions": ["RESPOND"],
        "exclusions": [],
        "deadline": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
        "conversationOperation": {
            "kind": "PROFESSIONAL_RESPONSE",
            "governedAction": "RESPOND",
            "promptPolicy": {"digest": prompt_digest, "version": "1"},
            "modelPolicy": {"digest": binding.model_policy_digest},
        },
    }
    payload = dict(
        schemaVersion="1.0",
        relationshipRef=str(relationship),
        conversationId=str(uuid4()),
        executionId=str(execution),
        contributionRef=str(contribution),
        operationalMandate=mandate,
        input={"text": "Synthetic customer request", "language": "en"},
    )
    payload["requestDigest"] = hashlib.sha256(canonical(payload)).hexdigest()
    request = GenerationRequest.model_validate(payload)
    context = SimpleNamespace(
        tenant_id=str(tenant),
        actor_subject=str(actor),
        effective_role="EMPLOYER",
        subject_reference=str(contribution),
        command_id=str(execution),
    )
    permit = InferencePermit(
        reservationId=uuid4(),
        commercialReservationId=uuid4(),
        evidenceId=uuid4(),
        maximumCostPaise=2,
        expiresAt=datetime.now(timezone.utc) + timedelta(seconds=29),
        binding=binding,
    )
    owner = SimpleNamespace(
        resolve=AsyncMock(return_value=binding),
        reserve=AsyncMock(return_value=permit),
        settle=AsyncMock(),
        release=AsyncMock(),
        reconcile=AsyncMock(return_value=InferenceReceipt(state="UNRESOLVED")),
        authorize_content=AsyncMock(),
    )
    return request, context, key, owner, permit


def test_batch_generation_verifies_every_source_and_exact_ordered_digest():
    original, context, _key, _owner, _permit = scenario()
    batch_id, work_item, invocation = uuid4(), uuid4(), uuid4()
    sources = []
    for sequence, text in enumerate(("Make a post", "Use a festive tone"), start=1):
        source_key, evidence = uuid4(), uuid4()
        mandate = copy.deepcopy(original.operational_mandate)
        mandate["mandateId"] = str(uuid4())
        mandate["idempotencyIdentity"] = str(source_key)
        mandate["constitutionalEvidenceRef"] = f"ce-evidence:{evidence}"
        mandate["deadline"] = datetime.fromisoformat(mandate["deadline"]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        mandate["mandateDigest"] = (
            "sha256:"
            + hashlib.sha256(canonical({key: value for key, value in mandate.items() if key != "mandateDigest"})).hexdigest()
        )
        sources.append(
            {
                "schemaVersion": "1.0",
                "messageId": str(uuid4()),
                "executionId": str(uuid4()),
                "sequence": sequence,
                "workItemId": str(work_item),
                "workItemRevision": 4,
                "workItemInvocationId": str(invocation),
                "idempotencyKey": str(source_key),
                "evidenceId": str(evidence),
                "text": text,
                "language": "en",
                "operationalMandate": mandate,
            }
        )
    digest_sources = [
        {
            "schemaVersion": source["schemaVersion"],
            "messageId": source["messageId"],
            "executionId": source["executionId"],
            "sequence": source["sequence"],
            "workItemId": source["workItemId"],
            "workItemRevision": source["workItemRevision"],
            "workItemInvocationId": source["workItemInvocationId"],
            "idempotencyKey": source["idempotencyKey"],
            "evidenceId": source["evidenceId"],
            "text": source["text"],
            "language": source["language"],
            "mandateId": source["operationalMandate"].get("mandateId"),
            "mandateDigest": source["operationalMandate"]["mandateDigest"],
        }
        for source in sources
    ]
    batch = {"batchId": str(batch_id), "sourceListDigest": "", "sources": sources}
    batch["sourceListDigest"] = "sha256:" + hashlib.sha256(canonical(digest_sources)).hexdigest()
    payload = {
        "schemaVersion": "1.0",
        "relationshipRef": str(original.relationship_ref),
        "conversationId": str(original.conversation_id),
        "executionId": str(original.execution_id),
        "contributionRef": str(batch_id),
        "operationalMandate": sources[0]["operationalMandate"],
        "input": {"text": "Make a post\nUse a festive tone", "language": "en"},
        "batch": batch,
    }
    payload["requestDigest"] = hashlib.sha256(canonical(payload)).hexdigest()
    request = GenerationRequest.model_validate(payload)
    batch_context = SimpleNamespace(
        tenant_id=context.tenant_id,
        actor_subject=context.actor_subject,
        effective_role=context.effective_role,
        subject_reference=str(batch_id),
        command_id=context.command_id,
    )

    request.verify_binding(batch_context, batch_id, recovery=False)

    changed = request.model_dump(by_alias=True, mode="json")
    changed["batch"]["sources"][1]["sequence"] = 3
    changed["requestDigest"] = hashlib.sha256(
        canonical({key: value for key, value in changed.items() if key != "requestDigest"})
    ).hexdigest()
    with pytest.raises(ValueError, match="batch identity"):
        GenerationRequest.model_validate(changed).verify_binding(batch_context, batch_id, recovery=False)


def resume_context(request, texts=("A prior customer turn", "A prior professional reply")):
    body = {
        "schemaVersion": "1.0",
        "tenantId": request.operational_mandate["tenantId"],
        "relationshipId": str(request.relationship_ref),
        "conversationId": str(request.conversation_id),
        "originalMessageId": str(request.contribution_ref),
        "skillId": request.operational_mandate["skillId"],
        "beforeSequence": 30,
        "turns": [
            {
                "messageId": str(uuid4()),
                "sequence": index + 1,
                "actor": "CUSTOMER" if index % 2 == 0 else "PROFESSIONAL",
                "text": text,
                "language": "en",
            }
            for index, text in enumerate(texts)
        ],
    }
    body["digest"] = "sha256:" + hashlib.sha256(canonical(body)).hexdigest()
    return body


def test_resume_prompt_uses_only_digest_bound_agent_specific_history():
    request, _, _, _, permit = scenario()
    history = ConversationResumeContext.model_validate(resume_context(request))
    payload = permit.binding.model_dump(by_alias=True, mode="json")
    payload["conversationContext"] = history.model_dump(by_alias=True, mode="json")
    payload["promptWrapper"] = "RAW_SYSTEM_CANONICAL_HISTORY_V1"
    payload["promptDigest"] = (
        "sha256:"
        + hashlib.sha256(
            canonical(
                {
                    "schemaVersion": "1.0",
                    "systemPrompt": payload["systemPrompt"],
                    "wrapper": payload["promptWrapper"],
                }
            )
        ).hexdigest()
    )
    binding = InferenceBinding.model_validate(payload)
    prompt = InstitutionalOllamaProvider._prompt(binding, request)
    assert "A prior customer turn" in prompt and "A prior professional reply" in prompt
    assert prompt.endswith(request.input.text) and "untrusted reference data" in prompt


@pytest.mark.parametrize("failure", ["tampered", "count", "utf16", "order", "current_message"])
def test_resume_context_rejects_unbounded_or_unproven_history(failure):
    request, _, _, _, _ = scenario()
    body = resume_context(request)
    if failure == "tampered":
        body["turns"][0]["text"] = "Substituted"
    elif failure == "count":
        body = resume_context(request, ("x",) * 13)
    elif failure == "utf16":
        body = resume_context(request, ("\U0001f600" * 4001,))
    elif failure == "order":
        body["turns"].reverse()
    else:
        body["turns"][0]["messageId"] = str(request.contribution_ref)
    if failure != "tampered":
        body["digest"] = (
            "sha256:" + hashlib.sha256(canonical({key: value for key, value in body.items() if key != "digest"})).hexdigest()
        )
    with pytest.raises(ValidationError):
        ConversationResumeContext.model_validate(body)


@pytest.mark.parametrize("field", ["tenantId", "relationshipId", "conversationId", "originalMessageId", "skillId"])
def test_resume_context_rejects_cross_customer_or_agent_skill(field):
    request, _, _, _, _ = scenario()
    body = resume_context(request)
    body[field] = "other-agent:skill" if field == "skillId" else str(uuid4())
    body["digest"] = (
        "sha256:" + hashlib.sha256(canonical({key: value for key, value in body.items() if key != "digest"})).hexdigest()
    )
    with pytest.raises(ValueError, match="original agent skill"):
        ConversationResumeContext.model_validate(body).verify_request(request)


def test_original_prompt_wrapper_cannot_silently_gain_history():
    request, _, _, _, permit = scenario()
    payload = permit.binding.model_dump(by_alias=True, mode="json")
    payload["conversationContext"] = resume_context(request)
    with pytest.raises(ValueError, match="does not admit"):
        InstitutionalOllamaProvider._prompt(InferenceBinding.model_validate(payload), request)


class Store:
    def __init__(self):
        self.created = False
        self.admission_claimed = False
        self.claimed = False
        self.result = None
        self.writes = 0
        self.retained_at = datetime.now(timezone.utc)

    async def claim(self, *_):
        self.created = True
        acquired = not self.admission_claimed and not self.claimed and self.result is None
        if acquired:
            self.admission_claimed = True
        return acquired, self.result

    async def release_queue_claim(self, *_):
        assert self.admission_claimed and not self.claimed and self.result is None
        self.admission_claimed = False

    async def begin_dispatch(self, *_):
        if self.claimed:
            return False
        self.claimed = True
        return True

    async def lookup(self, *_):
        return self.result

    async def lookup_retained(self, *_):
        return self.result, self.retained_at if self.result is not None else None

    async def save(self, *args):
        self.result = args[-1]
        self.writes += 1


class Provider:
    def __init__(self, prompt_tokens=8192, output_tokens=2048, timeout=False):
        self.prompt_tokens, self.output_tokens, self.timeout = prompt_tokens, output_tokens, timeout
        self.calls = 0

    def count_prompt(self, *_):
        return self.prompt_tokens

    async def generate(self, binding, request, permit, authorize, settle):
        self.calls += 1
        await authorize()
        if self.timeout:
            raise TimeoutError("Synthetic lost provider response")
        await settle(self.prompt_tokens, self.output_tokens)
        return "Synthetic professional output", self.prompt_tokens, self.output_tokens


@pytest.mark.parametrize("professional", ["digital-marketing-agent", "trading-fo-crypto", "agriculture-expert"])
async def test_confirmed_agent_specific_skill_reaches_bounded_generation(professional):
    request, context, key, owner, _ = scenario(professional)
    provider, store = Provider(), Store()
    result = await GovernedGenerationService(store, owner, provider).execute(request, context, key, recovery=False)
    assert result.state == "COMPLETED"
    assert result.input_tokens == 8192 and result.output_tokens == 2048
    assert owner.settle.await_count == 1 and provider.calls == 1 and store.claimed


@pytest.mark.parametrize("change", ["professionalType", "relationshipLifecycle", "actorId", "skillId"])
async def test_cross_agent_unconfirmed_relationship_and_original_actor_or_skill_drift_are_denied(change):
    request, context, key, owner, _ = scenario()
    payload = request.model_dump(by_alias=True, mode="json", exclude={"request_digest"})
    payload["operationalMandate"][change] = "foreign-or-unconfirmed"
    payload["requestDigest"] = hashlib.sha256(canonical(payload)).hexdigest()
    changed = GenerationRequest.model_validate(payload)
    if change == "skillId":
        owner.resolve.side_effect = ValueError("BP original admitted-skill authority rejected drift")
    provider = Provider()
    try:
        result = await GovernedGenerationService(Store(), owner, provider).execute(changed, context, key, recovery=False)
    except ValueError:
        pass
    else:
        assert result.state == "FAILED"
    assert provider.calls == 0 and owner.reserve.await_count == 0


@pytest.mark.parametrize(
    "prompt,output,state,dispatches", [(8192, 2048, "COMPLETED", 1), (8193, 1, "FAILED", 0), (1, 2049, "UNRESOLVED", 1)]
)
async def test_exact_token_limits_and_full_overrun_settlement(prompt, output, state, dispatches):
    request, context, key, owner, _ = scenario()
    provider = Provider(prompt, output)
    result = await GovernedGenerationService(Store(), owner, provider).execute(request, context, key, recovery=False)
    assert result.state == state and provider.calls == dispatches
    if output == 2049:
        assert owner.settle.await_args.args[-1] == 2049
        assert result.text is None


async def test_unknown_provider_outcome_retains_reservation_and_recovery_never_dispatches():
    request, context, key, owner, permit = scenario()
    provider, store = Provider(timeout=True), Store()
    service = GovernedGenerationService(store, owner, provider)
    first = await service.execute(request, context, key, recovery=False)
    recovered = await service.execute(request, context, key, recovery=True)
    assert first == recovered and recovered.state == "UNRESOLVED" and recovered.reservation_id == permit.reservation_id
    assert provider.calls == 1 and owner.reserve.await_count == 1 and owner.release.await_count == 0


async def test_read_only_recovery_of_absent_original_does_not_create_claim():
    request, context, key, owner, _ = scenario()
    store, provider = Store(), Provider()
    result = await GovernedGenerationService(store, owner, provider).execute(request, context, key, recovery=True)
    assert result.state == "UNRESOLVED" and not store.created and provider.calls == 0 and owner.resolve.await_count == 0


async def test_known_shared_concurrency_denial_keeps_pre_dispatch_work_queued():
    request, context, key, owner, _ = scenario()
    response = httpx.Response(
        503, headers={"X-Inference-State": "QUEUED"}, request=httpx.Request("POST", "https://owner.example.invalid")
    )
    owner.reserve.side_effect = httpx.HTTPStatusError(
        "Synthetic shared concurrency denial", request=response.request, response=response
    )
    provider, store = Provider(), Store()
    result = await GovernedGenerationService(store, owner, provider).execute(request, context, key, recovery=False)
    assert result.reason == "GENERATION_QUEUED" and not store.claimed and store.writes == 0 and provider.calls == 0
    owner.reserve.side_effect = None
    retried = await GovernedGenerationService(store, owner, provider).execute(request, context, key, recovery=False)
    assert retried.state == "COMPLETED" and provider.calls == 1


@pytest.mark.parametrize("text", ["\x00", " ", "x" * 32001, "\U0001f33e" * 16001])
def test_canonical_input_has_exact_utf16_bound_and_no_invalid_content(text):
    with pytest.raises(ValidationError):
        GenerationInput(text=text, language="en")


def test_non_completed_results_cannot_release_text():
    with pytest.raises(ValidationError):
        GenerationResult(executionId=uuid4(), requestDigest="a" * 64, state="UNRESOLVED", text="private output", reason="UNKNOWN")


async def test_completed_recovery_revalidates_current_owner_without_dispatch():
    request, context, key, owner, _ = scenario()
    store, provider = Store(), Provider()
    service = GovernedGenerationService(store, owner, provider)
    await service.execute(request, context, key, recovery=False)
    original_resolutions = owner.resolve.await_count
    recovered = await service.execute(request, context, key, recovery=True)
    assert recovered.state == "COMPLETED" and owner.resolve.await_count == original_resolutions + 1
    assert provider.calls == 1 and owner.reserve.await_count == 1
    owner.resolve.side_effect = ValueError("Original owner authority was revoked")
    with pytest.raises(ValueError):
        await service.execute(request, context, key, recovery=True)
    assert provider.calls == 1


class _DatabaseContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *_):
        return None


class _GenerationConnection:
    def __init__(self):
        self.execute = AsyncMock(return_value="OK")
        self.fetchrow = AsyncMock()
        self.fetchval = AsyncMock()

    def transaction(self):
        return _DatabaseContext(self)


class _GenerationPool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return _DatabaseContext(self.connection)


async def test_generation_store_preserves_exact_claim_and_result_identity():
    request, context, key, _, permit = scenario()
    relationship = request.relationship_ref
    connection = _GenerationConnection()
    store = ConversationGenerationStore(_GenerationPool(connection))
    result = GenerationResult(
        executionId=request.execution_id,
        requestDigest=request.request_digest,
        state="COMPLETED",
        text="synthetic result",
        inputTokens=1,
        outputTokens=1,
        reservationId=permit.reservation_id,
        commercialReservationId=permit.commercial_reservation_id,
        evidenceId=permit.evidence_id,
    )
    row = {
        "execution_id": request.execution_id,
        "request_digest": request.request_digest,
        "result_json": result.model_dump_json(by_alias=True),
        "completed_at": datetime.now(timezone.utc),
    }
    with pytest.raises(ValueError, match="idempotency binding conflict"):
        store._result({**row, "request_digest": "b" * 64}, request)

    connection.fetchval.return_value = False
    connection.fetchrow.return_value = None
    assert await store.lookup(context.tenant_id, relationship, key, request) is None
    assert await store.lookup_retained(context.tenant_id, relationship, key, request) == (
        None,
        None,
    )
    connection.fetchrow.return_value = row
    assert await store.lookup(context.tenant_id, relationship, key, request) == result
    retained, retained_at = await store.lookup_retained(context.tenant_id, relationship, key, request)
    assert retained == result and retained_at == row["completed_at"]

    connection.fetchrow.side_effect = [{"execution_id": request.execution_id}]
    assert await store.claim(context.tenant_id, relationship, key, request) == (
        True,
        None,
    )
    connection.fetchrow.side_effect = [None, None]
    with pytest.raises(ValueError, match="another original execution"):
        await store.claim(context.tenant_id, relationship, key, request)
    connection.fetchrow.side_effect = [None, row]
    connection.fetchval.side_effect = [False, True]
    assert await store.claim(context.tenant_id, relationship, key, request) == (
        True,
        result,
    )

    connection.fetchrow.side_effect = None
    connection.fetchval.side_effect = [False, False]
    with pytest.raises(ValueError, match="pre-dispatch admission claim"):
        await store.release_queue_claim(context.tenant_id, relationship, key, request)
    connection.fetchval.side_effect = [False, True]
    await store.release_queue_claim(context.tenant_id, relationship, key, request)
    connection.fetchval.side_effect = [False, True]
    assert await store.begin_dispatch(context.tenant_id, relationship, key, request)

    connection.fetchval.side_effect = None
    connection.fetchval.return_value = False
    connection.fetchrow.return_value = None
    with pytest.raises(ValueError, match="exact original claim"):
        await store.save(context.tenant_id, relationship, key, result)
    connection.fetchrow.return_value = {**row, "result_json": {"state": "foreign"}}
    with pytest.raises(ValueError, match="cannot replace"):
        await store.save(context.tenant_id, relationship, key, result)
    connection.fetchrow.return_value = {
        **row,
        "result_json": result.model_dump(by_alias=True, mode="json"),
    }
    await store.save(context.tenant_id, relationship, key, result)
    connection.fetchrow.return_value = {**row, "result_json": None}
    await store.save(context.tenant_id, relationship, key, result)
    connection.fetchval.return_value = True
    with pytest.raises(EmploymentDispatchStoppedError, match="Generation stopped"):
        await store._lock(connection, context.tenant_id, relationship)


async def test_business_platform_owner_signs_exact_commands_and_validates_receipts():
    request, context_values, key, _, permit = scenario()
    with pytest.raises(ValueError, match="institutional HTTPS"):
        BusinessPlatformGenerationOwner("http://business.test", Path("/unused"))
    now = int(datetime.now(timezone.utc).timestamp())
    context = DelegatedContext(
        "1.0",
        "source-key",
        "spiffe://source",
        "source-audience",
        "POST",
        "/source",
        "sourceOperation",
        1,
        context_values.actor_subject,
        "BP_SESSION",
        context_values.effective_role,
        context_values.tenant_id,
        str(request.relationship_ref),
        "SOURCE",
        context_values.subject_reference,
        request.request_digest,
        context_values.command_id,
        str(key),
        {},
        now,
        now,
        now + 60,
        str(uuid4()),
        str(uuid4()),
    )
    owner = BusinessPlatformGenerationOwner.__new__(BusinessPlatformGenerationOwner)
    owner.endpoint = "https://business.test"
    owner.key = ec.generate_private_key(ec.SECP256R1())
    owner.issuer = "spiffe://air"
    owner.key_id = "air-key"
    owner.audience = "urn:business"
    owner.client = AsyncMock()
    owner.client.post.return_value = httpx.Response(
        200,
        json={"state": "READ_ALLOWED"},
        request=httpx.Request("POST", "https://business.test"),
    )

    await owner._post(request, context, key, "resolve")
    await owner._post(request, context, key, "settle", permit, (1, 2))
    recovery, _, _ = content_read(request)
    await owner._post(
        request,
        context,
        key,
        "read-content",
        recovery=recovery,
    )
    sent = owner.client.post.await_args_list[-2]
    assert sent.args[0].endswith("/settle")
    assert sent.kwargs["headers"]["Content-Type"] == "application/json"

    owner._post = AsyncMock(
        return_value=httpx.Response(
            200,
            json=permit.binding.model_dump(by_alias=True, mode="json"),
            request=httpx.Request("POST", "https://business.test"),
        )
    )
    assert await owner.resolve(request, context, key) == permit.binding
    owner._post.return_value = httpx.Response(
        200,
        json=permit.model_dump(by_alias=True, mode="json"),
        request=httpx.Request("POST", "https://business.test"),
    )
    assert await owner.reserve(request, context, key, permit.binding) == permit
    changed = permit.model_copy(update={"binding": permit.binding.model_copy(update={"model": "foreign"})})
    owner._post.return_value = httpx.Response(
        200,
        json=changed.model_dump(by_alias=True, mode="json"),
        request=httpx.Request("POST", "https://business.test"),
    )
    with pytest.raises(ValueError, match="changed the admitted"):
        await owner.reserve(request, context, key, permit.binding)
    await owner.settle(request, context, key, permit, 1, 2)
    await owner.release(request, context, key, permit)
    owner._post.return_value = httpx.Response(
        200,
        json={"state": "UNRESOLVED"},
        request=httpx.Request("POST", "https://business.test"),
    )
    assert (await owner.reconcile(request, context, key)).state == "UNRESOLVED"
    owner._post.return_value = httpx.Response(
        200,
        json={"state": "READ_ALLOWED"},
        request=httpx.Request("POST", "https://business.test"),
    )
    await owner.authorize_content(recovery, context, key)
    owner._post.return_value = httpx.Response(
        200,
        json={"state": "DENIED"},
        request=httpx.Request("POST", "https://business.test"),
    )
    with pytest.raises(ValueError, match="did not authorize"):
        await owner.authorize_content(recovery, context, key)
    owner.client = AsyncMock()
    await owner.close()
    owner.client.aclose.assert_awaited_once()


def test_recovered_completion_requires_durable_retention_timestamp():
    result = GenerationResult(
        executionId=uuid4(),
        requestDigest="a" * 64,
        state="COMPLETED",
        text="retained output",
        inputTokens=1,
        outputTokens=1,
        reservationId=uuid4(),
        commercialReservationId=uuid4(),
        evidenceId=uuid4(),
    )
    with pytest.raises(ValidationError, match="durable result timestamp"):
        GenerationContentRecoveryResult(result=result, retainedAt=None)


async def test_lost_reservation_response_is_unknown_not_an_unfunded_failure():
    request, context, key, owner, _ = scenario()
    owner.reserve.side_effect = httpx.ReadTimeout("Synthetic lost BP reservation receipt")
    provider, store = Provider(), Store()
    result = await GovernedGenerationService(store, owner, provider).execute(request, context, key, recovery=False)
    assert result.state == "UNRESOLVED" and result.reason == "RESERVATION_OUTCOME_UNKNOWN"
    assert provider.calls == 0 and owner.release.await_count == 0 and store.result == result


@pytest.mark.parametrize("financial_state", ["RESERVED", "SETTLED", "RELEASED"])
async def test_financial_receipt_recovery_never_becomes_a_new_dispatch_or_content_permit(financial_state):
    request, context, key, owner, permit = scenario()
    owner.reserve.side_effect = httpx.ReadTimeout("Synthetic lost BP reservation receipt")
    provider, store = Provider(), Store()
    service = GovernedGenerationService(store, owner, provider)
    original = await service.execute(request, context, key, recovery=False)
    owner.reconcile.return_value = InferenceReceipt(
        state=financial_state,
        reservationId=permit.reservation_id,
        commercialReservationId=permit.commercial_reservation_id,
        evidenceId=permit.evidence_id,
        maximumCostPaise=permit.maximum_cost_paise,
        expiresAt=permit.expires_at,
    )
    recovered = await service.execute(request, context, key, recovery=True)
    assert recovered.state == "UNRESOLVED" and recovered.text is None
    assert recovered.reservation_id == permit.reservation_id and recovered.evidence_id == permit.evidence_id
    assert store.result == original and store.writes == 1 and not store.claimed
    assert provider.calls == 0 and owner.reserve.await_count == 1
    owner.release.assert_not_awaited()
    owner.settle.assert_not_awaited()


async def test_crash_before_air_result_save_can_read_financial_receipt_without_creating_claim():
    request, context, key, owner, permit = scenario()
    owner.reconcile.return_value = InferenceReceipt(
        state="RESERVED",
        reservationId=permit.reservation_id,
        commercialReservationId=permit.commercial_reservation_id,
        evidenceId=permit.evidence_id,
        maximumCostPaise=permit.maximum_cost_paise,
        expiresAt=permit.expires_at,
    )
    store, provider = Store(), Provider()
    recovered = await GovernedGenerationService(store, owner, provider).execute(request, context, key, recovery=True)
    assert recovered.reason == "ORIGINAL_RESULT_UNAVAILABLE" and recovered.text is None
    assert recovered.reservation_id == permit.reservation_id and not store.created and store.writes == 0
    assert provider.calls == 0
    owner.reserve.assert_not_awaited()
    owner.release.assert_not_awaited()


async def test_foreign_financial_receipt_cannot_replace_the_original_provider_reservation():
    request, context, key, owner, permit = scenario()
    provider, store = Provider(timeout=True), Store()
    service = GovernedGenerationService(store, owner, provider)
    await service.execute(request, context, key, recovery=False)
    owner.reconcile.return_value = InferenceReceipt(
        state="RESERVED",
        reservationId=uuid4(),
        commercialReservationId=uuid4(),
        evidenceId=permit.evidence_id,
        maximumCostPaise=permit.maximum_cost_paise,
        expiresAt=permit.expires_at,
    )
    with pytest.raises(ValueError, match="original reservation"):
        await service.execute(request, context, key, recovery=True)
    assert provider.calls == 1 and owner.reserve.await_count == 1


def test_financial_receipt_has_no_binding_or_professional_content():
    with pytest.raises(ValidationError):
        InferenceReceipt(state="UNRESOLVED", reservationId=uuid4())
    with pytest.raises(ValidationError):
        InferenceReceipt(state="RESERVED")
    with pytest.raises(ValidationError):
        InferenceReceipt(state="UNRESOLVED", text="private output")


def content_read(request):
    permission = {
        "schemaVersion": "1.0",
        "originalMessageId": str(request.contribution_ref),
        "originalSourceDigest": "sha256:" + "e" * 64,
        "afterSequence": 0,
        "reconciliationAuthorityId": str(uuid4()),
        "permissionExpiresAt": (datetime.now(timezone.utc) + timedelta(minutes=4)).isoformat(),
        "expectedProjectionVersion": 1,
    }
    body = GenerationContentRecoveryRequest(relationshipRef=request.relationship_ref, generation=request, permission=permission)
    reader = SimpleNamespace(
        tenant_id=request.operational_mandate["tenantId"],
        relationship_id=str(request.relationship_ref),
        actor_subject=str(uuid4()),
        effective_role="OWNER",
        command_id=permission["reconciliationAuthorityId"],
        subject_reference=str(request.contribution_ref),
    )
    return body, reader, uuid4()


async def test_fresh_reader_recovers_after_original_deadline_without_impersonation_or_new_work():
    request, _, _, owner, permit = scenario()
    payload = request.model_dump(by_alias=True, mode="json", exclude={"request_digest"})
    payload["operationalMandate"]["deadline"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    payload["requestDigest"] = hashlib.sha256(canonical(payload)).hexdigest()
    request = GenerationRequest.model_validate(payload)
    store, provider = Store(), Provider()
    store.result = GenerationResult(
        executionId=request.execution_id,
        requestDigest=request.request_digest,
        state="COMPLETED",
        text="Retained original reply",
        inputTokens=1,
        outputTokens=1,
        reservationId=permit.reservation_id,
        commercialReservationId=permit.commercial_reservation_id,
        evidenceId=permit.evidence_id,
    )
    body, reader, key = content_read(request)
    result = await GovernedGenerationService(store, owner, provider).recover_content(body, reader, key)
    assert result.result == store.result and result.retained_at == store.retained_at
    assert reader.actor_subject != request.operational_mandate["actorId"]
    assert owner.authorize_content.await_count == 2 and store.writes == 0 and not store.created
    assert provider.calls == 0
    owner.resolve.assert_not_awaited()
    owner.reserve.assert_not_awaited()
    owner.settle.assert_not_awaited()
    owner.release.assert_not_awaited()
    owner.reconcile.assert_not_awaited()


@pytest.mark.parametrize("denial_stage", [0, 1])
async def test_revocation_before_or_after_retained_read_never_releases_content(denial_stage):
    request, _, _, owner, permit = scenario()
    store, provider = Store(), Provider()
    store.result = GenerationResult(
        executionId=request.execution_id,
        requestDigest=request.request_digest,
        state="COMPLETED",
        text="Private retained reply",
        inputTokens=1,
        outputTokens=1,
        reservationId=permit.reservation_id,
        commercialReservationId=permit.commercial_reservation_id,
        evidenceId=permit.evidence_id,
    )
    owner.authorize_content.side_effect = [ValueError("Revoked")] if denial_stage == 0 else [None, ValueError("Revoked")]
    body, reader, key = content_read(request)
    with pytest.raises(ValueError, match="Revoked"):
        await GovernedGenerationService(store, owner, provider).recover_content(body, reader, key)
    assert provider.calls == 0 and store.writes == 0


async def test_missing_retained_content_remains_unresolved_without_claim_or_financial_recovery():
    request, _, _, owner, _ = scenario()
    store, provider = Store(), Provider()
    body, reader, key = content_read(request)
    result = await GovernedGenerationService(store, owner, provider).recover_content(body, reader, key)
    assert result.result.state == "UNRESOLVED" and result.result.text is None
    assert result.retained_at is None and not store.created and store.writes == 0
    owner.reconcile.assert_not_awaited()
    owner.reserve.assert_not_awaited()
    assert provider.calls == 0


@pytest.mark.parametrize("field", ["tenant_id", "relationship_id", "command_id", "subject_reference", "effective_role"])
async def test_content_read_rejects_wrong_reader_binding_before_owner_or_store(field):
    request, _, _, owner, _ = scenario()
    body, reader, key = content_read(request)
    setattr(reader, field, "foreign")
    store, provider = Store(), Provider()
    with pytest.raises(ValueError):
        await GovernedGenerationService(store, owner, provider).recover_content(body, reader, key)
    owner.authorize_content.assert_not_awaited()
    assert store.writes == 0 and not store.created and provider.calls == 0


async def test_tag_addressed_backend_is_unavailable_before_reservation_or_provider_traffic():
    request, context, key, owner, permit = scenario()
    client = AsyncMock()
    provider = InstitutionalOllamaProvider(Path("/synthetic-unavailable-tokenizers"), client)
    result = await GovernedGenerationService(Store(), owner, provider).execute(request, context, key, recovery=False)
    assert result.state == "FAILED" and result.text is None
    assert owner.reserve.await_count == 0 and client.stream.call_count == 0
    with pytest.raises(ValueError, match="IMMUTABLE_MODEL_DISPATCH_UNAVAILABLE"):
        await provider.invoke_admitted(permit.binding, request, AsyncMock())
    assert client.stream.call_count == 0


async def test_duplicate_during_reservation_cannot_poison_original_result_or_release_its_funds():
    request, context, key, owner, permit = scenario()
    store, provider = Store(), Provider()
    service = GovernedGenerationService(store, owner, provider)

    async def reserve(*_):
        duplicate = await service.execute(request, context, key, recovery=False)
        assert duplicate.state == "UNRESOLVED" and duplicate.reason == "ORIGINAL_OUTCOME_UNKNOWN"
        assert store.writes == 0 and owner.release.await_count == 0
        return permit

    owner.reserve.side_effect = reserve
    result = await service.execute(request, context, key, recovery=False)
    assert result.state == "COMPLETED" and provider.calls == 1 and owner.reserve.await_count == 1
