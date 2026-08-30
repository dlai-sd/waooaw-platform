// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Content And Internal Linking
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

export type PublicArticle = Readonly<{
  slug: string;
  title: string;
  description: string;
  category: string;
  publishedAt: string;
  modifiedAt: string;
  state: 'published' | 'draft';
  paragraphs: readonly string[];
  relatedProfessional: string;
}>;

const articles: readonly PublicArticle[] = [
  {
    slug: 'governed-digital-professional',
    title: 'What makes a digital professional governable?',
    description: 'A practical guide to visible scope, reviewable work, and the right to stop.',
    category: 'Governance',
    publishedAt: '2026-08-30',
    modifiedAt: '2026-08-30',
    state: 'published',
    paragraphs: [
      'A digital professional should not ask for unlimited trust. Its authority, limits, and expected evidence should be visible before work begins.',
      'WAOOAW relationships keep consequential decisions with the customer and preserve an unconditional route to stop active work.',
      'Reliable autonomy is therefore not the absence of control. It is useful work performed inside a boundary that people can inspect and change.',
    ],
    relatedProfessional: 'digital-marketing',
  },
  {
    slug: 'evidence-before-claims',
    title: 'Why evidence must come before a success claim',
    description: 'Transport, activity, and business outcomes are different states.',
    category: 'Evidence',
    publishedAt: '2026-08-30',
    modifiedAt: '2026-08-30',
    state: 'published',
    paragraphs: [
      'A message being sent does not prove that professional work succeeded. A completed task does not automatically prove a business outcome either.',
      'Evidence First keeps those states distinct. Customers see what happened, what remains uncertain, and what source supports a claim.',
      'This avoids polished but unsupported reporting and gives each review a concrete starting point.',
    ],
    relatedProfessional: 'agricultural-advisory',
  },
];

export function listPublishedArticles(): readonly PublicArticle[] {
  return articles.filter(({ state }) => state === 'published');
}

export function getPublishedArticle(slug: string): PublicArticle | undefined {
  return listPublishedArticles().find((article) => article.slug === slug);
}