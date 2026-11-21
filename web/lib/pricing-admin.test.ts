// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { pricingRouteFor, pricingRouteWrites, pricingRoutes } from './pricing-admin';

const id = '7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11';

function route<T>(value: T | undefined): T {
  if (value === undefined) throw new Error('Expected a published pricing route.');
  return value;
}

test('exactly the eighteen published operations are routable', () => {
  expect(pricingRoutes).toHaveLength(18);
  expect(new Set(pricingRoutes.map((route) => route.operationId)).size).toBe(18);
  expect(pricingRoutes.filter((route) => route.founderOnly).map((route) => route.operationId)).toEqual([
    'authorizePricingDraft',
    'activatePackageForSale',
  ]);
});

test.each([
  ['GET', ['drafts'], 'listPricingDrafts'],
  ['POST', ['drafts'], 'createPricingDraft'],
  ['GET', ['drafts', id], 'getPricingDraft'],
  ['PUT', ['drafts', id], 'updatePricingDraft'],
  ['POST', ['drafts', id, 'authorize'], 'authorizePricingDraft'],
  ['POST', ['packages', id, 'activate-for-sale'], 'activatePackageForSale'],
  ['GET', ['versions', 'export'], 'exportPricingVersions'],
  ['POST', ['safety', 'lower-ceiling'], 'lowerPricingCeiling'],
  ['GET', ['dashboard', 'funding'], 'getPricingFundingDashboard'],
  ['get', ['live-margin'], 'getPricingLiveMargin'],
])('%s %j is %s', (method, segments, operationId) => {
  expect(pricingRouteFor(method, segments)?.operationId).toBe(operationId);
});

test.each([
  ['DELETE', ['drafts', id]],
  ['GET', ['drafts', 'not-a-uuid']],
  ['GET', ['drafts', id, 'authorize']],
  ['POST', ['drafts', id, 'authorize', 'extra']],
  ['GET', ['..', 'etc']],
  ['POST', ['versions']],
  ['GET', []],
])('%s %j is not an operation', (method, segments) => {
  expect(pricingRouteFor(method, segments)).toBeUndefined();
});

test('only reads are free of the idempotency requirement', () => {
  expect(pricingRouteWrites(route(pricingRouteFor('GET', ['drafts'])))).toBe(false);
  expect(pricingRouteWrites(route(pricingRouteFor('PUT', ['drafts', id])))).toBe(true);
});
