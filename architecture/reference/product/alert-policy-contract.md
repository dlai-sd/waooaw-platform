# Alert Policy Contract (PG-24)

**Status:** v1.0, proposed by the author for the Founder's single-page confirmation of class wording and escalation timings (WC-171).
**Implements:** [WC-171](../../../work-contracts/WC-171-agent-navigation-alerts-and-oversight.md) WC171-R005 to R007, closes the design half of PG-24 in the [gap register](./waooaw-product-gap-register.md).
**Code:** `src/business-platform/Services/Alerts/AlertPolicy.cs` (the rules), `AlertPolicyService.cs` (the one way an alert enters), `tests/business-platform.Tests/AlertPolicyTests.cs`.
**Constitutional basis:** C-001, C-005, C-007, C-023, C-049, C-059, C-063.

## 1. Rule

Every alert source states what happened and its own severity. The policy, not the producer, decides the class, the channels, the deduplication key, the escalation and whether a message counts against the monthly allowance. An agent declares an alert as data; it cannot declare a class or a channel this contract does not allow, and admission refuses it.

## 2. Classes

| Class | Meaning | Channels | Counts against the 30 a month | Can be muted or snoozed | Quiet hours |
|---|---|---|---|---|---|
| FLOOR | Emergency Stop, authority and safety | portal, WhatsApp | No (uncounted floor) | Never | Ignored |
| ACTION_REQUIRED | The customer must decide or act | portal, WhatsApp | Yes | No | Respected |
| AT_RISK | A result or budget is drifting | portal, WhatsApp | Yes | Yes | Respected |
| INFORMATION | For information | portal | No | Yes | n/a |
| OPERATIONS | A platform problem for an operator | operator page only, never a customer channel | No | No | Ignored |

Quiet hours are 23:00 to 06:00 India time. Reserved floor categories, which a mute is refused for: `EMERGENCY_STOP`, `AUTHORITY`, `SAFETY`.

## 3. Sources and classification

| Source | Class |
|---|---|
| EMERGENCY_STOP | FLOOR |
| OPERATIONS | OPERATIONS |
| SPEND_DISCREPANCY | ACTION_REQUIRED |
| BILLING_THRESHOLD, AGENT_DECLARED | CRITICAL or HIGH: ACTION_REQUIRED; WARNING or MEDIUM: AT_RISK; otherwise INFORMATION |

An unknown source is refused, never guessed.

## 4. Deduplication

One key per tenant, relationship, event family and period. A billing threshold and a spend discrepancy for the same relationship and period are one family (`SPEND_RISK`), so they are one alert and one primary message. A later event may escalate an earlier one once, only to a strictly more material class; it is never a second message of the same or a lower class.

## 5. Delivery

1. The portal always receives the alert, once.
2. WhatsApp is used only when the class allows it, the customer has consented, STOP has not been received, the Founder's gate is open, the category is not muted, quiet hours allow it, and (for a counted class) the monthly allowance is consumed on send, idempotently. When the allowance is exhausted or cannot be read, the alert is portal-only and says why.
3. The gate is off by default. On Demo it sends to sandbox recipients only, and only after the thread rate `whatsapp_template_utility` is authorized on Pricing and a WhatsApp utility template is approved.

## 6. Escalation ladders (proposed)

| Class | Steps |
|---|---|
| FLOOR | at once: portal and WhatsApp; after 5 minutes: repeat on WhatsApp; after 15 minutes: operator page |
| ACTION_REQUIRED | at once: portal and WhatsApp; after 24 hours: remind in the portal; after 72 hours: operator review |
| AT_RISK | at once: portal and WhatsApp; after 72 hours: remind in the portal |
| INFORMATION | portal |
| OPERATIONS | page at once, again at 15 minutes and at 30 minutes; an acknowledgement stops the repeat paging for 30 minutes and never closes the signal |

## 7. Honest limits

A page handed to monitoring is recorded as EMITTED: that proves the platform raised it, not that a person received it. Producer wiring: the billing engine's threshold alerts, the spend discrepancy and the Emergency Stop confirmation reach this policy through `AlertPolicyService.RaiseAsync`; until each producer calls it, its alerts keep their present path, and this is tracked in the WC-171 Implementation Record.
