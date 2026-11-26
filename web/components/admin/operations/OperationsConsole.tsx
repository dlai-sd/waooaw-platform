'use client';

// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008, WC171-R009
// Constitutional basis: C-023, C-049, C-059, C-063

import { useCallback, useEffect, useState } from 'react';
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
  type OverviewView,
  type PageRecord,
  type ResolutionRecord,
  type ResolveAction,
  type TimelineView,
} from '@/lib/operations-client';

const actionLabels: Record<ResolveAction, string> = {
  RETRY: 'Unblock',
  CLOSE_WITH_REASON: 'Close with a reason',
  MARK_UNDELIVERABLE: 'Mark undeliverable',
};

const actionPastTense: Record<ResolveAction, string> = {
  RETRY: 'Unblocked',
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
  const [overview, setOverview] = useState<OverviewView | null>(null);
  const [blocked, setBlocked] = useState<BlockedMessage[] | null>(null);
  const [history, setHistory] = useState<ResolutionRecord[]>([]);
  const [pages, setPages] = useState<PageRecord[] | null>(null);
  const [notice, setNotice] = useState<string>();
  const [error, setError] = useState<string>();
  const [stepUp, setStepUp] = useState(false);
  const [reasons, setReasons] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    const [overviewResult, blockedResult, pageResult, historyResult] = await Promise.all([
      readOverview(),
      readBlocked(),
      readPages(),
      readResolutions(),
    ]);
    if (!overviewResult.ok) {
      setError(overviewResult.reason === 'forbidden' ? copy.forbidden : copy.loadFailed);
      return;
    }
    setError(undefined);
    setOverview(overviewResult.data);
    setBlocked(blockedResult.ok ? blockedResult.data.items : []);
    setPages(pageResult.ok ? pageResult.data.items : []);
    setHistory(historyResult.ok ? historyResult.data.items : []);
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
      setReasons((current) => ({ ...current, [message.outboxId]: '' }));
      await load();
    } else if (result.reason === 'step-up') setStepUp(true);
    else setError(result.reason === 'forbidden' ? copy.forbidden : copy.failed);
  }

  async function acknowledge(signal: string) {
    const result = await acknowledgePage(signal);
    if (result.ok) await load();
    else setError(copy.failed);
  }

  const tabs: Array<{ id: TabId; label: string }> = [
    { id: 'overview', label: 'Overview' },
    {
      id: 'blocked',
      label: blocked && blocked.length > 0 ? `Blocked messages (${blocked.length})` : 'Blocked messages',
    },
    { id: 'pages', label: 'Pages' },
    ...(canResolve ? [{ id: 'customers' as const, label: 'Customers' }] : []),
    { id: 'work', label: 'Work and spend' },
  ];

  return (
    <div className="operations-body">
      <div aria-label="Operations sections" className="operations-tabs" role="tablist">
        {tabs.map((item) => (
          <button
            aria-selected={tab === item.id}
            className={tab === item.id ? 'primary-command' : 'secondary-link'}
            id={`operations-tab-${item.id}`}
            key={item.id}
            onClick={() => setTab(item.id)}
            role="tab"
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>
      <output aria-live="polite">{notice ?? ''}</output>
      {error ? <p role="alert">{error}</p> : null}
      {stepUp ? (
        <>
          <p>{copy.stepUp}</p>
          <StepUpCommand />
        </>
      ) : null}
      <div aria-labelledby={`operations-tab-${tab}`} role="tabpanel">
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
              Unblock puts the same message back on the queue. Your name, the time and your reason are recorded; the
              message is never deleted.
            </p>
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
                              onClick={() => void resolve(message, action)}
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
            {history.length === 0 ? (
              <p>No blocked message has been changed yet.</p>
            ) : (
              <ul className="portal-list">
                {history.map((entry) => (
                  <li className="portal-list-item" key={entry.resolutionId}>
                    {actionPastTense[entry.action]} · {when(entry.resolvedAt)} · by {entry.resolvedBy} — “{entry.reason}
                    ”
                  </li>
                ))}
              </ul>
            )}
          </section>
        ) : null}
        {tab === 'pages' ? (
          <section aria-labelledby="ops-pages">
            <h2 id="ops-pages">Pages</h2>
            <p>{copy.emitted}. A standing alert is recorded once an hour, not every check.</p>
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
