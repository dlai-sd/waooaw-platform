# Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R005
# constitutional_basis: C-059, C-062, C-063 (no customer data), ADR-014 (no credential in output), ADR-046
"""Founder diagnostic: one fixed short prompt through the hosted fallback chain. Not a customer generation."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from employment_auth import DelegatedContext, EmploymentAuthError, EmploymentWorkloadAuth
from providers.hosted.base import MODEL_NAME
from providers.hosted.fallback import ApiKeySource, ChainEntry, run_fallback_chain

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/v1/provider-generations", tags=["Provider Generation Probe"])

PROBE_ROUTE = "/internal/v1/provider-generations/probe"
PROBE_OPERATION = "probeProviderGeneration"
PROBE_PURPOSE = "PROVIDER_GENERATION_PROBE"
PROBE_PROMPT = "Reply with one short sentence confirming you are working."
PROBE_MAX_OUTPUT_TOKENS = 64
PROBE_MAX_TEXT_CHARS = 500


class ProbeProvider(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    name: Literal["sarvam", "openai", "anthropic", "google"]
    model: str | None = None

    @field_validator("model")
    @classmethod
    def conservative_model(cls, value: str | None) -> str | None:
        if value is not None and not MODEL_NAME.fullmatch(value):
            raise ValueError("Model name is not an admitted identifier")
        return value


class ProbeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    providers: list[ProbeProvider] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def distinct(self) -> ProbeRequest:
        if len({provider.name for provider in self.providers}) != len(self.providers):
            raise ValueError("A provider may appear once per probe")
        return self


class ProviderGenerationProbeService:
    def __init__(self, keys: ApiKeySource, client: httpx.AsyncClient) -> None:
        self.keys, self.client = keys, client

    async def probe(self, body: ProbeRequest) -> dict[str, Any]:
        answer, attempts = await run_fallback_chain(
            [ChainEntry(item.name, item.model) for item in body.providers],
            self.keys,
            self.client,
            PROBE_PROMPT,
            PROBE_MAX_OUTPUT_TOKENS,
        )
        return {
            "answered": None
            if answer is None
            else {
                "provider": answer.provider,
                "model": answer.model,
                "reportedModel": answer.reported_model,
                "text": answer.text[:PROBE_MAX_TEXT_CHARS],
                "inputTokens": answer.input_tokens,
                "outputTokens": answer.output_tokens,
                "latencyMs": answer.latency_ms,
            },
            "attempts": [{"provider": item.provider, "outcome": item.outcome, "reason": item.reason} for item in attempts],
        }


def _digests(raw: bytes) -> list[str]:
    digests = [hashlib.sha256(raw).hexdigest()]
    try:
        value = json.loads(raw)
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        digests.append(hashlib.sha256(canonical.encode()).hexdigest())
    except ValueError:
        pass
    return digests


def _authorize(auth: EmploymentWorkloadAuth, request: Request, raw: bytes) -> DelegatedContext | None:
    # The body digest may be bound over the raw bytes or over canonical JSON; the replay store only consumes on success.
    for digest in _digests(raw):
        try:
            context = auth.authorize(request, PROBE_ROUTE, PROBE_OPERATION, digest, None, None)
        except EmploymentAuthError:
            continue
        return context if _is_platform_founder_probe(context) else None
    return None


NIL_ID = "00000000-0000-0000-0000-000000000000"


def _is_platform_founder_probe(context: DelegatedContext) -> bool:
    return (
        context.purpose == PROBE_PURPOSE
        and context.effective_role == "FOUNDER"
        and context.tenant_id == NIL_ID
        and context.relationship_id == NIL_ID
    )


@router.post("/probe")
async def probe(request: Request) -> JSONResponse:
    auth = getattr(request.app.state, "provider_probe_auth", None)
    service = getattr(request.app.state, "provider_generation_probe_service", None)
    if auth is None or service is None:
        return JSONResponse({"code": "PROVIDER_PROBE_UNAVAILABLE"}, status_code=503)
    raw = await request.body()
    if _authorize(auth, request, raw) is None:
        return JSONResponse({"code": "PROBE_UNAUTHORIZED"}, status_code=401)
    try:
        body = ProbeRequest.model_validate_json(raw)
    except ValidationError:
        return JSONResponse({"code": "PROBE_INVALID"}, status_code=422)
    return JSONResponse(await service.probe(body))
