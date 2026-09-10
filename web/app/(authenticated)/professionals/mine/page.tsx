// Implements: architecture/reference/ux/hybrid-application-shell.md §Navigation Contract
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { listEmploymentRelationships } from '@/lib/api/relationships';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function MyProfessionalsPage() {
	const [{ messages }, accessToken] = await Promise.all([getRequestI18n(), getServerAccessToken()]);
	if (!accessToken) return <StateView actionHref="/login" actionLabel="Sign in" kind="error" title="My Experts unavailable" description="Sign in again to view your employed professionals." />;
	try {
		const page = await listEmploymentRelationships(accessToken);
		if (!page.items.length) return <StateView actionHref="/marketplace" actionLabel="Browse professionals" kind="empty" title={messages.myExperts} description={messages.noProfessionalRelationships} />;
		return <section className="portal-page" aria-labelledby="my-experts-title"><header className="portal-heading"><p className="eyebrow">Your team</p><h1 id="my-experts-title">{messages.myExperts}</h1><p>Each expert keeps a separate contract, goals, skills, trial and workspace.</p></header><ul className="marketplace-grid">{page.items.map((item) => <li key={item.relationshipId}><div className="portal-item-heading"><h2>{item.professionalDisplayName}</h2><span className="status-label">{item.lifecycleState.replaceAll('_', ' ')}</span></div><p>{item.professionalType}</p><p>{item.currentGoalSummary ?? 'No current goal has been confirmed.'}</p><footer><span>{item.availabilityState.replaceAll('_', ' ')}</span><Link className="secondary-link" href={`/relationships/${item.relationshipId}`}>Open workspace <ArrowRight aria-hidden="true" size={18} /></Link></footer></li>)}</ul></section>;
	} catch {
		return <StateView actionHref="/home" actionLabel={messages.returnHome} kind="error" title="My Experts unavailable" description="Your authoritative relationship list could not be retrieved." />;
	}
}