# WC-085 Baseline

Status: PARTIAL baseline, not deployment acceptance. Office: INST-010.

- Authorized work: current-session Founder approval of WC-085 plus reproducible Demo Google configuration; Docker only, no virtual environments, no custom importer, no persistent identity database, no self-merge.
- Implementation base: `79ec8065ad448cb418551034366091693b7b316c`, main after PR #408.
- Code freeze: `14a28c18aa8774d8b2f956c475e2e60a245f4ddd`; later evidence-only commits do not change the tested code. The PR records its exact pushed HEAD separately.
- Original dirty worktree `/workspaces/waooaw-platform` was not modified by this implementation. Work was isolated in `/workspaces/waooaw-wc085`, branch `ib/085/remediation`.
- Reported auth defects: excessive initial dialog height, global loading ownership, and history-depth-dependent dismissal after switching login/register.
- Reported public Chrome distortion has not been deterministically reproduced; no public layout repair is claimed.
- Pre-existing Demo identity origin: `https://ca-demo-identity-edge.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io`.
- Earlier session operations enabled Google on the live Demo broker and observed a redirect. This is historical, not qualification of this code freeze. No real-account journey was proved.
- Google client ID and secret were previously stored as `google-client-id` and `google-client-secret` in `kv-waooaw-demo`. Values and versions were not read for this implementation.
- The checked-in identity Demo manifest still disables Google and uses planned custom domains/client IDs. Terraform's existing deployed realm uses ACA origins and `waooaw-web`. Full reconciliation remains BLOCKED under SP-06.
- The exact-six deployed release/revision binding for this candidate is NOT_RUN. No deployment, cloud mutation, UAT or Production work occurred during this implementation milestone.

No baseline observation, prior PR test, local fixture, or successful redirect is promoted to final WC-085 acceptance.