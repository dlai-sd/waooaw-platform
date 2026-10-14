const legacyEncode = jest.fn();
const legacyDecode = jest.fn();

jest.mock('next-auth/jwt', () => ({
  encode: legacyEncode,
  decode: legacyDecode,
}));
jest.mock('./identity-security-events', () => ({
  persistWebIdentitySecurityEvent: jest.fn(),
  recordWebIdentitySecurityEvent: jest.fn(),
}));
jest.mock('./web-session-store', () => ({
  acquireRefreshLease: jest.fn(),
  completeRefresh: jest.fn(),
  createSession: jest.fn(),
  loadSession: jest.fn(),
  revokeSession: jest.fn(),
}));

describe('NextAuth session migration wiring', () => {
  afterEach(() => {
    Reflect.deleteProperty(process.env, 'WAOOAW_SERVER_SESSION_MODE');
    jest.resetModules();
  });

  it('keeps the legacy JWT cookie authoritative while disabled', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'disabled';

    const { authOptions } = await import('./auth');

    expect(authOptions.cookies).toBeUndefined();
    expect(authOptions.jwt?.encode).toBe(legacyEncode);
    expect(authOptions.jwt?.decode).toBe(legacyDecode);
  });

  it('accepts only the opaque application cookie while enforced', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'enforced';

    const { authOptions } = await import('./auth');
    const encode = authOptions.jwt?.encode;
    if (!encode) throw new Error('JWT encoder is unavailable');
    const encoded = await encode({
      token: { sessionHandle: 'h'.repeat(43) },
      secret: 'test-secret',
      maxAge: 60,
    });

    expect(authOptions.cookies?.sessionToken?.name).toBe('__Host-waooaw-session');
    expect(encoded).toBe('h'.repeat(43));
    expect(legacyEncode).not.toHaveBeenCalled();
  });
});
