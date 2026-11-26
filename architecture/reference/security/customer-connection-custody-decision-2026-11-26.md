# Customer connection custody decision (Agent Operation, AO-M1)

**Status:** Recorded 2026-11-26 under Founder decision FD7 of WC-174. It grants no deployment, provider, spend or
Production authority. It is an experiment: review it after AO-M1 and decide to keep or move.

## Decision

WAOOAW owns the permission a customer grants when they tap Connect. No agent owns it, sees it or stores it.

For AO-M1 the key stays where WC-149 built it: written to the environment Key Vault under
`customer-connection-{id}` and read only at publish time inside the Business Platform. Every caller, including every
agent, reaches it through **one connection interface** (`ICustomerConnectionInterface`). The interface returns facts
(connector, status, account name) and results (a provider post id). It has no member that returns a key.

## Why this differs from ADR-021 and the publication contract

ADR-021 and invariant 5 of the DMA publication contract say a token vault (oauth-vault) owns customer tokens and keys
never enter the Business Platform. WC-149 already shipped the other design, and the Founder chose to keep it for the
first milestone to learn from it ("lets keep this as an experiement and see how it goes").

## Exit path

If the experiment is stopped, only the custody behind the interface changes: the vault implements the same two
operations (`ListAsync`, `PublishAsync`) and nothing an agent or the web calls is touched. This is proved by a test
that swaps a fake custody behind the interface and finds the interface and the agent-facing calls unchanged.

## Reconciliation

- Document to reconcile after the experiment: invariant 5 of
  [dma-content-and-social-publication-solution-contract.md](../components/dma-content-and-social-publication-solution-contract.md).
- Review owner: the Enterprise Architect, with the Founder deciding.
- Evidence the experiment is safe: secret-absence scans of images, prompts, logs and evidence; the connection interface
  contract test; the WC-149 custody tests.
