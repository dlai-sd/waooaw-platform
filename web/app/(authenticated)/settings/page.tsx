// Implements: architecture/reference/ux/hybrid-application-shell.md §Navigation Contract
// Constitutional basis: C-042 (Localization), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { Bell, Globe2, MoonStar, ShieldCheck } from 'lucide-react';
import { SettingsEditor } from '@/components/portal/SettingsEditor';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { getCustomerSettings } from '@/lib/api/identity';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function SettingsPage() {
	const [{ messages }, accessToken] = await Promise.all([getRequestI18n(), getServerAccessToken()]);
	if (!accessToken) {
		return <StateView actionHref="/login" actionLabel="Sign in" kind="error" title="Settings unavailable" description="Sign in again to view your server-owned preferences." />;
	}

	try {
		const settings = await getCustomerSettings(accessToken);
		const notificationRows = [
			['Approval requests', settings.notificationPreferences.approvalRequests],
			['Maturity reports', settings.notificationPreferences.maturityReports],
			['Monthly narratives', settings.notificationPreferences.monthlyNarratives],
			['Self-governance alerts', settings.notificationPreferences.selfGovernanceAlerts],
		] as const;
		return (
			<section className="portal-page" aria-labelledby="settings-title">
				<header className="portal-heading"><p className="eyebrow">{messages.preferences}</p><h1 id="settings-title">{messages.settings}</h1><p>{messages.settingsDescription}</p></header>
				<SettingsEditor locale={settings.locale} notificationPreferences={settings.notificationPreferences} theme={settings.theme} timestampVisibility={settings.timestampVisibility} />
				<div className="settings-grid">
					<section><Globe2 aria-hidden="true" /><h2>Language and time</h2><dl className="detail-list"><div><dt>Locale</dt><dd>{settings.locale}</dd></div><div><dt>Timestamps</dt><dd>{settings.timestampVisibility.toLowerCase()}</dd></div></dl></section>
					<section><MoonStar aria-hidden="true" /><h2>Appearance</h2><p>Theme preference: <strong>{settings.theme.toLowerCase()}</strong></p></section>
					<section className="settings-wide"><Bell aria-hidden="true" /><h2>Notifications</h2><dl className="detail-list">{notificationRows.map(([label, channels]) => <div key={label}><dt>{label}</dt><dd>{channels.length ? channels.map((channel) => channel.toLowerCase()).join(', ') : 'None'}</dd></div>)}</dl></section>
					<section className="settings-wide"><ShieldCheck aria-hidden="true" /><h2>Security actions</h2>{settings.availableSecurityActions?.length ? <ul className="compact-list">{settings.availableSecurityActions.map((action) => <li key={action}>{action.replaceAll('_', ' ').toLowerCase()}</li>)}</ul> : <p>No account security action is currently available.</p>}</section>
				</div>
			</section>
		);
	} catch {
		return <StateView actionHref="/home" actionLabel={messages.returnHome} kind="error" title="Settings unavailable" description="Current preferences could not be retrieved. Browser defaults are not presented as saved settings." />;
	}
}