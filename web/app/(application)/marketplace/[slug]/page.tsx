// Implements: work-contracts/WC-097-marketplace-acquisition-experience.md A04-A06
// Constitutional basis: C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { ArrowLeft, BadgeCheck, BarChart3, ShieldCheck, Sparkles, Target } from 'lucide-react';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { DisclosureContinuation } from '@/components/acquisition/DisclosureContinuation';
import { getProfessionalDisclosure } from '@/lib/api/professionals';

type AcquisitionIntent = 'trial' | 'hire';

export default async function MarketplaceOfferPage({ params, searchParams }: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ professionalType?: string; version?: string; intent?: string }>;
}) {
  const [{ slug }, query] = await Promise.all([params, searchParams]);
  const intent = query.intent as AcquisitionIntent | undefined;
  if (!query.professionalType || !/^[A-Z][A-Z0-9_]{0,63}$/.test(query.professionalType)
    || !query.version || !/^\d+\.\d+\.\d+$/.test(query.version)
    || (intent !== 'trial' && intent !== 'hire')) notFound();

  const disclosure = await getProfessionalDisclosure(query.professionalType).catch(() => undefined);
  if (!disclosure || disclosure.customerRouteSlug !== slug || disclosure.projectionVersion !== query.version
    || (intent === 'trial' && !disclosure.trial.available)) notFound();

  const price = new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: disclosure.indicativePrice.currency,
  }).format(disclosure.indicativePrice.amountInrPaise / 100);

  return <section className="portal-page marketplace-detail" aria-labelledby="offer-title">
    <Link className="offer-back" href="/marketplace"><ArrowLeft aria-hidden="true" size={18} />Marketplace</Link>
    <header className="offer-detail-heading">
      <div><p className="eyebrow">Your digital growth partner</p><h1 id="offer-title">{disclosure.displayName}</h1><p>{disclosure.suitability[0]}</p></div>
      <span className="offer-mark offer-mark-large"><Sparkles aria-hidden="true" size={28} /></span>
    </header>

    <div className="offer-detail-grid">
      <section className="offer-detail-main" aria-labelledby="included-title">
        <p className="offer-intent"><BadgeCheck aria-hidden="true" size={18} />You chose to {intent === 'trial' ? 'start a trial' : 'hire this professional'}.</p>
        <h2 id="included-title">What you can achieve</h2>
        <ul className="offer-outcomes offer-outcomes-detail">{disclosure.suitability.map((item, index) => <li key={item}>{index === 0 ? <Target aria-hidden="true" size={20} /> : <BarChart3 aria-hidden="true" size={20} />}<span>{item}</span></li>)}</ul>
        <h2>Included capabilities</h2>
        <ul className="offer-capabilities">{disclosure.skills.map((skill) => <li key={skill.skillId}><BadgeCheck aria-hidden="true" size={18} /><span><strong>{skill.displayName}</strong>{skill.applicableInTrial ? <small>Included in trial</small> : null}</span></li>)}</ul>
        <details className="offer-details"><summary>Scope, safeguards and your control</summary><div><h3>Honest limits</h3><ul>{disclosure.limitations.map((item) => <li key={item}>{item}</li>)}</ul><h3>Your control</h3><ul>{disclosure.customerRights.map((item) => <li key={item}>{item}</li>)}</ul></div></details>
      </section>

      <aside className="offer-decision" aria-label={`${intent === 'trial' ? 'Trial' : 'Hire'} summary`}>
        <ShieldCheck aria-hidden="true" size={24} />
        <p className="eyebrow">{intent === 'trial' ? `${disclosure.trial.durationDays}-day trial` : 'Professional plan'}</p>
        <p className="offer-decision-price"><strong>{intent === 'trial' ? 'No paid tools' : price}</strong>{intent === 'hire' ? <span>/ {disclosure.indicativePrice.cadence.toLowerCase()}</span> : <span>during your trial</span>}</p>
        <p>{intent === 'trial' ? 'Explore planning, research and strategy without publishing, external actions or paid API usage.' : 'Final included capability and provider costs are confirmed before contract acceptance.'}</p>
        <DisclosureContinuation disclosureRevision={disclosure.disclosureRevision} initialIntent={intent} professionalType={disclosure.professionalType} professionalVersion={disclosure.projectionVersion} termsVersion={disclosure.termsVersion} trialAvailable={disclosure.trial.available} />
      </aside>
    </div>
  </section>;
}