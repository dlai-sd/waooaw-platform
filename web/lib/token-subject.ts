// Implements: work-contracts/WC-167-acceptance-demo-readiness.md WC167-R001
// Constitutional basis: C-009, C-023, C-059, C-063

import { logServerFailure } from '@/lib/server-failure';

const subjectPattern = /^[A-Za-z0-9._:@-]{8,128}$/;

// Reads the person's own sign-in identifier from their token so it can be shown back to them. It trusts nothing:
// the Business Platform still validates the token and decides every role. A malformed token or subject gives null.
export function tokenSubject(token: string | undefined): string | null {
  const payload = token?.split('.')[1];
  if (!payload) return null;
  try {
    const claims: unknown = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
    const subject = claims && typeof claims === 'object' ? (claims as Record<string, unknown>).sub : undefined;
    return typeof subject === 'string' && subjectPattern.test(subject) ? subject : null;
  } catch (error) {
    logServerFailure('web.token_subject.parse_failed', error);
    return null;
  }
}
