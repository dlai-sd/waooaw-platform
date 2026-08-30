// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Content Rules
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { projectPublicLegalSource } from '@/lib/public-legal';

describe('public legal projection', () => {
  it('preserves policy substance while enforcing the sole public contact', () => {
    const source = '# Policy\nContact technology@dlaisd.com or yogesh.khandge@dlaisd.com | +91 8888912344 (WhatsApp).\n## Rights\nSubstance remains.';
    const projected = projectPublicLegalSource(source, 'privacy-policy.md');
    expect(projected).toContain('## Rights\nSubstance remains.');
    expect(projected.match(/customersupport@dlaisd\.com/g)).toHaveLength(2);
    expect(projected).not.toMatch(/technology@|yogesh\.khandge@|8888912344/);
  });

  it('reconciles the cookie source with runtime names and retention', () => {
    const projected = projectPublicLegalSource('# Cookie Policy\n`waooaw_lang` and `waooaw_analytics`.', 'cookie-policy.md');
    expect(projected).toContain('`waooaw-locale` and `waooaw_consent`');
    expect(projected).toContain('analytics choice, advertising choice');
    expect(projected).toContain('at most 30 minutes');
  });
});