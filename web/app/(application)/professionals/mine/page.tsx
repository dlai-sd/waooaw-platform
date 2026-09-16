// Implements: architecture/reference/ux/hybrid-application-shell.md §Navigation Contract
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { ArrowRight, Bot, Store } from 'lucide-react';
import Link from 'next/link';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import type { CustomerPortalDestinationV1 } from '@/lib/api/generated/models/CustomerPortalDestinationV1';
import { getIdentitySession } from '@/lib/api/identity';
import { listEmploymentRelationships } from '@/lib/api/relationships';
import { getServerAccessToken } from '@/lib/server-auth';

function resumeHref(destination: CustomerPortalDestinationV1): string {
	if (destination.relationshipId) return `/relationships/${encodeURIComponent(destination.relationshipId)}`;
	const routes: Partial<Record<CustomerPortalDestinationV1['surface'], string>> = {
		MARKETPLACE: '/marketplace', ALERTS: '/alerts', BILLING: '/profile', PROFILE: '/profile', SETTINGS: '/settings',
	};
	return routes[destination.surface] ?? '/home';
}

function EmptyMyAgentsWorkspace() {
	return (
		<section className="agent-empty-primary" aria-labelledby="my-agents-empty-title">
				<Store aria-hidden="true" size={36} />
				<p className="eyebrow">Build your AI team</p>
				<h1 id="my-agents-empty-title">Hire or try a WAOOAW AI Agent now.</h1>
				<p>Browse available professionals, compare their scope and terms, and begin registration only when you choose Trial or Hire.</p>
				<Link className="primary-link" href="/marketplace">Browse Marketplace <ArrowRight aria-hidden="true" size={18} /></Link>
		</section>
	);
}

export default async function MyProfessionalsPage() {
	const [{ messages }, accessToken] = await Promise.all([getRequestI18n(), getServerAccessToken()]);
	if (!accessToken) return <StateView actionHref="/login" actionLabel="Sign in" kind="error" title="My Experts unavailable" description="Sign in again to view your employed professionals." />;
	try {
		const identity = await getIdentitySession(accessToken);
		if (identity.kind === 'registration-required') return <EmptyMyAgentsWorkspace />;
		if (identity.kind !== 'ready') throw new Error('Customer identity is unavailable.');
		const page = await listEmploymentRelationships(accessToken);
		if (!page.items.length) return <EmptyMyAgentsWorkspace />;
		return <section className="portal-page" aria-labelledby="my-experts-title"><header className="portal-heading"><p className="eyebrow">Your team</p><h1 id="my-experts-title">{messages.myExperts}</h1><p>Review setup, current work, evidence and the next decision for each agent.</p></header><ul className="agent-dashboard">{page.items.map((item) => <li key={item.relationshipId}><div className="portal-item-heading"><Bot aria-hidden="true" size={22} /><h2>{item.professionalDisplayName}</h2><span className="status-label">{(item.trialStatus ?? item.lifecycleState).replaceAll('_', ' ')}</span></div><p className="agent-version">{item.professionalType} · {item.professionalVersion ?? 'Version unavailable'}</p><dl className="agent-facts"><div><dt>Setup</dt><dd>{item.configurationState.replaceAll('_', ' ')}</dd></div><div><dt>Skills</dt><dd>{item.enabledSkillCount} enabled · {item.pendingSkillCount} pending</dd></div><div><dt>Goal</dt><dd>{item.currentGoalSummary ?? 'No verified goal yet.'}</dd></div><div><dt>Work</dt><dd>{item.currentWorkSummary ?? 'No current work reported.'}</dd></div><div><dt>Performance</dt><dd>{item.performanceSummary}</dd></div><div><dt>Billing</dt><dd>{item.billingSummary}</dd></div></dl>{item.blockerSummary ? <p className="portal-error">{item.blockerSummary}</p> : null}<footer><span>{item.availabilityState.replaceAll('_', ' ')} · confirmed {new Intl.DateTimeFormat('en', { dateStyle: 'medium', timeStyle: 'short' }).format(item.lastAuthoritativelyConfirmedAt)}</span><Link className="primary-link" href={resumeHref(item.resumeTarget)}>{item.nextActionLabel} <ArrowRight aria-hidden="true" size={18} /></Link></footer></li>)}</ul></section>;
	} catch {
		return <StateView actionHref="/home" actionLabel={messages.returnHome} kind="error" title="My Experts unavailable" description="Your authoritative relationship list could not be retrieved." />;
	}
}