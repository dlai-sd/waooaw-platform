// Implements: work-contracts/WC-167-acceptance-demo-readiness.md WC167-R001
// Constitutional basis: C-009, C-023, C-059, C-063

import { tokenSubject } from './token-subject';

const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString('base64url');
const token = (claims: unknown) => `${encode({ alg: 'none' })}.${encode(claims)}.signature`;

beforeEach(() => {
  jest.spyOn(console, 'error').mockImplementation(() => undefined);
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('tokenSubject', () => {
  it('returns the sign-in identifier of a well formed token', () => {
    expect(tokenSubject(token({ sub: '8f1c2a7e-3b9d-4c55-a1f0-9a7d2c4e6b10' }))).toBe(
      '8f1c2a7e-3b9d-4c55-a1f0-9a7d2c4e6b10'
    );
  });

  it.each([
    ['no token', undefined],
    ['an empty token', ''],
    ['a token with no payload', 'header'],
    ['a payload that is not JSON', `${encode({})}.%%%.signature`],
    ['a missing subject', token({ email: 'a@b.co' })],
    ['a subject that is not text', token({ sub: 12345678 })],
    ['a subject that is too short', token({ sub: 'short' })],
    ['a subject with unsafe characters', token({ sub: 'has space and <markup>' })],
  ])('returns null for %s', (_name, value) => {
    expect(tokenSubject(value)).toBeNull();
  });
});

it('records a malformed token as a redacted failure without leaking the token', () => {
  const leaked = 'secret-looking-token-text';
  expect(tokenSubject(`${encode({})}.%%%${leaked}.signature`)).toBeNull();
  const written = jest
    .mocked(console.error)
    .mock.calls.map((call) => String(call[0]))
    .join('\n');
  expect(written).toContain('web.token_subject.parse_failed');
  expect(written).not.toContain(leaked);
});
