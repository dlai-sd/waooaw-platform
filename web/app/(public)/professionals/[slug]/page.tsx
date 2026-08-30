// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Professional Catalogue Boundary
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { StructuredData } from '@/components/public/StructuredData';
import { getPublicProfessional, listPublicProfessionals } from '@/config/professionals';
import { absoluteUrl } from '@/config/site';
import { breadcrumbData, publicMetadata } from '@/lib/public-seo';

export const dynamicParams = false;
export function generateStaticParams() { return listPublicProfessionals().map(({ slug }) => ({ slug })); }
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> { const item = getPublicProfessional((await params).slug); if (!item) notFound(); return publicMetadata(`${item.name} | WAOOAW`, item.summary, `/professionals/${item.slug}`); }
export default async function ProfessionalPage({ params }: { params: Promise<{ slug: string }> }) { const professional = getPublicProfessional((await params).slug); if (!professional) notFound(); const path = `/professionals/${professional.slug}`; return <article className="public-document professional-detail"><StructuredData value={[{ '@context': 'https://schema.org', '@type': 'Service', name: professional.name, description: professional.summary, url: absoluteUrl(path), provider: { '@type': 'Organization', name: 'WAOOAW' } }, breadcrumbData(professional.name, path)]} /><header><p className="eyebrow">{professional.domain}</p><h1>{professional.name}</h1><p>{professional.summary}</p></header><section><h2>Approved outcomes</h2><ul>{professional.outcomes.map((item) => <li key={item}>{item}</li>)}</ul></section><section><h2>Honest limits</h2><ul>{professional.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section><p className="publication-note">Publication {professional.version}. This page does not claim live availability or business-specific suitability.</p><a className="primary-link" href={`/register?professional=${professional.slug}`}>Start the approved registration path</a></article>; }