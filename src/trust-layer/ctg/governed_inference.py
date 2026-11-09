"""Inference CTG boundary with mandatory current-owner and durable-usage callbacks."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from conversation_generation import GenerationRequest, InferenceBinding, InferencePermit


class AdmittedInferenceSocket(Protocol):
    def count_prompt(self, binding: InferenceBinding, request: GenerationRequest) -> int: ...
    async def invoke_admitted(self, binding: InferenceBinding, request: GenerationRequest,
                              authorize: Callable[[], Awaitable[None]]) -> tuple[str, int, int]: ...


class GovernedInferenceToolGateway:
    def __init__(self, socket: AdmittedInferenceSocket) -> None:
        self.socket = socket

    def count_prompt(self, binding: InferenceBinding, request: GenerationRequest) -> int:
        return self.socket.count_prompt(binding, request)

    async def generate(self, binding: InferenceBinding, request: GenerationRequest, permit: InferencePermit,
                       authorize: Callable[[], Awaitable[None]],
                       settle: Callable[[int, int], Awaitable[None]]) -> tuple[str, int, int]:
        maximum = ((binding.input_paise_per_million * 8192 + 999999) // 1000000
            + (binding.output_paise_per_million * 2048 + 999999) // 1000000)
        remaining = (permit.expires_at - datetime.now(timezone.utc)).total_seconds()
        if (permit.binding != binding or permit.evidence_id.int == 0 or permit.reservation_id.int == 0
            or permit.commercial_reservation_id.int == 0
            or maximum != permit.maximum_cost_paise or remaining <= 0 or remaining > 30.5):
            raise ValueError("Tool call has no exact conservative admitted permit")
        async with asyncio.timeout(min(30, remaining)):
            await authorize()
            text, input_tokens, output_tokens = await self.socket.invoke_admitted(binding, request, authorize)
        # Usage is durably recorded even for an overrun; failed settlement never releases output.
        await settle(input_tokens, output_tokens)
        return text, input_tokens, output_tokens
