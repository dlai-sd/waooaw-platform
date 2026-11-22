# Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R002
# constitutional_basis: C-059, C-062, C-063, ADR-029 (hosted providers), ADR-014 (no credential in logs or errors)
"""One bounded hosted-provider interface. Fixed https hosts, no redirects, no SDKs, no key or body in any output."""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from httpx import AsyncClient

REQUEST_TIMEOUT_SECONDS = 20.0
MAX_RESPONSE_BYTES = 1_000_000
MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_API_KEY = re.compile(r"^[\x21-\x7e]{8,512}$")

# Provider hosts admitted for hosted inference, keyed by governed binding adapter.
HOSTED_ADAPTER_HOSTS: dict[str, str] = {
    "SARVAM_HOSTED": "api.sarvam.ai",
    "OPENAI_HOSTED": "api.openai.com",
    "ANTHROPIC_HOSTED": "api.anthropic.com",
    "GOOGLE_HOSTED": "generativelanguage.googleapis.com",
}
HOSTED_ADAPTER_PROVIDERS: dict[str, str] = {
    "SARVAM_HOSTED": "sarvam",
    "OPENAI_HOSTED": "openai",
    "ANTHROPIC_HOSTED": "anthropic",
    "GOOGLE_HOSTED": "google",
}

FailureReason = Literal["KEY_MISSING", "KEY_REJECTED", "TIMEOUT", "PROVIDER_ERROR", "UNSUPPORTED"]


class HostedProviderError(ValueError):
    """A hosted provider could not answer. Carries a reason code only, never a key, URL, prompt or provider body."""

    def __init__(self, provider: str, reason: FailureReason) -> None:
        self.provider = provider
        self.reason: FailureReason = reason
        super().__init__(f"hosted provider unavailable: provider={provider} reason={reason}")


@dataclass(frozen=True)
class HostedCompletion:
    text: str
    reported_model: str
    input_tokens: int | None
    output_tokens: int | None


def new_hosted_client() -> AsyncClient:
    return AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=False, trust_env=False)


def _count(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


class HostedAdapter(ABC):
    name: str
    host: str
    default_model: str

    def model_for(self, override: str | None = None) -> str:
        model = override or os.getenv(f"AIR_HOSTED_MODEL_{self.name.upper()}") or self.default_model
        if not MODEL_NAME.fullmatch(model):
            raise HostedProviderError(self.name, "UNSUPPORTED")
        return model

    @abstractmethod
    def build_request(
        self, api_key: str, prompt: str, model: str, max_output_tokens: int
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        """Return the fixed-host URL, the headers carrying the key, and the JSON body."""

    @abstractmethod
    def parse(self, data: Any, requested_model: str) -> HostedCompletion:
        """Map a provider JSON document to text, usage and the provider-reported model."""

    def rejects_key(self, response: httpx.Response) -> bool:
        return response.status_code in (401, 403)

    async def complete(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        prompt: str,
        model: str,
        max_output_tokens: int,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
    ) -> HostedCompletion:
        if not MODEL_NAME.fullmatch(model):
            raise HostedProviderError(self.name, "UNSUPPORTED")
        if not _API_KEY.fullmatch(api_key):
            raise HostedProviderError(self.name, "KEY_REJECTED")
        url, headers, body = self.build_request(api_key, prompt, model, max_output_tokens)
        try:
            response = await client.post(url, headers=headers, json=body, timeout=timeout_seconds)
        except httpx.TimeoutException:
            raise HostedProviderError(self.name, "TIMEOUT") from None
        except httpx.HTTPError:
            raise HostedProviderError(self.name, "PROVIDER_ERROR") from None
        if self.rejects_key(response):
            raise HostedProviderError(self.name, "KEY_REJECTED")
        if response.status_code != 200 or len(response.content) > MAX_RESPONSE_BYTES:
            raise HostedProviderError(self.name, "PROVIDER_ERROR")
        try:
            return self.parse(response.json(), model)
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise HostedProviderError(self.name, "PROVIDER_ERROR") from None

    @staticmethod
    def completion(
        text: object, reported_model: object, requested_model: str, input_tokens: object, output_tokens: object
    ) -> HostedCompletion:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("empty completion")
        model = reported_model if isinstance(reported_model, str) and MODEL_NAME.fullmatch(reported_model) else requested_model
        return HostedCompletion(text, model, _count(input_tokens), _count(output_tokens))
