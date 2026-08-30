// Implements: architecture/reference/ux/hybrid-application-shell.md §Product Decisions and Release Gates
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import { ArrowRight, BriefcaseBusiness, CheckCircle2, Scale, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { AutonomyHandoffConsole } from '@/components/public/AutonomyHandoffConsole';
import { StructuredData } from '@/components/public/StructuredData';
import { listPublicProfessionals } from '@/config/professionals';
import { absoluteUrl, siteConfig } from '@/config/site';
import { getRequestI18n } from '@/lib/i18n-server';
import { publicMetadata } from '@/lib/public-seo';

export const metadata = publicMetadata('WAOOAW | Governed digital professionals', 'Employ a governed digital professional with visible scope, reviewable work, and control that remains yours.', '/');

export default async function HomePage() {
  const { messages } = await getRequestI18n();
  const steps = [messages.stepBusiness, messages.stepScope, messages.stepControl];
  const professionals = listPublicProfessionals();
  return (
    <div className="public-home">
      <StructuredData value={[{ '@context': 'https://schema.org', '@type': 'Organization', name: siteConfig.name, legalName: siteConfig.company, url: absoluteUrl('/'), email: siteConfig.contactEmail }, { '@context': 'https://schema.org', '@type': 'WebSite', name: siteConfig.name, url: absoluteUrl('/') }]} />
      <div className="public-intro public-intro-wc078">
        <section className="public-hero">
          <p className="eyebrow">{messages.publicEyebrow}</p>
          <h1>WAOOAW</h1>
          <p className="hero-copy">{messages.publicDescription}</p>
          <div className="command-row"><Link className="primary-link" href="/professionals">Meet a professional <ArrowRight aria-hidden="true" size={18} /></Link><a href="/register">Start with a trial</a></div>
        </section>
        <AutonomyHandoffConsole />
      </div>

      <section className="trust-strip public-trust-band" aria-label={messages.safeguards}><ShieldCheck aria-hidden="true" size={26} /><div><strong>{messages.controlYours}</strong><span>{messages.safeguardsDescription}</span></div></section>

      <section className="public-section journey-section" aria-labelledby="getting-started-title">
        <div className="section-heading"><p className="eyebrow">01</p><h2 id="getting-started-title">Three clear steps. Then productive work begins.</h2><p>{messages.gettingStartedDescription}</p></div>
        <ol className="journey-steps">{steps.map((step, index) => <li key={step}><span>{index + 1}</span><strong>{step}</strong></li>)}</ol>
      </section>

      <section className="public-section professionals-section" aria-labelledby="expert-professionals-title">
        <div className="section-heading"><BriefcaseBusiness aria-hidden="true" size={28} /><h2 id="expert-professionals-title">{messages.expertProfessionals}</h2><p>{messages.expertDescription}</p></div>
        <ul className="professional-grid">{professionals.map((professional) => <li key={professional.slug}><CheckCircle2 aria-hidden="true" size={22} /><span><strong>{professional.name}</strong><small>{professional.domain}</small></span></li>)}</ul>
        <Link className="text-command" href="/professionals">{messages.browseProfessionals} <ArrowRight aria-hidden="true" size={18} /></Link>
      </section>

      <section className="public-section trust-journey" aria-labelledby="trust-journey-title">
        <div><p className="eyebrow">02</p><h2 id="trust-journey-title">{messages.trustJourney}</h2><p>{messages.trustDescription}</p></div>
        <div><Scale aria-hidden="true" size={32} /><p className="eyebrow">Illustrative governance journey</p><h2>{messages.constitutionalPromise}</h2><p>{messages.constitutionalDescription}</p></div>
      </section>

      <section className="public-section final-action"><p className="eyebrow">A professional relationship you can inspect</p><h2>Begin with visible scope, honest limits, and control that stays with you.</h2><div className="command-row"><a className="primary-link" href="/register">Start with a trial</a><Link href="/professionals">Browse professionals</Link></div></section>
      <section className="platform-dna" aria-labelledby="platform-dna-title"><p className="eyebrow">Platform DNA</p><h2 id="platform-dna-title">Built through a connected institutional lineage.</h2><dl><div><dt>Yashus</dt><dd>Product and experience foundation</dd></div><div><dt>DLAI Satellite Data</dt><dd>Technology and operating company</dd></div><div><dt>WAOOAW</dt><dd>Constitutionally governed digital professionals</dd></div></dl></section>
    </div>
  );
}