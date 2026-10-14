import {
  normalizeOidcCallback,
  oidcProtocolCookies,
  protocolCookiesMatch,
  providerClassFromPath,
} from './oidc-transaction';

const origin = 'https://app.example';

describe('server-owned OIDC transaction', () => {
  it('accepts only intent-matched local callback routes and safe targets', () => {
    expect(normalizeOidcCallback('/register?returnTo=%2Fmarketplace%3Fintent%3Dhire', 'HIRE', origin)).toEqual({
      intent: 'HIRE',
      callbackPath: '/register?returnTo=%2Fmarketplace%3Fintent%3Dhire',
    });
    expect(normalizeOidcCallback('https://attacker.example/register?returnTo=/home', 'REGISTER', origin)).toBeNull();
    expect(normalizeOidcCallback('/login?returnTo=/home', 'REGISTER', origin)).toBeNull();
  });

  it('normalizes unsafe return targets without preserving attacker input', () => {
    expect(normalizeOidcCallback('/login?returnTo=https://attacker.example', 'LOGIN', origin)).toEqual({
      intent: 'LOGIN',
      callbackPath: '/login?returnTo=%2Fhome',
    });
  });

  it('extracts and later requires state, nonce, and PKCE cookies', () => {
    const headers = new Headers();
    headers.append('set-cookie', '__Secure-next-auth.state=state-cookie; Path=/; HttpOnly');
    headers.append('set-cookie', '__Secure-next-auth.nonce=nonce-cookie; Path=/; HttpOnly');
    headers.append('set-cookie', '__Secure-next-auth.pkce.code_verifier=pkce-cookie; Path=/; HttpOnly');
    const expected = oidcProtocolCookies(headers);
    const actual = new Map(Object.entries(expected).map(([name, value]) => [name, { value }]));

    expect(Object.keys(expected)).toHaveLength(3);
    expect(protocolCookiesMatch(expected, actual)).toBe(true);
    actual.delete('__Secure-next-auth.nonce');
    expect(protocolCookiesMatch(expected, actual)).toBe(false);
  });

  it('maps only the closed provider paths', () => {
    expect(providerClassFromPath('/api/auth/callback/keycloak-google')).toBe('GOOGLE');
    expect(providerClassFromPath('/api/auth/callback/unknown')).toBeUndefined();
  });
});
