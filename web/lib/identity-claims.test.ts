// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063

import { hasFounderClaim, hasPricingAdminClaim, hasRealmRole } from './identity-claims';

test('the pricing_admin realm role and the Founder may administer pricing', () => {
  expect(hasPricingAdminClaim({ realm_access: { roles: ['pricing_admin'] } })).toBe(true);
  expect(hasPricingAdminClaim({ realm_access: { roles: ['founder'] } })).toBe(true);
  expect(hasPricingAdminClaim({ founder: true })).toBe(true);
});

test('a customer or a malformed profile may not administer pricing', () => {
  expect(hasPricingAdminClaim({ realm_access: { roles: ['employer'] } })).toBe(false);
  expect(hasPricingAdminClaim({ realm_access: 'pricing_admin' })).toBe(false);
  expect(hasPricingAdminClaim({ realm_access: { roles: 'pricing_admin' } })).toBe(false);
  expect(hasPricingAdminClaim({})).toBe(false);
  expect(hasPricingAdminClaim(null)).toBe(false);
  expect(hasPricingAdminClaim('pricing_admin')).toBe(false);
});

test('a role claim is read from the realm access roles only', () => {
  expect(hasRealmRole({ realm_access: { roles: ['a', 'b'] } }, 'b')).toBe(true);
  expect(hasRealmRole({ roles: ['b'] }, 'b')).toBe(false);
  expect(hasFounderClaim({ realm_access: { roles: ['b'] } })).toBe(false);
});
