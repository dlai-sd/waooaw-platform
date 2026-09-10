// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-04
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

const allowedTargets = /^\/(home|profile|settings|professionals\/mine|relationships\/[0-9a-f-]+)(?:[?#].*)?$/i;

export function safeReturnTarget(value: string | string[] | undefined, fallback = '/home'): string {
  if (typeof value !== 'string' || !allowedTargets.test(value)) return fallback;
  return value;
}

export function safePublicReturnTarget(value: string | undefined): string {
  if (!value || /[\\%\s]/.test(value)) return '/';
  const publicPath = /^\/(?:professionals(?:\/(?!mine(?:[/?#]|$))[a-z0-9-]+)?|blogs(?:\/[a-z0-9-]+)?|about|contact|careers|press|constitution|privacy|terms|cookies|refund|grievance)?$/;
  const [path, fragment] = value.split('#');
  if (!publicPath.test(path)) return '/';
  return fragment && /^[a-zA-Z][a-zA-Z0-9_-]{0,99}$/.test(fragment) ? `${path}#${fragment}` : path;
}