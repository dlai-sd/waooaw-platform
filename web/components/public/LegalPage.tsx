// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Content Rules
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { siteConfig } from '@/config/site';
import { breadcrumbData } from '@/lib/public-seo';
import { StructuredData } from './StructuredData';

export function LegalPage({ effectiveDate, path, summary, title }: { effectiveDate: string; path: string; summary: string; title: string }) {
  return <article className="public-document legal-document"><StructuredData value={breadcrumbData(title, path)} /><header><p className="eyebrow">Version 1.0 - Effective {effectiveDate}</p><h1>{title}</h1><p>{summary}</p></header><section><h2>Your choices and rights</h2><p>You may ask about this policy, exercise an applicable right, or raise a concern through WAOOAW&apos;s public support route.</p><a href={`mailto:${siteConfig.contactEmail}`}>{siteConfig.contactEmail}</a></section><section><h2>Governed handling</h2><p>WAOOAW applies data minimization, purpose limitation, access controls, and evidence-backed handling. Optional acquisition measurement remains consent-controlled.</p></section></article>;
}