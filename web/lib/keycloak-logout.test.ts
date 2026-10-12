import { requestKeycloakLogout } from './keycloak-logout';

afterEach(() => {
  Reflect.deleteProperty(globalThis, 'fetch');
});

it('returns the nonce-bound Keycloak logout continuation', async () => {
  Object.defineProperty(globalThis, 'fetch', {
    configurable: true,
    value: jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ logoutPath: '/api/auth/keycloak-logout?nonce=valid' }),
    }),
  });

  await expect(requestKeycloakLogout()).resolves.toBe('/api/auth/keycloak-logout?nonce=valid');
});

it('rejects a denied Keycloak logout request', async () => {
  Object.defineProperty(globalThis, 'fetch', {
    configurable: true,
    value: jest.fn().mockResolvedValue({ ok: false }),
  });

  await expect(requestKeycloakLogout()).rejects.toThrow('Keycloak logout could not start.');
});

it.each([undefined, null, {}, { logoutPath: 42 }, { logoutPath: '/api/auth/keycloak-logout' }])(
  'rejects invalid logout continuation %p',
  async (result) => {
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: jest.fn().mockResolvedValue({
        ok: true,
        json: async () => result,
      }),
    });

    await expect(requestKeycloakLogout()).rejects.toThrow('Keycloak logout response was invalid.');
  }
);
