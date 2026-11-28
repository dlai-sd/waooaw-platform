import { logServerFailure } from '@/lib/server-failure';
// Implements: architecture/reference/ux/hybrid-application-shell.md §Navigation Contract
// Constitutional basis: C-042 (Localization), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { Bell, Globe2, Link2, MoonStar, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { SessionManager } from '@/components/auth/SessionManager';
import { DataRightsPanel } from '@/components/portal/DataRightsPanel';
import { SettingsEditor } from '@/components/portal/SettingsEditor';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { getCustomerSettings, getIdentitySession } from '@/lib/api/identity';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { getServerAccessToken, getServerSessionToken } from '@/lib/server-auth';
import { listSessions } from '@/lib/web-session-store';

export default async function SettingsPage() {
  const [{ messages }, accessToken] = await Promise.all([getRequestI18n(), getServerAccessToken()]);
  if (!accessToken) {
    return (
      <StateView
        actionHref="/login"
        actionLabel="Sign in"
        kind="error"
        title="Settings unavailable"
        description="Sign in again to view your server-owned preferences."
      />
    );
  }

  try {
    const identity = await getIdentitySession(accessToken);
    if (identity.kind === 'registration-required') {
      if ((await resolvePlatformAccess(accessToken)).administrator) {
        return (
          <StateView
            actionHref="/home"
            actionLabel="Go to home"
            kind="empty"
            title="Staff account"
            description="This sign-in is a staff account, so it has no customer settings. Language and theme remain in the header, and staff tools are in the menu."
          />
        );
      }
      return (
        <StateView
          actionHref="/marketplace"
          actionLabel="Browse Marketplace"
          kind="empty"
          title="Customer settings will appear here"
          description="Language and theme remain available in the header. Notification and organization settings begin once you have registered and started a Trial or Hire."
        />
      );
    }
    if (identity.kind !== 'ready') throw new Error('Customer identity is unavailable.');
    const sessionToken = await getServerSessionToken();
    if (!sessionToken) throw new Error('Customer session is unavailable.');
    const [settings, sessions] = await Promise.all([getCustomerSettings(accessToken), listSessions(sessionToken)]);
    return (
      <section className="portal-page" aria-labelledby="settings-title">
        <header className="portal-heading">
          <p className="eyebrow">{messages.preferences}</p>
          <h1 id="settings-title">{messages.settings}</h1>
          <p>{messages.settingsDescription}</p>
        </header>
        <SettingsEditor
          locale={settings.locale}
          notificationPreferences={settings.notificationPreferences}
          theme={settings.theme}
          timestampVisibility={settings.timestampVisibility}
        />
        <div className="settings-grid">
          <section>
            <Globe2 aria-hidden="true" />
            <h2>Language and time</h2>
            <dl className="detail-list">
              <div>
                <dt>Language</dt>
                <dd>{settings.locale}</dd>
              </div>
              <div>
                <dt>Timestamps</dt>
                <dd>{settings.timestampVisibility.toLowerCase()}</dd>
              </div>
            </dl>
          </section>
          <section>
            <MoonStar aria-hidden="true" />
            <h2>Appearance</h2>
            <p>
              Theme preference: <strong>{settings.theme.toLowerCase()}</strong>
            </p>
          </section>
          <section className="settings-wide">
            <Link2 aria-hidden="true" />
            <h2>Connected accounts</h2>
            <p>
              The accounts your agents work through are managed under each agent.{' '}
              <Link href="/connections">See all connected accounts</Link>
            </p>
          </section>
          <section className="settings-wide">
            <Bell aria-hidden="true" />
            <h2>Notifications</h2>
            <p>Choose where each kind of message reaches you in the form above, then press Save settings.</p>
            <p>
              <Link href="/alerts">Choose which alerts reach your phone</Link>
            </p>
          </section>
          <section className="settings-wide">
            <ShieldCheck aria-hidden="true" />
            <h2>Security actions</h2>
            {settings.availableSecurityActions?.length ? (
              <ul className="compact-list">
                {settings.availableSecurityActions.map((action) => (
                  <li key={action}>{action.replaceAll('_', ' ').toLowerCase()}</li>
                ))}
              </ul>
            ) : (
              <p>No account security action is currently available.</p>
            )}
          </section>
          <SessionManager initialSessions={sessions} />
          <DataRightsPanel />
        </div>
      </section>
    );
  } catch (error) {
    logServerFailure('web.portal.settings.request_failed', error);
    return (
      <StateView
        actionHref="/home"
        actionLabel={messages.returnHome}
        back
        kind="error"
        title="Settings unavailable"
        description="Current preferences could not be retrieved. Browser defaults are not presented as saved settings."
      />
    );
  }
}
