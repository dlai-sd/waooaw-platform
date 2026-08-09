// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-03
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { hasFounderClaim } from './auth';

describe('Founder claim parsing', () => {
  it('accepts only an explicit Founder claim or realm role', () => {
    expect(hasFounderClaim({ founder: true })).toBe(true);
    expect(hasFounderClaim({ realm_access: { roles: ['customer', 'founder'] } })).toBe(true);
    expect(hasFounderClaim({ founder: false, realm_access: { roles: ['customer'] } })).toBe(false);
    expect(hasFounderClaim({ founder: 'true' })).toBe(false);
    expect(hasFounderClaim(undefined)).toBe(false);
  });
});