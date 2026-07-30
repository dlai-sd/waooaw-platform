# Implements: architecture/reference/components/manifest/air.yaml §surface.endpoints
# Constitutional basis: C-042 (Vocab Mandate), C-049 (Honest Limitation), C-051, C-063
# EA-PRODUCED SKELETON — DO NOT change signatures. Raise SPEC_GAP if change needed.

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID
from typing import Optional


class LlmTierEnum(str, Enum):
    LOCAL    = "LOCAL"
    MID_TIER = "MID_TIER"
    FRONTIER = "FRONTIER"
    ZERO_COST = "ZERO_COST"


class IPSERouter(ABC):
    """
    Provider Selection Engine — routes LLM requests to correct tier and provider.
    Constitutional: C-051 (Resource Transparency), C-042 (Vocab Mandate).
    """

    @abstractmethod
    async def route(
        self,
        request: InferenceRequest,
        jwt_claims: dict
    ) -> LlmTierEnum:
        # Steward bypass: always FRONTIER (ADR-028)
        # Plan tier check: per ADR-028
        # Bundle ration check: WBE balance query per C-095 (after GOAL-PLATFORM-REGISTRY)
        # Returns tier to use; raises BucketEmptyError if bucket at 0 per C-049
        ...


class ILLMDispatcher(ABC):
    """
    Dispatches inference requests to the correct provider after PSE routing.
    Constitutional: C-063 (Data Minimisation — no unnecessary PII to provider).
    """

    @abstractmethod
    async def dispatch(
        self,
        request: InferenceRequest,
        tier: LlmTierEnum,
        contract_id: UUID
    ) -> InferenceResponse:
        # MUST call WBE.reserve before provider call
        # MUST call WBE.release after provider call (consumed=True/False)
        # MUST call WBE.record_cost after success
        # Raises: ProviderUnavailableError → triggers fallback chain (ADR-029)
        ...


class IPIIGuard(ABC):
    """
    PII Injection Guard — strips PII from prompts before LLM dispatch.
    Constitutional: C-063 (Data Minimisation — LAW).
    """

    @abstractmethod
    def sanitize(self, prompt: str, tenant_id: str) -> tuple[str, list[str]]:
        # Returns: (sanitized_prompt, list_of_redacted_fields)
        # Raises: PIILeakageError if sanitization cannot be verified
        ...


@dataclass
class InferenceRequest:
    contract_id:      UUID
    tenant_id:        str
    prompt:           str
    task_complexity:  str          # simple | medium | complex
    language:         Optional[str]
    skill_id:         Optional[str]
    session_id:       Optional[UUID]


@dataclass(frozen=True)
class InferenceResponse:
    content:          str
    tier_used:        LlmTierEnum
    provider_id:      str
    input_tokens:     int
    output_tokens:    int
    latency_ms:       float
    pii_redacted:     list[str] = field(default_factory=list)


class BucketEmptyError(Exception):
    """Raised when WBE bucket is empty. Agent must disclose per C-049."""
    def __init__(self, thread_type: str, period_end: str): ...

class ProviderUnavailableError(Exception):
    """Raised when primary provider fails and fallback chain exhausted."""
    def __init__(self, tier: LlmTierEnum, providers_tried: list[str]): ...

class PIILeakageError(Exception):
    """Raised when PII guard cannot verify sanitization — blocks dispatch."""
