# GOAL-006 P1-WC07 Local Diagnostic Evidence

| Field | Value |
|---|---|
| `record_id` | ER-GOAL-006-INST-010-01 |
| Observation date | 2026-08-13 |
| Observation point | Commit `9227bd9`; `/workspaces/waooaw-platform` |
| Classification | Local diagnostic only; not C-080-compliant test evidence and not cloud/live evidence |
| Normalized evidence SHA-256 | `c01c6d4fb9877e8770ccd1938f8801c2d02faa4e1e91ae87719ac77a9ae041d4` |

## Toolchain Command

```bash
for tool in docker terraform node npm python dotnet gh git; do
  command -v "$tool" && "$tool" --version
done
```

Observed first-line versions: Docker `29.3.0`; Node `24.14.0`; npm `11.9.0`; Python
`3.12.1`; .NET SDK `10.0.200`; GitHub CLI `2.88.0`; Git `2.53.0`. Terraform was not found.

## Compose Parse

Command: `docker compose config --quiet`

Exit code: `0`.

Warnings reported blank defaults for `POSTGRES_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`,
`WHATSAPP_WEBHOOK_SECRET`, `IDENTITY_HMAC_KEY`, `WHATSAPP_TENANT_TOKEN_KEY`, and
`BP_SERVICE_JWT_SECRET`.

## Host Test Collection Diagnostic

Command: `python -m pytest --collect-only -q tests`

Exit code: `2`. Pytest reported `1701 tests collected` and two collection errors:

- `tests/professional-runtime` — `ModuleNotFoundError: No module named 'grpc'`
- `tests/test_wc012_dry_run.py` — `KeyError: 'WC012-01'`

This command did not execute the collected tests. It used host Python and therefore cannot count as
the required Docker-based Phase 2 validation. It was retained only to identify prerequisite failures.

## Normalization

The normalized digest above covers exactly:

```text
TOOLCHAIN docker=29.3.0 node=24.14.0 npm=11.9.0 python=3.12.1 dotnet=10.0.200 gh=2.88.0 git=2.53.0 terraform=MISSING
DOCKER_COMPOSE_CONFIG exit=0 warnings=POSTGRES_PASSWORD,KEYCLOAK_ADMIN_PASSWORD,WHATSAPP_WEBHOOK_SECRET,IDENTITY_HMAC_KEY,WHATSAPP_TENANT_TOKEN_KEY,BP_SERVICE_JWT_SECRET default blank
PYTEST_COLLECT command=python -m pytest --collect-only -q tests collected=1701 exit=2 errors=ModuleNotFoundError:grpc;KeyError:WC012-01
```
