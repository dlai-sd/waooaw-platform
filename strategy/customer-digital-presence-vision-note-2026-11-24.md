# Customer Digital Presence: From Connection To Maturity-Led Operation

**Working note for grooming. Not a decision, not an ADR.** Written 2026-11-24 from a Founder conversation. Statements marked *(hypothesis)* or *(verify)* are mine and need confirmation before they become requirements.

## 1. The vision in one paragraph

WAOOAW customers (a beauty artist, a dentist in Viman Nagar) must never do technical work. Creating Meta apps, Pages, tokens and test accounts is a **one-time platform setup that WAOOAW does**. The only human step left for a customer is **consent**: tap connect, sign in to their own account, approve. Everything before and after that is the digital marketing agent (DMA) working from evidence. The question "what do we do with a customer's accounts?" is answered by the DMA's **maturity assessment**, not by a checklist and not by whatever API happens to be connected first.

## 2. Who decides what happens to a customer's accounts

| Layer | Role | Boundary |
|---|---|---|
| DMA maturity skill | **Recommends**: scores each dimension from evidence, finds the gaps, proposes Starter, Runner or Winner | Shows sources, confidence and a correction path (GOAL-005 D06, trial Day 2) |
| The package | **Bounds**: which actions DMA may take and the budget it may spend | Components and limits are priced and visible before acceptance |
| The customer | **Approves**: the exact scope, and later each post or spend inside it | Nothing changes on their accounts before acceptance |
| The Constitution | **Enforces**: limits, approval gates, evidence and audit trail | Emergency Stop, revoke at any time |

The score **sizes** the package. It must not **exclude** an eligible customer (D06: "no segment preference or maturity score is used to exclude").

## 3. Existing authority this builds on (verified in the repo)

- `strategy/FOUNDER-SESSION-2026-08-07-customer-first-decision.md`: the DMA prerequisite chain is Skill 0 Customer Profiling, then Skill 1 Market Research + Maturity Score, then Phase 1 execution; Phase 2 unlocks at score 3+ after 2 to 3 months of Phase 1 data; Phase 3 at 5+. Running publish without Skills 0 and 1 is "an API wrapper, not a professional".
- `goals/GOAL-005-D06-dma-domain-authority-synthesis.md`: the 14-day trial runs a public-footprint and maturity assessment on Day 2; posts and Google profile changes stay preview-only ("no account mutation").
- Founder decision 2026-11-20 (pricing): Starter is about 2,000 rupees a month including one post a week (4 in total), one ad boost, and monitoring and tuning on up to four selected platforms. Customer price includes GST.
- Not found: a written mapping of Starter, Runner and Winner to score bands. That mapping is the main thing to groom.

## 4. Target customer journey

| Stage | What happens | Customer effort | Access needed |
|---|---|---|---|
| 0 Discover | Customer finds DMA, sees what it can and cannot do | Browse | None |
| 1 Assess | DMA scores the **public** footprint (profile, website, Google listing, public posts, reviews) | Give business name and links | **None** |
| 2 Propose | Gap report, score per dimension, recommended package, price | Read | None |
| 3 Accept | Customer chooses trial or hire, approves scope and budget | One decision | None |
| 4 Connect | Scoped consent per platform: **read-only first** (insights, enquiries), write access only for what the accepted package needs | One tap per platform | Scoped |
| 5 Set up presence | Profile, bio, catalogue, FAQs, appointment link, WhatsApp business profile, Google profile fixes; each change previewed and approved | Approve | Write, scoped |
| 6 Operate | Content on a shared theme tuned to each platform, enquiry handling, ads, monitoring | Approve posts and spend | Write, scoped |
| 7 Adapt | Re-score on real results; unlock Phase 2 at 3+ and Phase 3 at 5+; suggest package change | Approve | As needed |

## 5. Maturity scale (draft *(hypothesis)*)

Each dimension is scored 0 to 5 with **observable evidence**, a **confidence value** and a **correction path** (the customer can say "that is wrong, here is the proof"). Generic anchors: 0 absent, 1 ad hoc, 2 present but inconsistent, 3 consistent and measured, 4 optimised with a feedback loop, 5 adaptive and largely automated.

| Dimension | What is measured | Evidence, public or connected | Access |
|---|---|---|---|
| Profile | Completeness and consistency of name, address, hours, category, services, photos across platforms | Public | None |
| Posting rhythm | Frequency and consistency over the last 90 days | Public, richer when connected | None or read |
| Content and tag performance | Which themes, formats and tags earn reach and engagement | Connected insights | Read |
| Enquiries | Volume, response time, conversion to booking | Connected (messages, calls, forms) | Read |
| Booking readiness | A working appointment path from each platform | Public, then tested | None |
| Website and local SEO | Site quality, structured data, Google listing, local ranking | Public | None |
| Reviews and reputation | Count, recency, reply rate, rating | Public | None |
| Monitoring and ad adaptation | Are results tracked, and is spend tuned from them | Connected ads and analytics | Read |
| AI-search readiness | Consistent entity data, FAQs, structured answers so AI assistants can describe and recommend the business | Public checks | None |

Weights should vary by business type (a dentist leans on reviews and booking; a beauty artist on visual content). Business-type weights are an open design question.

## 6. Package mapping (hypothesis, for the Founder to decide)

- **Starter**: fix the basics and start a rhythm: profile, booking path, a first posting cadence, monitoring.
- **Runner**: consistent cadence with measurement, enquiry handling, local SEO, small ad boosts tuned to results.
- **Winner**: adaptive spend, cross-platform theming, AI-search tuning, continuous re-scoring.

Whether bands are by total score, by weakest dimension, or by customer goal is undecided.

## 7. Progressive consent and permissions *(verify each platform at grooming)*

| Platform | Stage 1 to 3 (no connection) | Stage 4 read-only | Stage 5 and 6 write |
|---|---|---|---|
| Facebook and Instagram (Meta) | Public page and profile | Insights and engagement read | Page post, Page metadata, Instagram publish |
| WhatsApp Business | Public number and profile if any | Business messages read | Message send, profile, catalogue; needs business verification and number onboarding |
| Google Business Profile and YouTube | Public listing and channel | Read insights | Profile edits, uploads; access approval required |
| LinkedIn | Public company page | Limited | Posting needs partner-level approval *(verify)* |

Consequences: ask for the smallest permission at each stage; request only what an accepted package needs; this also reduces what Meta App Review must approve.

## 8. What can be automated

- **Automated through API once approved:** posts, Page details, WhatsApp business profile and catalogue, Google profile fields.
- **Guided, customer approves in one tap:** anything an API limits (parts of Instagram, YouTube branding, LinkedIn). The agent prepares the change and the customer confirms.
- **Not possible for us:** creating a Facebook Page on a customer's behalf (the customer needs one; we guide the 2-minute creation); skipping consent.

## 9. Implications for current work

- **Connect-then-publish is the wrong first step.** WC-149 requests `pages_manage_posts` at the first connect. Revisit to read-first, write-after-acceptance.
- **Acceptance harness.** Add journeys for assess, propose and accept before connect. Today's journeys test connect and a test post.
- **WC-167 stays technical readiness**, not proof of this order.
- **Testing needs a real tester account.** Meta has switched off test-user creation, so the test setup uses a dedicated Facebook account with the Tester role. That is for WAOOAW testing only, never a customer step.
- **Meta App Review is the schedule risk.** Until approved, only people with a role on the app can connect. Real customers cannot.

## 10. Open questions for grooming

1. Final dimension list, scale anchors and per-business-type weights.
2. How scores map to Starter, Runner and Winner, and what happens at a band boundary.
3. How long an assessment stays valid and when it re-runs.
4. What the customer can correct, and who arbitrates a disputed score.
5. Which setup actions need approval each time and which once per package.
6. Per-platform review lead times and the order in which platforms go live.
7. Whether to assess before sign-in (acquisition hook) or after (customer data rules).
8. Which assessment data sources are lawful and acceptable for public data.

## 11. Suggested next artifacts

1. Architecture contract: **Digital Maturity Model and Package Mapping** (Business Architect or Product Owner owns the scale; Platform IT derives the permission matrix).
2. ADR: **Progressive consent by package** (read first, write after acceptance).
3. Permission and review matrix per platform, verified against each platform's current rules.
4. Acceptance journey slice: assess, propose, accept, then connect.
5. Customer presence setup contract (profile, catalogue, FAQs, appointments) after items 1 to 3.

## 12. Source files

`strategy/FOUNDER-SESSION-2026-08-07-customer-first-decision.md`, `goals/GOAL-005-D06-dma-domain-authority-synthesis.md`, `goals/GOAL-005-f4-dma-domain-authority-input.md`, `work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md`, `work-contracts/WC-167-acceptance-demo-readiness.md`, `architecture/reference/agents/digital-marketing-agent.md`.
