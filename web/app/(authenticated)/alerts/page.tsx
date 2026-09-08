// Implements: work-contracts/WC-084-auth-readiness-and-customer-portal-plan.md §8.7 Alerts
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { AlertFeed } from '@/components/portal/AlertFeed';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import type { CustomerPortalDestinationV1 } from '@/lib/api/generated/models/CustomerPortalDestinationV1';
import { listCustomerAlerts } from '@/lib/api/notifications';
import { portalMessages } from '@/lib/portal-i18n';
import { getServerAccessToken } from '@/lib/server-auth';

function alertHref(destination: CustomerPortalDestinationV1): string {
  if (destination.relationshipId) return `/relationships/${encodeURIComponent(destination.relationshipId)}`;
  const routes: Partial<Record<CustomerPortalDestinationV1['surface'], string>> = {
    MARKETPLACE: '/marketplace', ALERTS: '/alerts', BILLING: '/profile', PROFILE: '/profile', SETTINGS: '/settings',
  };
  return routes[destination.surface] ?? '/home';
}

export default async function AlertsPage() {
  const { locale, messages } = await getRequestI18n();
  const accessToken = await getServerAccessToken();
  if (!accessToken) {
    return <StateView actionHref="/login" actionLabel="Sign in" kind="error" title="Alerts unavailable" description="Sign in again to view alerts for your organization." />;
  }

  try {
    const page = await listCustomerAlerts(accessToken);
    if (page.items.length === 0) {
      return <StateView actionHref="/home" actionLabel={messages.returnHome} kind="empty" title="No alerts" description="There are no current alerts for your authorized relationships." />;
    }
    return (
      <section className="portal-page" aria-labelledby="alerts-title">
        <header className="portal-heading"><p className="eyebrow">Customer activity</p><h1 id="alerts-title">{portalMessages[locale].alerts}</h1><p>Opening or acknowledging an alert does not approve or complete its underlying action.</p></header>
        <AlertFeed initialAlerts={page.items.map((alert) => ({ ...alert, occurredAt: alert.occurredAt.toISOString(), href: alertHref(alert.destination) }))} locale={locale} />
      </section>
    );
  } catch {
    return <StateView actionHref="/home" actionLabel={messages.returnHome} kind="error" title="Alerts unavailable" description="The current server-owned alert feed could not be retrieved. No browser-generated alerts are shown." />;
  }
}