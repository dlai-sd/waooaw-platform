// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Configurable Public Experience Contract
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

export const siteConfig = {
  name: 'WAOOAW',
  company: 'DLAI Satellite Data (OPC) Pvt Ltd',
  canonicalOrigin: process.env.NEXT_PUBLIC_CANONICAL_ORIGIN ?? 'https://waooaw.com',
  contactEmail: 'customersupport@dlaisd.com',
  environment: process.env.NEXT_PUBLIC_WAOOAW_ENVIRONMENT ?? 'demo',
  locales: ['en', 'hi', 'mr', 'ta', 'te', 'kn', 'gu', 'bn', 'ml', 'pa', 'ur'],
  announcement: { enabled: false, message: '', href: '' },
  sectionSwitches: { professionalPreview: true, trustJourney: true, finalAction: true, platformDna: true },
  socialLinks: [],
  publicNavigation: [
    { href: '/', label: 'Home' },
    { href: '/professionals', label: 'Professionals' },
    { href: '/blogs', label: 'Insights' },
    { href: '/about', label: 'About' },
  ],
  footerGroups: [
    { label: 'Platform', links: [{ href: '/professionals', label: 'Professionals' }, { href: '/blogs', label: 'Insights' }, { href: '/constitution', label: 'Constitution' }] },
    { label: 'Company', links: [{ href: '/about', label: 'About' }, { href: '/careers', label: 'Careers' }, { href: '/press', label: 'Press' }, { href: '/contact', label: 'Contact' }] },
    { label: 'Legal', links: [{ href: '/privacy', label: 'Privacy' }, { href: '/terms', label: 'Terms' }, { href: '/cookies', label: 'Cookies' }, { href: '/refund', label: 'Refunds' }, { href: '/grievance', label: 'Grievance' }] },
  ],
} as const;

export function absoluteUrl(path: string): string {
  return new URL(path, siteConfig.canonicalOrigin).toString();
}