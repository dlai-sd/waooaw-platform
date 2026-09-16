// Implements: architecture/reference/ux/hybrid-application-shell.md §Navigation Contract
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { ArrowRight, Bot, CheckCircle2, Store } from 'lucide-react';
import Link from 'next/link';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { getIdentitySession } from '@/lib/api/identity';
import { listEmploymentRelationships } from '@/lib/api/relationships';
import { getServerAccessToken } from '@/lib/server-auth';

function EmptyMyAgentsWorkspace() {
	return (
		<section className="empty-agent-workspace" aria-labelledby="my-agents-empty-title">
			<aside className="agent-list-panel" aria-label="Your agents">
				<p className="section-label">My Agents</p>
				<div className="agent-list-empty"><Bot aria-hidden="true" size={24} /><p>No trial or hired agents yet.</p></div>
			</aside>
			<div className="agent-empty-primary">
				<Store aria-hidden="true" size={36} />
				<p className="eyebrow">Build your AI team</p>
				<h1 id="my-agents-empty-title">Hire or try a WAOOAW AI Agent now.</h1>
				<p>Browse available professionals, compare their scope and terms, and begin registration only when you choose Trial or Hire.</p>
				<Link className="primary-link" href="/marketplace">Browse Marketplace <ArrowRight aria-hidden="true" size={18} /></Link>
			</div>
			<aside className="agent-context-panel" aria-label="Getting started">
				<p className="section-label">Getting started</p>
				<h2>Your workspace will appear here</h2>
				<ul className="portal-checklist">
					<li><CheckCircle2 aria-hidden="true" size={18} /><span>Choose a professional in Marketplace</span></li>
					<li><CheckCircle2 aria-hidden="true" size={18} /><span>Start a trial or employment relationship</span></li>
					<li><CheckCircle2 aria-hidden="true" size={18} /><span>Continue onboarding, goals and work here</span></li>
				</ul>
			</aside>
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
		return <section className="portal-page" aria-labelledby="my-experts-title"><header className="portal-heading"><p className="eyebrow">Your team</p><h1 id="my-experts-title">{messages.myExperts}</h1><p>Each expert keeps a separate contract, goals, skills, trial and workspace.</p></header><ul className="marketplace-grid">{page.items.map((item) => <li key={item.relationshipId}><div className="portal-item-heading"><h2>{item.professionalDisplayName}</h2><span className="status-label">{(item.trialStatus ?? item.lifecycleState).replaceAll('_', ' ')}</span></div><p>{item.professionalType}</p><p>{item.currentGoalSummary ?? 'No current goal has been confirmed.'}</p><footer><span>{item.availabilityState.replaceAll('_', ' ')}</span><Link className="secondary-link" href={`/relationships/${item.relationshipId}`}>Open workspace <ArrowRight aria-hidden="true" size={18} /></Link></footer></li>)}</ul></section>;
	} catch {
		return <StateView actionHref="/home" actionLabel={messages.returnHome} kind="error" title="My Experts unavailable" description="Your authoritative relationship list could not be retrieved." />;
	}
}