// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-04, §UX-PRIV-01
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { safePublicReturnTarget, safeReturnTarget } from './safe-return';

describe('safe return targets', () => {
  it.each([
    'https://attacker.test',
    '//attacker.test',
    '/api/auth/signout',
    '/founder',
    '/relationships/../founder',
    '/marketplace?code=secret',
    '/marketplace#access_token=secret',
    '/marketplace?intent=delete',
    '/marketplace?intent=trial&intent=hire',
    '/marketplace?disclosureRevision=1.0.0&disclosureRevision=1.0.0',
    '/marketplace?idempotencyKey=not-a-uuid',
  ])('rejects %s', (target) => {
    expect(safeReturnTarget(target)).toBe('/home');
  });

  it.each([
    '/home',
    '/marketplace',
    '/marketplace?professionalType=DIGITAL_MARKETING&version=3.1.0&intent=trial',
    '/marketplace?professionalType=DIGITAL_MARKETING_LOCAL_SERVICE&version=1.0.0&intent=hire&disclosureRevision=1.0.0&termsVersion=2026-07-18&idempotencyKey=11111111-1111-4111-8111-111111111111',
    '/settings',
    '/professionals/mine',
    '/relationships/8f6f7550-98c7-4a8f-bd63-36f07ee15c9d',
  ])('accepts %s', (target) => {
    expect(safeReturnTarget(target)).toBe(target);
  });
});

describe('public auth dismissal targets', () => {
  it.each(['/professionals', '/professionals/digital-marketing', '/privacy', '/#professionals', '/blogs/first-post'])(
    'accepts %s',
    (target) => {
      expect(safePublicReturnTarget(target)).toBe(target);
    }
  );
  it.each([
    undefined,
    '//example.com',
    'https://example.com',
    '/login',
    '/register',
    '/home',
    '/professionals/mine',
    '/professionals/%2e%2e',
    '/\\example.com',
    '/professionals?token=value',
  ])('rejects %s', (target) => {
    expect(safePublicReturnTarget(target)).toBe('/');
  });
});
