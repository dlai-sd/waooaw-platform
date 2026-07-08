# ADR-020: MCP Integration Pattern — Tool Connectivity for Digital Professionals

**Status:** Accepted
**Date:** 2026-07-08
**Roles Applied:** AI Architect (tool architecture) + Solution Architect (integration pattern) + Security Architect (authorization)
**Constitutional Basis:** C-041 (every tool call governed by Decision Space — LAW); C-036 (Skills are constitutional units — tool calls are Skill-level actions); C-003 (Second Law — authority is licensed, not assumed)

---

## Context

Every Digital Professional needs to act in the world — post to Instagram, send a WhatsApp message, execute a trade. These actions require calling external APIs. The question is: how does the AI Runtime connect to these external platforms in a way that is constitutionally governed, extensible, and decoupled from specific platform APIs?

Three options:
1. Hard-coded platform-specific clients in AI Runtime
2. A plugin/integration pattern custom to WAOOAW
3. MCP (Model Context Protocol) as a standardized protocol for tool connectivity

---

## Decision

**Model Context Protocol (MCP) is the standard for all external tool connectivity in WAOOAW. The AI Runtime is an MCP client. Each external platform capability is an MCP server. The Decision Space governs which MCP servers a Skill may call and which actions it may request.**

### Why MCP

MCP provides a standardized protocol that:
- Decouples the AI Runtime from specific platform SDKs (Instagram SDK, WhatsApp Business SDK, broker API)
- Enables adding new platforms without modifying AI Runtime code (DP-003 — Configuration over Code)
- Provides a uniform tool invocation and response format across all external capabilities
- Has growing ecosystem support (Anthropic, OpenAI, and major tool providers adopt MCP)

### Constitutional Integration

C-041 mandates that every tool call is governed by the Decision Space. The integration point is:

```
AI Runtime wants to call MCP tool "instagram.post_content"
        ↓
Decision Space check FIRST (before MCP client sends the request):
  Is "instagram.post_content" in decision_space.authorized_tools? → YES → proceed
                                                                 → NO  → reject (C-041 violation)
        ↓
CE.ValidateAction called (Evidence First — AD-002):
  action_type = "INSTAGRAM_POST", tool = "instagram.post_content"
  CE returns ALLOW / DENY / ESCALATE
        ↓
If ALLOW: MCP client sends request to Instagram MCP Server
If DENY:  Evidence First records REJECTED state; tool call does not execute
If ESCALATE: Routes to customer approval (Approval-Gate model)
```

The Constitutional Engine is called BEFORE every MCP tool invocation. C-041 + AD-002 together make this mandatory.

---

## MCP Server Taxonomy

| Category | MCP Server | Tools | Authorization |
|---|---|---|---|
| **Social** | instagram-mcp | post_content, post_story, post_reel, get_insights | authorized_tools list in Decision Space |
| **Social** | facebook-mcp | post_content, create_event, get_insights | authorized_tools |
| **Social** | whatsapp-business-mcp | send_broadcast, update_status, manage_catalogue | authorized_tools |
| **Search/Local** | google-business-mcp | post_update, respond_review, update_info | authorized_tools |
| **Content** | image-generation-mcp | generate_image, edit_image | authorized_tools |
| **Content** | video-generation-mcp | generate_video, edit_video, compose_reel | authorized_tools |
| **Analytics** | platform-analytics-mcp | get_instagram_insights, get_facebook_insights, get_gbp_metrics | read-only, always authorized |
| **Calendar** | scheduling-mcp | create_post_schedule, get_calendar | authorized_tools |
| **Trading** | market-data-mcp | get_price_feed, get_order_book | read-only, always authorized for trading agents |
| **Trading** | broker-mcp | place_order, cancel_order, get_positions | PAAS Decision Space only — most restrictive |

**WAOOAW operates:** image-generation-mcp, video-generation-mcp, scheduling-mcp, platform-analytics-mcp
**Third-party:** instagram-mcp, facebook-mcp, whatsapp-business-mcp, google-business-mcp, market-data-mcp, broker-mcp

---

## MCP Server Failure Handling

A core constitutional concern: if an MCP server fails (Instagram API is down), the agent must degrade gracefully at the Skill level — not halt the entire agent.

**Pattern:**
1. MCP tool call fails → AI Runtime catches the error
2. If the tool is classified `DEGRADABLE`: log the failure, continue without the tool, mark the Skill execution as INCOMPLETE
3. If the tool is classified `REQUIRED`: record a constitutional evidence ABANDONED state, notify the customer
4. Emergency Stop is never degradable

**Classification in the Agent Specification:**
Each MCP tool in the Agent Specification must be labelled `DEGRADABLE` or `REQUIRED`. This guides the failure handling at runtime.

---

## Adding a New External Platform

Adding TikTok as a new social platform for a future agent:

1. Build or adopt a `tiktok-mcp` MCP server (WAOOAW-built or third-party)
2. Register it in the Tool Registry (`ai-runtime.md` Tool Registry)
3. Update the relevant Agent Specification to add TikTok as a new Skill or extend an existing Skill's MCP tools
4. Update the customer's Decision Space template to include `tiktok.post_video` in `authorized_tools`
5. No changes to AI Runtime code (DP-003)

---

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Hard-coded platform clients | Tightly couples AI Runtime to each platform SDK. Adding TikTok requires code change. Violates DP-003. |
| LangChain/LangGraph tool framework | Not a standard protocol. Ecosystem-specific. Creates vendor lock-in. No constitutional authorization hook. |
| REST APIs called directly by AI Runtime | No standardization. Every platform needs custom client code. Violates DP-003. |

---

## Consequences

**Benefits:**
- Adding a new platform requires an MCP server + Agent Specification update — no AI Runtime code changes
- Constitutional authorization (C-041) is enforced at a single chokepoint in the Tool Registry
- Ecosystem support for MCP is growing — third-party MCP servers will become available
- Failure isolation: one MCP server failing does not cascade to the whole agent

**Trade-offs:**
- MCP adds one additional network hop per tool call (~5-10ms)
- WAOOAW must build and maintain MCP servers for platforms without native MCP support (WhatsApp Business, Google Business at MVI)
- MCP protocol versioning must be managed as the protocol evolves
