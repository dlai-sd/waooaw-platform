# WC-034 F4 Relationship Workspace CE Contract Coverage

## Attestation

| Field | Value |
|---|---|
| institution_id | INST-005 |
| goal_id | GOAL-005 |
| record_id | CR-GOAL-005-INST-005-12-CE-COVERAGE |
| record_type | Coverage Mapping |
| produced_at | 2026-08-11T02:26:15+00:00 |
| scope | Map F4 selected-policy consequence families to existing CE gRPC RPCs only |
| boundary | No constitutional_service.proto change in this record |

## Policy Tuple

Selected Founder policy tuple is fixed and preserved exactly: A,A,B,A,B,A.

| Policy | Selected | Consequence family |
|---|---|---|
| F4-POL-01 | A | Typed acknowledgement for material classes |
| F4-POL-02 | A | Evidence export self-service within approved sensitivity/recipient boundaries |
| F4-POL-03 | B | Read-only/non-consequential continuation with consequential pause at thresholds |
| F4-POL-04 | A | Self-service authority reduction only |
| F4-POL-05 | B | Selected pause/resume paths enabled; renewal/termination remain fail-closed where unresolved |
| F4-POL-06 | A | Read-only under stale/unknown/partial/unavailable/unresolved owner state |

## CE RPC Mapping

| F4 command or consequence | Existing CE RPC(s) | Coverage result |
|---|---|---|
| Material approval or rejection requiring constitutional check and evidence | ValidateAction, RecordEvidence | COVERED |
| Distinct scope-boundary confirmation (typed acknowledgement retained) | ValidateAction, RecordEvidence | COVERED |
| Evidence export authorization and evidence-state transitions | EvaluatePolicy, RecordEvidence | COVERED |
| Threshold/ceiling consequential pause path (policy B) | EvaluatePolicy, ValidateAction, RecordEvidence | COVERED |
| Authority reduction/self-service constrain or revoke (policy A) | RevokeAuthorityLicense, RecordEvidence | COVERED |
| Authority grant or restore paths when explicitly allowed by future policy | GrantAuthorityLicense, RecordEvidence | COVERED (future path, still policy-gated) |
| Lifecycle pause/resume commands with constitutional evidence ordering | ValidateAction, RecordEvidence | COVERED |
| Emergency Stop independence from workspace command paths | TriggerEmergencyStop | COVERED |
| Unknown/partial reconciliation does not claim success before evidence | RecordEvidence | COVERED |

## Coverage Notes

1. Service authentication and workload identity controls are handled by ADR-046 route architecture and are intentionally not delegated to CE.
2. CE remains the constitutional authorization and evidence authority; no BP/PR/WBE/domain adapter private route may replace CE evidence semantics.
3. No new CE RPC is required for Order 3 canonical contract publication.
4. No change to constitutional_service.proto is authorized or required by this mapping.

## Blockers

No CE-contract blocker is raised in this Order 3 publication slice.

