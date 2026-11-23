// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §7 Oracle Read Contract
// Constitutional basis: C-059 (Implementation Traceability)
import type { ClaimDefinition, ClaimResult, WitnessId, WitnessReading } from "./types.ts";
import { WITNESSES } from "./types.ts";

export class ClaimDefinitionError extends Error {}

/** A state claim needs two independent witnesses unless a listed exception carries a reason (ADR-054 item 4). */
export function defineClaim(definition: ClaimDefinition): ClaimDefinition {
  const required = [...new Set(definition.witnessesRequired)];
  for (const witness of required) {
    if (!WITNESSES.includes(witness)) {
      throw new ClaimDefinitionError(`claim ${definition.id}: unknown witness ${String(witness)}`);
    }
  }
  const reason = definition.exception?.reason.trim() ?? "";
  if (required.length < 2 && reason === "") {
    throw new ClaimDefinitionError(
      `claim ${definition.id}: needs at least two witnesses or a listed exception with a reason`,
    );
  }
  return { ...definition, witnessesRequired: required };
}

/** Builds a reading by comparing what the witness saw with what the claim expects. */
export function reading(witness: WitnessId, expected: unknown, actual: unknown, detail = ""): WitnessReading {
  return { witness, readable: true, holds: stable(expected) === stable(actual), detail };
}

export function unreadable(witness: WitnessId, detail: string): WitnessReading {
  return { witness, readable: false, detail };
}

function stable(value: unknown): string {
  if (Array.isArray(value)) {
    return JSON.stringify(value.map((item) => JSON.parse(stable(item))));
  }
  if (value !== null && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => [key, JSON.parse(stable(item))]);
    return JSON.stringify(Object.fromEntries(entries));
  }
  return JSON.stringify(value ?? null);
}

/**
 * A disagreeing witness fails the claim. A required witness that cannot be read is NOT-WITNESSED and is never a pass.
 * A witness that is not required for this claim is not applicable and cannot change the verdict.
 */
export function evaluateClaim(definition: ClaimDefinition, readings: WitnessReading[]): ClaimResult {
  const required = defineClaim(definition).witnessesRequired;
  const byWitness = new Map<WitnessId, WitnessReading>();
  for (const item of readings) {
    byWitness.set(item.witness, item);
  }
  const disagreeing: string[] = [];
  const missing: string[] = [];
  const witnessesRead: WitnessId[] = [];
  for (const witness of required) {
    const item = byWitness.get(witness);
    if (item === undefined || !item.readable) {
      missing.push(`${witness}${item?.detail ? ` (${item.detail})` : ""}`);
      continue;
    }
    witnessesRead.push(witness);
    if (item.holds !== true) {
      disagreeing.push(`${witness}${item.detail ? ` (${item.detail})` : ""}`);
    }
  }
  if (disagreeing.length > 0) {
    return {
      claimId: definition.id,
      verdict: "FAIL",
      witnessesRead,
      reason: `witness disagrees with the claim: ${disagreeing.join(", ")}`,
    };
  }
  if (missing.length > 0) {
    return {
      claimId: definition.id,
      verdict: "NOT-WITNESSED",
      witnessesRead,
      reason: `required witness not read: ${missing.join(", ")}`,
    };
  }
  return { claimId: definition.id, verdict: "PASS", witnessesRead, reason: "all required witnesses agree" };
}
