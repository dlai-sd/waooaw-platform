// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063

export type PlatformRole = 'founder' | 'pricing_admin';

export type PlatformAccessRequest = {
  requestId: string;
  email: string;
  role: string;
  justification: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  requestedAt: string;
  decidedAt?: string | null;
  decidedBy?: string | null;
  decisionReason?: string | null;
};

export type PlatformGrant = {
  grantId: string;
  email: string;
  role: string;
  source: 'CONFIG' | 'APPROVAL';
  grantedBy: string;
  grantedAt: string;
  expiresAt?: string | null;
  revocable: boolean;
};

export type PlatformAccess = {
  administrator: boolean;
  founder: boolean;
  emailVerified: boolean;
  email: string | null;
  requestableRoles: string[];
  requests: PlatformAccessRequest[];
};

export const noPlatformAccess: PlatformAccess = {
  administrator: false,
  founder: false,
  emailVerified: false,
  email: null,
  requestableRoles: [],
  requests: [],
};

type AccessRoute = { method: 'GET' | 'POST'; pattern: RegExp };

// The browser may only reach these Business Platform routes; the Business Platform decides who may use them.
const accessRoutes: AccessRoute[] = [
  { method: 'GET', pattern: /^me\/roles$/ },
  { method: 'POST', pattern: /^access-requests$/ },
  { method: 'GET', pattern: /^access-requests$/ },
  { method: 'POST', pattern: /^access-requests\/[0-9a-f-]{36}\/decision$/i },
  { method: 'GET', pattern: /^grants$/ },
  { method: 'POST', pattern: /^grants\/[0-9a-f-]{36}\/revoke$/i },
];

export function platformAccessRouteAllowed(method: string, segments: readonly string[]): boolean {
  const path = segments.join('/');
  return accessRoutes.some((route) => route.method === method.toUpperCase() && route.pattern.test(path));
}

export function platformAccessFrom(payload: unknown): PlatformAccess {
  if (!payload || typeof payload !== 'object') return noPlatformAccess;
  const body = payload as Record<string, unknown>;
  const founder = body.founder === true;
  return {
    founder,
    administrator: founder || body.pricingAdmin === true,
    emailVerified: body.emailVerified === true,
    email: typeof body.email === 'string' ? body.email : null,
    requestableRoles: Array.isArray(body.requestableRoles)
      ? body.requestableRoles.filter((role): role is string => typeof role === 'string')
      : [],
    requests: Array.isArray(body.requests) ? (body.requests as PlatformAccessRequest[]) : [],
  };
}
