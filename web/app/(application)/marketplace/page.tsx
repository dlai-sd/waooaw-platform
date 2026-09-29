// Implements: work-contracts/WC-097-marketplace-acquisition-experience.md A01-A03
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { ArrowRight, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { AcquisitionContinuation } from '@/components/acquisition/AcquisitionContinuation';
import { DisclosureContinuation } from '@/components/acquisition/DisclosureContinuation';
import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { browseMarketplaceProfessionals } from '@/lib/api/professionals';
import { describePortalFailure } from '@/lib/api/portal-failure';
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
    couponCode?: string;
  }>;
}

export default async function MarketplacePage({ searchParams }: MarketplacePageProps) {
  const { locale, messages } = await getRequestI18n();
  const [accessToken, filters] = await Promise.all([getServerAccessToken(), searchParams]);
  if (!accessToken) {
    return (
      <StateView
        actionHref="/login"
        actionLabel="Sign in"
        kind="error"
        title="Marketplace unavailable"
        description="Sign in again to browse available professionals."
      />
    );
  }

  const continuation =
    filters.professionalType &&
    filters.version &&
    (filters.intent === 'trial' || filters.intent === 'hire') &&
    filters.disclosureRevision &&
    filters.termsVersion &&
    filters.idempotencyKey ? (
      <AcquisitionContinuation
        disclosureRevision={filters.disclosureRevision}
        idempotencyKey={filters.idempotencyKey}
        intent={filters.intent}
        professionalType={filters.professionalType}
        professionalVersion={filters.version}
        termsVersion={filters.termsVersion}
        couponCode={filters.couponCode}
      />
    ) : null;

  try {
    const page = await browseMarketplaceProfessionals(accessToken, filters);
    return (
      <section className="portal-page" aria-labelledby="marketplace-title">
        <header className="portal-heading marketplace-heading">
          <p className="eyebrow">Find a professional</p>
          <h1 id="marketplace-title">{portalMessages[locale].marketplace}</h1>
          <p>Choose a professional whose skills and approach fit the outcome you want.</p>
        </header>
        {continuation}
        {page.items.length === 0 ? (
          <StateView
            actionHref="/marketplace"
            actionLabel="Clear filters"
            kind="empty"
            title="No professionals found"
            description="No published professional currently matches these filters."
          />
        ) : (
          <ul className="marketplace-grid">
            {page.items.map((professional) => (
              <li className="marketplace-offer" key={`${professional.professionalType}:${professional.version}`}>
                <header className="marketplace-offer-heading">
                  <span className="offer-mark">
                    <Sparkles aria-hidden="true" size={22} />
                  </span>
                  <div>
                    <p className="eyebrow">Growth professional</p>
                    <h2>{professional.displayName}</h2>
                  </div>
                  <span className="offer-available">
                    <span aria-hidden="true" />
                    Available now
                  </span>
                </header>
                {professional.suitability?.[0] ? <p className="offer-promise">{professional.suitability[0]}</p> : null}
                <ul className="offer-capabilities" aria-label="Included capabilities">
                  {professional.capabilitySignals.map((capability) => (
                    <li key={capability}>{capability}</li>
                  ))}
                </ul>
                <div className="offer-commercial">
                  {professional.indicativePrice ? (
                    <p>
                      <span>From</span>
                      <strong>
                        {new Intl.NumberFormat(locale, {
                          style: 'currency',
                          currency: professional.indicativePrice.currency,
                        }).format(professional.indicativePrice.amountInrPaise / 100)}
                      </strong>
                      <span>/ {professional.indicativePrice.cadence.toLowerCase()}</span>
                      <small>{professional.indicativePrice.qualification}</small>
                    </p>
                  ) : (
                    <p>Price available during review</p>
                  )}
                  {professional.trialTerms ? (
                    <p>
                      <strong>{professional.trialTerms}</strong>
                    </p>
                  ) : null}
                </div>
                <details className="offer-details">
                  <summary>Scope, safeguards and your control</summary>
                  <h3>Honest limits</h3>
                  <ul>
                    {professional.limitations.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <h3>Your control</h3>
                  <ul>
                    {professional.customerRights.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <Link href={professional.disclosurePath}>Open expanded disclosure</Link>
                </details>
                {professional.indicativePrice ? (
                  <DisclosureContinuation
                    disclosureRevision={professional.disclosureRevision}
                    priceInrPaise={professional.indicativePrice.amountInrPaise}
                    professionalType={professional.professionalType}
                    professionalVersion={professional.version}
                    termsVersion={professional.termsVersion}
                    trialAvailable={professional.availableIntents.has('TRIAL')}
                    trialDurationDays={professional.trial.durationDays}
                  />
                ) : null}
                <p className="offer-footnote">
                  Review what is included before you decide. Nothing starts until you confirm.
                </p>
              </li>
            ))}
          </ul>
        )}
        {page.nextCursor ? (
          <Link
            className="secondary-link portal-next"
            href={`/marketplace?cursor=${encodeURIComponent(page.nextCursor)}${filters.q ? `&q=${encodeURIComponent(filters.q)}` : ''}`}
          >
            Next page <ArrowRight aria-hidden="true" size={18} />
          </Link>
        ) : null}
      </section>
    );
  } catch (error) {
    const failure = await describePortalFailure(error, 'MARKETPLACE');
    return (
      <StateView
        actionHref="/home"
        actionLabel={messages.returnHome}
        correlationId={failure.correlationId}
        kind="error"
        reasonCode={failure.reasonCode}
        title="Marketplace unavailable"
        description="Published professional offers could not be retrieved. Eligibility and pricing are not estimated in the browser."
      />
    );
  }
}
