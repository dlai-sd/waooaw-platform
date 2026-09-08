// Implements: architecture/reference/ux/hybrid-application-shell.md §Entry and Resume Behavior
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { ArrowRight, CircleAlert } from 'lucide-react';
import Link from 'next/link';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { listEmploymentRelationships } from '@/lib/api/relationships';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function CustomerHomePage() {
	const [{ messages }, accessToken] = await Promise.all([
		getRequestI18n(),
		getServerAccessToken(),
	]);

	if (!accessToken) {
		return <StateView actionHref="/login" actionLabel="Sign in" kind="error" title="Your session is unavailable" description="Sign in again to view your authorized agents." />;
	}

	try {
		const relationships = await listEmploymentRelationships(accessToken);
		if (relationships.items.length === 0) {
			return <StateView actionHref="/marketplace" actionLabel="Browse marketplace" kind="empty" title="No agents yet" description="Explore available digital professionals when you are ready to start a governed relationship." />;
		}

		return (
			<section className="portal-page" aria-labelledby="my-agents-title">
				<header className="portal-heading">
					<p className="eyebrow">Customer workspace</p>
					<h1 id="my-agents-title">My Agents</h1>
					<p>Resume work from the destination selected by the Business Platform.</p>
				</header>
				<ul className="portal-list">
					{relationships.items.map((relationship) => (
						<li key={relationship.relationshipId} className="portal-list-item">
							<div>
								<div className="portal-item-heading">
									<h2>{relationship.professionalDisplayName}</h2>
									<span className="status-label">{relationship.lifecycleState}</span>
								</div>
								<p>{relationship.professionalType}</p>
								<p>{relationship.currentGoalSummary ?? 'No current goal summary is available.'}</p>
								{relationship.unreadState !== 'NONE' ? (
									<span className="attention-label"><CircleAlert aria-hidden="true" size={16} />{relationship.unreadState.replaceAll('_', ' ')}</span>
								) : null}
							</div>
							<Link className="secondary-link" href={`/relationships/${encodeURIComponent(relationship.relationshipId)}`}>
								Open workspace <ArrowRight aria-hidden="true" size={18} />
							</Link>
						</li>
					))}
				</ul>
			</section>
		);
	} catch {
		return <StateView actionHref="/home" actionLabel={messages.returnHome} kind="error" title="My Agents is unavailable" description="The Business Platform could not provide your authorized relationships. No browser-cached relationship data is shown." />;
	}
}