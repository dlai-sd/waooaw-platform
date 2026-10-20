---
name: iac-configuration-lifecycle-engineering
description: "Use when: Terraform or Azure Resource Manager reports convergence while runtime configuration, secret consumption, dependency propagation, or deployed resource behavior may still be stale."
---

# Infrastructure-as-Code and Configuration Lifecycle Engineering

## Required method

1. Identify the producer value, its immutable identity or version, and every consuming resource.
2. Inspect Terraform state, plan, provider schema, and dependency edges separately.
3. Prove whether a producer change creates a consumer diff; a successful write is not propagation evidence.
4. Bind mutable external values to an explicit version or deterministic change marker where immediate consumption is required.
5. Apply dormant dependencies before migrations and activate applications only after runtime qualification.
6. Read back the deployed resource and compare it with the reviewed plan and expected version.

## Evidence

- Producer version and consumer resource identity
- Terraform plan showing the required consumer update
- Post-apply readback from Azure
- Drift classification when state and runtime disagree

## Stop conditions

Stop if Terraform has a no-op plan while a required runtime value changed, if the dependency graph is
implicit, or if a provider refresh interval is being treated as immediate propagation.
