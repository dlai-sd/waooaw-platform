# Digital Marketing monthly package for Demo (WC-176 R013) and the live-run prerequisites (WC-176 R025)

**Status:** values proposed for the Founder's review. Nothing here activates a package: the Founder activates it on the
Founder Pricing page with a fresh strong sign-in. Demo only.

## What the Founder does, in order

| # | Step | Where | Done when |
|---|---|---|---|
| 1 | Approve Digital Marketing 1.0.0 | Founder Professionals page (fresh strong sign-in) | The version shows Approved. Done on 2026-11-28. |
| 2 | Razorpay Test Mode keys and webhook | Demo vault and Razorpay dashboard | `razorpay-test-key-id` (starts `rzp_test_`), `razorpay-test-key-secret` and `razorpay-test-webhook-secret` are in the Demo vault, and Test Mode has a webhook to the Demo address ending `/api/v1/payments/webhooks/razorpay`. Done; see [razorpay-test-mode-demo.md](./razorpay-test-mode-demo.md). |
| 3 | GST identity | Billing engine settings | The six `GST_*` settings are in the Demo billing engine (rendered by Terraform from the values below). |
| 4 | Create and publish the package | Founder Pricing page (fresh strong sign-in) | The package below shows Published, with its GST terms. |

## The package

| Field | Value |
|---|---|
| Professional | `DIGITAL_MARKETING_LOCAL_SERVICE`, version `1.0.0` |
| Package code | `STARTER_LIVE` (the older `STARTER` draft is marked "illustrative, not for sale" and stays untouched) |
| Display name | Digital Marketing Starter |
| Billing period | 30 days |
| Price the customer pays, GST included | ₹599.00 (`59900` paise) |
| GST rate | 18% |
| Price before GST | ₹507.63, GST ₹91.37 |
| Cost floor (Starter ration) | ₹217.30 a month, so the margin before GST is about 57% against the 55% policy minimum |
| Infrastructure share | ₹180.00 (`18000` paise) |

Components, as the Pricing page shows them (each component's price share adds up to the full ₹599.00):

| Component | Quantity | Price share (paise) | Cost thread |
|---|---|---|---|
| Content plans (`CONTENT_PLAN`) | 1 | 3000 | `llm_mid_gemini`, 10 calls |
| Content drafts (`CONTENT_DRAFT`) | 8 | 12000 | `llm_mid_gemini`, 4 calls each |
| Pictures and short videos (`CONTENT_ASSET`) | 5 | 9000 | `image_gen_per_image`, 1 each |
| Approved posts published (`SOCIAL_PUBLICATION`) | 8 | 6000 | `llm_mid_gemini`, 2 calls each |
| Social accounts watched (`SOCIAL_OBSERVATION`, up to 4 chosen) | 2 | 18000 | `llm_mid_gemini`, 5 calls each |
| WhatsApp messages from your agent (`PROACTIVE_MESSAGE`) | 30 | 11900 | `whatsapp_template_utility` |

That is at most 68 of the ration's 80 mid-tier calls, 5 of 5 images and 30 of 30 WhatsApp windows. Paid boosts (`AD_BOOST`)
are not in this package: the agent's manifest marks them unavailable.

The Pricing page checks the package and lists any problem (for example a cost thread the Founder has not yet authorized).
Authorize the three threads above first (Pricing page, Cost rates). If the page names another problem, change the
value it names; do not skip a check.

## GST terms (the values the billing engine uses)

| Setting | Value |
|---|---|
| `GST_LEGAL_NAME` | DLAI Satellite Data (OPC) Pvt Ltd |
| `GST_GSTIN` | 27AAKCD8188R1ZH |
| `GST_ADDRESS` | C8, Everest Heights, Park Road, Viman Nagar, Pune 411014, Maharashtra, India |
| `GST_STATE_CODE` | 27 |
| `GST_SAC_CODE` | 9984 (the accounting code for the service; the Founder's tax professional confirms it before real money) |
| `GST_RATE_PERCENT` | 18 |
| Invoice numbers | `WAOOAW/2026-27/000001` and on, one series for the financial year, no gaps |

## Check that the steps are done (read-only)

Run `python3 scripts/wc176_razorpay_readonly_check.py` for the Razorpay settings (it prints no secret). The package and the
approval are visible on the two Founder pages; a package that is not Published makes Hire show "not available".
