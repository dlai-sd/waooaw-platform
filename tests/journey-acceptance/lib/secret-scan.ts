// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §4 Run Lifecycle step 10
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { readdirSync, readFileSync, rmSync } from "node:fs";
import { join, relative } from "node:path";
import { SECRET_PATTERNS, scanText } from "./guards.ts";
import type { SecretPattern } from "./guards.ts";

export interface LeakFinding {
  path: string;
  kind: string;
}

const MAX_SCANNED_BYTES = 20 * 1024 * 1024;

function walk(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = join(directory, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

/** Scans every file that would be uploaded. A finding carries the path and pattern kind only, never the value. */
export function scanArtifacts(
  directory: string,
  extraPatterns: SecretPattern[] = [],
  literals: string[] = [],
): LeakFinding[] {
  const findings: LeakFinding[] = [];
  const patterns = [...SECRET_PATTERNS, ...extraPatterns];
  const secrets = literals.filter((literal) => literal.length >= 8);
  for (const file of walk(directory)) {
    const content = readFileSync(file);
    if (content.length > MAX_SCANNED_BYTES) {
      findings.push({ path: relative(directory, file), kind: "unscannable-oversized-file" });
      continue;
    }
    const text = content.toString("latin1");
    const path = relative(directory, file);
    for (const kind of scanText(text, patterns)) {
      findings.push({ path, kind });
    }
    if (secrets.some((secret) => text.includes(secret))) {
      findings.push({ path, kind: "run-secret-literal" });
    }
  }
  return findings;
}

/** A leak withholds the artifact: everything is removed and only the path and kind of each finding remain. */
export function withholdArtifacts(directory: string, keep: string[] = []): void {
  for (const entry of readdirSync(directory)) {
    if (!keep.includes(entry)) {
      rmSync(join(directory, entry), { recursive: true, force: true });
    }
  }
}
