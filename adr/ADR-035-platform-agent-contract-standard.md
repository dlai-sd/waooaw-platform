# ADR-035 — Platform-Agent Contract (PAC) Standard

**Status:** Accepted
**Date:** 2026-07-30
**Author:** Enterprise Architect (INST-004)
**Constitutional Basis:** C-070 (Constitutional DNA — mandatory inheritance), C-094 (Agent Base Spec
Compliance), C-049 (Honest Limitation), ADR-034 (WBE)
**Industry Alignment:** AsyncAPI 3.0 (signal schema format), CloudEvents 1.0 (envelope convention),
Consumer-Driven Contract pattern (Pact.io analogy — agent as consumer, platform as provider)

---

## Context

WAOOAW adds platform components over time (CE, BP, PR, AIR, WBE, future components). Each
component emits signals to agents. Before this ADR, there was no formal mechanism for:

1. **Declaring** which signals an agent handles (and in what version)
2. **Detecting** when a new platform component requires updates to existing agent specs
3. **Versioning** signals so breaking changes are caught before they affect 30+ agents
4. **Validating** that an agent spec is complete relative to the current platform

Industry analysis (2026-07-30) confirmed: AsyncAPI 3.0 is the closest standard for WAOOAW's
event-driven signal model. Pact.io (HTTP request-response) is the wrong fit. Confluent Schema
Registry (Kafka-centric) is too heavy. Lightweight Git-based schema registry + DB table is right.

---

## Decision

### 1. Platform-Agent Contract (PAC) — Mandatory Section in Every Agent Spec

Every agent spec must include a `## Platform-Agent Contract` section containing a YAML block.
This block is the agent's declaration of:
- Which platform services it depends on
- Which signal channels from each service it handles
- What schema version of each signal it expects
- How it handles unavailability of each service

**Format:**
```yaml
## Platform-Agent Contract
# Declared per ADR-035. Every field is required for C-094 compliance.

base_spec_version: "1.0"   # Must match current AGENT-BASE-SPEC.md version

platform_services:
  wbe:
    schema_version: "1.0"  # Signals schema: architecture/reference/signals/wbe-signal-schema.yaml
    handles_signals:
      - channel: "platform/billing/bucket-at-50pct"
        handler: "[brief description of agent behavior in customer vocabulary]"
      - channel: "platform/billing/bucket-at-85pct"
        handler: "[brief description]"
      - channel: "platform/billing/bucket-empty"
        handler: "[brief description — MUST mention C-049 disclosure]"
      - channel: "platform/billing/topup-applied"
        handler: "acknowledge_topup_and_resume"
      - channel: "platform/billing/subscription-renewed"
        handler: "silent_full_capability_resume"
    does_not_handle:
      - channel: "[any signal deliberately ignored with reason]"
    unavailability: "[behavior when WBE is unreachable — default: continue_silent]"

    budget_vocabulary:
      llm_mid:          "[customer-facing term for MID_TIER LLM calls]"
      llm_frontier:     "[customer-facing term for FRONTIER LLM calls]"
      video_clips:      "[customer-facing term — or null if agent has no video]"
      whatsapp_windows: "[customer-facing term]"
      image_gen:        "[customer-facing term — or null]"

  ce:
    unavailability: "halt_and_disclose_advisory_only"  # default per ADR-031; do not change

  air:
    unavailability: "zero_cost_templates_with_C049_disclosure"  # default; may override with reason

  trial_profile:
    trial_disclosure_opening: "[One sentence in domain vocabulary]"
    zero_cost_thread_substitutes:
      llm_mid:     "ollama/llama3.2-3b"
      llm_frontier: "ollama/llama3.2-3b"
      video_clips:  "[sample_library or null]"
    live_only_features:
      - skill: "[Skill name]"
        trial_response: "[What agent says when customer asks for this in trial]"
```

### 2. Signal Schema Registry — Git + DB Table

Platform signal schemas live in two places:
- **Authoritative spec:** `architecture/reference/signals/{component}-signal-schema.yaml`
  (AsyncAPI 3.0-aligned, reviewed via PR, version-controlled in Git)
- **Runtime registry:** `institutional.platform_signal_schemas` table (DB, queried by Gap Scanner)

Adding a new signal or changing a signal schema requires:
1. Update the YAML file (PR with EA review)
2. Bump schema version (MINOR for backward-compatible, MAJOR for breaking)
3. Run Gap Scanner: `python3 scripts/gap_scanner.py --signal {channel_name}`
   → Reports which agent PACs handle this signal at which version
   → Flags any agents that don't handle the new/changed signal
4. Raise P1 spec-gap issues for affected agents

### 3. Signal Versioning Rules

Based on AsyncAPI + Confluent conventions:

| Change type | Version bump | Agent PAC impact |
|---|---|---|
| Add optional field | 1.0 → 1.1 (MINOR) | No change needed — agents at 1.0 still work |
| Add new signal channel | 1.x → new channel | New PAC entry required for affected agents |
| Remove field | 1.x → 2.0 (MAJOR) | All agents on 1.x must update PAC to 2.0 |
| Rename field | 1.x → 2.0 (MAJOR) | All agents on 1.x must update PAC to 2.0 |
| Change field type | 1.x → 2.0 (MAJOR) | All agents on 1.x must update PAC to 2.0 |

**Deprecation protocol (MAJOR bumps):**
- Signal v1.x remains active for 2 sprint cycles after v2.0 is released
- After 2 cycles, v1.x is marked `deprecated_at` in `platform_signal_schemas`
- After 4 cycles, v1.x is removed from schema registry
- Any agent still on v1.x after 2 cycles receives a P0 blocker

### 4. Gap Scanner — Lightweight (Initial Implementation)

`scripts/gap_scanner.py` (to be implemented in WBE-S8 or a dedicated sprint):

```python
# Gap Scanner — checks which agents have PAC entries for a given signal
# Called: manually by EA, or automatically when new signal schema PR merges

def scan_agent_pacs_for_signal(signal_channel: str, schema_version: str):
    """
    1. Read all agent specs in architecture/reference/agents/
    2. Parse ## Platform-Agent Contract YAML section
    3. Check: does this agent declare a handler for {signal_channel} at {schema_version}?
    4. Report: agents with handler, agents missing handler, agents on old version
    5. For agents missing handler: raise P1 IB item if signal is mandatory for their domain
    """
```

The Gap Scanner is the Self-Improvement Analyst's (INST-009, C-069) primary tool for
detecting platform-agent alignment gaps at each new component deployment.

### 5. Agent Base Spec Version Pinning

Every agent spec declares `base_spec_version: "1.0"` in its PAC. When AGENT-BASE-SPEC.md
version bumps (e.g., to 1.1 for a new mandatory section), the Gap Scanner detects all agents
still on 1.0 and raises P1 spec-gap issues.

An agent's `base_spec_version` must always equal the current version of AGENT-BASE-SPEC.md.
An agent with a lower version is constitutionally non-compliant per C-094.

---

## Consequences

- All 4 existing agent specs updated with PAC section (done in this session)
- `architecture/reference/signals/` directory created for platform signal schemas
- `AGENT-AUTHORING-GUIDE` updated: PAC section is mandatory (Section 3.x)
- `CONSTITUTIONAL_DNA.md` updated: C-094 base spec compliance added
- `scripts/gap_scanner.py` stub added to implementation backlog (WBE-S8 or dedicated sprint)
- `institutional.platform_signal_schemas` table added to D-08 schema (addendum)
