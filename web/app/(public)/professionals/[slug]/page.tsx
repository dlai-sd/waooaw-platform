// Implements: WC-096 §4.3 Marketplace And Disclosure
// Constitutional basis: C-002 (Evidence Integrity), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { DisclosureContinuation } from '@/components/acquisition/DisclosureContinuation';
import { StructuredData } from '@/components/public/StructuredData';
import { getPublicProfessional, listPublicProfessionals } from '@/config/professionals';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { absoluteUrl } from '@/config/site';
import { breadcrumbData, publicMetadata } from '@/lib/public-seo';

type AcquisitionIntent = 'trial' | 'hire';
type ProfessionalPageProps = {
  params: Promise<{ slug: string }>;
  searchParams?: Promise<{ professionalType?: string; version?: string; intent?: string }>;
};

export const dynamicParams = false;
export function generateStaticParams() {
  return listPublicProfessionals().map(({ slug }) => ({ slug }));
}
export async function generateMetadata({ params }: ProfessionalPageProps): Promise<Metadata> {
  const item = getPublicProfessional((await params).slug);
  if (!item) notFound();
  return publicMetadata(`${item.name} | WAOOAW`, item.summary, `/professionals/${item.slug}`);
}

export default async function ProfessionalPage({ params, searchParams }: ProfessionalPageProps) {
  const { slug } = await params;
  const publication = getPublicProfessional(slug);
  if (!publication) notFound();

  const query = await searchParams;
  const requestedProfessionalType = query?.professionalType;
  const hasAcquisitionQuery = Boolean(query?.professionalType || query?.version || query?.intent);
  const intent = query?.intent as AcquisitionIntent | undefined;
  if (
    hasAcquisitionQuery &&
    (!requestedProfessionalType ||
      !/^[A-Z][A-Z0-9_]{0,63}$/.test(requestedProfessionalType) ||
      !query.version ||
      !/^\d+\.\d+\.\d+$/.test(query.version) ||
      (intent !== 'trial' && intent !== 'hire'))
  )
    notFound();

  const disclosure = hasAcquisitionQuery
    ? await getProfessionalDisclosure(requestedProfessionalType ?? '').catch(() => undefined)
    : undefined;
  if (
    hasAcquisitionQuery &&
    (!disclosure ||
      disclosure.projectionVersion !== query?.version ||
      disclosure.customerRouteSlug !== slug ||
      (intent === 'trial' && !disclosure.trial.available))
  )
    notFound();

  const path = `/professionals/${slug}`;
  const displayName = disclosure?.displayName ?? publication.name;
  const suitability = disclosure?.suitability ?? publication.outcomes;
  const limitations = disclosure?.limitations ?? publication.limitations;
  const professionalType = disclosure?.professionalType ?? publication.professionalType;
  const version = disclosure?.projectionVersion ?? publication.version;
  const disclosureRevision = disclosure?.disclosureRevision ?? publication.version;
  const termsVersion = disclosure?.termsVersion ?? '2026-07-18';

  return (
    <article className="public-document professional-detail">
      <StructuredData
        value={[
          {
            '@context': 'https://schema.org',
            '@type': 'Service',
            name: displayName,
            description: publication.summary,
            url: absoluteUrl(path),
            provider: { '@type': 'Organization', name: 'WAOOAW' },
          },
          breadcrumbData(displayName, path),
        ]}
      />
      <header>
        <p className="eyebrow">{publication.domain}</p>
        <h1>{displayName}</h1>
        <p>{publication.summary}</p>
      </header>
      <section>
        <h2>What this professional can help with</h2>
        <ul>
          {suitability.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
      {disclosure ? (
        <section>
          <h2>Skills included</h2>
          <ul>
            {disclosure.skills.map((skill) => (
              <li key={skill.skillId}>
                {skill.displayName}
                {skill.applicableInTrial ? ' (available in trial)' : ''}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <section>
        <h2>Honest limits</h2>
        <ul>
          {limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
      {disclosure ? (
        <>
          <section>
            <h2>Your control</h2>
            <ul>
              {disclosure.customerRights.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
          <section>
            <h2>Before live work</h2>
            <ul>
              {disclosure.authorityNeeds.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
          <p className="price-disclosure">
            <strong>
              {new Intl.NumberFormat('en-IN', {
                style: 'currency',
                currency: disclosure.indicativePrice.currency,
              }).format(disclosure.indicativePrice.amountInrPaise / 100)}
            </strong>{' '}
            / {disclosure.indicativePrice.cadence.toLowerCase()}
            <small>{disclosure.indicativePrice.qualification}</small>
          </p>
        </>
      ) : null}
      <p className="publication-note">
        Disclosure {disclosureRevision} for professional release {version}. Availability is confirmed before
        continuation.
      </p>
      <DisclosureContinuation
        disclosureRevision={disclosureRevision}
        initialIntent={intent}
        professionalType={professionalType}
        professionalVersion={version}
        termsVersion={termsVersion}
        trialAvailable={disclosure?.trial.available ?? true}
      />
    </article>
  );
}
