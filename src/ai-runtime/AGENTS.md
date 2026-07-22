# AGENTS.md — AI Runtime (AIR) Context
# FinOps Pattern 2: Scoped context for AIR subdirectory work only
# constitutional_basis: C-051 (Token Economy), C-062 (AI Security), C-059, C-076

## Service Identity
- **Name:** AI Runtime (AIR)
- **Language:** Python 3.12 FastAPI async
- **Decision Space:** Provider Selection Engine (PSE), LLM dispatch, RAG retrieval, prompt injection defense
- **ADR Authority:** ADR-019 (RAG), ADR-020 (MCP), ADR-024 (Token Economy), ADR-029 (Multi-provider LLM)

## Primary Spec Files (load these — nothing else)
- `architecture/reference/components/ai-runtime.md`
- `standards/CODING-STANDARDS.md` §3 (Python) + §7.5 (Coverage C-076)
- `adr/ADR-INDEX.md` lines for ADR-024, ADR-029 only

## Constitutional Claims This Service Enforces
- **C-051** — Token Economy (66-74% cost reduction via 4-tier PSE routing)
- **C-062** — AI Security (prompt injection defense, Decision Space bypass prevention)
- **C-063** — Data Minimisation (no PII in LLM calls, redaction required)
- **C-059** — Implementation Traceability

## Provider Selection Engine (PSE) Rules (ADR-029)
- MID tier → Gemini 2.0 Flash (Vertex AI Mumbai) — DEFAULT for all customer agents
- FRONTIER → Gemini 2.5 Pro Mumbai (Steward Assistant — C-068 only)
- Agricultural → Sarvam AI Saaras (India-hosted, C-042 compliance)
- LOCAL → AI4Bharat IndicBERT (₹0 cost — vocabulary/safety checks)
- Fallback → Azure GPT-4o-mini (UAE North — only if primary circuit-breaker open)

## Test Requirements (C-076)
- **Line coverage:** ≥90% — `pytest --cov --cov-fail-under=90`
- **Prompt injection suite:** 100% of 50 attack patterns blocked (tests/conftest.py)
- **PSE routing tests:** each routing rule (PSE-R01 to PSE-R08) has a test
- **Multi-tenant isolation:** no cross-tenant prompt or context leakage

## Critical Pattern — Prompt Injection Defense (C-062)
```python
# EVERY user input must pass prompt injection check before LLM dispatch
INJECTION_PATTERNS = [
    r"ignore.*previous.*instructions",
    r"you are now",
    r"system prompt",
    r"jailbreak",
    # ... full list in tests/conftest.py INJECTION_ATTACKS
]

def detect_prompt_injection(user_input: str) -> bool:
    return any(re.search(p, user_input, re.IGNORECASE) for p in INJECTION_PATTERNS)

# NEVER: pass user_input directly to LLM without injection check
```
