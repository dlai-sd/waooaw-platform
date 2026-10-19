---
name: secrets-runtime-configuration-engineering
description: "Use when: creating, rotating, reconciling, or diagnosing Azure Key Vault secrets, managed identities, secret versions, placeholders, and Container Apps secret consumption."
---

# Secrets and Runtime Configuration Engineering

## Required method

1. Inventory the logical secret, vault name, format, owner role, consumer identity, and current version.
2. Validate authorization independently for producer writes and consumer reads.
3. Preserve credentials when repairing routing or serialization; never rotate a password as a side effect.
4. Reject unresolved placeholders, missing secrets, incompatible metadata, disabled versions, and mixed grant digests.
5. Record the resulting secret version and force consumers to resolve that version before qualification.
6. Inspect only sanitized fields such as version, scheme, host, port, and status; never emit secret values.

## Evidence

- Secret metadata and version inventory
- Write status: created, updated, or preserved
- Consumer identity and exact secret reference
- Runtime proof that the consumer resolved the expected version

## Stop conditions

Stop on missing or disabled secrets, ambiguous ownership, permission mismatch, unintended password rotation,
or any inability to prove that the consumer loaded the updated configuration.
