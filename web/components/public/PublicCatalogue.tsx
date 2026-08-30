// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Professional Catalogue Boundary
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import { ArrowRight } from 'lucide-react';
import type { PublicProfessional } from '@/config/professionals';

export function PublicCatalogue({ professionals }: { professionals: readonly PublicProfessional[] }) {
  return <div className="public-catalogue">{professionals.map((professional) => <article key={professional.slug}><p className="eyebrow">{professional.domain}</p><h2>{professional.name}</h2><p>{professional.summary}</p><ul>{professional.outcomes.map((outcome) => <li key={outcome}>{outcome}</li>)}</ul><a className="text-command" href={`/professionals/${professional.slug}`}>View scope and limits <ArrowRight aria-hidden="true" size={17} /></a></article>)}</div>;
}