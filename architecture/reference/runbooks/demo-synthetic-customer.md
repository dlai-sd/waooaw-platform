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
| `scripts/run_acceptance_with_synthetic_customers.sh JOURNEY` | Runs one customer-journey-acceptance journey locally in Docker against those customers. |

Both need `WAOOAW_RUNNER_TYPESCRIPT_IMAGE` (and the Python image for the journey runner).

## Rules the utility already follows (read before changing it)

- Usernames are `acc-<run>-<label>`; the run id is 8 to 12 lowercase letters or digits (the marker route needs 8 or more).
- Passwords satisfy the realm policy: 12 or more characters, an upper-case letter, a digit and a special character.
- The provisioning token lives about 60 seconds, so the in-network job fetches its own and the marker call uses a fresh one.
- In-network calls use only `X-Forwarded-*` headers. Forcing a `Host` header makes Container Apps answer 404.
- Deletion touches only users that carry the prefix and are in the `synthetic` group.

## Known limitation (found 2026-11-26)

A throwaway customer can be created and can sign in to Keycloak, but Business Platform then denies the customer actor
(`Customer identity actor denied by actor_provider`) because it accepts only customers whose token carries a configured
broker identity (`idp` or `identity_provider` of `google` or `facebook`). Until a `synthetic` provider alias exists for
Demo, customer pages show "Access not permitted" for these users and the journey harness cannot act as a customer.
The Founder-page step-up probe and the public pages do not depend on this.
