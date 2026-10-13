# WC-120 Product Owner Disposition

## Review Control

| Field | Value |
|---|---|
| Office | Product Owner, INST-011 |
| Scope | Founder-requested single-pass review and repair |
| Requirements | WC120-R005, R012-R016, R021, R040, R042 |
| Decisions | PRODUCT-01 through PRODUCT-05 |
| Journeys | Consent; service-window/template; voice/media; accessibility/low-literacy; stale/ambiguous/degraded |
| Final disposition | **PASS** |

## 1. Repaired And Closed Owner Findings

| ID | WC120-R | Repair and exact accepted value | Result |
|---|---|---|---|
| PRODUCT-01 | R005, R021, R042 | Set initial locale to `en-IN`; unsupported locales fail visibly with zero action; set Flesch-Kincaid grade ceiling 8, 20-word sentence ceiling, one primary action per turn, recorded exceptions, text alternative for audio, and semantic parity across renderings. | CLOSED |
| PRODUCT-02 | R013, R042 | Approved exact ACTIVE/MISSING/WITHDRAWN/UNKNOWN copy and actions; actions appear only when an approved route exists; channel change never carries consent; every non-active or denied state has zero dispatch. | CLOSED |
| PRODUCT-03 | R015, R042 | Limited initial Product media support to `en-IN` WhatsApp voice contributions, maximum 5 MiB and 120 seconds; all other media unsupported; approved exact unsafe/expired/unavailable/low-confidence/confirm/cancel copy and exact-version correction/confirmation behavior. | CLOSED |
| PRODUCT-04 | R012-R014, R042 | Approved exact window-expired, template-rejected, template-version-mismatch, and unknown copy; prohibited retry while unresolved and prohibited template/locale/purpose/channel fallback. | CLOSED |
| PRODUCT-05 | R016, R021, R040, R042 | Set WCAG 2.2 AA target; exact keyboard, focus, live-region, non-color, screen-reader, zoom, and Stop controls; defined Docker-only axe, keyboard, focus, semantic, monochrome/zoom, and CE-FIT-13 oracles. | CLOSED |

All five journey rows now reference exact accepted values and oracles. The WC-120 contract
and R042 ledger row identify the repaired matrix as the controlling Product profile. Missing
implementation evidence is expected-fail until implementation and is not a specification blocker.

## 2. Exact External Dependencies

| Dependency | Named owner | Exact gate; Product decision remains closed |
|---|---|---|
| Material consent rights | Legal/Founder | Accept opt-in, purpose, withdrawal, re-consent policy, and consent-route authority before consent activation. |
| Provider window/templates | Provider configuration owner with Platform authority | Supply exact service-window boundary and approved versioned template/category/language/schema configuration; authorize configuration/activation separately. |
| Media safety | Security Architect | Accept media admission, scanner, parser, and safety limits. A stricter accepted limit overrides, but cannot expand, the Product ceiling. |
| Media lifecycle | Data Architect; Legal/Founder where protected | Accept retention, erasure, legal-hold, and transcript/media lifecycle controls. |
| Provider media constraints/activation | Provider/Platform authority | Verify the bounded voice profile against the exact provider contract and separately authorize configuration/activation. |
| Executable UI evidence | Test Champion during approved implementation | Bind selectors and produce the exact Docker-only R042 evidence. This artifact cannot exist before the implementation phase and is not a current blocker. |

No Product-owned value remains pending. These external gates stop only the affected activation
or qualification and may not be filled by an implementer assumption.

## 3. Final Disposition

**PASS.** The Product Owner accepts PRODUCT-01 through PRODUCT-05 and all five customer
journeys. WC120-R042 is specification-complete from Product Decision Space: locale,
readability, copy, actions, media ceiling, voice correction/send consent, accessibility,
Stop reachability, degraded states, and direct oracles are exact.

This PASS is not Legal/Founder consent-policy approval, Security/Data media approval,
provider/cloud/deployment authority, implementation evidence, activation, or merge authority.
Those named external dependencies remain fail-closed gates for their affected capability.
