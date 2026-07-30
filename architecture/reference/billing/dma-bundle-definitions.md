# DMA Bundle Definitions — Starter / Runner / Winner

**Authority:** Chief Business Architect (INST-003) — GOAL-004 D-05
**Agent:** Digital Marketing Agent (DMA) v3.0
**Constitutional Basis:** C-088 (Agent Billing Profile), C-089 (Minimum Margin Floor),
C-090 (Grandfather Pricing), C-091 (Thread Catalog Sovereignty)
**Thread Catalog Reference:** architecture/reference/billing/thread-catalog.md
**Status:** APPROVED — 2026-07-30 | Founder pricing authorization: PENDING (open decisions §7)
**Implements:** D-05 per GOAL-004 Goal Execution Plan

---

## 1. Bundle Philosophy

DMA bundles are designed around three customer archetypes:

- **Starter (Curtain Raiser):** A local business owner who has never run digital marketing
  before. They need guidance, content help, and to understand what "social media presence"
  means for their business. Low volume, exploratory.

- **Runner (Growth Engine):** A business owner who has seen results from Starter and is
  ready to invest more. They run campaigns, generate video content regularly, and want
  weekly strategic input.

- **Winner (Maturity Phase):** A business with established digital presence that wants to
  maximize reach. High volume of content, deep analytics, Reels + Avatar, full FRONTIER
  AI access for strategy.

---

## 2. Bundle Resource Rations

All rations are per 30-day billing period. "LLM calls" = complete request-response cycles.

| Resource | thread_id | Starter | Runner | Winner |
|---|---|---|---|---|
| LOCAL classification | `llm_local` | Unlimited | Unlimited | Unlimited |
| MID_TIER LLM calls | `llm_mid_gemini` | 80 | 200 | 500 |
| FRONTIER LLM calls | `llm_frontier_gemini` | 0 | 20 | 60 |
| Video clips (Kling) | `video_kling_clip` | 0 | 4 | 8 |
| Avatar video minutes (HeyGen) | `video_heygen_minute` | 0 | 0 | 2 |
| Voice synthesis | `voice_elevenlabs_monthly` | — | — | Included (plan allocation) |
| WhatsApp windows | `whatsapp_window` | 30 | 60 | 120 |
| Image generation | `image_gen_per_image` | 5 | 20 | 60 |
| Infrastructure share | `infra_share` | ₹180/month | ₹180/month | ₹180/month |
| Ad spend wallet | Customer-funded | Min ₹2,000 | Min ₹3,000 | Min ₹5,000 |

---

## 3. Customer-Facing Descriptions

These are the descriptions shown to customers. No technical terms, no provider names.

### Starter — "Your Digital Marketing Foundation"
> Every month you get: up to 30 conversations with your marketing expert, 5 custom
> graphics, assistance with up to 80 marketing decisions and content pieces, and support
> for up to 30 days of social posting activity. Perfect if you're just starting out.

### Runner — "Your Active Growth Engine"
> Every month you get: up to 60 days of active social presence management, 4 professional
> video reels for your business, 20 custom graphics, expert analysis on up to 200 marketing
> decisions, plus 20 strategic deep-dives for your campaigns. Includes paid advertising
> management when you add an ad budget.

### Winner — "Your Full Marketing Department"
> Every month you get: unlimited daily engagement management, 8 video reels + 2 minutes of
> personalised avatar content + voice narration, 60 custom graphics, 500 marketing
> decisions with expert AI, 60 strategic sessions, and priority FRONTIER AI access for
> your most important business decisions.

---

## 4. Pricing Derivation (Markup Engine — Layer 1 → 2 → 3)

### Starter Bundle Cost Floor

| Thread | Ration | Marked-up unit cost | Bundle cost |
|---|---|---|---|
| `llm_mid_gemini` (2K tokens avg) | 80 calls | 3 paise/1K → 6 paise/call | 480 paise |
| `llm_frontier_gemini` | 0 calls | — | 0 |
| `video_kling_clip` | 0 clips | — | 0 |
| `whatsapp_window` | 30 windows | 70 paise/window | 2,100 paise |
| `image_gen_per_image` | 5 images | 230 paise/image | 1,150 paise |
| `infra_share` | flat | 18,000 paise/month | 18,000 paise |
| **Bundle Cost Floor** | | | **21,730 paise (₹217.30)** |

**Platform margin (suggested 65%):** ₹217.30 ÷ 0.35 = ₹620.86 → rounded to **₹699 base**
**With GST 18%:** ₹699 × 1.18 = **₹825 customer-facing price**

*Note: Current ADR-022 prices Curtain Raiser at ₹1,271 base (₹1,499 incl. GST). This implies
an 83% margin at the Starter tier — well above the C-089 floor. The Founder may choose to
maintain ₹1,499 pricing (higher margin), reduce to ₹825 (floor pricing, higher volume), or
position between. Pricing authorization is a Founder Decision (open decision §7.1).*

### Runner Bundle Cost Floor

| Thread | Ration | Marked-up unit cost | Bundle cost |
|---|---|---|---|
| `llm_mid_gemini` | 200 calls | 6 paise/call | 1,200 paise |
| `llm_frontier_gemini` (6K tokens avg) | 20 calls | 21 paise/1K → 126 paise/call | 2,520 paise |
| `video_kling_clip` | 4 clips | 1,725 paise/clip | 6,900 paise |
| `whatsapp_window` | 60 windows | 70 paise/window | 4,200 paise |
| `image_gen_per_image` | 20 images | 230 paise/image | 4,600 paise |
| `infra_share` | flat | 18,000 paise/month | 18,000 paise |
| **Bundle Cost Floor** | | | **37,420 paise (₹374.20)** |

**Platform margin (suggested 65%):** ₹374.20 ÷ 0.35 = ₹1,069 → rounded to **₹1,099 base**
**With GST 18%:** **₹1,297 customer-facing price**

*Current ADR-022 prices Growth Engine at ₹2,118 base (₹2,499 incl. GST) → implied 82% margin.*

### Winner Bundle Cost Floor

| Thread | Ration | Marked-up unit cost | Bundle cost |
|---|---|---|---|
| `llm_mid_gemini` | 500 calls | 6 paise/call | 3,000 paise |
| `llm_frontier_gemini` | 60 calls | 126 paise/call | 7,560 paise |
| `video_kling_clip` | 8 clips | 1,725 paise/clip | 13,800 paise |
| `video_heygen_minute` | 2 minutes | 1,438 paise/min | 2,876 paise |
| `voice_elevenlabs_monthly` | Plan share (÷10 customers) | 275,000 ÷ 10 | 27,500 paise |
| `whatsapp_window` | 120 windows | 70 paise/window | 8,400 paise |
| `image_gen_per_image` | 60 images | 230 paise/image | 13,800 paise |
| `infra_share` | flat | 18,000 paise/month | 18,000 paise |
| **Bundle Cost Floor** | | | **94,936 paise (₹949.36)** |

**Platform margin (suggested 65%):** ₹949.36 ÷ 0.35 = ₹2,712 → rounded to **₹2,799 base**
**With GST 18%:** **₹3,303 customer-facing price**

*Current ADR-022 prices Maturity Phase at ₹3,389 base (₹3,999 incl. GST) → implied 72% margin.*

---

## 5. Top-Up Plans Available Per Bundle

| Top-Up Type | Starter | Runner | Winner | Unit Price |
|---|---|---|---|---|
| +30 MID_TIER LLM calls | ✅ | ✅ | ✅ | ₹29 (inc. GST) |
| +10 FRONTIER LLM calls | ❌ | ✅ | ✅ | ₹79 (inc. GST) |
| +2 video clips (Kling) | ❌ | ✅ | ✅ | ₹129 (inc. GST) |
| +10 image generations | ✅ | ✅ | ✅ | ₹39 (inc. GST) |
| +10 WhatsApp windows | ✅ | ✅ | ✅ | ₹29 (inc. GST) |
| Diwali Festival Pack | ✅ | ✅ | ✅ | ₹699 (inc. GST) |
| Grand Opening Pack | ✅ | ✅ | ✅ | ₹499 (inc. GST) |

**Diwali Festival Pack contents:** +8 video clips + 100 MID_TIER calls + 20 FRONTIER calls
+ 40 images + 30 WhatsApp windows. Valid within current billing period only.

**Grand Opening Pack contents:** +5 video clips + 50 MID_TIER calls + 10 FRONTIER calls
+ 25 images + 20 WhatsApp windows. Valid within current billing period only.

**Auto-refill authorization (pre-authorized by customer):**
- MID_TIER LLM: auto-add 30 calls when balance = 0 → ₹29 deducted from wallet
- WhatsApp windows: auto-add 10 when balance < 3 → ₹29 deducted from wallet
- Video clips: DO NOT auto-refill — always ask (customer's creative decision)

---

## 6. Trial Profile (Zero-Cost Substitutions)

| Thread | Trial Substitution | What customer experiences |
|---|---|---|
| `llm_mid_gemini` | Ollama llama3.2-3b (LOCAL) | "Guided assistant" responses — slightly less nuanced |
| `llm_frontier_gemini` | Ollama llama3.2-3b (LOCAL) | Basic responses only |
| `video_kling_clip` | Pre-generated sample reel (library) | Agent shows an example reel for their category |
| `image_gen_per_image` | Stock image from free library | Agent presents a relevant stock image |
| `whatsapp_window` | Demo mode (free BSP allowance) | Normal WhatsApp chat, no per-window charge |
| `ad_spend` | Simulated campaign (no real spend) | Agent shows mock campaign preview |

**Trial mode disclosure (C-049 + C-051):** Agent says:
> "I'm showing you what I can do for your business. I'm running on my demonstration engine
> right now — when you hire me, I'll upgrade to full capability. Want to see what a typical
> month looks like for a business like yours?"

No mention of provider names. No mention of "Ollama" or "AI engine." Customer sees outcomes.

---

## 7. Open Decisions Requiring Founder Authorization

| # | Decision | Suggested | Impact |
|---|---|---|---|
| 7.1 | Final customer-facing prices (Starter/Runner/Winner in INR incl. GST) | Starter ₹999, Runner ₹1,999, Winner ₹3,499 OR maintain ADR-022 prices | All three are above C-089 floor |
| 7.2 | Minimum margin % (C-089) | 55% | Sets the computational floor for all bundles |
| 7.3 | Top-up pricing final approval | As listed in §5 | Each top-up must be above C-089 floor at thread level |
| 7.4 | Auto-refill ceiling (₹/month without re-asking) | ₹500/month per customer | Higher = more convenience; lower = more customer control |
| 7.5 | ElevenLabs voice: amortise across how many customers? | 10 customers | Affects Winner bundle cost floor at lower customer count |

*Founder must authorize pricing before WBE activates these bundles for production customers.*
