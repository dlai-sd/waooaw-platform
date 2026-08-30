// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Professional Catalogue Boundary
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

export type ProfessionalPublicationState = 'published' | 'draft' | 'retired';

export type PublicProfessional = Readonly<{
  slug: string;
  professionalType: string;
  version: string;
  name: string;
  domain: string;
  summary: string;
  outcomes: readonly string[];
  limitations: readonly string[];
  publicationState: ProfessionalPublicationState;
  modifiedAt: string;
  approvalReference: string;
}>;

const catalogue: readonly PublicProfessional[] = [
  {
    slug: 'digital-marketing',
    professionalType: 'DIGITAL_MARKETING',
    version: '3.1.0',
    name: 'Digital Marketing Professional',
    domain: 'Audience growth and customer acquisition',
    summary: 'Plans and operates approved digital marketing work within visible campaign boundaries.',
    outcomes: ['Campaign planning', 'Content operations', 'Performance reporting'],
    limitations: ['No unsupported outcome guarantees', 'Advertising spend always requires approval'],
    publicationState: 'published',
    modifiedAt: '2026-08-30',
    approvalReference: 'architecture/reference/agents/digital-marketing-agent.md',
  },
  {
    slug: 'agricultural-advisory',
    professionalType: 'AGRICULTURAL_ADVISORY',
    version: '2.8.0',
    name: 'Agricultural Advisory Professional',
    domain: 'Farm planning and practical agricultural guidance',
    summary: 'Provides bounded agricultural guidance while keeping consequential decisions with the customer.',
    outcomes: ['Season planning', 'Crop guidance', 'Risk-aware recommendations'],
    limitations: ['Guidance is not a guarantee of yield', 'Local conditions require customer verification'],
    publicationState: 'published',
    modifiedAt: '2026-08-30',
    approvalReference: 'architecture/reference/agents/agricultural-advisor-agent.md',
  },
  {
    slug: 'trading-advisory',
    professionalType: 'TRADING_ADVISORY',
    version: '1.8.0',
    name: 'Trading Advisory Professional',
    domain: 'Research-led trading analysis',
    summary: 'Prepares explainable market analysis within declared financial and regulatory limits.',
    outcomes: ['Market briefings', 'Risk framing', 'Portfolio review support'],
    limitations: ['No execution of trades', 'No promise of returns'],
    publicationState: 'published',
    modifiedAt: '2026-08-30',
    approvalReference: 'architecture/reference/agents/trading-professional-agent.md',
  },
  {
    slug: 'private-tutoring',
    professionalType: 'PRIVATE_TUTORING',
    version: '1.1.0',
    name: 'Private Tutoring Professional',
    domain: 'Structured learning support',
    summary: 'Supports approved learning goals with reviewable plans and age-appropriate boundaries.',
    outcomes: ['Learning plans', 'Practice support', 'Progress summaries'],
    limitations: ['Does not replace school or guardian oversight', 'No unsupported grade guarantee'],
    publicationState: 'published',
    modifiedAt: '2026-08-30',
    approvalReference: 'architecture/reference/agents/private-tutor-agent.md',
  },
];

export function listPublicProfessionals(): readonly PublicProfessional[] {
  return catalogue.filter(({ publicationState }) => publicationState === 'published');
}

export function getPublicProfessional(slug: string): PublicProfessional | undefined {
  return listPublicProfessionals().find((professional) => professional.slug === slug);
}