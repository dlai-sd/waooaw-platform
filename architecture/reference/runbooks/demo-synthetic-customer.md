# Demo throwaway customers and customer walk

**Status:** tooling, report-only. Demo only. Nothing here changes a Production or UAT environment.

## Why this exists

The public identity edge denies the Keycloak admin API, so a test customer can only be created from inside the Demo
network. `scripts/demo_synthetic_customer.py` does that with a short-lived Container Apps job that runs as the existing Demo
deployment identity, then registers each customer as synthetic through the platform marker route and writes the sign-in
details to a private file outside the repository (`/workspaces/.synthetic-customers/<run>.json`, mode 600).

```bash
python3 scripts/demo_synthetic_customer.py create --count 2          # about 3 minutes (an in-network job)
python3 scripts/demo_synthetic_customer.py list
python3 scripts/demo_synthetic_customer.py delete --run-id <run>     # or: delete --all
```

Add `--harness-private DIR` to also write `run-state.json` so the journey harness adopts these customers.

## Reusable tests

| Script | What it does |
|---|---|
| `scripts/run_demo_customer_walk.sh` | Signs in as a throwaway customer in a real browser, visits every customer and Founder route, records status, headings, tabs, buttons, console errors, failed requests and a screenshot per page, and probes which Founder pages can start a two-factor sign-in. |
| `JOURNEY=explore\|register\|trial scripts/run_demo_customer_walk.sh` | Runs `tests/demo-customer-walk/journey.mjs`: opens Register, signs in, opens the Trial review, and with `trial` confirms it, with `register` fills the profile and stops at the WhatsApp step. Records every API call, status and a screenshot per step. Needs a throwaway customer and the Founder's approval. |
| `scripts/run_acceptance_with_synthetic_customers.sh JOURNEY` | Runs one customer-journey-acceptance journey locally in Docker against those customers. |

Both need `WAOOAW_RUNNER_TYPESCRIPT_IMAGE` (and the Python image for the journey runner).

## Rules the utility already follows (read before changing it)

- Usernames are `acc-<run>-<label>`; the run id is 8 to 12 lowercase letters or digits (the marker route needs 8 or more).
- Passwords satisfy the realm policy: 12 or more characters, an upper-case letter, a digit and a special character.
- The provisioning token lives about 60 seconds, so the in-network job fetches its own and the marker call uses a fresh one.
- In-network calls use only `X-Forwarded-*` headers. Forcing a `Host` header makes Container Apps answer 404.
- Deletion touches only users that carry the prefix and are in the `synthetic` group.

## How a throwaway customer passes the customer identity proof

Business Platform accepts a customer only when the token carries a broker `idp` claim and Keycloak holds exactly one
federated link to that provider. A password user has neither, so the first live run (2026-11-26) showed "Access not
permitted" on every customer page. The fix needs no Business Platform change:

- The Demo realm declares an admin-only user attribute `synthetic_idp` (only `google` or `facebook`; users cannot view or edit it).
- The `waooaw-web` client maps that attribute to the `idp` claim. The mapper exists only when the acceptance provisioner is enabled (Demo).
- The utility sets `synthetic_idp=google` and creates one fake federated link (`synthetic-<username>`) for each throwaway user.
- Real brokered users are unchanged: they have no such attribute, so their `idp` still comes from the broker session.

This works only after the deploy that carries the realm change has re-imported the realm.
The Founder-page step-up probe and the public pages do not depend on it.

## Registration code for a throwaway customer

A real customer's WhatsApp code is sent through Meta and costs money. A throwaway customer never uses it. When
`AcceptanceSyntheticTenants__Enabled` is true (Demo and test only; the platform refuses it in Production) and the customer
is registered as synthetic, Business Platform answers the WhatsApp registration step with the fixed test code
(`AcceptanceSyntheticTenants__TestVerificationCode`, default `123456`) and sends nothing, so no template and no budget is used.

- The check is server-side: the customer must be in the synthetic registry written by the marker route. A real customer is never affected.
- Each throwaway customer gets its own fictitious number in the `+1555xxxxxxx` range (stored in the sign-in file as `mobile`),
  so two throwaway customers never share a number.
- `JOURNEY=register scripts/run_demo_customer_walk.sh` enters that number and the code, confirms it and completes registration.
- The real WhatsApp delivery (`waooaw_registration_otp`) is a separate, Founder-approved live check with a real number.
