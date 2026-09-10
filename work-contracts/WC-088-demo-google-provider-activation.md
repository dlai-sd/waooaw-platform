# WC-088 - Demo Google Provider Activation

**Office:** Platform IT Expert (INST-010)
**Status:** READY FOR FOUNDER REVIEW
**Authorized by:** Founder instruction in the current session, 2026-09-10
**Scope:** Demo identity manifest only; immutable application images remain unchanged

## Evidence Reference

`WC-088-DEMO-GOOGLE-ACTIVATION-AUTHORIZED-2026-09-10`

The Founder authorized enabling the existing Demo Google broker configuration.
The manifest uses the deployment-time Key Vault reference
`kv://kv-waooaw-demo/secrets/bp-identity-reader-client-secret`; no secret value
is recorded here. The approved broker alias is `google` and scopes are exactly
`openid`, `profile`, and `email`.

This record proves current-session authorization and configuration intent. It
does not claim real Google user acceptance, UAT/Production activation, or final
customer readiness. Those remain separate Founder-controlled gates.

## Validation

- Docker-local identity manifest regression passes.
- Facebook, Apple, and Email remain disabled.
- No image rebuild or environment value is baked into an image.
- Deployment, if separately authorized, uses the existing `deploy.yaml` path.