# PII Masking Pipeline — Specification

**Version:** 1.0
**Date:** 2026-07-23
**Authority:** C-078 (PII Masking Before LLM Dispatch — RATIFIED)
**Owner:** WAOOAW AI Agent — Platform IT Expert (implementation) · Ojal Khandge (ethics stewardship)
**Constitutional Basis:** C-078, C-048 (Non-Exploitation), C-063 (Right to Erasure), DPDPA 2023 §8(7)
**Implements:** AI Runtime Component 7 — PII Scrubber
**CCTs:** CCT-PII-01 (unit — PII detection accuracy), CCT-PII-02 (integration — red-team adversarial)

---

## 1. The Problem

Every inference request that WAOOAW sends to an external LLM provider (Google Vertex AI, Azure OpenAI, Sarvam AI) may contain customer-sourced context — the customer's name, phone number, business address, historical content, or financial data. This data was collected under WAOOAW's privacy policy for the purpose of running the customer's autonomous agent — not for inclusion in training data, logging, or processing by external AI companies.

Sending raw PII to external providers without a technical safeguard:
- Violates DPDPA 2023 Section 8(7) — mandatory technical measures
- Violates C-048 — customer data used beyond stated purpose
- Creates an audit evidence gap (the data's external journey is untracked)

**The solution is mandatory, in-line PII scrubbing — every prompt passes through the scrubber before leaving WAOOAW's network boundary.**

---

## 2. Scope

| Situation | PII Scrubbing Required? |
|---|---|
| Prompt → Google Vertex AI (Gemini) | **YES — mandatory (C-078)** |
| Prompt → Azure OpenAI (GPT-4o) | **YES — mandatory (C-078)** |
| Prompt → Sarvam AI (Saaras) | **YES — mandatory (C-078)** |
| Prompt → Ollama (self-hosted, local network) | NO — data never crosses WAOOAW boundary |
| Prompt → AI4Bharat IndicBERT (self-hosted) | NO — data never crosses WAOOAW boundary |
| MCP tool call bodies | NO — MCP calls are between WAOOAW services; PII is appropriate in tool requests |
| Evidence records (constitutional schema) | NO — constitutional schema is WAOOAW-controlled DB |
| Reasoning traces (institutional schema) | YES — stored with tokens, not original values |

---

## 3. PII Categories and Token Map

| PII Category | Detection Method | Token |
|---|---|---|
| Indian mobile number (10-digit, +91 prefix) | Regex: `(\+91[\s-]?)?[6-9]\d{9}` | `{{CUSTOMER_PHONE}}` |
| Email address | RFC 5321 regex | `{{CUSTOMER_EMAIL}}` |
| Person name (detected by NER) | AI4Bharat IndicNER — PER entity | `{{CUSTOMER_NAME}}` |
| Business name (detected by NER) | AI4Bharat IndicNER — ORG entity | `{{CUSTOMER_BUSINESS_NAME}}` |
| Physical address (detected by NER) | AI4Bharat IndicNER — LOC entity | `{{CUSTOMER_ADDRESS}}` |
| Aadhaar number (12-digit) | Regex: `\d{4}[\s-]?\d{4}[\s-]?\d{4}` | `{{CUSTOMER_AADHAAR}}` |
| PAN number | Regex: `[A-Z]{5}[0-9]{4}[A-Z]{1}` | `{{CUSTOMER_PAN}}` |
| Bank account number | Regex: `\d{9,18}` (preceded by "account" keyword) | `{{CUSTOMER_BANK_ACCOUNT}}` |
| IFSC code | Regex: `[A-Z]{4}0[A-Z0-9]{6}` | `{{CUSTOMER_IFSC}}` |
| GST number | Regex: `\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}` | `{{CUSTOMER_GSTIN}}` |
| UPI ID | Regex: `[\w.-]+@[\w.-]+` (UPI context) | `{{CUSTOMER_UPI}}` |
| Vehicle number (Indian) | Regex: `[A-Z]{2}[\s-]?\d{2}[\s-]?[A-Z]{1,2}[\s-]?\d{4}` | `{{CUSTOMER_VEHICLE}}` |

### 3.1 Numbered Tokens (when multiple of the same type)

If a prompt contains two phone numbers, they are tokenized distinctly:
`{{CUSTOMER_PHONE_1}}`, `{{CUSTOMER_PHONE_2}}` — the in-memory map preserves the mapping per token.

### 3.2 Context-Aware Detection

NER is run on the full prompt text before structural regex. NER detects names and locations even when they appear in unexpected formats. Structural regex catches high-precision structured PII that NER may miss (Aadhaar, PAN, UPI — perfectly structured).

### 3.3 False Negative Policy

- Structural PII (phone, email, Aadhaar, PAN, bank, GSTIN, UPI): **Zero tolerance**. If a structural regex matches, the field must be tokenized. CCT-PII-01 must achieve 100% recall on structural PII.
- NER-detected PII (name, address, business): **< 0.1% false negative rate** acceptable. CCT-PII-02 adversarial test must achieve ≥99.9% detection.

---

## 4. Pipeline Architecture

```
Professional Runtime
  → inference_request (prompt + context + decision_space)
        ↓
[AI Runtime — LLM Gateway receives request]
        ↓
[Component 7: PII Scrubber — MANDATORY pre-dispatch step]
  Step 1: Run AI4Bharat IndicNER on full prompt text
          → extract PER, ORG, LOC entities with character offsets
  Step 2: Run structural regex battery on full prompt text
          → extract phone, email, Aadhaar, PAN, bank, IFSC, GSTIN, UPI, vehicle
  Step 3: Merge detections (NER + regex) with offset deduplication
  Step 4: Sort by character offset (reverse order) — replace from end to preserve offsets
  Step 5: Build token_map: {token → original_value}
  Step 6: Replace each PII occurrence in prompt with token
  Step 7: Return (scrubbed_prompt, token_map)
        ↓
[Provider Selection Engine selects provider]
        ↓
[External LLM Provider receives scrubbed_prompt only — never token_map]
        ↓
[LLM returns response (may contain tokens)]
        ↓
[Component 7: PII Restorer — response reconstruction]
  If execution requires original values (e.g., "send WhatsApp to {{CUSTOMER_PHONE_1}}"):
    Step 1: Scan response for tokens
    Step 2: Look up token_map in-memory
    Step 3: Restore original values for tool execution only
  If response is a customer-facing message or reasoning trace:
    → Store response as-is (with tokens, not original values)
    → Customer-facing messages: restore only if the customer typed the value themselves
        ↓
[token_map: discarded after request completes — never persisted]
```

---

## 5. Token Map Lifecycle

| Phase | Token Map State |
|---|---|
| Before scrubbing | Not yet created |
| During scrubbing | Created in-memory, scoped to single HTTP request context |
| During LLM call | Held in-memory; never logged, never serialized |
| During response handling | Used for selective restoration (tool execution only) |
| After request completes | Explicitly cleared from memory (not GC-dependent) |
| In reasoning traces | Tokens stored, not original values |
| In evidence records | Tokens stored; originals remain in Tier 2 customer store |

**The token map is never persisted, never logged, never transmitted.** It lives and dies within a single inference request context.

---

## 6. LOCAL Provider Exemption — Architecture Enforcement

LOCAL-tier providers (Ollama, AI4Bharat IndicBERT) are exempt from PII scrubbing because data never leaves WAOOAW's infrastructure. This exemption must be enforced architecturally:

```python
async def dispatch(self, request: InferenceRequest, provider: LLMProvider) -> InferenceResponse:
    if provider.data_residency == DataResidency.EXTERNAL:
        # C-078: MANDATORY — PII scrubbing before external dispatch
        scrubbed_prompt, token_map = await self.pii_scrubber.scrub(request.prompt)
        request = request.with_scrubbed_prompt(scrubbed_prompt)
    else:
        # LOCAL provider — data stays within WAOOAW boundary — exempt (C-078 §2)
        token_map = {}

    response = await provider.complete(request)

    if token_map:
        response = await self.pii_scrubber.restore_for_execution(response, token_map)

    return response
```

The `data_residency` field is a mandatory attribute on every `LLMProvider` implementation. Attempting to dispatch to a provider with `data_residency = EXTERNAL` without scrubbing is a compile-time error (enforced by the type system — `ExternalLLMProvider.complete()` only accepts `ScrubbedPrompt`, not `RawPrompt`).

---

## 7. CCT Specifications

### CCT-PII-01 — Unit: PII Detection Accuracy

```python
# Location: tests/constitutional/test_pii_scrubber.py
# Authority: C-078

# Test battery: 50 synthetic prompts covering all PII categories
# For each prompt: assert 100% recall on structural PII, ≥99.9% on NER-based

def test_indian_phone_detection():
    scrubber = PIIScrubber()
    prompts = [
        "Call Dr. Mehta on 9876543210",
        "WhatsApp: +91 98765 43210",
        "Reach at +91-9876543210 for appointment",
    ]
    for prompt in prompts:
        scrubbed, token_map = scrubber.scrub(prompt)
        assert "9876543210" not in scrubbed          # original must be replaced
        assert "{{CUSTOMER_PHONE" in scrubbed         # token must be present
        assert len(token_map) >= 1                    # map must be populated

def test_aadhaar_detection():
    scrubber = PIIScrubber()
    prompt = "Suresh's Aadhaar is 1234 5678 9012"
    scrubbed, _ = scrubber.scrub(prompt)
    assert "1234" not in scrubbed or "5678" not in scrubbed  # partially removed
    assert "{{CUSTOMER_AADHAAR}}" in scrubbed

def test_external_provider_cannot_receive_raw_prompt():
    # Type-system enforcement: ExternalLLMProvider.complete() only accepts ScrubbedPrompt
    provider = VertexAIProvider()
    raw_prompt = RawPrompt("Call 9876543210")
    with pytest.raises(TypeError):
        await provider.complete(raw_prompt)  # must raise — wrong type
```

### CCT-PII-02 — Integration: Red-Team Adversarial PII Injection

```python
# Location: tests/constitutional/test_pii_adversarial.py
# Authority: C-078

# 50 adversarial prompts designed to bypass detection:
# - PII embedded in markdown: "name: **Suresh Kumar**"
# - PII in JSON within prompt: '{"phone": "9876543210"}'
# - PII with Unicode lookalikes: "98765О4321О" (Cyrillic О instead of 0)
# - PII split across lines
# - Regional language PII (Hindi, Marathi)
# Minimum pass rate: 99.9% detection rate across all 50 prompts
```

---

## 8. Monitoring and Alerting

| Metric | Source | Alert threshold |
|---|---|---|
| `pii_scrubber.detections_per_request` | Histogram | P95 > 10 PII items/request (unusual, investigate) |
| `pii_scrubber.false_negatives` | Counter (CCT red-team, not prod) | > 0 structural false negatives in CCT → block PR |
| `pii_scrubber.latency_ms` | Histogram | P99 > 50ms (NER is fast; this should be < 20ms P99) |
| `pii_scrubber.exempted_requests` | Counter | Track LOCAL-tier exemptions vs external dispatches |

**The PII scrubber must add < 20ms P99 to inference latency.** AI4Bharat IndicNER runs on CPU (not GPU) for the scrubber — it processes text, not images. The regex battery is near-zero latency.
