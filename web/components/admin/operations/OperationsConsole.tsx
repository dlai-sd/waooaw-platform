'use client';

// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008, WC171-R009
// Constitutional basis: C-023, C-049, C-059, C-063

import { useCallback, useEffect, useState } from 'react';
import { StepUpCommand } from '@/components/admin/StepUpCommand';
import {
  acknowledgePage,
  operationsCopy as copy,
  readBlocked,
  readOverview,
  readPages,
  readSpendChain,
  readTimeline,
  resolveBlocked,
  type BlockedMessage,
  type OverviewView,
  type PageRecord,
  type ResolveAction,
  type TimelineView,
} from '@/lib/operations-client';

const actionLabels: Record<ResolveAction, string> = {
  RETRY: 'Try again',
  CLOSE_WITH_REASON: 'Close with a reason',
  MARK_UNDELIVERABLE: 'Mark undeliverable',
};

const humanize = (value: string) => value.replaceAll('_', ' ').toLowerCase();

const idPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// The work timeline and the spend chain of one relationship, read for an operator who names the tenant and relationship.
function ChainLookup() {
  const [tenantId, setTenantId] = useState('');
  const [relationshipId, setRelationshipId] = useState('');
  const [timeline, setTimeline] = useState<TimelineView | null>(null);
  const [spend, setSpend] = useState<string>();
  const [problem, setProblem] = useState<string>();

  async function lookup() {
    setProblem(undefined);
    setTimeline(null);
    setSpend(undefined);
    if (!idPattern.test(tenantId.trim()) || !idPattern.test(relationshipId.trim())) {
      setProblem('Enter a tenant and a relationship as full identifiers.');
      return;
    }
    const [work, chain] = await Promise.all([
      readTimeline(tenantId.trim(), relationshipId.trim()),
      readSpendChain(tenantId.trim(), relationshipId.trim()),
    ]);
    if (work.ok) setTimeline(work.data);
    else setProblem(work.reason === 'forbidden' ? copy.forbidden : copy.loadFailed);
    setSpend(
      chain.ok
        ? `${chain.data.authorizations.length} authorizations, ${chain.data.items.length} items, ${chain.data.reconciliations.length} reconciliations`
        : 'The spend chain cannot be read yet: it needs a route grant to the billing engine.'
    );
  }

  return (
    <section aria-labelledby="ops-chain">
      <h2 id="ops-chain">Work and spend</h2>
      <label>
        Tenant
        <input onChange={(event) => setTenantId(event.target.value)} value={tenantId} />
      </label>
      <label>
        Relationship
        <input onChange={(event) => setRelationshipId(event.target.value)} value={relationshipId} />
      </label>
      <button className="secondary-link" onClick={() => void lookup()} type="button">
        Read
      </button>
      {problem ? <p role="alert">{problem}</p> : null}
      {timeline ? (
        <>
          <p>{timeline.emergencyStopActive ? 'Emergency Stop is active.' : 'No Emergency Stop.'}</p>
          <ul className="portal-list">
            {timeline.workItems.map((item) => (
              <li className="portal-list-item" key={item.workItemId}>
                {item.sentence} ({humanize(item.state)}
                {item.reasonCode ? `, ${humanize(item.reasonCode)}` : ''})
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {spend ? <p>{spend}</p> : null}
    </section>
  );
}

export function OperationsConsole({ canResolve }: { canResolve: boolean }) {
  const [overview, setOverview] = useState<OverviewView | null>(null);
  const [blocked, setBlocked] = useState<BlockedMessage[] | null>(null);
  const [pages, setPages] = useState<PageRecord[] | null>(null);
  const [notice, setNotice] = useState<string>();
  const [error, setError] = useState<string>();
  const [stepUp, setStepUp] = useState(false);
  const [reasons, setReasons] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    const [overviewResult, blockedResult, pageResult] = await Promise.all([readOverview(), readBlocked(), readPages()]);
    if (!overviewResult.ok) {
      setError(overviewResult.reason === 'forbidden' ? copy.forbidden : copy.loadFailed);
      return;
    }
    setError(undefined);
    setOverview(overviewResult.data);
    setBlocked(blockedResult.ok ? blockedResult.data.items : []);
    setPages(pageResult.ok ? pageResult.data.items : []);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function resolve(message: BlockedMessage, action: ResolveAction) {
    setNotice(undefined);
    setError(undefined);
    const reason = (reasons[message.outboxId] ?? '').trim();
    if (reason.length < 5) {
      setError('Write a reason of at least five characters.');
      return;
    }
    const result = await resolveBlocked(message.outboxId, action, reason);
    if (result.ok) {
      setNotice(copy.resolved);
      await load();
    } else if (result.reason === 'step-up') setStepUp(true);
    else setError(result.reason === 'forbidden' ? copy.forbidden : copy.failed);
  }

  async function acknowledge(signal: string) {
    const result = await acknowledgePage(signal);
    if (result.ok) await load();
    else setError(copy.failed);
  }

  return (
    <div className="operations-body">
      <output aria-live="polite">{notice ?? ''}</output>
      {error ? <p role="alert">{error}</p> : null}
      {stepUp ? (
        <>
          <p>{copy.stepUp}</p>
          <StepUpCommand />
        </>
      ) : null}
      {overview ? (
        <section aria-labelledby="ops-overview">
          <h2 id="ops-overview">Overview</h2>
          <dl className="detail-list">
            <div>
              <dt>Environment</dt>
              <dd>{overview.environment}</dd>
            </div>
            <div>
              <dt>WhatsApp</dt>
              <dd>
                {overview.whatsApp === 'ACTIVE'
                  ? 'Active'
                  : `Not active (${humanize(overview.whatsAppReason ?? 'unknown')})`}
              </dd>
            </div>
            <div>
              <dt>Open signals</dt>
              <dd>{overview.openSignals}</dd>
            </div>
            <div>
              <dt>Blocked messages</dt>
              <dd>
                {overview.blockedMessages}
                {overview.oldestBlockedMinutes != null
                  ? ` (oldest ${Math.round(overview.oldestBlockedMinutes)} min)`
                  : ''}
              </dd>
            </div>
            <div>
              <dt>Unresolved messages</dt>
              <dd>{overview.unresolvedMessages}</dd>
            </div>
            <div>
              <dt>Oldest queued</dt>
              <dd>
                {overview.oldestQueuedMinutes != null
                  ? `${Math.round(overview.oldestQueuedMinutes)} min`
                  : 'Nothing queued'}
              </dd>
            </div>
          </dl>
          <h3>Alert delivery, last 24 hours</h3>
          {overview.deliveries.length === 0 ? (
            <p>None recorded.</p>
          ) : (
            <ul className="portal-list">
              {overview.deliveries.map((item) => (
                <li className="portal-list-item" key={`${item.channel}-${item.outcome}`}>
                  {humanize(item.channel)}: {humanize(item.outcome)} — {item.count}
                </li>
              ))}
            </ul>
          )}
          <h3>Service health</h3>
          <ul className="portal-list">
            {overview.services.map((service) => (
              <li className="portal-list-item" key={service.name}>
                {humanize(service.name)}: {humanize(service.state)}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <section aria-labelledby="ops-blocked">
        <h2 id="ops-blocked">Blocked messages</h2>
        {blocked !== null && blocked.length === 0 ? <p>{copy.noBlocked}</p> : null}
        <ul className="portal-list">
          {(blocked ?? []).map((message) => (
            <li className="portal-list-item" key={message.outboxId}>
              <p>
                <strong>{humanize(message.purpose)}</strong> blocked for {Math.round(message.ageMinutes)} min
                {message.blockedReason ? ` — ${humanize(message.blockedReason)}` : ''} (attempt {message.attemptNumber})
              </p>
              {canResolve ? (
                <>
                  <label>
                    Reason
                    <input
                      maxLength={240}
                      onChange={(event) =>
                        setReasons((current) => ({ ...current, [message.outboxId]: event.target.value }))
                      }
                      value={reasons[message.outboxId] ?? ''}
                    />
                  </label>
                  <div className="alert-actions">
                    {(Object.keys(actionLabels) as ResolveAction[]).map((action) => (
                      <button
                        className="secondary-link"
                        key={action}
                        onClick={() => void resolve(message, action)}
                        type="button"
                      >
                        {actionLabels[action]}
                      </button>
                    ))}
                  </div>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      </section>
      <ChainLookup />
      <section aria-labelledby="ops-pages">
        <h2 id="ops-pages">Pages</h2>
        <p>{copy.emitted}.</p>
        {pages !== null && pages.length === 0 ? <p>{copy.noPages}</p> : null}
        <ul className="portal-list">
          {(pages ?? []).map((page, index) => (
            <li className="portal-list-item" key={`${page.signal}-${page.recordedAt}-${index}`}>
              {humanize(page.signal)}: {humanize(page.outcome)} · {new Date(page.recordedAt).toLocaleString('en')}
              {canResolve && page.outcome === 'EMITTED' ? (
                <button className="secondary-link" onClick={() => void acknowledge(page.signal)} type="button">
                  Acknowledge
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
