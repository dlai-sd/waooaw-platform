// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Information Architecture
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import { siteConfig } from '@/config/site';
import { breadcrumbData } from '@/lib/public-seo';
import { StructuredData } from './StructuredData';

export function InformationPage({ contact = false, path, sections, summary, title }: { contact?: boolean; path: string; sections: readonly (readonly [string, string])[]; summary: string; title: string }) {
  const data = contact ? [breadcrumbData(title, path), { '@context': 'https://schema.org', '@type': 'ContactPoint', contactType: 'customer support', email: siteConfig.contactEmail }] : breadcrumbData(title, path);
  return <article className="public-document"><StructuredData value={data} /><header><p className="eyebrow">WAOOAW</p><h1>{title}</h1><p>{summary}</p></header>{sections.map(([heading, content]) => <section key={heading}><h2>{heading}</h2><p>{content}</p></section>)}{contact ? <a className="primary-link" href={`mailto:${siteConfig.contactEmail}`}>Email {siteConfig.contactEmail}</a> : null}</article>;
}