export function hasFounderClaim(profile: unknown): boolean {
  if (!profile || typeof profile !== 'object') return false;
  const claims = profile as Record<string, unknown>;
  if (claims.founder === true) return true;
  const realmAccess = claims.realm_access;
  if (!realmAccess || typeof realmAccess !== 'object') return false;
  const roles = (realmAccess as Record<string, unknown>).roles;
  return Array.isArray(roles) && roles.includes('founder');
}
