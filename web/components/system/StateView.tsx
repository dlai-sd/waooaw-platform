// Implements: architecture/reference/ux/hybrid-application-shell.md §Interaction and Failure Semantics
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { AlertTriangle, ArrowLeft, Inbox, LoaderCircle } from 'lucide-react';

type StateKind = 'empty' | 'error' | 'forbidden' | 'loading' | 'not-found';
type StateViewProps = {
  actionHref?: string;
  correlationId?: string;
  description: string;
  reasonCode?: string;
  title: string;
} & ({ actionLabel?: never; kind: 'loading' } | { actionLabel: string; kind: Exclude<StateKind, 'loading'> });

const icons = {
  empty: Inbox,
  error: AlertTriangle,
  forbidden: AlertTriangle,
  loading: LoaderCircle,
  'not-found': AlertTriangle,
};

export function StateView(props: StateViewProps) {
  const { actionHref = '/', description, kind, title } = props;
  const Icon = icons[kind];
  return (
    <section
      className="state-view"
      aria-live={kind === 'loading' ? 'polite' : undefined}
      data-reason-code={props.reasonCode}
    >
      <Icon aria-hidden="true" className={kind === 'loading' ? 'spin' : undefined} size={32} />
      <h1>{title}</h1>
      <p>{description}</p>
      {props.correlationId ? <p>Reference: {props.correlationId}</p> : null}
      {kind === 'loading' ? null : (
        <a href={actionHref}>
          <ArrowLeft aria-hidden="true" size={18} /> {props.actionLabel}
        </a>
      )}
    </section>
  );
}
