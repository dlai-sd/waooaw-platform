// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §7 W2 Platform
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

/** Finds the first value stored under any of the given keys, at any depth. A missing field means the route did not expose it. */
export function pick(json: unknown, keys: string[]): unknown {
  const wanted = new Set(keys.map((key) => key.toLowerCase()));
  const queue: unknown[] = [json];
  while (queue.length > 0) {
    const current = queue.shift();
    if (Array.isArray(current)) {
      queue.push(...current);
    } else if (current !== null && typeof current === "object") {
      for (const [key, value] of Object.entries(current as Record<string, unknown>)) {
        if (wanted.has(key.toLowerCase()) && value !== null && typeof value !== "object") {
          return value;
        }
        queue.push(value);
      }
    }
  }
  return undefined;
}

const IDENTIFIER = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;

/** Every UUID in a payload, used to learn customer B's identifiers from B's own session (ADR-054 S8). */
export function collectIdentifiers(payload: unknown): string[] {
  const text = typeof payload === "string" ? payload : JSON.stringify(payload ?? "");
  return [...new Set((text.match(IDENTIFIER) ?? []).map((value) => value.toLowerCase()))];
}

export function relationshipIdFromUrl(url: string): string | undefined {
  const match = /\/relationships\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i.exec(url);
  return match?.[1].toLowerCase();
}
