// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063

export function hasRealmRole(profile: unknown, role: string): boolean {
  if (!profile || typeof profile !== 'object') return false;
  const realmAccess = (profile as Record<string, unknown>).realm_access;
  if (!realmAccess || typeof realmAccess !== 'object') return false;
  const roles = (realmAccess as Record<string, unknown>).roles;
  return Array.isArray(roles) && roles.includes(role);
}

// Pricing administration is open to the pricing_admin realm role and to the Founder; the server still decides each call.
export function hasPricingAdminClaim(profile: unknown): boolean {
  return hasRealmRole(profile, 'pricing_admin') || hasFounderClaim(profile);
}

export function hasFounderClaim(profile: unknown): boolean {
  if (!profile || typeof profile !== 'object') return false;
  const claims = profile as Record<string, unknown>;
  if (claims.founder === true) return true;
  const realmAccess = claims.realm_access;
  if (!realmAccess || typeof realmAccess !== 'object') return false;
  const roles = (realmAccess as Record<string, unknown>).roles;
  return Array.isArray(roles) && roles.includes('founder');
}
