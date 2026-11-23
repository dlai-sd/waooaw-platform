// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 Identity, Secrets And Authority (Output)
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const LITERALS = "literals.json";

/** Run-generated secrets live only in a private directory outside the uploaded artifact, so the pre-upload scan can search for them. */
export function registerLiteral(privateDir: string, value: string): void {
  mkdirSync(privateDir, { recursive: true });
  const path = join(privateDir, LITERALS);
  const known = readLiterals(privateDir);
  writeFileSync(path, JSON.stringify([...known, value]));
  chmodSync(path, 0o600);
}

export function readLiterals(privateDir: string): string[] {
  const path = join(privateDir, LITERALS);
  return existsSync(path) ? (JSON.parse(readFileSync(path, "utf8")) as string[]) : [];
}
