// Implements: adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decisions 1, 2(c) and 5; architecture/reference/acceptance/customer-journey-acceptance-architecture.md §9 F13, F18
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import type { Provisioner } from "./keycloak.ts";
import type { Finding } from "./types.ts";

export interface CleanupResult {
  removed: string[];
  leftOver: string[];
  findings: Finding[];
}

/**
 * Removes every synthetic Keycloak user, proves none remain, and audits the provisioning client's admin events:
 * a user touched that this run does not own, or a user left behind, is a finding and fails the run.
 */
export async function cleanupSyntheticUsers(
  provisioner: Pick<Provisioner, "removeAllSynthetic" | "listSyntheticUsers" | "outsideTouches">,
  ownedIds: string[],
  sinceIso: string,
): Promise<CleanupResult> {
  const removed = await provisioner.removeAllSynthetic();
  const leftOver = (await provisioner.listSyntheticUsers()).map((user) => user.id);
  const outside = await provisioner.outsideTouches(sinceIso, [...ownedIds, ...removed]);
  const findings: Finding[] = [
    ...leftOver.map((id) => ({ guard: "synthetic_cleanup", where: "keycloak", detail: `synthetic user ${id.slice(0, 8)}… remains after cleanup` })),
    ...outside.map((id) => ({
      guard: "provisioner_containment",
      where: "keycloak admin events",
      detail: `the provisioning client changed user ${id.slice(0, 8)}…, which is outside this run's synthetic users`,
    })),
  ];
  return { removed, leftOver, findings };
}
