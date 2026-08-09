// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-04
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

const allowedTargets = /^\/(home|profile|settings|professionals\/mine|relationships\/[0-9a-f-]+)(?:[?#].*)?$/i;

export function safeReturnTarget(value: string | string[] | undefined, fallback = '/home'): string {
  if (typeof value !== 'string' || !allowedTargets.test(value)) return fallback;
  return value;
}