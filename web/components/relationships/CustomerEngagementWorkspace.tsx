'use client';

// Implements: WC-121 Components 02-06 conversation-first customer engagement workspace
// Constitutional basis: C-001, C-005, C-007, C-023, C-026, C-059, C-063

import { AlertCircle, CheckCircle2, CircleDashed, ExternalLink, RefreshCw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import type { CustomerEngagementProgressV1 } from '@/lib/api/generated/models/CustomerEngagementProgressV1';
import type { WorkspaceFocusRefV1 } from '@/lib/api/generated/models/WorkspaceFocusRefV1';

const stateLabel = (value: string) => value.replaceAll('_', ' ').toLowerCase();

function TruthState({ label, value }: { label: string; value: string }) {
  const Icon =
    value === 'COMPLETED' || value === 'RECORDED' ? CheckCircle2 : value === 'UNKNOWN' ? AlertCircle : CircleDashed;
  return (
    <span className="engagement-truth-state" data-state={value.toLowerCase()}>
      <Icon aria-hidden="true" size={15} />
      {label}: {stateLabel(value)}
    </span>
  );
}

export function CustomerEngagementWorkspace({
  progress,
}: {
  progress: CustomerEngagementProgressV1;
}) {
  const router = useRouter();
  const [resolving, setResolving] = useState<string>();
  const [problem, setProblem] = useState<string>();

  async function resolveFocus(focus: WorkspaceFocusRefV1) {
    setResolving(focus.focusToken);
    setProblem(undefined);
    const response = await fetch(`/api/relationships/${progress.relationshipId}/focus-resolutions`, {
      body: JSON.stringify({ focusToken: focus.focusToken }),
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      method: 'POST',
    });
    const body = (await response.json().catch(() => undefined)) as
      | { canonicalRoute?: unknown; title?: unknown }
      | undefined;
    if (!response.ok || typeof body?.canonicalRoute !== 'string') {
      setProblem(
        typeof body?.title === 'string'
          ? body.title
          : 'This destination cannot be confirmed. Refresh progress before trying again.'
      );
      setResolving(undefined);
      return;
    }
    router.push(body.canonicalRoute);
  }

  return (
    <section className="customer-engagement-workspace" aria-labelledby="engagement-workspace-title">
      <header>
        <div>
          <p className="section-label">{stateLabel(progress.lifecycleStage)}</p>
          <h2 id="engagement-workspace-title">{progress.headline}</h2>
          {progress.summary ? <p>{progress.summary}</p> : null}
        </div>
        <button aria-label="Refresh current progress" onClick={() => router.refresh()} type="button">
          <RefreshCw aria-hidden="true" size={17} />
          Refresh
        </button>
      </header>

      <nav aria-label="Relationship workspace destinations" className="engagement-focus-navigation">
        {progress.availableFocuses.map((focus) => (
          <button
            disabled={resolving !== undefined}
            key={`${focus.destination}:${focus.expiresAt.toISOString()}`}
            onClick={() => resolveFocus(focus)}
            type="button"
          >
            {focus.label}
            <ExternalLink aria-hidden="true" size={15} />
          </button>
        ))}
      </nav>

      {problem ? (
        <p aria-live="assertive" className="engagement-problem" role="alert">
          {problem}
        </p>
      ) : null}

      <ol className="engagement-progress-list">
        {progress.items.map((item) => (
          <li data-state={item.state.toLowerCase()} key={item.itemId}>
            <div>
              <strong>{item.title}</strong>
              <span>{stateLabel(item.state)}</span>
            </div>
            {item.summary ? <p>{item.summary}</p> : null}
            {item.blockedEffect ? <p className="engagement-blocked-effect">{item.blockedEffect}</p> : null}
            <div aria-label={`${item.title} truth`} className="engagement-truth">
              <TruthState label="Delivery" value={item.truth.delivery} />
              <TruthState label="Processing" value={item.truth.processing} />
              <TruthState label="Evidence" value={item.truth.evidence} />
              <TruthState label="Commercial" value={item.truth.commercial} />
              <TruthState label="Outcome" value={item.truth.outcome} />
            </div>
            <small>
              Confirmed by {stateLabel(item.provenance.sourceOwner)} at{' '}
              {item.provenance.lastAuthoritativeConfirmationAt.toLocaleString('en-IN')}
            </small>
            {item.nextAction ? (
              <button
                disabled={resolving !== undefined}
                onClick={() => item.nextAction && resolveFocus(item.nextAction.focus)}
                type="button"
              >
                {resolving === item.nextAction.focus.focusToken ? 'Confirming…' : item.nextAction.label}
              </button>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
