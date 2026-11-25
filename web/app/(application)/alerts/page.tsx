import { logServerFailure } from '@/lib/server-failure';
// Implements: work-contracts/WC-084-auth-readiness-and-customer-portal-plan.md §8.7 Alerts
// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R007
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { AlertInbox } from '@/components/portal/AlertInbox';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { getIdentitySession } from '@/lib/api/identity';
import { listEmploymentRelationships } from '@/lib/api/relationships';
import { portalMessages } from '@/lib/portal-i18n';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function AlertsPage() {
  const { locale, messages } = await getRequestI18n();
  const accessToken = await getServerAccessToken();
  if (!accessToken) {
    return (
      <StateView
        actionHref="/login"
        actionLabel="Sign in"
        kind="error"
        title="Alerts unavailable"
        description="Sign in again to view alerts for your organization."
      />
    );
  }

  try {
    const identity = await getIdentitySession(accessToken);
    if (identity.kind === 'registration-required') {
      return (
        <StateView
          actionHref="/marketplace"
          actionLabel="Browse Marketplace"
          kind="empty"
          title="No alerts yet"
          description="Relationship decisions and activity will appear here after you try or hire a WAOOAW AI Agent."
        />
      );
    }
    if (identity.kind !== 'ready') throw new Error('Customer identity is unavailable.');
    // One inbox across agents; the agent filter lists only the agents this customer actually has.
    const relationships = await listEmploymentRelationships(accessToken);
    const agents = relationships.items.map((item) => ({
      id: item.relationshipId,
      name: item.professionalDisplayName ?? item.professionalType,
    }));
    return (
      <section className="portal-page" aria-labelledby="alerts-title">
        <header className="portal-heading">
          <p className="eyebrow">Customer activity</p>
          <h1 id="alerts-title">{portalMessages[locale].alerts}</h1>
          <p>Opening or acknowledging an alert does not approve or complete its underlying action.</p>
        </header>
        <AlertInbox agents={agents} locale={locale} showControls />
      </section>
    );
  } catch (error) {
    logServerFailure('web.portal.alerts.request_failed', error);
    return (
      <StateView
        actionHref="/home"
        actionLabel={messages.returnHome}
        back
        kind="error"
        title="Alerts unavailable"
        description="The current server-owned alert feed could not be retrieved. No browser-generated alerts are shown."
      />
    );
  }
}
