# Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R002
from __future__ import annotations

from typing import Any

from providers.hosted.base import HostedAdapter, HostedCompletion


class OpenAIHostedAdapter(HostedAdapter):
    name = "openai"
    host = "api.openai.com"
    default_model = "gpt-4o-mini"

    def build_request(
        self, api_key: str, prompt: str, model: str, max_output_tokens: int
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        return (
            f"https://{self.host}/v1/chat/completions",
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            {"model": model, "messages": [{"role": "user", "content": prompt}], "max_completion_tokens": max_output_tokens},
        )

    def parse(self, data: Any, requested_model: str) -> HostedCompletion:
        usage = data.get("usage") or {}
        return self.completion(
            data["choices"][0]["message"]["content"],
            data.get("model"),
            requested_model,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )
