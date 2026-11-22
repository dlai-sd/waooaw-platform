from __future__ import annotations

from providers.hosted.anthropic import AnthropicHostedAdapter
from providers.hosted.base import HostedAdapter
from providers.hosted.google import GoogleHostedAdapter
from providers.hosted.openai import OpenAIHostedAdapter
from providers.hosted.sarvam import SarvamHostedAdapter

HOSTED_ADAPTERS: dict[str, HostedAdapter] = {
    adapter.name: adapter
    for adapter in (SarvamHostedAdapter(), OpenAIHostedAdapter(), AnthropicHostedAdapter(), GoogleHostedAdapter())
}
