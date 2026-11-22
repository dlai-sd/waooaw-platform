# Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R004
"""Bounded ordered fallback: the first provider that answers wins; every skip carries a sanitized reason code."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx

from providers.credential_resolver import ProviderCredentialUnavailable
from providers.hosted import HOSTED_ADAPTERS
from providers.hosted.base import REQUEST_TIMEOUT_SECONDS, FailureReason, HostedProviderError

MAX_CHAIN_LENGTH = 4


class ApiKeySource(Protocol):
    async def get_api_key(self, provider_name: str) -> str: ...


@dataclass(frozen=True)
class ChainEntry:
    name: str
    model: str | None = None


@dataclass(frozen=True)
class ChainAttempt:
    provider: str
    outcome: Literal["ANSWERED", "SKIPPED"]
    reason: FailureReason | None


@dataclass(frozen=True)
class ChainAnswer:
    provider: str
    model: str
    reported_model: str
    text: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int


async def run_fallback_chain(
    entries: list[ChainEntry],
    keys: ApiKeySource,
    client: httpx.AsyncClient,
    prompt: str,
    max_output_tokens: int,
    *,
    timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[ChainAnswer | None, list[ChainAttempt]]:
    if not 1 <= len(entries) <= MAX_CHAIN_LENGTH:
        raise ValueError("Fallback chain must name between one and four providers")
    attempts: list[ChainAttempt] = []
    for entry in entries:
        adapter = HOSTED_ADAPTERS.get(entry.name)
        if adapter is None:
            attempts.append(ChainAttempt(entry.name, "SKIPPED", "UNSUPPORTED"))
            continue
        try:
            model = adapter.model_for(entry.model)
            try:
                key = await keys.get_api_key(entry.name)
            except ProviderCredentialUnavailable:
                raise HostedProviderError(entry.name, "KEY_MISSING") from None
            started = clock()
            completion = await adapter.complete(client, key, prompt, model, max_output_tokens, timeout_seconds)
        except HostedProviderError as error:
            attempts.append(ChainAttempt(entry.name, "SKIPPED", error.reason))
            continue
        attempts.append(ChainAttempt(entry.name, "ANSWERED", None))
        answer = ChainAnswer(
            entry.name,
            model,
            completion.reported_model,
            completion.text,
            completion.input_tokens,
            completion.output_tokens,
            max(0, round((clock() - started) * 1000)),
        )
        return answer, attempts
    return None, attempts
