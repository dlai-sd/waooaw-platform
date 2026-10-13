# WC-120 Security Architect Disposition

## Record

| Field | Value |
|---|---|
| Work Contract | WC-120 |
| Reviewing office | Security Architect (INST-007) |
| Review mode | Founder-requested single-pass specialist review and owner-bounded repair |
| Reviewed package | WC-120 contract, requirements ledger, fitness evidence matrix, product acceptance matrix, and PR body |
| Controlling security inputs | ADR-023; Conversation Core blob `1004255bbd01e3d10dd53a64a2b115ac059ad631`; WC-114 blob `11ba639efa43d3288ba1eb39fd2e05308c42e6c0`; WC-115 blob `337fcef0a51a4c2ef2ff72423a7afc64969d8914`; accepted specialist profile blob `9c7ccecd64791010f1ba15b69d9b8a128d466d66`; PR #498 reviewed head `65add4540698116b00be1ec72e6000333d05eac9`; PR #499 merged package `c2a1baf64cb3b2652ce29ed930ac4a60f14e73bb` |
| Disposition | **PASS** |
| Implementation state | **BLOCKED** by WC-120's existing implementation gates and the stops below; this disposition is not implementation, deployment, provider, cloud, traffic, activation, Production, approval, or merge authority |

## Accepted Profile References

- Employment service-to-service calls: accepted profile
  `security_profile.workload_identity`, `security_profile.assurance`,
  `security_profile.denial`, `freshness_profile`, and `emergency_stop_profile` at blob
  `9c7ccecd64791010f1ba15b69d9b8a128d466d66`.
- WhatsApp phone identity and operation assurance: ADR-023 as constrained by PR #498
  §§12.7/14.2 and the non-lowering Tier 1-4 floors in PR #499 §7.
- WhatsApp runtime, media-scanner, and configurator workload authority: PR #498 §13.6,
  including audience `urn:waooaw:service:whatsapp-adapter:<environment>`.
- Webhook, media, Stop, and telemetry: PR #498 §§12.1, 12.5, 12.8, 14.2-14.3 and
  PR #499 §§10.1, 10.3, 12-14.

The employment profile and WhatsApp workload profile apply to different calls. Substituting
one for the other, broadening an audience, or introducing a catch-all credential is prohibited.

## Findings And Repairs

| Finding ID | WC120-R mapping | Finding | Exact owner-controlled repair | Result |
|---|---|---|---|---|
| WC120-SEC-001 | R009, R010, R024, R044; CE-FIT-09 | The ledger named raw-byte authentication and replay but did not bind pre-decompression/pre-middleware ordering, constant-time checks, the inclusive ADR-023 boundary, or the already-claimed delayed-retry exception. | Added WC-120 §2.4; expanded R009/R010 and CE-FIT-09 to require bounded exact bytes, approved HMAC form, fail-before-parse/owner-call, host/app/WABA/recipient/environment binding, unseen-event freshness, compound identity/digest conflict, and durable delayed-retry replay with zero additional mutation. | RESOLVED |
| WC120-SEC-002 | R008, R038 | Phone identity and assurance were compressed into a general fail-closed statement, leaving relationship attachment and Tier 1-4 invalidation predicates indirect. | Bound R008 and §2.4 to ADR-023 plus PR #498 §12.7: phone possession cannot attach an existing relationship; first contact, membership, reassignment/revocation, exact intent, stronger-factor, portal-only, commit freshness, and non-enumerating zero-mutation cases are explicit. | RESOLVED |
| WC120-SEC-003 | R012, R018-R020, R026, R038; CE-FIT-12 | The contract did not distinguish accepted WC-115 employment-call tuples from WhatsApp-specific workload identities/audiences or state exact rotation, emergency revocation, and rollback rules. | Added the profile-separation rule, pinned accepted profile blob, exact WhatsApp adapter audience, bounded current/immediately-previous overlap, no fallback, in-flight reconciliation, unavailable live-revocation denial, and prohibition on restoring revoked authority to §2.4, R038, and CE-FIT-12. | RESOLVED |
| WC120-SEC-004 | R015, R024, R042, R044; CE-FIT-11 | Media safety lacked direct predicates for active/parser-capable content, individual expansion/resource controls, isolated scanner identity, unknown verdict, and zero canonical contribution. | Expanded §2.4, R015, and CE-FIT-11 to require quarantine, signature/type sniffing, bounded expanded size/ratio/page/frame/duration/CPU/memory/recursion/time, isolated clean verdict, immutable lineage, fail-safe unknown/error/timeout, and zero contribution before acceptance. | RESOLVED |
| WC120-SEC-005 | R016, R024, R042, R044; CE-FIT-13 | Stop resilience was present but its exact precedence and release-denial paths were not complete in the WC-120 ledger/oracle. | Bound typed Stop after signature/binding but before context/model/queue/billing/outbound work; added CE/identity outage, duplicate, simultaneous-channel, restart, reconnect, late-result, WhatsApp/operator release-denial, accepted routes, independence, and latency predicates. | RESOLVED |
| WC120-SEC-006 | R008-R010, R015-R017, R038; CE-FIT-09/11/12/14 | Privacy-safe telemetry and zero-mutation denial were not uniformly asserted across framework, scanner, workload, media, and identity failures. | Added a closed non-enumerating denial invariant: no downstream owner call; zero relationship/binding/command/conversation/dispatch/payload-promotion/authority mutation; and automated absence checks covering headers, signatures, proofs, identifiers, refs, prompts, transcripts, metadata, template/context facts, secrets, baggage, exceptions, request capture, dead letters, scanner failures, sampling, and high-cardinality labels. | RESOLVED |
| WC120-SEC-007 | R009, R010, R015-R017, R038; CE-FIT-09/11-14; PRODUCT-03 | Security-owned ceilings and floors remained deferred despite INST-007 authority, and the Platform Stop target was weaker than the accepted emergency-stop profile. | Added §2.4.1 and direct ledger/oracle mappings: 1 MiB identity-encoded raw webhook and bounded GET; inclusive five-minute freshness with payload-free replay floor subordinate to the accepted longer Data horizon; five-minute JIT memory authority, fifteen-minute planned overlap and zero emergency overlap; exact media types/resource/scanner ceilings; closed telemetry dimensions/reasons; and 50 ms PR / 250 ms p99 Stop targets with a one-second hard ceiling. Product's accepted voice subset is now bound to this security profile. | RESOLVED |

## Exact External Dependencies

1. **Implementation office and Test Champion:** exact-candidate tests do not yet exist by design.
   During the separately authorized implementation phase they must prove every R008-R010,
   R015-R017, and R038 positive,
   negative, race, outage, rollback, and telemetry predicate with both state and call-spy evidence.
2. **Data Architect with Legal/Founder where protected:** media/transcript/diagnostic lifecycle,
   erasure, hold, and backup expiry remain externally owned. WC-120's accepted 30-day terminal
   replay tombstone controls this candidate and exceeds the seven-day Security floor.
3. **Provider/Platform/Founder:** provider account topology, confirmation that planned
   current/immediately-previous credential overlap is supported, and every cloud, DNS, deployment,
   traffic, Production, and activation action remain separately owned. Unsupported overlap means
   zero overlap; it never permits fallback.

## Required Security Stops

1. Stop if the employment accepted profile and WhatsApp workload profile are conflated, their
   pinned sources change without owner acceptance, or any caller/audience/purpose/operation/
   environment tuple is inferred.
2. Stop if revocation cannot terminate new dispatch/retrieval without fallback, if rollback can
   reactivate revoked authority, or if live revocation unavailability permits work.
3. Stop if typed Stop is delayed until context/model interpretation, depends on CE for local
   halt, can be released through WhatsApp or ordinary operations, or misses accepted route/SLO
   evidence.
4. Stop if unsafe/unproven media can leave quarantine, if telemetry leakage is non-zero, or if
   any denial mutates protected state, calls a downstream owner, or reveals identity cardinality.
5. Retain all existing WC-120 authorization, Product, Data, Platform, Test Champion,
   compatibility, provider/environment, and exact-candidate stops.

## Disposition

**PASS** for the reviewed WC-120 security specification after the repairs above. All INST-007-owned
values, controls, oracles, and targets identified in this pass are closed.

- **CHANGES_REQUIRED:** no, for the Security Architect specification scope.
- **BLOCKED:** only the named Data/Legal/Founder, Provider/Platform/Founder, and
  pre-implementation exact-candidate test dependencies above. Runtime implementation and
  provider/cloud/deployment/traffic/Production activation remain blocked until their applicable
  gates and separate authority pass.

No secret, provider, cloud, deployment, traffic, runtime-state, or infrastructure mutation was
performed.
