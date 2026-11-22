# Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R002
from __future__ import annotations

from typing import Any

import httpx

from providers.hosted.base import HostedAdapter, HostedCompletion


class GoogleHostedAdapter(HostedAdapter):
    name = "google"
    host = "generativelanguage.googleapis.com"
    default_model = "gemini-2.0-flash"

    def build_request(
        self, api_key: str, prompt: str, model: str, max_output_tokens: int
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        return (
            f"https://{self.host}/v1beta/models/{model}:generateContent",
            {"x-goog-api-key": api_key, "Content-Type": "application/json"},
            {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_output_tokens},
            },
        )

    def rejects_key(self, response: httpx.Response) -> bool:
        # Gemini reports an invalid key as HTTP 400 with an API_KEY_INVALID reason.
        return response.status_code in (401, 403) or (response.status_code == 400 and b"API_KEY_INVALID" in response.content)

    def parse(self, data: Any, requested_model: str) -> HostedCompletion:
        usage = data.get("usageMetadata") or {}
        text = "".join(part["text"] for part in data["candidates"][0]["content"]["parts"] if "text" in part)
        model = data.get("modelVersion")
        return self.completion(text, model, requested_model, usage.get("promptTokenCount"), usage.get("candidatesTokenCount"))
