# GOAL-006 P1-WC04 CT-02 Release-Scope Decision

| Field | Value |
|---|---|
| `institution_id` | INST-011 |
| `goal_id` | GOAL-006 |
| `record_id` | DR-GOAL-006-INST-011-01 |
| `record_type` | Decision Record |
| `produced_at` | 2026-08-13T10:15:47Z |
| `subject` | P1-WC04 CT-02 cloud release membership |

| Component | Product outcome decision | Effect |
|---|---|---|
| Billing Engine | MANDATORY member of the GOAL-006 cloud release baseline. | P1-WC04/05/06/07 must include its topology, security, data, feasibility, tests, promotion evidence, cost and operations. |
| Trust Layer/OAuth Vault | CONDITIONAL. Include only if P1-WC05 establishes it as the accepted production OAuth credential-management component. | Until that decision it has no cloud exposure or release-manifest membership. No unsafe fallback secret mechanism is authorized. |
| MCP Compose services | EXCLUDED from the platform baseline. | Each MCP requires separate agent/feature scope, owner, implementation/security/data/cost evidence, and explicit release authorization. Compose stubs are not cloud deliverables. |

Billing is part of the customer activation/usage contract and cannot remain outside the qualified
release. OAuth Vault depends on the Security Architect's credential-boundary decision. MCPs are
domain adapters rather than one platform capability and may not enter GOAL-006 collectively.

This decision changes release scope only. It makes no architecture, security, data, implementation,
cost, provider, cloud, DNS, deployment, or activation decision.
