# WC-097 - Marketplace Acquisition Experience

| Field | Value |
|---|---|
| Office | Platform IT Expert (INST-010) |
| Authorized by | Founder instruction in the 2026-09-16 continuous working session |
| Status | IMPLEMENTATION AUTHORIZED - ENGINEERING QUALIFIED |
| Branch | `ib/097/marketplace-acquisition-experience` |
| Baseline | `origin/main` at `b7472535` |
| Defect | DF-014 |

## Objective

Replace the compliance-led Marketplace presentation with one professional, inviting and truthful
customer acquisition experience. Trial and Hire must remain inside the Customer Portal through the
offer review step, use one coherent visual language, and preserve exact offer intent.

## Required Experience

- Lead with customer-facing professional identity, outcomes, availability, trial and price.
- Do not show internal professional identifiers or eligibility policy prose on the offer card.
- Use WAOOAW blue, green and orange as semantic accents without a photograph or decorative artwork.
- Show concise outcome and trust signals; detailed limits and rights use progressive disclosure.
- Trial and Hire open an authenticated `/marketplace/{slug}` route under the persistent portal shell.
- The decision view visually continues the card and shows API-owned skills, trial boundaries, price,
  limitations and customer rights without a second legal-document presentation.
- Continuation uses one explicit consent statement with links to Terms and Privacy Policy.
- No trial, relationship, contract, payment or authority begins before explicit continuation.

## Ownership And Safety

- Business Platform owns the canonical Marketplace route, offer/version, suitability, skills, trial
  terms, price, limitations and rights.
- The browser does not derive a professional slug, price, eligibility, discount or authority.
- This work does not implement DF-012 checkout, discount or payment orchestration. Existing
  acquisition consequences remain unchanged and require their separately governed repair.
- Public professional pages remain available for public discovery; authenticated Marketplace actions
  use the application-owned route.

## Acceptance Matrix

| ID | Condition | Required evidence |
|---|---|---|
| WC097-A01 | Card omits internal type and eligibility lecture | Component test and browser text assertion |
| WC097-A02 | Card shows name, outcomes, trust, price, trial, Trial and Hire | Component test and screenshot |
| WC097-A03 | BP projects `/marketplace/{slug}` and Web uses it without derivation | BP controller and Web component tests |
| WC097-A04 | Trial/Hire detail stays under the customer application layout | Route ownership test and browser shell identity assertion |
| WC097-A05 | Detail uses authoritative offer/version/intent and fails closed on mismatch | Detail component tests |
| WC097-A06 | Consent links Terms and Privacy and blocks continuation until checked | Component tests |
| WC097-A07 | Desktop, tablet and mobile have no overflow, overlap or clipped actions | Browser geometry, axe and screenshots |
| WC097-A08 | OpenAPI, TypeScript, lint, build and affected BP/Web tests pass in Docker | Exact command evidence |

## Non-Claims

Local tests and browser evidence do not establish Demo deployment, UAT, Production readiness,
payment-provider acceptance, discount correctness or completion of DF-010 through DF-013.

## Qualification Evidence

All commands ran in Docker against this branch.

| Evidence | Result |
|---|---|
| Business Platform controller tests | 8 passed |
| Marketplace, detail, consent and shell Jest suites | 5 suites, 21 tests passed |
| TypeScript `tsc --noEmit` | Passed |
| Next.js lint | Passed with no warnings or errors |
| Next.js production build | Passed; 52 pages generated and `/marketplace/[slug]` present |
| Spectral 6.15.0 OpenAPI lint | Passed with 0 errors; 80 pre-existing repository warnings |
| Chromium Trial and Hire journeys | 6 passed: 1440x900, 768x1024 and 360x800 |
| Browser integrity | No horizontal overflow and no serious or critical axe violations |
| Visual evidence | Card, Trial and Hire screenshots inspected at desktop, tablet and mobile sizes |

The production build continues to report the pre-existing Autoprefixer mixed-support warning in
`web/app/globals.css`; this change did not introduce or alter the warned declaration.