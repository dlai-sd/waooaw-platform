// Implements: work-contracts/WC-084-auth-readiness-and-customer-portal-plan.md §8.6 Marketplace
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { ArrowRight, BadgeCheck, Search } from 'lucide-react';
import Link from 'next/link';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { browseMarketplaceProfessionals } from '@/lib/api/professionals';
import { portalMessages } from '@/lib/portal-i18n';
import { getServerAccessToken } from '@/lib/server-auth';

interface MarketplacePageProps {
  searchParams: Promise<{ cursor?: string; professionalType?: string; q?: string }>;
}

export default async function MarketplacePage({ searchParams }: MarketplacePageProps) {
  const { locale, messages } = await getRequestI18n();
  const [accessToken, filters] = await Promise.all([getServerAccessToken(), searchParams]);
  if (!accessToken) {
    return <StateView actionHref="/login" actionLabel="Sign in" kind="error" title="Marketplace unavailable" description="Sign in again to browse professionals available to your organization." />;
  }

  try {
    const page = await browseMarketplaceProfessionals(accessToken, filters);
    return (
      <section className="portal-page" aria-labelledby="marketplace-title">
        <header className="portal-heading">
          <p className="eyebrow">Find a professional</p>
          <h1 id="marketplace-title">{portalMessages[locale].marketplace}</h1>
          <p>Eligibility, price, and available next steps come directly from the Business Platform.</p>
        </header>
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
              <li key={`${professional.professionalType}:${professional.version}`}>
                <div className="portal-item-heading"><h2>{professional.displayName}</h2><span className="status-label">{professional.offerabilityState.replaceAll('_', ' ')}</span></div>
                <p>{professional.professionalType}</p>
                <p>{professional.eligibility.explanation}</p>
                {professional.suitability?.length ? <ul className="compact-list">{professional.suitability.map((item) => <li key={item}><BadgeCheck aria-hidden="true" size={16} />{item}</li>)}</ul> : null}
                {professional.indicativePrice ? <p className="price-disclosure"><strong>{new Intl.NumberFormat(locale, { style: 'currency', currency: professional.indicativePrice.currency }).format(professional.indicativePrice.amountInrPaise / 100)}</strong> / {professional.indicativePrice.cadence.toLowerCase()}<small>{professional.indicativePrice.qualification}</small></p> : <p>Price is not available.</p>}
                {professional.trialTerms ? <p><strong>Trial:</strong> {professional.trialTerms}</p> : null}
                <footer>
                  <span>{professional.nextAction.replaceAll('_', ' ')}</span>
                  {professional.nextAction !== 'NONE' ? <Link className="secondary-link" href={`/professionals/${encodeURIComponent(professional.professionalType.toLowerCase().replaceAll('_', '-'))}`}>{professional.nextAction === 'START_TRIAL' ? 'Review trial disclosure' : professional.nextAction === 'START_HIRE' ? 'Review hire disclosure' : 'View disclosure'} <ArrowRight aria-hidden="true" size={18} /></Link> : null}
                </footer>
                {professional.nextAction === 'START_TRIAL' || professional.nextAction === 'START_HIRE' ? <p className="portal-action-note">The action continues through the approved relationship lifecycle after disclosure review.</p> : null}
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