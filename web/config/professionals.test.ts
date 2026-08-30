// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Professional Catalogue Boundary
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import { getPublicProfessional, listPublicProfessionals } from './professionals';

describe('public professional catalogue', () => {
  it('publishes only records carrying traceable release metadata', () => {
    const professionals = listPublicProfessionals();

    expect(professionals).toHaveLength(4);
    expect(professionals).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ slug: 'digital-marketing', publicationState: 'published' }),
      ]),
    );
    expect(professionals.every(({ approvalReference, modifiedAt }) => approvalReference && modifiedAt)).toBe(true);
  });

  it('resolves admitted slugs without manufacturing unknown records', () => {
    expect(getPublicProfessional('private-tutoring')?.professionalType).toBe('PRIVATE_TUTORING');
    expect(getPublicProfessional('unknown-professional')).toBeUndefined();
  });
});