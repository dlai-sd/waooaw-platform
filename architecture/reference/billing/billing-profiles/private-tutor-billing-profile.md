# Agent Billing Profile — Private Tutor

**Authority:** Chief Business Architect (INST-003) — GOAL-004 D-09
**Agent Spec:** architecture/reference/agents/private-tutor-agent.md
**Constitutional Basis:** C-088 (Agent Billing Profile Requirement), C-060 (Minor Student Protection — LAW)
**Status:** FOUNDER_AUTHORIZED — 2026-07-30
**WBE Registry ID:** `private_tutor_v1` (institutional.billing_profiles.agent_type)

---

## Thread Profile

### Platform Threads (inherited)
- `llm_local` — query classification, subject routing
- `llm_mid_gemini` — explanation, practice problem generation, concept clarification
- `llm_frontier_gemini` — complex multi-step problem solving, exam strategy (rare)
- `whatsapp_window` — parent communication (student communication is app-based, not WhatsApp)
- `infra_share` — platform infrastructure

### Agent-Specific Threads
- `syllabus_cbse` — CBSE syllabus data (maintained, low cost amortised)
- `syllabus_state_boards` — State board syllabi (Maharashtra, Karnataka, etc.)
- `image_whiteboard` — whiteboard diagrams for math/science problems

## Default Bundle Rations

| Resource | thread_id | Starter (per child/month) | Runner (per child/month) |
|---|---|---|---|
| LOCAL classification | `llm_local` | Unlimited | Unlimited |
| MID_TIER LLM calls | `llm_mid_gemini` | 150 | 400 |
| FRONTIER LLM calls | `llm_frontier_gemini` | 0 | 10 |
| Whiteboard diagrams | `image_whiteboard` | 10 | 40 |
| Syllabus data | `syllabus_*` | Unlimited (amortised) | Unlimited |
| WhatsApp windows (parent) | `whatsapp_window` | 8 | 20 |
| Infrastructure share | `infra_share` | ₹180/month | ₹180/month |

*Note: Billing is per-child subscription. Parent with 2 children = 2 separate subscriptions.*
*The WhatsApp window count is very low because WhatsApp is parent-only (progress reports, billing). Student sessions are in-app — not WhatsApp conversations.*

## Minimum Wallet Requirements Per Active Skill
- No ad spend wallet required (Private Tutor does not run paid advertising)

## Trial Profile (Zero-Cost Substitutions)
- `llm_mid_gemini` → Ollama llama3.2-3b: demonstration lesson on sample topic
- `llm_frontier_gemini` → Not available in trial (Winner feature)
- `image_whiteboard` → Pre-generated sample whiteboard diagrams
- `syllabus_*` → CBSE/board data already free/public — no substitution needed

## Constitutional Billing Obligations — CRITICAL (C-060)

**C-060 (Minor Student Protection — LAW) creates mandatory billing isolation:**

1. **Billing information is NEVER surfaced to the student.** The agent interacts with
   the student as an educator. It NEVER mentions subscription, pricing, billing, wallet
   balance, or payment to the student user. Ever.

2. **All billing communication goes to the parent/guardian ONLY.** Parent's WhatsApp
   number is the billing contact. Student's app session is billing-blind.

3. **WBE bucket alerts go to parent, not student.** When WhatsApp window bucket is at
   85%, the alert WhatsApp goes to the registered parent number — not to the student
   session interface.

4. **Session continuity for student during billing issues.** If parent's subscription
   lapses (payment failure), the student's in-progress session completes. Only new
   sessions are blocked after the grace period expires. An exam-day session is NEVER
   interrupted for billing reasons.

5. **Trial experience is framed as educational, not commercial.** Trial session uses
   zero-cost substitutions but the agent never says "this is a trial" or "free version"
   to the student. It says: "Let's have a session together" — and shows the student what
   learning with a dedicated tutor feels like.
