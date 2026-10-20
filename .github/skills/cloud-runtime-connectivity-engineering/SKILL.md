---
name: cloud-runtime-connectivity-engineering
description: "Use when: diagnosing Azure Container Apps DNS, TCP, ingress, VNet, private endpoint, PgBouncer, PostgreSQL, or other runtime connectivity from the actual consumer context."
---

# Cloud Networking and Runtime Connectivity Engineering

## Required method

1. Run the probe from the exact consumer image, identity, Container Apps environment, and network boundary.
2. Extract only the effective scheme, host, and port from runtime configuration.
3. Test DNS resolution and TCP connection independently.
4. Compare the effective endpoint with the canonical endpoint in the same execution.
5. Classify the failure as configuration, DNS, routing, ingress, identity, TLS, or upstream service.
6. Preserve execution, replica, image digest, addresses, timing, and sanitized results.

## Evidence

- ACA job execution and replica
- Effective and expected endpoint metadata
- DNS result for each endpoint
- TCP or TLS result from the consumer context

## Stop conditions

Stop speculative diagnosis when an in-context probe is possible. Do not treat successful DNS as TCP
reachability or a control-plane resource state as data-plane connectivity.
