// Implements: adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4 (marker registry route)
// Constitutional basis: C-059 (Implementation Traceability), C-065 (Separation of Duties)
import type { FetchLike } from "./razorpay.ts";

export class MarkerRefusal extends Error {}

async function send(
  fetchImpl: FetchLike,
  url: string,
  method: string,
  token: string,
  body?: unknown,
): Promise<number> {
  const response = await fetchImpl(url, {
    method,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return response.status;
}

/**
 * Registers a Keycloak subject as synthetic before its first login so the tenant it creates inherits the marker.
 * The marker only reduces side effects; it grants no authority and the caller's token carries the acceptance-provisioner role.
 */
export async function registerSyntheticSubject(
  fetchImpl: FetchLike,
  apiOrigin: string,
  token: string,
  runId: string,
  subject: string,
): Promise<void> {
  const status = await send(fetchImpl, `${apiOrigin}/internal/v1/acceptance/runs/${runId}/synthetic-subjects`, "POST", token, { subject });
  if (status !== 201 && status !== 204) {
    throw new MarkerRefusal(`the synthetic marker was not registered (HTTP ${status}); the run stops before any customer acts`);
  }
}

/** Declares the one sandbox recipient that messages from synthetic tenants may reach (E.164). */
export async function registerSandboxRecipient(
  fetchImpl: FetchLike,
  apiOrigin: string,
  token: string,
  runId: string,
  recipient: string,
): Promise<void> {
  const status = await send(fetchImpl, `${apiOrigin}/internal/v1/acceptance/runs/${runId}/sandbox-recipients`, "PUT", token, { recipient });
  if (status < 200 || status >= 300) {
    throw new MarkerRefusal(`the sandbox recipient was not registered (HTTP ${status})`);
  }
}

/** Ends the run's synthetic scope; the product keeps append-only evidence, labelled synthetic. */
export async function deactivateRun(fetchImpl: FetchLike, apiOrigin: string, token: string, runId: string): Promise<void> {
  const status = await send(fetchImpl, `${apiOrigin}/internal/v1/acceptance/runs/${runId}`, "DELETE", token);
  if (status < 200 || status >= 300) {
    throw new MarkerRefusal(`the run could not be deactivated (HTTP ${status})`);
  }
}
