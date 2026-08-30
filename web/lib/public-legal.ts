// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Content Rules
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { marketingConfig } from '@/config/marketing';
import { siteConfig } from '@/config/site';

export function projectPublicLegalSource(source: string, sourceFile: string): string {
  let projected = source
    .replace(/^# .*\n+/, '')
    .replace(/(?:technology|yogesh\.khandge)@dlaisd\.com/gi, siteConfig.contactEmail)
    .replace(/\s*(?:\||or)?\s*\+91 8888912344(?:\s*\([^)]*\))?/g, '')
    .replace(/waooaw_lang/g, 'waooaw-locale')
    .replace(/waooaw_analytics/g, 'waooaw_consent')
    .replace(/Settings\s*→\s*Cookie Preferences/g, 'the Cookie preferences control');
  if (sourceFile === 'cookie-policy.md') projected += `\n\n## Runtime preference record\n\nThe \`waooaw_consent\` first-party cookie stores only the policy version, necessary flag, analytics choice, advertising choice, and update time for 12 months. The \`waooaw-locale\` and \`waooaw-theme\` necessary preference cookies last 12 months. When analytics or advertising is accepted, \`waooaw:acquisition:session\` holds a random session identifier and approved UTM values in session storage for at most ${marketingConfig.attributionWindowMinutes} minutes. Rejecting or withdrawing optional consent prevents future dispatch and clears optional browser identifiers managed by WAOOAW.\n`;
  return projected;
}