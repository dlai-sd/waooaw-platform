import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { notFound } from 'next/navigation';

interface EmploymentContractPageProps {
  searchParams: Promise<{
    professionalType?: string;
    version?: string;
    disclosureRevision?: string;
    termsVersion?: string;
    mode?: string;
  }>;
}

export default async function EmploymentContractPage({ searchParams }: EmploymentContractPageProps) {
  const query = await searchParams;
  if (
    !query.professionalType ||
    !query.version ||
    !query.disclosureRevision ||
    !query.termsVersion ||
    (query.mode !== 'trial' && query.mode !== 'hire')
  )
    notFound();
  const disclosure = await getProfessionalDisclosure(query.professionalType);
  if (
    disclosure.projectionVersion !== query.version ||
    disclosure.disclosureRevision !== query.disclosureRevision ||
    disclosure.termsVersion !== query.termsVersion
  )
    notFound();

  return (
    <article className="portal-page legal-page" aria-labelledby="employment-contract-title">
      <header className="portal-heading">
        <p className="eyebrow">{query.mode === 'trial' ? 'Trial' : 'Hire'} agreement</p>
        <h1 id="employment-contract-title">Employment Contract</h1>
        <p>
          {disclosure.displayName} · Agent version {disclosure.projectionVersion} · Contract version{' '}
          {disclosure.termsVersion}
        </p>
      </header>
      <section>
        <h2>Customer rights</h2>
        <ul>
          {disclosure.customerRights.map((right) => (
            <li key={right}>{right}</li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Capabilities and limitations</h2>
        <ul>
          {disclosure.limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Authority and Stop</h2>
        <ul>
          {disclosure.authorityNeeds.map((authority) => (
            <li key={authority}>{authority}</li>
          ))}
        </ul>
        <p>Emergency Stop and termination remain available throughout the relationship.</p>
      </section>
      <section>
        <h2>Commercial terms</h2>
        {query.mode === 'trial' ? (
          <p>
            This Trial is free for {disclosure.trial.durationDays} days, has no automatic paid conversion, and does not
            invoke a payment provider.
          </p>
        ) : (
          <p>
            The server-owned checkout will show list price, tax, discount, final payable amount, renewal consequences
            and payment readiness before commitment.
          </p>
        )}
      </section>
      <p>
        Disclosure revision {disclosure.disclosureRevision}. Evidence posture: {disclosure.evidencePosture}.
      </p>
    </article>
  );
}
