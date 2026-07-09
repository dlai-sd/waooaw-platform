# MCP Tool Catalogues

**Authority:** GENESIS Part 05 — Agent Definition Protocol (Tool Registry)
**Date:** 2026-07-09
**Constitutional Basis:** C-041 (every tool call governed by Decision Space); ADR-020 (MCP integration pattern)
**Purpose:** Formal tool signatures for all MCP server adapters. Every tool listed here corresponds to an authorized_action or read-only operation in the agent Decision Space. Developers implement MCP servers to these contracts exactly. The AI Runtime calls these tools — deviation from this contract is a C-041 violation.

**Format:** Each tool defines: name, HTTP method + path on the MCP server, request body schema, response schema, authorization requirement, and failure mode (REQUIRED = skill halts if tool fails; DEGRADABLE = skill continues with reduced capability).

---

## customer-profile-mcp (port 8112)

Used by: Digital Marketing Agent — Skill 0 (Customer Profiling), Skill 1 (Market Research)

### profile.get_registration
```
GET /call/profile.get_registration
Request:  { organisation_id: string (UUID) }
Response: {
  owner_name: string | null,
  business_name: string | null,
  business_domain: string | null,
  locality: string | null,
  city: string | null,
  prospective_customers: string | null,
  aspiration: string | null,
  phone_number_whatsapp: string | null,
  whatsapp_opt_in: boolean
}
Authorization: Always authorized (read-only, own org data only — RLS enforced)
Failure: REQUIRED — profiling cannot begin without registration data
```

### profile.update_field
```
POST /call/profile.update_field
Request:  {
  organisation_id: string (UUID),
  field_name: string,           -- one of the digital_marketing_profiles column names
  field_value: string | null,
  source: "registration" | "conversation" | "inference" | "customer_correction"
}
Response: { updated: boolean, profile_status: "INCOMPLETE" | "MINIMUM_VIABLE" | "COMPLETE" }
Authorization: CUSTOMER_PROFILING in Decision Space
Failure: REQUIRED
```

### profile.confirm
```
POST /call/profile.confirm
Request:  { organisation_id: string (UUID), confirmed_by_customer: boolean }
Response: { confirmed_at: string (ISO timestamp), profile_status: "COMPLETE" }
Authorization: CUSTOMER_PROFILING in Decision Space + customer CONFIRMED
Failure: REQUIRED — synthetic approval mode cannot activate without confirmed profile
```

### maturity.save_score
```
POST /call/maturity.save_score
Request:  {
  organisation_id: string (UUID),
  maturity_score: integer (1-7),
  maturity_label: string,
  axis_scores: {
    digital_footprint: integer, social_presence: integer,
    google_business: integer, paid_advertising: integer,
    content_quality: integer, competitor_landscape: integer,
    analytics: integer
  },
  industry_benchmark_avg: number | null,
  industry_benchmark_p80: number | null,
  benchmark_domain: string | null,
  benchmark_city: string | null,
  report_pdf_url: string | null,
  recommended_bundle: "CURTAIN_RAISER" | "GROWTH_ENGINE" | "MATURITY_PHASE"
}
Response: { maturity_score_id: string (UUID), recorded_at: string }
Authorization: MARKET_RESEARCH in Decision Space
Failure: REQUIRED — report cannot be delivered without a score record
```

### needs.save_heatmap
```
POST /call/needs.save_heatmap
Request:  {
  organisation_id: string (UUID),
  maturity_score_id: string (UUID),
  needs: [
    {
      need_state: "VISIBILITY"|"LEADS"|"CONVERSION"|"EFFICIENCY"|"COMPETITION"|"CONSISTENCY"|"TRUST"|"CLARITY",
      status: "ACTIVE"|"LATENT"|"NOT_APPLICABLE",
      evidence_summary: string,
      evidence_source_url: string | null
    }
  ]  -- must contain exactly 8 entries, one per need_state
}
Response: { saved: integer }  -- count of rows saved
Authorization: MARKET_RESEARCH in Decision Space
Failure: REQUIRED
```

### competitors.save_snapshot
```
POST /call/competitors.save_snapshot
Request:  {
  organisation_id: string (UUID),
  competitor_name: string,
  competitor_confirmed_by_customer: boolean,
  axes: {
    social_post_frequency: integer | null,
    social_follower_count: integer | null,
    google_review_count: integer | null,
    google_review_rating: number | null,
    meta_ads_active: boolean | null,
    meta_ads_count: integer | null,
    website_has_booking_cta: boolean | null
  },
  data_sources: object,     -- {axis_name: "source_url"}
  notable_changes: string | null
}
Response: { snapshot_id: string (UUID) }
Authorization: COMPETITIVE_INTELLIGENCE in Decision Space
Failure: REQUIRED (competitor-private data — if save fails, report must not be delivered)
```

---

## web-search-mcp (port 8113)

Used by: Digital Marketing Agent — Skills 1, 10, 13

### search.query
```
POST /call/search.query
Request:  {
  query: string,
  num_results: integer (default: 10, max: 20),
  region: string (default: "IN"),        -- India results prioritised
  safe_search: boolean (default: true)
}
Response: {
  results: [
    { title: string, url: string, snippet: string, published_date: string | null }
  ]
}
Authorization: MARKET_RESEARCH | LOCAL_SEO | COMPETITIVE_INTELLIGENCE in Decision Space
Failure: DEGRADABLE — partial research report if search fails
Notes: Uses Brave Search API or Bing Search API. API key in SEARCH_API_KEY env var.
       Never returns authenticated-only content. Public web only (C-041 constraint).
```

---

## google-places-mcp (port 8114)

Used by: Digital Marketing Agent — Skills 1, 6, 13

### place.get_details
```
POST /call/place.get_details
Request:  {
  business_name: string,
  locality: string,
  city: string,
  fields: ["rating", "user_ratings_total", "reviews", "opening_hours",
           "website", "formatted_phone_number", "photos", "business_status"]
           -- subset; requesting all fields increases API cost
}
Response: {
  place_id: string | null,
  name: string | null,
  rating: number | null,
  user_ratings_total: integer | null,
  business_status: "OPERATIONAL" | "CLOSED_TEMPORARILY" | "CLOSED_PERMANENTLY" | null,
  website: string | null,
  recent_reviews: [{ rating: integer, text: string, time: string, reply: string | null }] | null,
  last_update_signal: string | null,  -- inferred from recent review dates
  photos_count: integer | null
}
Authorization: MARKET_RESEARCH | GOOGLE_BUSINESS_PROFILE | COMPETITIVE_INTELLIGENCE in Decision Space
Failure: DEGRADABLE
Notes: Uses Google Places API. Key in GOOGLE_PLACES_API_KEY env var.
       Returns only publicly visible data. No authenticated GBP management.
```

---

## social-profile-mcp (port 8115)

Used by: Digital Marketing Agent — Skills 1, 13

### profile.get_public_data
```
POST /call/profile.get_public_data
Request:  {
  platform: "INSTAGRAM" | "FACEBOOK",
  search_term: string,      -- business name or @handle
  locality_hint: string     -- helps disambiguate multiple results
}
Response: {
  handle: string | null,
  follower_count: integer | null,
  following_count: integer | null,
  post_count: integer | null,
  last_post_date: string | null,     -- ISO date
  posts_last_30_days: integer | null,
  bio: string | null,
  website_link: string | null,
  is_business_account: boolean | null,
  engagement_rate_approx: number | null   -- likes+comments / followers, last 5 posts
}
Authorization: MARKET_RESEARCH | COMPETITIVE_INTELLIGENCE in Decision Space
Failure: DEGRADABLE
Notes: Uses public web scraping / Apify Instagram Scraper (no Graph API auth).
       IMPORTANT: Do NOT use Meta Graph API (requires OAuth — violates public-data-only constraint).
       If handle not found: return null values, not an error.
```

---

## meta-ad-library-mcp (port 8116)

Used by: Digital Marketing Agent — Skills 1, 13

### ads.search_active
```
POST /call/ads.search_active
Request:  {
  search_term: string,      -- business name or Facebook Page name
  country: string (default: "IN")
}
Response: {
  ads_found: integer,
  active_ads: [
    { ad_id: string, start_date: string, status: "ACTIVE"|"INACTIVE",
      platform: "FACEBOOK"|"INSTAGRAM"|"BOTH",
      media_type: "IMAGE"|"VIDEO"|"CAROUSEL"|null }
  ]
}
Authorization: MARKET_RESEARCH | COMPETITIVE_INTELLIGENCE in Decision Space
Failure: DEGRADABLE
Notes: Uses Meta Ad Library API (public, no auth required).
       endpoint: https://www.facebook.com/ads/library/api/
```

---

## scheduling-mcp (port 8105)

Used by: Digital Marketing Agent — Skills 2, 3, 4, 5, 6, 7, 8

### calendar.get_history
```
GET /call/calendar.get_history
Request:  { contract_id: string (UUID), skill_type: string, months_back: integer (default: 3) }
Response: {
  plans: [
    { plan_id: string, month: string, status: "APPROVED"|"DRAFT"|"EXECUTING"|"COMPLETE",
      post_count: integer, approved_count: integer, published_count: integer }
  ]
}
Authorization: CONTENT_STRATEGY in Decision Space
Failure: DEGRADABLE
```

### calendar.create_plan
```
POST /call/calendar.create_plan
Request:  {
  contract_id: string (UUID),
  skill_type: string,
  month: string,             -- YYYY-MM
  posts: [
    { week: integer (1-4), day_of_week: string, time_ist: string,
      theme: string, content_type: "POST"|"STORY"|"REEL",
      caption_draft: string, hashtags: string[] }
  ]
}
Response: { plan_id: string (UUID), status: "DRAFT" }
Authorization: CONTENT_STRATEGY in Decision Space + customer APPROVED
Failure: REQUIRED
```

### calendar.schedule_post
```
POST /call/calendar.schedule_post
Request:  {
  contract_id: string (UUID),
  plan_id: string (UUID),
  post_id: string (UUID),
  platform: "INSTAGRAM" | "FACEBOOK",
  scheduled_at_ist: string    -- ISO datetime in IST
}
Response: { scheduled: boolean, scheduling_reference: string }
Authorization: INSTAGRAM_POST | FACEBOOK_POST in Decision Space
Failure: REQUIRED
```

---

## instagram-mcp (port 8106)

Used by: Digital Marketing Agent — Skills 3 (Instagram)

### post.publish
```
POST /call/post.publish
Request:  {
  contract_id: string (UUID),
  image_url: string,          -- pre-uploaded to media store; must be publicly accessible
  caption: string,
  hashtags: string[],
  approval_evidence_id: string (UUID)   -- MUST be a valid evidence_record with state=APPROVED or type=SYNTHETIC
}
Response: {
  instagram_post_id: string,
  permalink: string,
  published_at: string
}
Authorization: INSTAGRAM_POST in Decision Space + approval_evidence_id valid
Failure: REQUIRED — publishing without approved evidence is a C-041 violation
Notes: Uses Meta Graph API — POST /{ig-user-id}/media + /{ig-user-id}/media_publish
       Access token from customer-profile OAuth vault (ADR-021)
```

### story.publish
```
POST /call/story.publish
Request:  {
  contract_id: string (UUID),
  image_url: string,
  approval_evidence_id: string (UUID)
}
Response: { instagram_story_id: string, published_at: string }
Authorization: INSTAGRAM_STORY in Decision Space + approval_evidence_id valid
Failure: DEGRADABLE (story failure does not halt skill)
```

### post.get_insights
```
POST /call/post.get_insights
Request:  { contract_id: string (UUID), post_id: string, metrics: string[] }
Response: { metrics: { [metric_name]: number } }
Authorization: Always authorized (read-only)
Failure: DEGRADABLE
```

---

## meta-ads-mcp (port 8120)

Used by: Digital Marketing Agent — Skill 11 (Paid Advertising)

### campaign.create
```
POST /call/campaign.create
Request:  {
  contract_id: string (UUID),
  ce_validate_action_response_id: string,   -- REQUIRED: ValidateAction must have been called first
  name: string,
  objective: "REACH" | "TRAFFIC" | "LEADS" | "CONVERSIONS",
  daily_budget_inr_paise: integer,
  start_date: string,
  end_date: string | null,
  targeting: { locations: string[], age_min: integer, age_max: integer, interests: string[] },
  approval_evidence_id: string (UUID)
}
Response: { campaign_id: string, status: "ACTIVE" | "PAUSED" | "PENDING_REVIEW" }
Authorization: PAID_AD_CAMPAIGN in Decision Space + CE budget check passed + approval_evidence_id valid
Failure: REQUIRED
Notes: Developer MUST call CE.ValidateAction with budget_context BEFORE calling this tool.
       The ce_validate_action_response_id field proves the CE check was done.
       If ce_validate_action_response_id is absent or invalid → MCP server returns 403.
       This is a C-043 enforcement mechanism at the MCP adapter layer.
```

### campaign.pause
```
POST /call/campaign.pause
Request:  { contract_id: string (UUID), campaign_id: string }
Response: { paused: boolean }
Authorization: PAID_AD_CAMPAIGN in Decision Space
Failure: REQUIRED (pausing is the safe fallback — must work)
```

---

## platform-analytics-mcp (port 8109)

Used by: Digital Marketing Agent — Skill 9 (Performance Analytics)

### instagram.get_insights
```
POST /call/instagram.get_insights
Request:  {
  contract_id: string (UUID),
  period: "day" | "week" | "month",
  since: string (ISO date),
  until: string (ISO date),
  metrics: string[]    -- ["impressions","reach","profile_visits","website_clicks","follower_count"]
}
Response: { metrics: { [metric_name]: { values: [{ value: number, end_time: string }] } } }
Authorization: Always authorized (read-only, own account only)
Failure: DEGRADABLE
```

### gbp.get_metrics
```
POST /call/gbp.get_metrics
Request:  {
  contract_id: string (UUID),
  metric_types: string[],  -- ["QUERIES_DIRECT","QUERIES_INDIRECT","VIEWS_MAPS","VIEWS_SEARCH","ACTIONS_PHONE","ACTIONS_DRIVING_DIRECTIONS"]
  start_date: string,
  end_date: string
}
Response: { metrics: { [type]: integer } }
Authorization: Always authorized (read-only)
Failure: DEGRADABLE
```

---

## Developer Notes — Common Implementation Patterns

### C-041 Enforcement Pattern (every MCP adapter must implement)

```python
# In every MCP server /call/{tool_name} handler:
@app.post("/call/{tool_name}")
async def call_tool(tool_name: str, body: dict, request: Request):
    # Step 1: Extract contract_id from body
    contract_id = body.get("contract_id")
    if not contract_id:
        raise HTTPException(400, "contract_id required")

    # Step 2: Validate CE approval evidence if required
    approval_evidence_id = body.get("approval_evidence_id")
    ce_response_id = body.get("ce_validate_action_response_id")
    # For spend-incurring tools: validate ce_response_id exists (proof CE was called)
    # For approval-gate tools: validate approval_evidence_id is a valid APPROVED/SYNTHETIC record

    # Step 3: Execute the real tool action
    # (real implementation — stub returns STUB_RESULT)
    result = await execute_tool(tool_name, body)

    return result
```

### OAuth Token Retrieval Pattern (for customer-authenticated tools)

```python
# instagram-mcp, facebook-mcp, google-business-mcp, meta-ads-mcp, google-ads-mcp
# must retrieve the customer's OAuth access token from the credential vault (ADR-021).

async def get_access_token(contract_id: str, platform: str) -> str:
    # Call the oauth-vault service (internal HTTP)
    # GET http://oauth-vault:8130/tokens/{contract_id}/{platform}
    # Returns: { access_token: str, expires_at: datetime }
    # Token refresh is handled by oauth-vault — MCP server never refreshes directly
    response = await http_client.get(
        f"http://oauth-vault:8130/tokens/{contract_id}/{platform}"
    )
    return response.json()["access_token"]
```

---

## Tool Catalogue Version History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-09 | Initial catalogue — customer-profile-mcp, web-search-mcp, google-places-mcp, social-profile-mcp, meta-ad-library-mcp, scheduling-mcp, instagram-mcp, meta-ads-mcp, platform-analytics-mcp |

---

## razorpay-mcp (port 8131)

Used by: Business Platform (billing, subscription management, GST invoicing)
**ADR-022.** All tools require mTLS from Business Platform only. Never exposed externally.

### subscription.create
```
POST /call/subscription.create
Request:  { contract_id, plan_id, customer_email, customer_phone, customer_name, total_count?, notes }
Response: { razorpay_subscription_id, short_url }
Authorization: Internal only. Called on trial → paid conversion.
Failure: REQUIRED — no subscription = no billing = contract cannot activate
```

### subscription.pause / resume / cancel
```
POST /call/subscription.pause | /call/subscription.resume | /call/subscription.cancel
Request:  { razorpay_subscription_id, pause_at?: "now"|"cycle_end" }
Response: { success: boolean }
Authorization: Internal only. Triggered by employment contract lifecycle events.
Failure: REQUIRED
```

### mandate.create_upi_autopay  ← R016-01 fix
```
POST /call/mandate.create_upi_autopay
Request:  {
  contract_id: string (UUID),
  customer_phone: string,        -- +91XXXXXXXXXX (E.164)
  customer_name: string,
  amount_inr_paise: integer,     -- 20000 = ₹200
  description: string,           -- "WAOOAW Agricultural Advisor — ₹200/month"
  farmer_language: string        -- for localised UPI app message
}
Response: {
  mandate_id: string,            -- Razorpay mandate ID (track completion)
  mandate_link: string,          -- UPI AutoPay deep link to send via WhatsApp
  expires_at: string             -- link expires after 24 hours
}
Authorization: Internal only. Called when farmer's profile reaches MINIMUM_VIABLE and is WhatsApp-registered.
Failure: REQUIRED — without mandate, recurring billing cannot be established
Notes: Uses Razorpay Recurring Payments API (UPI AutoPay / Standing Instruction).
       Farmer approves ONCE in their UPI app; Razorpay auto-collects monthly.
       On mandate approval: Razorpay sends webhook mandate.confirmed → SUBSCRIPTION_ACTIVATED.
```

### mandate.get_status  ← R016-01 fix
```
POST /call/mandate.get_status
Request:  { mandate_id: string }
Response: {
  status: "CREATED" | "CONFIRMED" | "REJECTED" | "PAUSED" | "CANCELLED",
  confirmed_at: string | null,
  bank_name: string | null      -- which bank the farmer approved from
}
Authorization: Internal only. Polled after mandate link is sent, to activate the subscription.
Failure: DEGRADABLE — agent can retry if status check fails
```

### invoice.get_gst
```
POST /call/invoice.get_gst
Request:  { razorpay_payment_id: string }
Response: { invoice_number, gstin_waooaw, hsn_sac_code, base_amount_inr, cgst_amount_inr, sgst_amount_inr, total_amount_inr, customer_gstin?, pdf_url }
Authorization: Internal only.
Failure: DEGRADABLE — invoice can be regenerated on demand
```

---

## Agricultural Advisor — End-to-End Billing Flow (R016-01 specification)

```
[New farmer registered via WhatsApp — auto-registration complete]
    ↓
Profile reaches MINIMUM_VIABLE (4 exchanges)
    ↓
Agent sends billing setup message via whatsapp-business-mcp (HSM template):
  "शेतकरी मित्र: ₹200/महिना — एकदाच approve करा, दर महिना आपोआप होईल: [mandate_link]"
  razorpay-mcp.mandate.create_upi_autopay → mandate_id + mandate_link
    ↓
Farmer taps link → UPI app opens → approves ₹200/month standing instruction
    ↓
Razorpay webhook: mandate.confirmed → Business Platform
  → razorpay-mcp.subscription.create (using confirmed mandate)
  → employment_contracts.state = ACTIVE
  → CE.RecordEvidence(SUBSCRIPTION_ACTIVATED)
  → Agent begins daily check-ins
    ↓
Monthly auto-collection (1st of each month):
  Razorpay debits farmer's bank → payment.captured webhook → WAOOAW
  → subscription_billing_events record
  → gst_invoices record (SAC 9984, ₹169 base + ₹30 GST)
    ↓
Payment failure path:
  Razorpay webhook: payment.failed → Business Platform
  → 3-day grace period starts (payment_transactions.grace_period_ends_at)
  → Day 1: WhatsApp message: "Payment failed. Retry: [razorpay payment link]"
  → Day 3: If no payment: employment_contracts.state = SUSPENDED
  → Agent stops daily check-ins (PMFBY evidence records preserved)
```

**HSM Templates Required (Meta pre-approval needed before production):**
| Template | When sent | Content |
|---|---|---|
| `agri_billing_setup` | After profiling complete | UPI AutoPay mandate setup link + ₹200/month explanation |
| `agri_payment_failure` | On Razorpay payment.failed | Payment failed message + retry link |
| `agri_subscription_active` | After mandate.confirmed | Confirmation that advisor is active |
