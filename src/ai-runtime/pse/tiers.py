# Implements: adr/ADR-029-multi-provider-llm-strategy.md
# constitutional_basis: C-051 (Token Economy — 66-74% cost reduction)
# PSE-R01 to PSE-R08 routing rules defined here.

from enum import StrEnum


class LlmTier(StrEnum):
    """ADR-029 §3 routing tiers. NEVER add tiers without EA approval."""
    LOCAL = "local"        # Ollama (₹0/token) — default for dev
    MID = "mid"            # Sarvam AI (Indian SMEs, optimised cost)
    FRONTIER = "frontier"  # Gemini / Anthropic (complex reasoning)
    FALLBACK = "fallback"  # Anthropic Claude (when Gemini unavailable)
