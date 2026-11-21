// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063

import { noPlatformAccess, platformAccessFrom, platformAccessRouteAllowed } from './platform-access';

const id = '7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11';

test.each([
  ['GET', ['me', 'roles']],
  ['POST', ['access-requests']],
  ['GET', ['access-requests']],
  ['POST', ['access-requests', id, 'decision']],
  ['GET', ['grants']],
  ['POST', ['grants', id, 'revoke']],
])('the browser may call %s %j', (method, segments) => {
  expect(platformAccessRouteAllowed(method, segments)).toBe(true);
});

test.each([
  ['DELETE', ['grants', id]],
  ['PUT', ['access-requests']],
  ['GET', ['grants', id, 'revoke']],
  ['POST', ['access-requests', 'not-a-guid', 'decision']],
  ['GET', ['me', 'roles', 'extra']],
  ['GET', []],
])('the browser may not call %s %j', (method, segments) => {
  expect(platformAccessRouteAllowed(method, segments)).toBe(false);
});

test('a founder is also an administrator and a non-object grants nothing', () => {
  expect(platformAccessFrom({ founder: true, emailVerified: true, email: 'f@x.com' })).toMatchObject({
    founder: true,
    administrator: true,
    emailVerified: true,
    email: 'f@x.com',
  });
  expect(platformAccessFrom({ pricingAdmin: true })).toMatchObject({ founder: false, administrator: true });
  expect(platformAccessFrom({ roles: ['founder'] }).founder).toBe(false);
  expect(platformAccessFrom(null)).toBe(noPlatformAccess);
  expect(platformAccessFrom('founder')).toBe(noPlatformAccess);
});

test('only well-formed lists are accepted', () => {
  expect(platformAccessFrom({ requestableRoles: ['pricing_admin', 7], requests: [{ requestId: id }] })).toMatchObject({
    requestableRoles: ['pricing_admin'],
    requests: [{ requestId: id }],
  });
  expect(platformAccessFrom({ requestableRoles: 'founder', requests: 'x', email: 5 })).toMatchObject({
    requestableRoles: [],
    requests: [],
    email: null,
  });
});
