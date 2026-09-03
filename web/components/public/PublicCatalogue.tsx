// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Professional Catalogue Boundary
// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §10.5 (WC-05)
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import { ArrowRight, CheckCircle2 } from 'lucide-react';
import type { ProfessionalPublicationState, PublicProfessional } from '@/config/professionals';

const publicationLabel: Record<ProfessionalPublicationState, string> = {
  published: 'Published',
  draft: 'In preparation',
  retired: 'No longer offered',
};

export function PublicCatalogue({ compact = false, professionals }: { compact?: boolean; professionals: readonly PublicProfessional[] }) {
  return <div className={compact ? 'public-catalogue public-catalogue-preview' : 'public-catalogue'}>{professionals.map((professional) => <article key={professional.slug}><p className="eyebrow">{professional.domain}</p><h2>{professional.name}</h2>{compact ? null : <p>{professional.summary}</p>}<ul>{(compact ? professional.outcomes.slice(0, 1) : professional.outcomes).map((outcome) => <li key={outcome}>{outcome}</li>)}</ul><p className={`publication-state publication-state-${professional.publicationState}`}>{professional.publicationState === 'published' ? <CheckCircle2 aria-hidden="true" size={16} /> : null}{publicationLabel[professional.publicationState]}</p><a className="text-command" href={`/professionals/${professional.slug}`}>View scope and limits <ArrowRight aria-hidden="true" size={17} /></a></article>)}</div>;
}