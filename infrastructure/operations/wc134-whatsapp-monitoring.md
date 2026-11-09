# WC-134 bounded operational monitoring

This repository-owned plan is disabled by absence: `whatsapp_monitoring = null`
creates no alert resource and leaves the existing receiver unchanged. It is not
authorization for cloud apply, traffic, provider access or incremental spend.

## Reviewed deployment tuple

The optional Demo workload input has closed fields:
`workspace_id`, `action_group_id`, `approval_reference`, `query_digest`,
`activation_digest`, `release_digest`, `configuration_digest`, `starts_at`, `expires_at`.
The existing action group and canonical foundation workspace must be in the same
Demo subscription/resource group. Release must match the BP release manifest.
Activation digest is the SHA-256 hexadecimal digest of the exact protected
activation reference, not a sender identifier. Runtime configuration digest is
the protected activation configuration digest. Query digest is `sha256:` plus the
SHA-256 digest of [the query](./wc134-whatsapp-monitor.kql). UTC timestamps use
`YYYY-MM-DDTHH:MM:SSZ`, must match the approved active window, and must fit within
the active workload lease. Input preparation rejects attempts to widen that lease.

The Founder must review the **whole** tuple, expected cost of the actual rule,
log ingestion/export and receiver, and response owner. The earlier estimate for
one rule does not approve this plan or account for ingestion, tax or other rules.
Do not set this input merely because its syntax is accepted. Missing canonical
foundation workspace output fails rule deployment; publish that output through
the normal approved foundation path first.

## Signal contract and missing-signal detection

After a successful current-authority tenant-scoped evaluation, BP emits
`WC134_OBSERVATION=` followed by a closed JSON record: schema version, environment,
activation/release/configuration digests, observation time, kind and optional code.
It contains no customer text, sender, token, endpoint, conversation or tenant ID.
The authority is checked again after evaluation, including environment identity.
Database failures, inactive capability or changed authority emit no success
heartbeat. This record acknowledges evaluation only, never receiver delivery.

One one-minute scheduled-query rule, with a five-minute query window and no
dimensions, forwards any evaluated breach or missing heartbeat to the existing
action group. It accepts only the exact BP app and candidate tuple. Fresh
observations must have been produced in the last two minutes within the approved
activation window; delayed old logs and old replicas cannot keep the rule healthy.
Missing heartbeat begins after a two-minute startup grace (four expected worker
intervals). Rule evaluation adds up to one minute; actual Azure ingestion and
delivery latency must be measured against the accepted five-minute response
deadline. No conclusions are drawn outside the approved window.

Both resource-specific and legacy console table names are supported. Empty logs
in an existing table produce a missing-heartbeat result. If neither table exists,
the query cannot execute: Azure rule-health/query-error evidence is required and
readiness fails, rather than treating that failure as successful monitoring.

## Receiver acknowledgement, escalation and readiness

These remain separate operator evidence, not inferred from an Azure action
`Succeeded` status:

1. Verify the exact candidate, receiver, enabled rule/query digest, foundation
   workspace and approved window privately after the separately authorized apply.
2. Demonstrate a current payload-free operational breach and loss of evaluator
   heartbeat, including a stale/different candidate that must not satisfy it.
   Record rule fire time, action status, actual receiver receipt, acknowledgement
   time and the accountable operator using protected evidence references only.
3. Operator acknowledges and takes the accepted action within five minutes of
   the breach, not five minutes after reading an email. Critical signals require
   the already authorized Stop/fencing procedure; this query does not itself Stop.
4. Missing receipt, absent owner or overdue acknowledgement is a readiness
   blocker. Escalate to the Founder through the agreed operational channel and
   use the approved Stop procedure; do not silently clear/retry UNKNOWN sends.
5. Rule auto-mitigation only resolves the Azure incident when the query clears.
   It is not customer incident resolution, human acknowledgement or proof of
   recovery. Rule health, receiver failure and push delivery still require
   separate verified evidence and an accepted escalation route.

Cross-tenant monitoring, actual receiver delivery, automatic acknowledgement
tracking/escalation, and restore-egress signal production are not established by
this bounded wiring. R010 remains BLOCKED until those scoped requirements and
Docker qualification pass. No cloud action or live alert test was performed.
