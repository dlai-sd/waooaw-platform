// Implements: architecture/reference/ux/hybrid-application-shell.md §Entry and Resume Behavior
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R013, WC105-R017
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { redirect } from 'next/navigation';
import { StateView } from '@/components/system/StateView';
import { getIdentitySession } from '@/lib/api/identity';
import { listEmploymentRelationships } from '@/lib/api/relationships';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function ApplicationHomePage() {
  const [{ messages }, accessToken] = await Promise.all([getRequestI18n(), getServerAccessToken()]);
  if (!accessToken) redirect('/login');

  const identity = await getIdentitySession(accessToken);
  if (identity.kind === 'registration-required') redirect('/marketplace');
  if (identity.kind === 'expired' || identity.kind === 'unauthorized') redirect('/login');
  if (identity.kind === 'step-up' || identity.kind === 'forbidden') {
    return (
      <StateView
        actionHref="/login"
        actionLabel={messages.retrySecureSignIn}
        kind="forbidden"
        title={messages.accessNotPermitted}
        description={messages.accessNotPermittedDescription}
      />
    );
  }
  if (identity.kind === 'unavailable') {
    return (
      <StateView
        actionHref="/home"
        actionLabel={messages.tryAgain}
        kind="error"
        title={messages.globalErrorTitle}
        description={messages.globalErrorDescription}
      />
    );
  }

  let relationships: Awaited<ReturnType<typeof listEmploymentRelationships>>;
  try {
    relationships = await listEmploymentRelationships(accessToken);
  } catch {
    return (
      <StateView
        actionHref="/home"
        actionLabel={messages.tryAgain}
        kind="error"
        title={messages.globalErrorTitle}
        description={messages.globalErrorDescription}
      />
    );
  }
  redirect(relationships.items.length > 0 ? '/professionals/mine' : '/marketplace');
}
