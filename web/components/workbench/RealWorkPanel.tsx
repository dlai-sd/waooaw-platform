'use client';

// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2 to DC-5 customer projections (WC170-R005 to WC170-R008)
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-023, C-042, C-049, C-059, C-063

import { useCallback, useEffect, useState } from 'react';
import {
  humanize,
  type DecisionCommandKind,
  type OutcomeClaim,
  type RealWorkArtifactItem,
  type RealWorkSnapshot,
  type TimelineWorkItem,
} from '@/lib/api/real-work-types';
import { realWorkCopy as copy } from '@/lib/real-work-copy';

type Props = { relationshipId: string; initial?: RealWorkSnapshot | null };

type DecisionResult = 'ok' | 'strong-sign-in' | 'failed';

export async function decide(
  relationshipId: string,
  kind: DecisionCommandKind,
  item: RealWorkArtifactItem,
  commandContext: NonNullable<RealWorkSnapshot['artifacts']>['commandContext']
): Promise<DecisionResult> {
  let response: Response;
  try {
    response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/real-work`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        idempotencyKey: crypto.randomUUID(),
        kind,
        artifactId: item.artifact.artifactId,
        artifactDigest: item.artifact.digest,
        commandContext,
      }),
    });
  } catch {
    return 'failed';
  }
  if (response.status === 403) return 'strong-sign-in';
  if (!response.ok) return 'failed';
  const body = (await response.json().catch(() => null)) as { state?: string } | null;
  return body?.state === 'BLOCKED' || body?.state === 'REJECTED' ? 'failed' : 'ok';
}

function StepState({ done }: { done: boolean }) {
  return <span data-state={done ? 'done' : 'waiting'}>{done ? copy.done : copy.waiting}</span>;
}

function DecisionCard({
  item,
  busy,
  onDecide,
}: {
  item: RealWorkArtifactItem;
  busy: boolean;
  onDecide: (kind: DecisionCommandKind, item: RealWorkArtifactItem) => void;
}) {
  const { artifact, decisions } = item;
  const replaced = artifact.status === 'SUPERSEDED';
  return (
    <li className="workbench-card" data-status={artifact.status}>
      <h4>
        {humanize(artifact.artifactType)} · {copy.versionLabel} {artifact.version}
      </h4>
      <p>{artifact.plainLanguageSummary}</p>
      {artifact.authorityBoundary ? (
        <p>
          <strong>{copy.authorityLabel}:</strong> {artifact.authorityBoundary}
        </p>
      ) : null}
      {artifact.limitations.length > 0 ? (
        <>
          <p>{copy.limitationsLabel}</p>
          <ul className="workbench-plain-list">
            {artifact.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </>
      ) : null}
      <details>
        <summary>{copy.seeEveryDetail}</summary>
        <pre>{JSON.stringify(artifact.content ?? {}, null, 2)}</pre>
        <p className="workbench-hint">
          {copy.digestLabel}: <code>{artifact.digest.slice(0, 12)}</code>
        </p>
      </details>
      {replaced ? (
        <p className="workbench-hint">{copy.replaced}</p>
      ) : (
        <ol className="workbench-plain-list" aria-label={copy.decisionsTitle}>
          <li>
            <strong>{copy.stepApprove}</strong> <StepState done={decisions.approval !== null} />
            <p>{copy.stepApproveQuestion}</p>
            <button
              className="primary-command"
              disabled={busy || decisions.approval !== null || artifact.status !== 'PROPOSED'}
              onClick={() => onDecide('ACCEPT_ARTIFACT_VERSION', item)}
              type="button"
            >
              {copy.approveAction}
            </button>
          </li>
          <li>
            <strong>{copy.stepScope}</strong> <StepState done={decisions.scopeConfirmation !== null} />
            <p>{copy.stepScopeQuestion}</p>
            <button
              className="primary-command"
              disabled={busy || decisions.approval === null || decisions.scopeConfirmation !== null}
              onClick={() => onDecide('CONFIRM_SCOPE_BOUNDARY', item)}
              type="button"
            >
              {copy.scopeAction}
            </button>
          </li>
        </ol>
      )}
      {decisions.executable ? <p className="workbench-hint">{copy.executable}</p> : null}
    </li>
  );
}

function TimelineItem({ item }: { item: TimelineWorkItem }) {
  const evidence = item.events.reduce((count, event) => count + event.evidenceRefs.length, 0);
  return (
    <li data-state={item.state.toLowerCase()}>
      <strong>{copy.states[item.state] ?? humanize(item.state)}</strong> · {item.sentence}
      <details>
        <summary>{copy.details}</summary>
        <ul className="workbench-plain-list">
          {item.events.map((event) => (
            <li key={event.eventId}>
              <time dateTime={event.occurredAt}>{new Date(event.occurredAt).toLocaleString()}</time> ·{' '}
              {copy.states[event.state] ?? event.state} · {event.sentence}
            </li>
          ))}
          <li>{copy.evidenceCount(evidence)}</li>
        </ul>
      </details>
    </li>
  );
}

function Claim({ claim, timeline }: { claim: OutcomeClaim; timeline: RealWorkSnapshot['timeline'] }) {
  const behind = (timeline?.workItems ?? []).filter((item) => claim.workItemIds.includes(item.workItemId));
  return (
    <li>
      <strong>{claim.claimText}</strong>
      {claim.label ? <span className="workbench-hint"> · {claim.label}</span> : null}
      <details>
        <summary>{copy.traceLabel}</summary>
        <p>{copy.workBehind}</p>
        <ul className="workbench-plain-list">
          {behind.map((item) => (
            <li key={item.workItemId}>{item.sentence}</li>
          ))}
        </ul>
        <p>{copy.evidenceBehind}</p>
        <ul className="workbench-plain-list">
          {claim.evidenceIds.map((evidence) => (
            <li key={evidence}>{evidence}</li>
          ))}
        </ul>
        {claim.limitations.map((limitation) => (
          <p className="workbench-hint" key={limitation}>
            {limitation}
          </p>
        ))}
      </details>
    </li>
  );
}

export function RealWorkView({
  snapshot,
  busy,
  message,
  onDecide,
}: {
  snapshot: RealWorkSnapshot;
  busy: boolean;
  message: string;
  onDecide: (kind: DecisionCommandKind, item: RealWorkArtifactItem) => void;
}) {
  const items = (snapshot.artifacts?.items ?? []).filter((item) => item.artifact.status !== 'DRAFT');
  const timeline = snapshot.timeline;
  const outcomes = snapshot.outcomes;
  return (
    <div className="workbench-stack">
      <output aria-live="polite">{message}</output>
      <section aria-labelledby="real-work-decisions" className="workbench-section">
        <h3 id="real-work-decisions">{copy.decisionsTitle}</h3>
        {snapshot.artifacts === null ? <p role="alert">{copy.unavailable}</p> : null}
        {snapshot.artifacts !== null && items.length === 0 ? <p>{copy.noDecisions}</p> : null}
        <ul className="workbench-cards">
          {items.map((item) => (
            <DecisionCard busy={busy} item={item} key={item.artifact.artifactId} onDecide={onDecide} />
          ))}
        </ul>
      </section>
      <section aria-labelledby="real-work-timeline" className="workbench-section">
        <h3 id="real-work-timeline">{copy.timelineTitle}</h3>
        {timeline === null ? <p role="alert">{copy.unavailable}</p> : null}
        {timeline?.emergencyStopActive ? <p role="alert">{copy.stopActive}</p> : null}
        {timeline !== null && timeline.workItems.length === 0 ? <p>{copy.noTimeline}</p> : null}
        <ol className="workbench-plain-list">
          {(timeline?.workItems ?? []).map((item) => (
            <TimelineItem item={item} key={item.workItemId} />
          ))}
        </ol>
      </section>
      <section aria-labelledby="real-work-results" className="workbench-section">
        <h3 id="real-work-results">{copy.resultsTitle}</h3>
        {outcomes === null ? <p role="alert">{copy.unavailable}</p> : null}
        <h4>{copy.activityTitle}</h4>
        <p className="workbench-hint">{copy.activityNote}</p>
        {outcomes !== null && outcomes.activity.length === 0 ? <p>{copy.noResults}</p> : null}
        <ul className="workbench-plain-list">
          {(outcomes?.activity ?? []).map((claim) => (
            <Claim claim={claim} key={claim.claimId} timeline={timeline} />
          ))}
        </ul>
        {(outcomes?.agentStated.length ?? 0) > 0 ? (
          <>
            <h4>{copy.agentStatedTitle}</h4>
            <ul className="workbench-plain-list">
              {(outcomes?.agentStated ?? []).map((claim) => (
                <Claim claim={claim} key={claim.claimId} timeline={timeline} />
              ))}
            </ul>
          </>
        ) : null}
        <h4>{copy.businessResultsTitle}</h4>
        {(outcomes?.outcomes ?? []).map((claim) => (
          <p key={claim.claimId}>{claim.claimText}</p>
        ))}
        <ul className="workbench-plain-list">
          {(outcomes?.notMeasurableYet ?? []).map((slot) => (
            <li key={slot.measureId}>
              {humanize(slot.measureId)}: {copy.notMeasurable}
            </li>
          ))}
        </ul>
        {(outcomes?.withheldClaims ?? 0) > 0 ? (
          <p className="workbench-hint">{copy.withheld(outcomes?.withheldClaims ?? 0)}</p>
        ) : null}
      </section>
    </div>
  );
}

export function RealWorkPanel({ relationshipId, initial = null }: Props) {
  const [snapshot, setSnapshot] = useState<RealWorkSnapshot | null>(initial);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    try {
      const response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/real-work`, {
        cache: 'no-store',
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error('unavailable');
      setSnapshot((await response.json()) as RealWorkSnapshot);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, [relationshipId]);

  useEffect(() => {
    if (initial === null) void load();
  }, [initial, load]);

  const onDecide = useCallback(
    async (kind: DecisionCommandKind, item: RealWorkArtifactItem) => {
      setBusy(true);
      setMessage('');
      const result = await decide(relationshipId, kind, item, snapshot?.artifacts?.commandContext ?? null);
      if (result === 'strong-sign-in') setMessage(copy.strongSignIn);
      else if (result === 'failed') setMessage(copy.decisionFailed);
      await load();
      setBusy(false);
    },
    [relationshipId, snapshot, load]
  );

  if (snapshot === null) return <p>{failed ? copy.unavailable : copy.loading}</p>;
  return <RealWorkView busy={busy} message={message} onDecide={onDecide} snapshot={snapshot} />;
}
