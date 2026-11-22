# Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R002
from __future__ import annotations

from typing import Any

from providers.hosted.base import HostedAdapter, HostedCompletion

ANTHROPIC_VERSION = "2023-06-01"


class AnthropicHostedAdapter(HostedAdapter):
    name = "anthropic"
    host = "api.anthropic.com"
    default_model = "claude-haiku-4-5"

    def build_request(
        self, api_key: str, prompt: str, model: str, max_output_tokens: int
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        return (
            f"https://{self.host}/v1/messages",
            {"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION, "Content-Type": "application/json"},
            {"model": model, "max_tokens": max_output_tokens, "messages": [{"role": "user", "content": prompt}]},
        )

    def parse(self, data: Any, requested_model: str) -> HostedCompletion:
        usage = data.get("usage") or {}
        text = "".join(part["text"] for part in data["content"] if part.get("type") == "text")
        return self.completion(text, data.get("model"), requested_model, usage.get("input_tokens"), usage.get("output_tokens"))
