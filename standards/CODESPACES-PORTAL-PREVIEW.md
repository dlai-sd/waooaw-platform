# Codespaces Portal Preview Standard

| Control | Value |
|---|---|
| Owner | Platform IT Expert (INST-010) |
| Authority | Founder instruction, 2026-09-24 |
| Work Contract | WC-105 / WC105-R027 |
| Scope | Local Codespaces review only; no cloud or provider mutation |

Use the repository launcher whenever the Founder asks for a WAOOAW application URL in a Codespace.
It builds the checked-out Web, Business Platform, and Constitutional Engine source, starts their real
PostgreSQL, Temporal, and Jaeger dependencies, waits for health checks, and prints the forwarded HTTPS
URL and customer routes.

```sh
scripts/run_auth_preview.sh start
```

The current Codespace origin must be the exact Demo `waooaw-web-preview` origin registered by
Terraform for Google or Facebook login. The launcher uses the registered Demo Keycloak only as the
external identity authority; Business Platform data and application execution remain in the isolated
local Compose project. It does not mutate Azure, Keycloak, Meta, or Google configuration.

Use an immutable release image instead of building the current Web source only when reproducing a
specific release:

```sh
WAOOAW_WEB_IMAGE=ghcr.io/dlai-sd/web@sha256:<digest> scripts/run_auth_preview.sh start
```

Runtime secrets and the release manifest are generated under `.auth-preview/`, which must remain
untracked. Existing cryptographic secrets are reused so the persistent database and Data Protection
key ring remain readable across repeated starts. Each `start` creates a new deployment generation:
browser sessions from the previous deployment are rejected, and new preview sessions expire after
one hour. A container restart within the same Compose deployment retains its generation and does not
invalidate an otherwise active session. Stop the stack without deleting its database using:

The launcher also installs a local-only Marketplace fixture. Existing active customer memberships
are backfilled with the current DMA catalog admission, and registrations created while the preview
is running receive the same fixture automatically. Production admission data and controls are not
modified.

```sh
scripts/run_auth_preview.sh stop
```

The launcher contract is verified in Docker by `tests/pipeline/test_auth_preview.py`. Browser review
is acceptance evidence for the displayed candidate only; it does not prove Azure, provider, UAT, or
Production readiness and grants no approval or merge authority.