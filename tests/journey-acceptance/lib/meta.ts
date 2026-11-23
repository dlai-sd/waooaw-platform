// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §7 W3 Provider (Meta Graph, test user)
// Constitutional basis: C-059 (Implementation Traceability), C-023 (Evidence First)
import type { FetchLike } from "./razorpay.ts";

export class MetaModeError extends Error {}

const GRAPH = "https://graph.facebook.com/v21.0";

async function graph<T>(fetchImpl: FetchLike, path: string, token: string): Promise<T> {
  const separator = path.includes("?") ? "&" : "?";
  const response = await fetchImpl(`${GRAPH}${path}${separator}access_token=${encodeURIComponent(token)}`);
  if (!response.ok) {
    throw new MetaModeError(`Meta Graph answered HTTP ${response.status} for ${path.split("?")[0]}`);
  }
  return JSON.parse(await response.text()) as T;
}

/**
 * A development-mode app only serves its own roles and test users, so the signed-in user being a registered test
 * user of the app proves the run stays inside the sandbox; any other user stops the run (AD-006).
 */
export async function assertTestUser(
  fetchImpl: FetchLike,
  app: { id: string; secret: string },
  userId: string,
): Promise<void> {
  const appToken = `${app.id}|${app.secret}`;
  const users = await graph<{ data?: { id: string }[] }>(fetchImpl, `/${app.id}/accounts/test-users?limit=200`, appToken);
  if (!(users.data ?? []).some((user) => user.id === userId)) {
    throw new MetaModeError("the Meta user is not a test user of the development app; refusing to continue");
  }
}

export interface GrantedPermissions {
  granted: string[];
  declined: string[];
}

/** Reads which permissions the test user has granted to the app, straight from Graph (W3). */
export async function readGrantedPermissions(
  fetchImpl: FetchLike,
  app: { id: string; secret: string },
  userId: string,
): Promise<GrantedPermissions> {
  const body = await graph<{ data?: { permission: string; status: string }[] }>(
    fetchImpl,
    `/${userId}/permissions`,
    `${app.id}|${app.secret}`,
  );
  const items = body.data ?? [];
  return {
    granted: items.filter((item) => item.status === "granted").map((item) => item.permission).sort(),
    declined: items.filter((item) => item.status !== "granted").map((item) => item.permission).sort(),
  };
}
