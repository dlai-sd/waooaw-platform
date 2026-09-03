// Implements: architecture/reference/ux/hybrid-application-shell.md §Product Decisions and Release Gates
// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §6-10 (WC-03, WC-04)
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import { ArrowRight, BriefcaseBusiness, Scale, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { ProfessionalJourneyShowcase } from '@/components/public/ProfessionalJourneyShowcase';
import { PublicCatalogue } from '@/components/public/PublicCatalogue';
import { StructuredData } from '@/components/public/StructuredData';
import { listPublicProfessionals } from '@/config/professionals';
import { absoluteUrl, siteConfig } from '@/config/site';
import { getRequestI18n } from '@/lib/i18n-server';
import { getProfessionalJourneyContent } from '@/lib/professional-journey-content';
import { publicMetadata } from '@/lib/public-seo';

export const metadata = publicMetadata('WAOOAW | Governed digital professionals', 'Employ a governed digital professional with visible scope, reviewable work, and control that remains yours.', '/');

export default async function HomePage() {
  const { locale, messages } = await getRequestI18n();
  const professionals = listPublicProfessionals();
  const journeyContent = getProfessionalJourneyContent(locale);
  return (
    <div className="public-home">
      <StructuredData value={[{ '@context': 'https://schema.org', '@type': 'Organization', name: siteConfig.name, legalName: siteConfig.company, url: absoluteUrl('/'), email: siteConfig.contactEmail }, { '@context': 'https://schema.org', '@type': 'WebSite', name: siteConfig.name, url: absoluteUrl('/') }]} />
      <div className="public-intro public-intro-wc078">
        <section className="public-hero">
          <p className="eyebrow">{messages.publicEyebrow}</p>
          <h1>{journeyContent.heroTitle}</h1>
          <p className="hero-copy">{journeyContent.heroSubtitle}</p>
          <div className="command-row"><Link className="primary-link" href="/professionals">Meet a professional <ArrowRight aria-hidden="true" size={18} /></Link><a className="secondary-link" href="/register">Start with a trial</a></div>
        </section>
        <ProfessionalJourneyShowcase content={journeyContent} />
      </div>

      <section className="trust-strip public-trust-band" aria-label={messages.safeguards}><ShieldCheck aria-hidden="true" size={26} /><div><strong>{messages.controlYours}</strong><span>{messages.safeguardsDescription}</span></div></section>

      <section className="public-section professionals-section" aria-labelledby="expert-professionals-title">
        <div className="section-heading"><BriefcaseBusiness aria-hidden="true" size={28} /><h2 id="expert-professionals-title">{messages.expertProfessionals}</h2><p>{messages.expertDescription}</p></div>
        <PublicCatalogue compact professionals={professionals.slice(0, 3)} />
        <Link className="text-command" href="/professionals">{messages.browseProfessionals} <ArrowRight aria-hidden="true" size={18} /></Link>
      </section>

      <section className="public-section trust-journey" aria-labelledby="trust-journey-title">
        <div><p className="eyebrow">02</p><h2 id="trust-journey-title">{messages.trustJourney}</h2><p>{messages.trustDescription}</p></div>
        <div><Scale aria-hidden="true" size={32} /><p className="eyebrow">Illustrative governance journey</p><h2>{messages.constitutionalPromise}</h2><p>{messages.constitutionalDescription}</p></div>
      </section>

      <section className="public-section final-action"><p className="eyebrow">A professional relationship you can inspect</p><h2>Begin with visible scope, honest limits, and control that stays with you.</h2><div className="command-row"><Link className="primary-link" href="/professionals">Meet a professional <ArrowRight aria-hidden="true" size={18} /></Link><a className="secondary-link" href="/register">Start with a trial</a></div></section>
      <section className="platform-dna" aria-labelledby="platform-dna-title"><p className="eyebrow">Platform DNA</p><h2 id="platform-dna-title">Built through a connected institutional lineage.</h2><dl><div><dt>Yashus</dt><dd>Product and experience foundation</dd></div><div><dt>DLAI Satellite Data</dt><dd>Technology and operating company</dd></div><div><dt>WAOOAW</dt><dd>Constitutionally governed digital professionals</dd></div></dl></section>
    </div>
  );
}