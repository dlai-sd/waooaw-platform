// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-04
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

const allowedPath = /^\/(home|profile|settings|professionals\/mine|relationships\/[0-9a-f-]+)$/i;
const marketplaceParameters = new Set(['professionalType', 'version', 'intent']);

export function safeReturnTarget(value: string | string[] | undefined, fallback = '/home'): string {
  if (typeof value !== 'string') return fallback;
  try {
    const target = new URL(value, 'https://return.waooaw.invalid');
    if (target.origin !== 'https://return.waooaw.invalid' || target.hash) return fallback;
    if (allowedPath.test(target.pathname) && !target.search) return value;
    if (target.pathname !== '/marketplace') return fallback;
    if ([...target.searchParams.keys()].some((key) => !marketplaceParameters.has(key))) return fallback;
    if (target.searchParams.getAll('professionalType').length > 1
      || target.searchParams.getAll('version').length > 1
      || target.searchParams.getAll('intent').length > 1) return fallback;
    const professionalType = target.searchParams.get('professionalType');
    const version = target.searchParams.get('version');
    const intent = target.searchParams.get('intent');
    if (professionalType !== null && !/^[A-Z][A-Z0-9_]{0,63}$/.test(professionalType)) return fallback;
    if (version !== null && !/^[0-9]+\.[0-9]+\.[0-9]+$/.test(version)) return fallback;
    if (intent !== null && intent !== 'trial' && intent !== 'hire') return fallback;
    return value;
  } catch {
    return fallback;
  }
}

export function safePublicReturnTarget(value: string | undefined): string {
  if (!value || /[\\%\s]/.test(value)) return '/';
  const publicPath = /^\/(?:professionals(?:\/(?!mine(?:[/?#]|$))[a-z0-9-]+)?|blogs(?:\/[a-z0-9-]+)?|about|contact|careers|press|constitution|privacy|terms|cookies|refund|grievance)?$/;
  const [path, fragment] = value.split('#');
  if (!publicPath.test(path)) return '/';
  return fragment && /^[a-zA-Z][a-zA-Z0-9_-]{0,99}$/.test(fragment) ? `${path}#${fragment}` : path;
}