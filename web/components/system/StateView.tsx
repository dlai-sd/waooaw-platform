// Implements: architecture/reference/ux/hybrid-application-shell.md §Interaction and Failure Semantics
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { AlertTriangle, ArrowLeft, Inbox, LoaderCircle } from 'lucide-react';
import Link from 'next/link';

type StateKind = 'empty' | 'error' | 'forbidden' | 'loading' | 'not-found';

const icons = { empty: Inbox, error: AlertTriangle, forbidden: AlertTriangle, loading: LoaderCircle, 'not-found': AlertTriangle };

export function StateView({ actionHref = '/', actionLabel = 'Return home', description, kind, title }: {
  actionHref?: string; actionLabel?: string; description: string; kind: StateKind; title: string;
}) {
  const Icon = icons[kind];
  return (
    <section className="state-view" aria-live={kind === 'loading' ? 'polite' : undefined}>
      <Icon aria-hidden="true" className={kind === 'loading' ? 'spin' : undefined} size={32} />
      <h1>{title}</h1>
      <p>{description}</p>
      {kind === 'loading' ? null : <Link href={actionHref}><ArrowLeft aria-hidden="true" size={18} /> {actionLabel}</Link>}
    </section>
  );
}