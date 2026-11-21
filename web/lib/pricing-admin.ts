// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

const uuid = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';

export type PricingMethod = 'GET' | 'POST' | 'PUT';

export type PricingRoute = {
  operationId: string;
  method: PricingMethod;
  pattern: RegExp;
  founderOnly: boolean;
};

// The 18 operations of pricing-admin-business-platform.openapi.yaml; nothing else is ever proxied.
export const pricingRoutes: readonly PricingRoute[] = [
  { operationId: 'listPricingDrafts', method: 'GET', pattern: /^drafts$/, founderOnly: false },
  { operationId: 'createPricingDraft', method: 'POST', pattern: /^drafts$/, founderOnly: false },
  { operationId: 'getPricingDraft', method: 'GET', pattern: new RegExp(`^drafts/${uuid}$`), founderOnly: false },
  { operationId: 'updatePricingDraft', method: 'PUT', pattern: new RegExp(`^drafts/${uuid}$`), founderOnly: false },
  {
    operationId: 'simulatePricingDraft',
    method: 'POST',
    pattern: new RegExp(`^drafts/${uuid}/simulate$`),
    founderOnly: false,
  },
  {
    operationId: 'submitPricingDraft',
    method: 'POST',
    pattern: new RegExp(`^drafts/${uuid}/submit$`),
    founderOnly: false,
  },
  {
    operationId: 'authorizePricingDraft',
    method: 'POST',
    pattern: new RegExp(`^drafts/${uuid}/authorize$`),
    founderOnly: true,
  },
  {
    operationId: 'discardPricingDraft',
    method: 'POST',
    pattern: new RegExp(`^drafts/${uuid}/discard$`),
    founderOnly: false,
  },
  { operationId: 'listPricingVersions', method: 'GET', pattern: /^versions$/, founderOnly: false },
  { operationId: 'exportPricingVersions', method: 'GET', pattern: /^versions\/export$/, founderOnly: false },
  { operationId: 'importPricingVersions', method: 'POST', pattern: /^versions\/import$/, founderOnly: false },
  {
    operationId: 'activatePackageForSale',
    method: 'POST',
    pattern: new RegExp(`^packages/${uuid}/activate-for-sale$`),
    founderOnly: true,
  },
  { operationId: 'lowerPricingCeiling', method: 'POST', pattern: /^safety\/lower-ceiling$/, founderOnly: false },
  { operationId: 'closePackageToNewCustomers', method: 'POST', pattern: /^safety\/close-package$/, founderOnly: false },
  { operationId: 'disablePricingGrant', method: 'POST', pattern: /^safety\/disable-grant$/, founderOnly: false },
  { operationId: 'getPricingLiveMargin', method: 'GET', pattern: /^live-margin$/, founderOnly: false },
  { operationId: 'getPricingFundingDashboard', method: 'GET', pattern: /^dashboard\/funding$/, founderOnly: false },
  { operationId: 'getPricingMarginDashboard', method: 'GET', pattern: /^dashboard\/margin$/, founderOnly: false },
];

export const pricingQueryNames = ['kind', 'state', 'subjectKey', 'limit', 'cursor', 'from', 'to'] as const;

export function pricingRouteFor(method: string, segments: readonly string[]): PricingRoute | undefined {
  const path = segments.join('/');
  return pricingRoutes.find((route) => route.method === method.toUpperCase() && route.pattern.test(path));
}

export function pricingRouteWrites(route: PricingRoute): boolean {
  return route.method !== 'GET';
}
