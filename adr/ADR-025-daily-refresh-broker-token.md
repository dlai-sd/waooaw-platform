# ADR-025 — Daily-Refresh Broker Token Management (Zerodha Kite + Similar Brokers)

**Status:** Accepted
**Date:** 2026-07-12
**Author:** Enterprise Architect (GAP-T003 Simulation 005, GAP-T012 Simulation 008)
**Constitutional Basis:** C-041 (tool authorization — authenticated broker API calls require customer delegation); C-053 (Signal Sensing Obligation — broker auth expiry is a CRITICAL signal); ADR-021 (OAuth vault — this ADR extends ADR-021 for daily-refresh tokens)

---

## Context

ADR-021 defines the oauth-vault service for managing long-lived OAuth tokens (Instagram, Facebook, Google) that can be refreshed in the background without customer involvement. These tokens typically live for 60 days (Meta) or indefinitely with a refresh token (Google).

Indian broker APIs (Zerodha Kite Connect, Upstox v2, Angel One SmartAPI) use a fundamentally different authentication model:
- **No refresh token exists** — tokens cannot be refreshed programmatically
- **Tokens are session-scoped** — they expire at midnight (IST) every trading day
- **Re-authentication requires active customer involvement** — the customer must log into the broker's login page each day, which generates a one-time `request_token` (valid for 60 seconds)
- **The exchange window is 60 seconds** — if `request_token` is not exchanged for an `access_token` within 60 seconds, it expires

This is architecturally incompatible with ADR-021's background refresh model.

---

## Decision

Declare a new token class `DAILY_BROKER_TOKEN` in oauth-vault alongside the existing `PLATFORM_OAUTH_TOKEN` class. The two classes have distinct storage, lifecycle, and customer interaction patterns.

### DAILY_BROKER_TOKEN class

**Storage:** Same encrypted PostgreSQL store as PLATFORM_OAUTH_TOKEN, but separate token_class column to distinguish lifecycle management.

**Lifecycle:**
```
Trading Day T:
  7:00 PM IST: SIL BROKER_AUTH_EXPIRY signal fires (5 hours before midnight)
               → Customer receives CRITICAL WhatsApp alert with deep link
  Customer action: opens deep link → Kite login page → logs in → WAOOAW callback URL
  Callback: receives request_token (60-second validity)
  oauth-vault: immediately exchanges request_token for access_token
  access_token stored: valid until midnight IST tonight
  
Trading Day T+1:
  9:15 AM: SESSION_PREP uses today's access_token → trades
  Midnight: access_token expires → repeat cycle
```

**The 60-second exchange window:**
```
Customer completes Kite login → browser redirects to:
  https://api.waooaw.in/oauth/callback/zerodha?request_token=XXX&status=success

oauth-vault receives request_token:
  1. Start 55-second timer (safety margin from 60-second window)
  2. POST to Kite API: /session/token
     { api_key, request_token, checksum: sha256(api_key + request_token + api_secret) }
  3. Kite returns: { access_token, user_id, login_time }
  4. oauth-vault stores access_token with expiry = midnight IST tonight
  5. Signal to Professional Runtime: BROKER_RECONNECTED
  
If exchange fails (timeout, Kite error):
  6. Retry once with 2-second delay
  7. If second attempt fails: notify customer "Connection failed — please try again"
     Raise BROKER_RECONNECT_FAILED event → no session possible today
```

**Why this matters for constitutional compliance:**
- Without broker auth, NO trading session can start → agent cannot serve its core function
- BROKER_AUTH_EXPIRY is therefore a CRITICAL signal (C-053) with `emergency_exempt: true`
- The daily re-authentication is not a design flaw — it is Zerodha's security model, and WAOOAW must accommodate it while minimizing customer friction

### Customer Experience (Reducing Daily Friction)

The 7:00 PM re-auth alert gives the customer 5 hours to act before midnight, and 14 hours before the next morning's session. This is designed to fit into the customer's evening routine (after work, before sleep).

**Portal deep link flow:**
```
WhatsApp message → "Re-authenticate" button → WAOOAW portal
  → Portal shows: "Connect Zerodha for tomorrow's session"
  → Customer clicks "Connect Zerodha"
  → Zerodha OAuth URL opens in browser (WAOOAW redirect_uri configured)
  → Customer logs in with Zerodha credentials
  → Zerodha redirects to WAOOAW callback with request_token
  → oauth-vault exchanges within 60 seconds
  → Portal shows: "✓ Connected for tomorrow. Your session will run as normal."
```

**If customer forgets or chooses to skip:**
- No re-auth by midnight → access_token expires → no session next day
- At 9:15 AM next day: SESSION_PREP detects missing auth → notifies customer
- "Your Zerodha session couldn't run today — broker connection was not refreshed last night."
- Customer can re-auth for next day

### Distinction from ADR-021 PLATFORM_OAUTH_TOKEN

| Property | PLATFORM_OAUTH_TOKEN | DAILY_BROKER_TOKEN |
|---|---|---|
| Refresh mechanism | Background auto-refresh (oauth-vault daemon) | Customer active re-authentication required |
| Token lifetime | 60 days (Meta) / indefinite (Google with refresh) | Until midnight IST of current trading day |
| Customer involvement | Zero (after initial connect) | Daily (5-10 seconds of action) |
| Exchange window | N/A (refresh API call) | 60 seconds from request_token generation |
| Failure handling | Pause skill + notify customer | Skip session + notify at 9:15 AM |
| CRITICAL signal trigger | N/A | BROKER_AUTH_EXPIRY at 7:00 PM IST daily |

### Supported Brokers (Daily-Refresh Model)

| Broker | API Name | Auth endpoint | Notes |
|---|---|---|---|
| Zerodha | Kite Connect v3 | `POST /session/token` | Checksum = SHA256(api_key + request_token + api_secret) |
| Upstox | Upstox v2 | `POST /login/authorization/token` | Standard OAuth exchange with PKCE |
| Angel One | SmartAPI | `POST /rest/auth/angelbroking/user/v1/loginByPassword` | Uses TOTP for 2FA; different flow — requires ADR amendment |

**Angel One note:** Angel One's SmartAPI uses password + TOTP (time-based OTP) rather than an OAuth flow. This is a different security model and may require a dedicated solution (e.g., customer provides TOTP secret to WAOOAW's secure vault). This is deferred — Angel One support requires a separate decision.

---

## Rejected Alternatives

**A — Store Zerodha password in vault and auto-login:** Security risk unacceptable. WAOOAW would hold customer's broker password — a breach would expose financial account credentials. Never acceptable.

**B — Use Zerodha's API access token with extended validity:** Zerodha does not offer extended tokens. This is their security policy. No workaround available.

**C — Ignore daily auth and let session fail:** Would result in customer paying for a day they can't trade. C-038 (pro-rata billing) may require session credit when auth failure prevents the session — this is an open billing question to be resolved.

---

## Consequences

- oauth-vault service: add DAILY_BROKER_TOKEN class to token storage schema
- oauth-vault: add daily expiry check job (runs at 11:55 PM IST: check all DAILY_BROKER_TOKENs, mark expired)
- broker-api-mcp: implement Kite Connect daily auth flow (request_token → access_token exchange)
- trading-agent.md: add `BROKER_DAILY_REAUTH` as always-ask action
- BROKER_AUTH_EXPIRY signal: CRITICAL, `emergency_exempt: true`, fired at 7:00 PM IST daily on trading days
- Portal: "Reconnect Broker" deep link flow (WAOOAW → Kite OAuth → WAOOAW callback)
- `broker_connections` table: add `token_class` column; add `last_reconnected_at`, `reconnection_count_today`
