// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Destination And Environment Matrix
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

export type MarketingDestination = 'ga4' | 'serverGtm' | 'meta';

function publicIdentifier(value: string | undefined): string | undefined {
  return value && /^[A-Za-z0-9_-]{3,80}$/.test(value) ? value : undefined;
}

export const marketingConfig = {
  policyVersion: '2026-08-30',
  attributionWindowMinutes: 30,
  ga4: { enabled: process.env.NEXT_PUBLIC_GA4_ENABLED === 'true', id: publicIdentifier(process.env.NEXT_PUBLIC_GA4_ID) },
  serverGtm: { enabled: process.env.NEXT_PUBLIC_GTM_ENABLED === 'true' },
  meta: { enabled: process.env.NEXT_PUBLIC_META_ENABLED === 'true', id: publicIdentifier(process.env.NEXT_PUBLIC_META_PIXEL_ID) },
} as const;