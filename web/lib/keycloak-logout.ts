// Implements: work-contracts/WC-119-auth-session-account-switch-recovery.md WC119-R001, WC119-R002, WC119-R005
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

export async function requestKeycloakLogout(command: 'LOCAL_LOGOUT' | 'ACCOUNT_SWITCH' = 'LOCAL_LOGOUT') {
  const response = await fetch('/api/auth/keycloak-logout', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  });
  if (!response.ok) throw new Error('Keycloak logout could not start.');
  const result: unknown = await response.json();
  if (
    !result ||
    typeof result !== 'object' ||
    !('logoutPath' in result) ||
    typeof result.logoutPath !== 'string' ||
    !result.logoutPath.startsWith('/api/auth/keycloak-logout?nonce=')
  ) {
    throw new Error('Keycloak logout response was invalid.');
  }
  return result.logoutPath;
}
