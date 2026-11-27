'use client';

// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008, WC171-R009
// Constitutional basis: C-023, C-049, C-059, C-063

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { StepUpCommand } from '@/components/admin/StepUpCommand';
import {
  acknowledgePage,
  operationsCopy as copy,
  readBlocked,
  readCustomers,
  readOverview,
  readPages,
  readResolutions,
  readSpendChain,
  readTimeline,
  resolveBlocked,
  type BlockedMessage,
  type CustomerEntry,
  type CustomerStatus,
  type OperationsResult,
  type ResolveAction,
  type TimelineView,
} from '@/lib/operations-client';
import { stepUpResumingText, useResumeAfterStepUp } from '@/lib/step-up-resume';

const actionLabels: Record<ResolveAction, string> = {
  RETRY: 'Retry send',
  CLOSE_WITH_REASON: 'Close with a reason',
  MARK_UNDELIVERABLE: 'Mark undeliverable',
};

const actionPastTense: Record<ResolveAction, string> = {
  RETRY: 'Retry queued',
  CLOSE_WITH_REASON: 'Closed',
  MARK_UNDELIVERABLE: 'Marked undeliverable',
};

const statusLabels: Record<CustomerStatus, string> = {
  LOGGED_IN_ONLY: 'Logged in only',
  REGISTRATION_STARTED: 'Registration started',
  REGISTERED: 'Registered',
};

const humanize = (value: string) => value.replaceAll('_', ' ').toLowerCase();
const when = (value: string) => new Date(value).toLocaleString('en');

const idPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type TabId = 'overview' | 'blocked' | 'pages' | 'customers' | 'work';

const resolveKey = 'operations.resolve';
const acknowledgeKey = 'operations.acknowledge';

// Each read is loading, loaded or failed on its own, so a failed read is never shown as an empty list.
type Remote<T> = { status: 'loading' } | { status: 'loaded'; data: T } | { status: 'failed'; message: string };

function failureText(reason: 'step-up' | 'forbidden' | 'inactive' | 'failed', what: string): string {
  if (reason === 'forbidden') return copy.forbidden;
  if (reason === 'inactive') return copy.inactive;
  return `${what} could not be loaded right now. Nothing was changed.`;
}

function useRemote<T>(reader: () => Promise<OperationsResult<T>>, what: string) {
  const [state, setState] = useState<Remote<T>>({ status: 'loading' });
  const reload = useCallback(async () => {
    const result = await reader();
    setState(
      result.ok
        ? { status: 'loaded', data: result.data }
        : { status: 'failed', message: failureText(result.reason, what) }
    );
  }, [reader, what]);
  const retry = useCallback(() => {
    setState({ status: 'loading' });
    void reload();
  }, [reload]);
  useEffect(() => {
    void reload();
  }, [reload]);
  return { state, reload, retry };
}

function LoadProblem({ state, onRetry }: { state: Remote<unknown>; onRetry: () => void }) {
  if (state.status === 'loading') return <output aria-busy="true">{copy.loading}</output>;
  if (state.status === 'failed') {
    return (
      <div>
        <p role="alert">{state.message}</p>
        <button className="secondary-link" onClick={onRetry} type="button">
          {copy.retryLoad}
        </button>
      </div>
    );
  }
  return null;
}

type PendingResolve = { outboxId: string; action: ResolveAction; reason: string };
type PendingStepUp = { key: string; payload: unknown };

function asPendingResolve(value: unknown): PendingResolve | null {
  const candidate = value as Partial<PendingResolve> | null;
  if (
    !candidate ||
    typeof candidate.outboxId !== 'string' ||
    typeof candidate.reason !== 'string' ||
    typeof candidate.action !== 'string' ||
    !(candidate.action in actionLabels)
  )
    return null;
  return { outboxId: candidate.outboxId, action: candidate.action as ResolveAction, reason: candidate.reason };
}

function spendChainProblem(result: { reason: string; code?: string }): string {
  if (result.reason === 'forbidden') return copy.forbidden;
  if (result.code?.includes('ROUTE_GRANT')) return copy.spendChainGrant;
  if (result.code === 'SPEND_CHAIN_READ_UNAVAILABLE') return copy.spendChainUnavailable;
  return copy.spendChainFailed;
}

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
        : spendChainProblem(chain)
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

// Who has signed in and who has registered: the latest ten first, filtered, one page at a time by cursor.
function CustomersPanel() {
  const [name, setName] = useState('');
  const [contact, setContact] = useState('');
  const [status, setStatus] = useState<CustomerStatus | ''>('');
  const [applied, setApplied] = useState({ name: '', contact: '', status: '' as CustomerStatus | '' });
  const [cursors, setCursors] = useState<string[]>([]);
  const [items, setItems] = useState<CustomerEntry[] | null>(null);
  const [next, setNext] = useState<string | null>(null);
  const [problem, setProblem] = useState<string>();

  const load = useCallback(async (filters: typeof applied, cursor?: string) => {
    const result = await readCustomers({ ...filters, cursor });
    if (!result.ok) {
      setProblem(result.reason === 'forbidden' ? copy.forbidden : copy.loadFailed);
      return;
    }
    setProblem(undefined);
    setItems(result.data.items);
    setNext(result.data.nextCursor ?? null);
  }, []);

  useEffect(() => {
    void load({ name: '', contact: '', status: '' });
  }, [load]);

  function search() {
    const filters = { name, contact, status };
    setApplied(filters);
    setCursors([]);
    void load(filters);
  }

  function older() {
    if (!next) return;
    setCursors((current) => [...current, next]);
    void load(applied, next);
  }

  function newer() {
    const remaining = cursors.slice(0, -1);
    setCursors(remaining);
    void load(applied, remaining[remaining.length - 1]);
  }

  return (
    <section aria-labelledby="ops-customers">
      <h2 id="ops-customers">Customers</h2>
      <p>People who have signed in at least once, newest activity first, ten at a time. Contact details are masked.</p>
      <form
        aria-label="Find customers"
        onSubmit={(event) => {
          event.preventDefault();
          search();
        }}
      >
        <label>
          Name starts with
          <input maxLength={120} onChange={(event) => setName(event.target.value)} value={name} />
        </label>
        <label>
          Email or mobile number (exact)
          <input maxLength={254} onChange={(event) => setContact(event.target.value)} value={contact} />
        </label>
        <label>
          Status
          <select onChange={(event) => setStatus(event.target.value as CustomerStatus | '')} value={status}>
            <option value="">All</option>
            {(Object.keys(statusLabels) as CustomerStatus[]).map((value) => (
              <option key={value} value={value}>
                {statusLabels[value]}
              </option>
            ))}
          </select>
        </label>
        <button className="primary-command" type="submit">
          Search
        </button>
      </form>
      {problem ? <p role="alert">{problem}</p> : null}
      {items !== null && items.length === 0 ? <p>{copy.noCustomers}</p> : null}
      {items !== null && items.length > 0 ? (
        <table aria-label="Customers">
          <thead>
            <tr>
              <th scope="col">Name</th>
              <th scope="col">Email</th>
              <th scope="col">Mobile</th>
              <th scope="col">Status</th>
              <th scope="col">First seen</th>
              <th scope="col">Last active</th>
              <th scope="col">Registered</th>
            </tr>
          </thead>
          <tbody>
            {items.map((customer) => (
              <tr key={customer.registrationId}>
                <th scope="row">{customer.displayName || 'No name yet'}</th>
                <td>{customer.maskedEmail ?? '-'}</td>
                <td>{customer.maskedMobile ?? '-'}</td>
                <td>{statusLabels[customer.status]}</td>
                <td>{when(customer.firstSeenAt)}</td>
                <td>{when(customer.lastActiveAt)}</td>
                <td>{customer.registeredAt ? when(customer.registeredAt) : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <div className="alert-actions">
        <button className="secondary-link" disabled={cursors.length === 0} onClick={newer} type="button">
          Newer
        </button>
        <button className="secondary-link" disabled={!next} onClick={older} type="button">
          Older
        </button>
      </div>
    </section>
  );
}

export function OperationsConsole({ canResolve }: { canResolve: boolean }) {
  const [tab, setTab] = useState<TabId>('overview');
  const overviewRead = useRemote(readOverview, 'The overview');
  const blockedRead = useRemote(readBlocked, 'Blocked messages');
  const pagesRead = useRemote(readPages, 'Urgent alerts');
  const historyRead = useRemote(readResolutions, 'Recent changes');
  const [notice, setNotice] = useState<string>();
  const [error, setError] = useState<string>();
  const [stepUp, setStepUp] = useState<PendingStepUp | null>(null);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  const overview = overviewRead.state.status === 'loaded' ? overviewRead.state.data : null;
  const blocked = blockedRead.state.status === 'loaded' ? blockedRead.state.data.items : null;
  const history = historyRead.state.status === 'loaded' ? historyRead.state.data.items : null;
  const pages = pagesRead.state.status === 'loaded' ? pagesRead.state.data.items : null;

  const { reload: reloadOverview } = overviewRead;
  const { reload: reloadBlocked } = blockedRead;
  const { reload: reloadPages } = pagesRead;
  const { reload: reloadHistory } = historyRead;
  const load = useCallback(
    () => Promise.all([reloadOverview(), reloadBlocked(), reloadPages(), reloadHistory()]),
    [reloadOverview, reloadBlocked, reloadPages, reloadHistory]
  );

  async function submitResolution(outboxId: string, action: ResolveAction, reason: string) {
    setNotice(undefined);
    setError(undefined);
    setStepUp(null);
    const result = await resolveBlocked(outboxId, action, reason);
    if (result.ok) {
      setNotice(action === 'RETRY' ? copy.retryQueued : copy.resolved);
      setReasons((current) => ({ ...current, [outboxId]: '' }));
      await load();
    } else if (result.reason === 'step-up') setStepUp({ key: resolveKey, payload: { outboxId, action, reason } });
    else if (result.reason === 'forbidden') setError(copy.forbidden);
    else if (action === 'RETRY') setError(result.reason === 'inactive' ? copy.retryInactive : copy.retryFailed);
    else setError(copy.failed);
  }

  function resolve(message: BlockedMessage, action: ResolveAction) {
    setNotice(undefined);
    setError(undefined);
    const reason = (reasons[message.outboxId] ?? '').trim();
    if (reason.length < 5) {
      setError('Write a reason of at least five characters.');
      return;
    }
    void submitResolution(message.outboxId, action, reason);
  }

  async function acknowledge(signal: string) {
    setError(undefined);
    setStepUp(null);
    const result = await acknowledgePage(signal);
    if (result.ok) await load();
    else if (result.reason === 'step-up') setStepUp({ key: acknowledgeKey, payload: { signal } });
    else setError(result.reason === 'forbidden' ? copy.forbidden : copy.failed);
  }

  const resumingResolve = useResumeAfterStepUp<unknown>(resolveKey, async (payload) => {
    const pending = asPendingResolve(payload);
    if (!pending) return;
    setTab('blocked');
    setReasons((current) => ({ ...current, [pending.outboxId]: pending.reason }));
    await submitResolution(pending.outboxId, pending.action, pending.reason);
  });
  const resumingAcknowledge = useResumeAfterStepUp<{ signal?: unknown }>(acknowledgeKey, async (payload) => {
    if (typeof payload.signal !== 'string') return;
    setTab('pages');
    await acknowledge(payload.signal);
  });

  const tabs: Array<{ id: TabId; label: string }> = [
    { id: 'overview', label: 'Overview' },
    {
      id: 'blocked',
      label: blocked && blocked.length > 0 ? `Blocked messages (${blocked.length})` : 'Blocked messages',
    },
    { id: 'pages', label: 'Urgent alerts' },
    ...(canResolve ? [{ id: 'customers' as const, label: 'Customers' }] : []),
    { id: 'work', label: 'Work and spend' },
  ];

  function moveTab(event: KeyboardEvent<HTMLButtonElement>) {
    const current = Math.max(
      0,
      tabs.findIndex((item) => item.id === tab)
    );
    let target: number;
    if (event.key === 'ArrowRight') target = (current + 1) % tabs.length;
    else if (event.key === 'ArrowLeft') target = (current - 1 + tabs.length) % tabs.length;
    else if (event.key === 'Home') target = 0;
    else if (event.key === 'End') target = tabs.length - 1;
    else return;
    event.preventDefault();
    const next = tabs[target].id;
    setTab(next);
    tabRefs.current[next]?.focus();
  }

  return (
    <div className="operations-body">
      <div aria-label="Operations sections" className="operations-tabs" role="tablist">
        {tabs.map((item) => (
          <button
            aria-controls="operations-tabpanel"
            aria-selected={tab === item.id}
            className={tab === item.id ? 'primary-command' : 'secondary-link'}
            id={`operations-tab-${item.id}`}
            key={item.id}
            onClick={() => setTab(item.id)}
            onKeyDown={moveTab}
            ref={(node) => {
              tabRefs.current[item.id] = node;
            }}
            role="tab"
            tabIndex={tab === item.id ? 0 : -1}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>
      <output aria-live="polite">{resumingResolve || resumingAcknowledge ? stepUpResumingText : (notice ?? '')}</output>
      {error ? <p role="alert">{error}</p> : null}
      {stepUp ? (
        <>
          <p>
            {copy.stepUp} {copy.stepUpResume}
          </p>
          <StepUpCommand payload={stepUp.payload} pendingKey={stepUp.key} />
        </>
      ) : null}
      <div aria-labelledby={`operations-tab-${tab}`} id="operations-tabpanel" role="tabpanel">
        {tab === 'overview' && overview === null ? (
          <section aria-labelledby="ops-overview">
            <h2 id="ops-overview">Overview</h2>
            <LoadProblem onRetry={overviewRead.retry} state={overviewRead.state} />
          </section>
        ) : null}
        {tab === 'overview' && overview ? (
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
        {tab === 'blocked' ? (
          <section aria-labelledby="ops-blocked">
            <h2 id="ops-blocked">Blocked messages</h2>
            <p>
              Retry send puts the same message back on the queue. It does not confirm that WhatsApp delivered it; the
              message leaves this list when it is no longer blocked. Your name, the time and your reason are recorded;
              the message is never deleted.
            </p>
            <LoadProblem onRetry={blockedRead.retry} state={blockedRead.state} />
            {blocked !== null && blocked.length === 0 ? <p>{copy.noBlocked}</p> : null}
            <ul className="portal-list">
              {(blocked ?? []).map((message) => (
                <li className="portal-list-item" key={message.outboxId}>
                  <p>
                    <strong>{humanize(message.purpose)}</strong> blocked for {Math.round(message.ageMinutes)} min (
                    attempt {message.attemptNumber})
                  </p>
                  <p>Why: {message.reasonText}</p>
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
                        {(Object.keys(actionLabels) as ResolveAction[])
                          .filter((action) => action !== 'RETRY' || message.canUnblock)
                          .map((action) => (
                            <button
                              className="secondary-link"
                              key={action}
                              onClick={() => resolve(message, action)}
                              type="button"
                            >
                              {actionLabels[action]}
                            </button>
                          ))}
                      </div>
                      {message.canUnblock ? null : (
                        <p className="workbench-hint">
                          This message cannot be sent again. Close it or mark it undeliverable.
                        </p>
                      )}
                    </>
                  ) : null}
                </li>
              ))}
            </ul>
            <h3>Recent changes</h3>
            <LoadProblem onRetry={historyRead.retry} state={historyRead.state} />
            {history !== null && history.length === 0 ? <p>No blocked message has been changed yet.</p> : null}
            {history !== null && history.length > 0 ? (
              <ul className="portal-list">
                {history.map((entry) => (
                  <li className="portal-list-item" key={entry.resolutionId}>
                    {actionPastTense[entry.action]} · {when(entry.resolvedAt)} · by {entry.resolvedBy} — “{entry.reason}
                    ”
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        ) : null}
        {tab === 'pages' ? (
          <section aria-labelledby="ops-pages">
            <h2 id="ops-pages">Urgent alerts</h2>
            <p>
              Alerts that ask a person to act now, such as a message stuck for over half an hour. {copy.emitted}. A
              standing alert is recorded once an hour, not every check.
            </p>
            <LoadProblem onRetry={pagesRead.retry} state={pagesRead.state} />
            {pages !== null && pages.length === 0 ? <p>{copy.noPages}</p> : null}
            <ul className="portal-list">
              {(pages ?? []).map((page, index) => (
                <li className="portal-list-item" key={`${page.signal}-${page.outcome}-${index}`}>
                  {humanize(page.signal)}: {humanize(page.outcome)} ·{' '}
                  {page.count > 1
                    ? `${page.count} times, first ${when(page.firstRecordedAt)}, last ${when(page.recordedAt)}`
                    : when(page.recordedAt)}
                  {canResolve && page.outcome === 'EMITTED' ? (
                    <button className="secondary-link" onClick={() => void acknowledge(page.signal)} type="button">
                      Acknowledge
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        {tab === 'customers' ? <CustomersPanel /> : null}
        {tab === 'work' ? <ChainLookup /> : null}
      </div>
    </div>
  );
}
