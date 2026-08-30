// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Destination And Environment Matrix
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

export type MarketingDestination = 'ga4' | 'serverGtm' | 'meta';

export const marketingConfig = {
  policyVersion: '2026-08-30',
  attributionWindowMinutes: 30,
  ga4: { enabled: false, id: undefined },
  serverGtm: { enabled: false },
  meta: { enabled: false, id: undefined },
} as const;