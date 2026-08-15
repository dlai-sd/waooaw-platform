// Implements: architecture/reference/ux/hybrid-application-shell.md §Product Decisions and Release Gates
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import { ArrowRight, BriefcaseBusiness, CheckCircle2, Scale, ShieldCheck } from 'lucide-react';
import { getRequestI18n } from '@/lib/i18n-server';

export default async function HomePage() {
  const { messages } = await getRequestI18n();
  const steps = [messages.stepBusiness, messages.stepScope, messages.stepControl];
  const professionalCategories = [messages.marketingExpert, messages.agricultureExpert, messages.tradingExpert, messages.tutorExpert];
  return (
    <div className="public-home">
      <div className="public-intro">
        <section className="public-hero">
          <p className="eyebrow">{messages.publicEyebrow}</p>
          <h1>WAOOAW</h1>
          <p className="hero-copy">{messages.publicDescription}</p>
          <div className="command-row"><a className="primary-link" href="/professionals">{messages.browseProfessionals} <ArrowRight aria-hidden="true" size={18} /></a><a href="/login">{messages.continueWorkspace}</a></div>
        </section>
        <section className="trust-strip" aria-label={messages.safeguards}><ShieldCheck aria-hidden="true" size={26} /><div><strong>{messages.controlYours}</strong><span>{messages.safeguardsDescription}</span></div></section>
      </div>

      <section className="public-section journey-section" aria-labelledby="getting-started-title">
        <div className="section-heading"><p className="eyebrow">01</p><h2 id="getting-started-title">{messages.gettingStarted}</h2><p>{messages.gettingStartedDescription}</p></div>
        <ol className="journey-steps">{steps.map((step, index) => <li key={step}><span>{index + 1}</span><strong>{step}</strong></li>)}</ol>
      </section>

      <section className="public-section professionals-section" aria-labelledby="expert-professionals-title">
        <div className="section-heading"><BriefcaseBusiness aria-hidden="true" size={28} /><h2 id="expert-professionals-title">{messages.expertProfessionals}</h2><p>{messages.expertDescription}</p></div>
        <ul className="professional-grid">{professionalCategories.map((category) => <li key={category}><CheckCircle2 aria-hidden="true" size={22} /><strong>{category}</strong></li>)}</ul>
        <a className="text-command" href="/professionals">{messages.browseProfessionals} <ArrowRight aria-hidden="true" size={18} /></a>
      </section>

      <section className="public-section trust-journey" aria-labelledby="trust-journey-title">
        <div><p className="eyebrow">02</p><h2 id="trust-journey-title">{messages.trustJourney}</h2><p>{messages.trustDescription}</p></div>
        <div><Scale aria-hidden="true" size={32} /><h2>{messages.constitutionalPromise}</h2><p>{messages.constitutionalDescription}</p></div>
      </section>
    </div>
  );
}