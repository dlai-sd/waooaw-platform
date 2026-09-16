// Implements: work-contracts/WC-097-marketplace-acquisition-experience.md A01-A03
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { ArrowRight, BadgeCheck, BarChart3, Clock3, Search, ShieldCheck, Sparkles, Target } from 'lucide-react';
import Link from 'next/link';
import { AcquisitionContinuation } from '@/components/acquisition/AcquisitionContinuation';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { browseMarketplaceProfessionals } from '@/lib/api/professionals';
import { portalMessages } from '@/lib/portal-i18n';
import { getServerAccessToken } from '@/lib/server-auth';

interface MarketplacePageProps {
  searchParams: Promise<{
    cursor?: string;
    professionalType?: string;
    q?: string;
    version?: string;
    intent?: string;
    disclosureRevision?: string;
    termsVersion?: string;
    idempotencyKey?: string;
  }>;
}

export default async function MarketplacePage({ searchParams }: MarketplacePageProps) {
  const { locale, messages } = await getRequestI18n();
  const [accessToken, filters] = await Promise.all([getServerAccessToken(), searchParams]);
  if (!accessToken) {
    return <StateView actionHref="/login" actionLabel="Sign in" kind="error" title="Marketplace unavailable" description="Sign in again to browse available professionals." />;
  }

  const continuation = filters.professionalType && filters.version
    && (filters.intent === 'trial' || filters.intent === 'hire')
    && filters.disclosureRevision && filters.termsVersion && filters.idempotencyKey
    ? <AcquisitionContinuation
        disclosureRevision={filters.disclosureRevision}
        idempotencyKey={filters.idempotencyKey}
        intent={filters.intent}
        professionalType={filters.professionalType}
        professionalVersion={filters.version}
        termsVersion={filters.termsVersion}
      />
    : null;

  try {
    const page = await browseMarketplaceProfessionals(accessToken, filters);
    return (
      <section className="portal-page" aria-labelledby="marketplace-title">
        <header className="portal-heading">
          <p className="eyebrow">Find a professional</p>
          <h1 id="marketplace-title">{portalMessages[locale].marketplace}</h1>
          <p>Choose a professional whose skills and approach fit the outcome you want.</p>
        </header>
        {continuation}
        <form className="portal-filter" role="search">
          <label htmlFor="marketplace-search">Search</label>
          <div><Search aria-hidden="true" size={18} /><input id="marketplace-search" name="q" defaultValue={filters.q} placeholder="Name or capability" /></div>
          <button className="secondary-link" type="submit">Apply</button>
        </form>
        {page.items.length === 0 ? (
          <StateView actionHref="/marketplace" actionLabel="Clear filters" kind="empty" title="No professionals found" description="No published professional currently matches these filters." />
        ) : (
          <ul className="marketplace-grid">
            {page.items.map((professional) => (
              <li className="marketplace-offer" key={`${professional.professionalType}:${professional.version}`}>
                <header className="marketplace-offer-heading">
                  <span className="offer-mark"><Sparkles aria-hidden="true" size={22} /></span>
                  <div><p className="eyebrow">Growth professional</p><h2>{professional.displayName}</h2></div>
                  <span className="offer-available"><span aria-hidden="true" />Available now</span>
                </header>
                <p className="offer-promise">A focused digital marketing partner for local businesses ready to grow with clarity.</p>
                {professional.suitability?.length ? <ul className="offer-outcomes">{professional.suitability.map((item, index) => <li key={item}>{index === 0 ? <Target aria-hidden="true" size={19} /> : <BarChart3 aria-hidden="true" size={19} />}<span>{item}</span></li>)}</ul> : null}
                <div className="offer-trust-line"><span><ShieldCheck aria-hidden="true" size={17} />Evidence-backed plans</span>{professional.trialTerms ? <span><Clock3 aria-hidden="true" size={17} />Trial available</span> : null}<span><BadgeCheck aria-hidden="true" size={17} />You stay in control</span></div>
                <div className="offer-commercial">
                  {professional.indicativePrice ? <p><span>From</span><strong>{new Intl.NumberFormat(locale, { style: 'currency', currency: professional.indicativePrice.currency }).format(professional.indicativePrice.amountInrPaise / 100)}</strong><span>/ {professional.indicativePrice.cadence.toLowerCase()}</span></p> : <p>Price available during review</p>}
                  {professional.trialTerms ? <p><strong>{professional.trialTerms}</strong></p> : null}
                </div>
                <footer className="offer-actions">
                  <div className="command-row">
                    {professional.availableIntents.has('TRIAL') ? <Link className="secondary-link" href={`${professional.disclosurePath}?${new URLSearchParams({ professionalType: professional.professionalType, version: professional.version, intent: 'trial' })}`}>Start trial <ArrowRight aria-hidden="true" size={18} /></Link> : null}
                    {professional.availableIntents.has('HIRE') ? <Link className="primary-link" href={`${professional.disclosurePath}?${new URLSearchParams({ professionalType: professional.professionalType, version: professional.version, intent: 'hire' })}`}>Hire <ArrowRight aria-hidden="true" size={18} /></Link> : null}
                  </div>
                </footer>
                <p className="offer-footnote">Review what is included before you decide. Nothing starts until you confirm.</p>
              </li>
            ))}
          </ul>
        )}
        {page.nextCursor ? <Link className="secondary-link portal-next" href={`/marketplace?cursor=${encodeURIComponent(page.nextCursor)}${filters.q ? `&q=${encodeURIComponent(filters.q)}` : ''}`}>Next page <ArrowRight aria-hidden="true" size={18} /></Link> : null}
      </section>
    );
  } catch {
    return <StateView actionHref="/home" actionLabel={messages.returnHome} kind="error" title="Marketplace unavailable" description="Published professional offers could not be retrieved. Eligibility and pricing are not estimated in the browser." />;
  }
}