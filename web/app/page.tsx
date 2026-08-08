'use client';

import { ArrowRight, ShieldCheck } from 'lucide-react';
import { signIn, useSession, SessionProvider } from 'next-auth/react';

function AccessPanel() {
  const { status } = useSession();
  return (
    <main className="access-page">
      <section className="access-copy">
        <p className="brand">WAOOAW</p>
        <h1>Your professional relationship, under your control.</h1>
        <p className="lede">One durable workspace for rights, employment state, evidence, and Emergency Stop.</p>
        <button
          className="primary-command"
          type="button"
          onClick={() => signIn('keycloak')}
          disabled={status === 'loading'}
        >
          Sign in securely <ArrowRight aria-hidden="true" size={18} />
        </button>
      </section>
      <aside className="trust-band" aria-label="Constitutional safeguards">
        <ShieldCheck aria-hidden="true" size={28} />
        <strong>Evidence before action</strong>
        <span>Tenant-isolated access with customer-controlled Stop.</span>
      </aside>
    </main>
  );
}

export default function HomePage() {
  return (
    <SessionProvider>
      <AccessPanel />
    </SessionProvider>
  );
}