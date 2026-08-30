// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Structured Data
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)
export function StructuredData({ value }: { value: Record<string, unknown> | Array<Record<string, unknown>> }) {
  return <script dangerouslySetInnerHTML={{ __html: JSON.stringify(value).replace(/</g, '\\u003c') }} type="application/ld+json" />;
}