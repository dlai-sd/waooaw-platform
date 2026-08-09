// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-03
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import type { Session } from 'next-auth';
import { hasFounderClaim, projectSession } from './auth';

describe('Founder claim parsing', () => {
  it('accepts only an explicit Founder claim or realm role', () => {
    expect(hasFounderClaim({ founder: true })).toBe(true);
    expect(hasFounderClaim({ realm_access: { roles: ['customer', 'founder'] } })).toBe(true);
    expect(hasFounderClaim({ founder: false, realm_access: { roles: ['customer'] } })).toBe(false);
    expect(hasFounderClaim({ founder: 'true' })).toBe(false);
    expect(hasFounderClaim(undefined)).toBe(false);
  });
});

describe('Browser session projection', () => {
  it('reports authentication without exposing the Keycloak bearer token', () => {
    const session = projectSession({ expires: '2099-01-01', user: {} } as Session, { accessToken: 'secret-bearer-token', founder: false });
    expect(session.authenticated).toBe(true);
    expect(session).not.toHaveProperty('accessToken');
    expect(JSON.stringify(session)).not.toContain('secret-bearer-token');
  });
});