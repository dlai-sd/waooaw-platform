// Implements: architecture/reference/ux/hybrid-application-shell.md §Interaction and Failure Semantics
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { AuthFailureReporter } from '@/components/auth/AuthFailureReporter';
import { StateView } from '@/components/system/StateView';
import { siteConfig } from '@/config/site';
import { getRequestI18n } from '@/lib/i18n-server';
export default async function AuthErrorPage() {
  const { messages } = await getRequestI18n();
  return (
    <>
      <AuthFailureReporter />
      <StateView
        actionHref="/login"
        actionLabel={messages.retrySecureSignIn}
        description={
          <>
            {messages.authErrorDescription} Contact WAOOAW support at{' '}
            <a href={`mailto:${siteConfig.contactEmail}`}>{siteConfig.contactEmail}</a>.
          </>
        }
        kind="error"
        title={messages.authErrorTitle}
      />
    </>
  );
}
