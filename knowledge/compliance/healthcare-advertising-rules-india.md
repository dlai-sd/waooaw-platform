# Healthcare Advertising Compliance Rules — India (DIGITAL_MARKETING_HEALTHCARE)

**Purpose:** Machine-readable compliance rule set for SCR Check 3 (GAP-D003 — Simulation 007)
**Authority:** MCI (Medical Council of India) Code of Medical Ethics 2002 + State Medical Council guidelines + Consumer Protection Act 2019 (advertising claims) + ASCI (Advertising Standards Council of India) Healthcare Code
**Used by:** DMA agent Synthetic Content Reviewer (SCR) — Check 3 (Compliance) for all healthcare agent content
**Version:** 1.0.0 (2026-07-12)

---

## How SCR Uses This File

SCR Check 3 retrieves the top-5 most relevant rules from this file via RAG (Tier 1) for each content piece, then applies pattern matching to detect violations. A violation causes `SCR_3_COMPLIANCE: FAIL` which always routes to the customer — it is never auto-regenerated silently.

---

## Rule Format

Each rule has:
- `RULE_ID`: unique identifier for citation in evidence records
- `CATEGORY`: rule category (GUARANTEE, COMPARATIVE, TESTIMONIAL, PRICE, PROCEDURE, IMAGE, GENERAL)
- `PROHIBITED_PATTERN`: what the rule prohibits (text pattern or semantic description)
- `ALLOWED_ALTERNATIVE`: how to express the same idea compliantly
- `SOURCE`: authoritative source of the rule
- `SEVERITY`: HARD (absolute prohibition) | SOFT (requires context; may be compliant in certain forms)

---

## Rules

### RULE-HC-001 — No Guaranteed Outcomes
**CATEGORY:** GUARANTEE
**PROHIBITED_PATTERN:** "guaranteed", "100%", "definitely", "always works", "no pain guaranteed", "pain-free guaranteed", "results guaranteed", "success guaranteed"
**ALLOWED_ALTERNATIVE:** "most patients experience", "typically", "in our experience", "for many patients", "may help reduce"
**SOURCE:** MCI Code of Medical Ethics Regulation 6.1.1 — "A physician shall not solicit patients directly or indirectly, by a group of physicians or by institutions or organisations. It is improper to treat patients under a contract in which payment to the physician is made contingent on the outcome of treatment."
**SEVERITY:** HARD

### RULE-HC-002 — No Comparative Price Claims Against Competitors
**CATEGORY:** COMPARATIVE
**PROHIBITED_PATTERN:** Claims that competitor charges more (e.g., "cheaper than [clinic name]", "other clinics charge ₹X but we charge ₹Y", "lowest price in Viman Nagar", "most affordable dental clinic")
**ALLOWED_ALTERNATIVE:** State own prices only ("A preventive checkup at our clinic costs ₹500"); state own price progression ("a root canal can cost ₹15,000-25,000 — prevention costs far less")
**SOURCE:** ASCI Code — comparative advertising must be factually verifiable; MCI Regulation 6.7 — false claims about competitor services
**SEVERITY:** HARD for named competitors; SOFT for generic comparisons

### RULE-HC-003 — No Before/After Images Without Disclosure
**CATEGORY:** IMAGE
**PROHIBITED_PATTERN:** Dental/medical before-and-after photos without explicit consent disclosure AND without stating that results may vary
**ALLOWED_ALTERNATIVE:** Include disclaimer: "Results vary by patient. Shown with patient consent." OR use illustrated/diagram images instead of actual patient photos
**SOURCE:** ASCI Healthcare Code Rule 3.4 — before/after images must include "Results may vary" disclaimer; C-052 (Creative Fingerprint) reinforces patient photo consent
**SEVERITY:** HARD for actual patient photos without consent + disclaimer; SOFT for stock illustrations

### RULE-HC-004 — No Testimonials Claiming Specific Medical Outcomes
**CATEGORY:** TESTIMONIAL
**PROHIBITED_PATTERN:** Patient testimonials that claim specific medical improvements ("I was cured", "my pain disappeared in 2 days", "it worked when nothing else did")
**ALLOWED_ALTERNATIVE:** Experience testimonials are acceptable ("Dr. Mehta was very gentle", "The staff was very helpful", "I felt at ease during my treatment")
**SOURCE:** MCI Code Regulation 6.1 — testimonials that imply specific medical outcomes are prohibited as they may mislead other patients into expecting the same results
**SEVERITY:** HARD for outcome claims; SOFT for experience claims

### RULE-HC-005 — No Unverified Health Claims
**CATEGORY:** PROCEDURE
**PROHIBITED_PATTERN:** "Whitening removes all stains", "Our treatment cures gum disease", "This procedure eliminates sensitivity permanently", clinical outcome claims without scientific qualification
**ALLOWED_ALTERNATIVE:** "Whitening significantly lightens most surface stains", "Our treatment helps manage gum disease", "Many patients report reduced sensitivity after treatment"
**SOURCE:** Consumer Protection Act 2019 Section 2(1)(r) — unfair trade practices include misleading claims about product/service efficacy; ASCI Code — health claims must be truthful and non-misleading
**SEVERITY:** HARD

### RULE-HC-006 — No Denigration of Other Medical Professionals
**CATEGORY:** COMPARATIVE
**PROHIBITED_PATTERN:** "Unlike other dentists", "other clinics don't care about your pain", "most dentists just want your money", direct or implied criticism of other dental professionals
**ALLOWED_ALTERNATIVE:** Focus on own positive attributes without reference to competitors
**SOURCE:** MCI Code of Medical Ethics Regulation 6.7 — "A physician shall not claim to be a specialist in any particular area unless they are properly qualified."
**SEVERITY:** HARD

### RULE-HC-007 — No Emergency/Urgency Language for Non-Emergency Services
**CATEGORY:** GENERAL
**PROHIBITED_PATTERN:** "ACT NOW or you'll lose your teeth", "URGENT: last chance for free consultation", creating false urgency for elective procedures
**ALLOWED_ALTERNATIVE:** Time-bound offers stated factually ("This month only: ₹100 off checkups"); genuine clinical urgency stated appropriately ("If you're experiencing pain, please don't delay — pain can indicate a worsening condition")
**SOURCE:** ASCI Code — false urgency is a prohibited pressure technique; Consumer Protection Act 2019 — misleading practices
**SEVERITY:** HARD for false urgency; SOFT for genuine clinical urgency

### RULE-HC-008 — Pricing Claims Must Be Accurate and Complete
**CATEGORY:** PRICE
**PROHIBITED_PATTERN:** Advertised prices that exclude mandatory charges (GST, consultation fee, materials); "starting from ₹X" without stating what ₹X covers; prices that expire but don't show the expiry
**ALLOWED_ALTERNATIVE:** "Preventive checkup + X-ray: ₹500 inclusive" or "Consultation from ₹200 (treatment priced separately)"
**SOURCE:** Consumer Protection Act 2019 — hidden charges are an unfair trade practice; GST disclosure requirements
**SEVERITY:** HARD for missing GST inclusion; SOFT for "starting from" language with context

### RULE-HC-009 — No Sexual, Violent, or Body-Shaming Content
**CATEGORY:** GENERAL
**PROHIBITED_PATTERN:** Content that body-shames patients ("fix your ugly smile", "hide your yellow teeth"), sexualizes dental procedures, or uses fear-inducing imagery beyond clinically appropriate education
**ALLOWED_ALTERNATIVE:** Positive, empowering framing ("invest in your smile", "feel confident at any age")
**SOURCE:** ASCI General Code + Platform policies (Meta, Google both prohibit body-shaming healthcare ads)
**SEVERITY:** HARD

### RULE-HC-010 — PCPNDT Act Compliance (Dental practices only)
**CATEGORY:** PROCEDURE
**PROHIBITED_PATTERN:** For any content involving diagnostic imaging: references that could imply sex determination services are offered (PCPNDT Act prohibits advertising any diagnostic facility that could perform sex determination)
**ALLOWED_ALTERNATIVE:** Dental X-ray content is not affected by PCPNDT (dental X-rays are clearly for dental diagnostics); content about "diagnostic services" in general should not imply reproductive health
**SOURCE:** Pre-Conception and Pre-Natal Diagnostic Techniques (PCPNDT) Act 1994 — applies to diagnostic facilities broadly
**SEVERITY:** HARD if applicable; NOT APPLICABLE for dental-specific content that does not reference reproductive diagnostics

---

## Platform-Specific Addenda

### Meta (Instagram + Facebook) Healthcare Advertising Policy
- No ads for "sensitive health conditions" without prior approval (cosmetic surgery, dental implants require Meta approval)
- "Before and after" images require "Results may vary" overlay
- No targeting based on health conditions (dental anxiety, sensitivity) — this applies only to PAID ads, not organic content

### Google Ads Healthcare Policy (for DMA Skill 11 — Paid Advertising)
- Dental services require Healthcare and Medicine certification in Google Ads
- Cannot target based on specific health conditions
- Landing pages must have clear pricing and qualifications disclosure

---

## Application Notes for SCR

1. **RAG retrieval:** For each content piece, retrieve top-5 rules by semantic similarity to the content. Common high-retrieval rules: RULE-HC-001 (guarantee language), RULE-HC-002 (price claims), RULE-HC-003 (images).

2. **Pattern matching first, LLM second:** Run deterministic pattern matching for HARD severity rules before LLM reasoning. LLM is used only for SOFT severity judgment calls.

3. **False positive mitigation:** Healthcare education content about procedures ("here's what a root canal involves") should not trigger RULE-HC-001 (guarantee). The trigger requires an outcome claim ("our root canal is painless"). Context matters.

4. **Customer disclosure when SCR-3 fails:** The agent must explain WHICH rule was triggered and WHY, not just "compliance violation." Dr. Mehta must understand the issue to make an informed correction choice.

