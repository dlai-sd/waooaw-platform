// Implements: architecture/reference/ux/hybrid-application-shell.md §Navigation Contract
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { BadgeCheck, CircleAlert, CreditCard, Mail, Smartphone } from 'lucide-react';
import { ProfileEditor } from '@/components/portal/ProfileEditor';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { getCustomerProfile, listCustomerLoginMethods } from '@/lib/api/identity';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function ProfilePage() {
	const [{ messages }, accessToken] = await Promise.all([getRequestI18n(), getServerAccessToken()]);
	if (!accessToken) {
		return <StateView actionHref="/login" actionLabel="Sign in" kind="error" title="Profile unavailable" description="Sign in again to view your identity-owned profile." />;
	}

	try {
		const [profile, loginMethods] = await Promise.all([
			getCustomerProfile(accessToken),
			listCustomerLoginMethods(accessToken),
		]);
		return (
			<section className="portal-page" aria-labelledby="profile-title">
				<header className="portal-heading"><p className="eyebrow">Account</p><h1 id="profile-title">{messages.profile}</h1><p>Identity and organization details are scoped to your authenticated account.</p></header>
				<div className="portal-sections">
					  <section aria-labelledby="identity-heading"><h2 id="identity-heading">Identity</h2><ProfileEditor displayName={profile.displayName} organizationDisplayName={profile.organizationDisplayName} /><dl className="detail-list"><div><dt>Role</dt><dd>{profile.activeRole.toLowerCase()}</dd></div><div><dt>Email</dt><dd>{profile.email} {profile.emailVerified ? <BadgeCheck aria-label="Verified" size={16} /> : <CircleAlert aria-label="Not verified" size={16} />}</dd></div><div><dt>Mobile</dt><dd>{profile.mobileVerified ? 'Verified' : 'Not verified'}</dd></div></dl></section>
					<section aria-labelledby="login-methods-heading"><h2 id="login-methods-heading">Login methods</h2><ul className="method-list">{loginMethods.items.map((method) => <li key={method.provider}>{method.provider === 'EMAIL' ? <Mail aria-hidden="true" /> : <Smartphone aria-hidden="true" />}<div><strong>{method.provider.toLowerCase()}</strong><span>{method.maskedIdentifier ?? 'Identifier withheld'}</span></div><span className="status-label">{method.state.replaceAll('_', ' ').toLowerCase()}</span></li>)}</ul></section>
					  <section className="unavailable-panel" id="billing" aria-labelledby="billing-heading"><CreditCard aria-hidden="true" /><div><h2 id="billing-heading">Billing</h2><p>Billing preference, payment method, allowance, invoices, and forecast are unavailable because the customer-global WBE projection is not yet supplied. No defaults are inferred.</p></div></section>
				</div>
			</section>
		);
	} catch {
		return <StateView actionHref="/home" actionLabel={messages.returnHome} kind="error" title="Profile unavailable" description={messages.profileUnavailableDescription} />;
	}
}