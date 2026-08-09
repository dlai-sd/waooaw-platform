// Implements: architecture/reference/ux/hybrid-application-shell.md §Product Decisions and Release Gates
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import { ArrowRight, ShieldCheck } from 'lucide-react';
import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="public-home">
      <section className="public-hero">
        <p className="eyebrow">Constitutionally governed digital professionals</p>
        <h1>WAOOAW</h1>
        <p className="hero-copy">Employ a professional whose scope is visible, whose work is reviewable, and whom you can stop at any time.</p>
        <div className="command-row"><Link className="primary-link" href="/professionals">Browse professionals <ArrowRight aria-hidden="true" size={18} /></Link><Link href="/login">Continue to your workspace</Link></div>
      </section>
      <section className="trust-strip" aria-label="WAOOAW safeguards"><ShieldCheck aria-hidden="true" size={26} /><div><strong>Control remains yours.</strong><span>Clear scope, evidence-backed states, and persistent Emergency Stop.</span></div></section>
    </div>
  );
}