'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R017, R018, R020, R021, R022
// Constitutional basis: C-001, C-023, C-042, C-059, C-063

import { useCallback, useEffect, useState } from 'react';
import {
  humanize,
  operationApi,
  problemText,
  type ItemView,
  type ModeId,
  type PlatformView,
} from '@/lib/agent-operation';
import type { OperationMessages } from '@/lib/operation-i18n';
import { ItemCard } from './ItemCard';

type Common = { relationshipId: string; copy: OperationMessages; onChanged: () => void; refreshKey: number };

function useItems(relationshipId: string, kinds: string[], refreshKey: number) {
  const [items, setItems] = useState<ItemView[] | null>(null);
  const [failed, setFailed] = useState(false);
  const joined = kinds.join(',');
  const load = useCallback(async () => {
    const results = await Promise.all(joined.split(',').map((kind) => operationApi.items(relationshipId, kind)));
    setFailed(results.some((result) => !result.ok));
    setItems(results.flatMap((result) => (result.ok ? result.data : [])));
  }, [relationshipId, joined]);
  useEffect(() => {
    void load();
  }, [load, refreshKey]);
  return { items, failed, load };
}

function Failed({ copy, retry }: { copy: OperationMessages; retry: () => void }) {
  return (
    <div role="alert">
      <p>{copy.failed}</p>
      <button className="secondary-link" onClick={retry} type="button">
        {copy.retry}
      </button>
    </div>
  );
}

function ScheduleForm({
  content,
  platforms,
  relationshipId,
  copy,
  onChanged,
  onGoMode,
}: {
  content: ItemView;
  platforms: PlatformView[];
  relationshipId: string;
  copy: OperationMessages;
  onChanged: () => void;
  onGoMode?: (mode: ModeId) => void;
}) {
  const choices = platforms.filter((platform) => platform.presence === 'CONNECTED_TESTED');
  const [platformId, setPlatformId] = useState(content.platformId ?? choices[0]?.platformId ?? '');
  const [date, setDate] = useState('');
  const [message, setMessage] = useState('');
  const [gate, setGate] = useState<ModeId | null>(null);

  async function schedule() {
    const result = await operationApi.schedule(relationshipId, content.itemId, platformId, date);
    if (result.ok) {
      setMessage('');
      setGate(null);
      onChanged();
    } else {
      setMessage(problemText(result.problem));
      setGate(result.problem.nextMode ?? null);
    }
  }

  return (
    <form
      aria-label={`${copy.schedule}: ${content.title}`}
      onSubmit={(event) => {
        event.preventDefault();
        void schedule();
      }}
    >
      <label>
        {copy.platformsTitle}
        <select onChange={(event) => setPlatformId(event.target.value)} required value={platformId}>
          <option value="">—</option>
          {platforms.map((platform) => (
            <option key={platform.platformId} value={platform.platformId}>
              {platform.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        {copy.dateField}
        <input onChange={(event) => setDate(event.target.value)} required type="date" value={date} />
      </label>
      <button className="primary-command" type="submit">
        {copy.schedule}
      </button>
      <output aria-live="polite">{message}</output>
      {gate && onGoMode ? (
        <button className="secondary-link" onClick={() => onGoMode(gate)} type="button">
          {copy.goToMode}
        </button>
      ) : null}
    </form>
  );
}

// What waits for the customer: each piece is approved as one exact version, then scheduled within the package.
export function ApprovalsView({
  relationshipId,
  copy,
  onChanged,
  refreshKey,
  platforms,
  onGoMode,
}: Common & { platforms: PlatformView[]; onGoMode?: (mode: ModeId) => void }) {
  const { items, failed, load } = useItems(relationshipId, ['CONTENT', 'PLAN_NODE', 'SLOT'], refreshKey);
  const [selected, setSelected] = useState<string | null>(null);

  function changed() {
    onChanged();
    void load();
  }

  if (failed) return <Failed copy={copy} retry={() => void load()} />;
  if (items === null) return <p aria-busy="true">{copy.loading}</p>;
  const visible = items.filter((item) => item.state !== 'HIDDEN' && item.state !== 'REJECTED');
  const waiting = visible.filter((item) => item.kind !== 'SLOT' && !item.isApproved);
  const slotted = new Set(visible.filter((item) => item.kind === 'SLOT').map((slot) => slot.parentId));
  const ready = visible.filter((item) => item.kind === 'CONTENT' && item.isApproved && !slotted.has(item.itemId));
  return (
    <section aria-label={copy.approvalsTitle} className="op-approvals">
      <h2>{copy.approvalsTitle}</h2>
      {waiting.length === 0 ? <p>{copy.nothingYet}</p> : null}
      <ul>
        {waiting.map((item) => (
          <li key={item.itemId}>
            <button
              aria-pressed={selected === item.itemId}
              className="op-entry"
              onClick={() => setSelected(item.itemId)}
              type="button"
            >
              {item.title}
            </button>
            {selected === item.itemId ? (
              <ItemCard
                copy={copy}
                item={item}
                key={`${item.itemId}-${item.versionNo}`}
                onChanged={changed}
                relationshipId={relationshipId}
              />
            ) : null}
          </li>
        ))}
      </ul>
      <h2>{copy.scheduleTitle}</h2>
      {ready.length === 0 ? <p>{copy.nothingYet}</p> : null}
      <ul>
        {ready.map((content) => (
          <li key={content.itemId}>
            <strong>{content.title}</strong>
            <ScheduleForm
              content={content}
              copy={copy}
              onChanged={changed}
              onGoMode={onGoMode}
              platforms={platforms}
              relationshipId={relationshipId}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

export function PublishedView({
  relationshipId,
  copy,
  onChanged,
  refreshKey,
  publishAuthority,
  onGoMode,
}: Common & { publishAuthority: boolean; onGoMode?: (mode: ModeId) => void }) {
  const { items, failed, load } = useItems(relationshipId, ['SLOT'], refreshKey);
  const [message, setMessage] = useState('');
  const [gate, setGate] = useState<ModeId | null>(null);

  async function publish(slot: ItemView) {
    const result = await operationApi.publish(relationshipId, slot.itemId);
    if (result.ok) {
      setMessage('');
      setGate(null);
    } else {
      setMessage(problemText(result.problem));
      setGate(result.problem.nextMode ?? null);
    }
    onChanged();
    void load();
  }

  async function authority(granted: boolean) {
    const result = await operationApi.publishAuthority(relationshipId, granted);
    if (result.ok) {
      setMessage('');
      onChanged();
    } else {
      setMessage(problemText(result.problem));
    }
  }

  if (failed) return <Failed copy={copy} retry={() => void load()} />;
  if (items === null) return <p aria-busy="true">{copy.loading}</p>;
  return (
    <section aria-label={copy.publishedTitle} className="op-published">
      <h2>{copy.publishedTitle}</h2>
      <button className="secondary-link" onClick={() => void authority(!publishAuthority)} type="button">
        {publishAuthority ? copy.revokePublish : copy.grantPublish}
      </button>
      {items.length === 0 ? <p>{copy.nothingYet}</p> : null}
      <ul>
        {items.map((slot) => (
          <li data-state={slot.state} key={slot.itemId}>
            <strong>{slot.title}</strong> — {humanize(slot.state)}
            {slot.startDate ? <time dateTime={slot.startDate}> {slot.startDate}</time> : null}
            {slot.state === 'SCHEDULED' || slot.state === 'PUBLISH_FAILED' ? (
              <button className="primary-command" onClick={() => void publish(slot)} type="button">
                {copy.publishNow}
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      <output aria-live="polite">{message}</output>
      {gate && onGoMode ? (
        <button className="secondary-link" onClick={() => onGoMode(gate)} type="button">
          {copy.goToMode}
        </button>
      ) : null}
    </section>
  );
}

type DigestRow = {
  skillId: string;
  baseline?: string | null;
  current?: string | null;
  howToMeasure?: string | null;
  source?: string | null;
  freshness?: string | null;
};

function rowsOf(digest: ItemView): DigestRow[] {
  const rows = digest.payload.rows;
  return Array.isArray(rows) ? (rows as DigestRow[]) : [];
}

// Results come from connected and customer-owned sources; where there is no source the screen says so and how to add one.
export function ResultsView({
  relationshipId,
  copy,
  refreshKey,
  labels,
}: Pick<Common, 'relationshipId' | 'copy' | 'refreshKey'> & { labels: Record<string, string> }) {
  const { items, failed, load } = useItems(relationshipId, ['DIGEST'], refreshKey);
  if (failed) return <Failed copy={copy} retry={() => void load()} />;
  if (items === null) return <p aria-busy="true">{copy.loading}</p>;
  const latest = [...items].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))[0];
  return (
    <section aria-label={copy.resultsTitle} className="op-results">
      <h2>{copy.resultsTitle}</h2>
      {latest === undefined ? <p>{copy.nothingYet}</p> : null}
      {latest ? (
        <table>
          <thead>
            <tr>
              <th scope="col">Skill</th>
              <th scope="col">{copy.baseline}</th>
              <th scope="col">Now</th>
              <th scope="col">{copy.evidenceSource}</th>
            </tr>
          </thead>
          <tbody>
            {rowsOf(latest).map((row) => (
              <tr key={row.skillId}>
                <th scope="row">{labels[row.skillId] ?? humanize(row.skillId)}</th>
                <td>{row.baseline ?? '—'}</td>
                <td>
                  {row.current ?? 'Not measured'}
                  {row.howToMeasure ? <small> {row.howToMeasure}</small> : null}
                </td>
                <td>
                  {row.source ?? '—'}
                  {row.freshness ? <small> {row.freshness}</small> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}

export function ImproveView({
  relationshipId,
  copy,
  onChanged,
  refreshKey,
}: Pick<Common, 'relationshipId' | 'copy' | 'onChanged' | 'refreshKey'>) {
  const { items, failed, load } = useItems(relationshipId, ['DIGEST'], refreshKey);
  const [message, setMessage] = useState('');

  async function decide(digest: ItemView, accept: boolean) {
    const result = await operationApi.decideDigest(relationshipId, digest.itemId, accept);
    if (result.ok) {
      setMessage('');
      onChanged();
      void load();
    } else {
      setMessage(problemText(result.problem));
    }
  }

  if (failed) return <Failed copy={copy} retry={() => void load()} />;
  if (items === null) return <p aria-busy="true">{copy.loading}</p>;
  return (
    <section aria-label={copy.improveTitle} className="op-improve">
      <h2>{copy.improveTitle}</h2>
      {items.length === 0 ? <p>{copy.nothingYet}</p> : null}
      <ul>
        {items.map((digest) => {
          const request = typeof digest.payload.request === 'string' ? digest.payload.request : null;
          return (
            <li data-state={digest.state} key={digest.itemId}>
              <h3>{digest.title}</h3>
              <p>{digest.body}</p>
              {request ? <p>{request}</p> : null}
              {digest.state === 'PROPOSED' ? (
                <>
                  <button className="primary-command" onClick={() => void decide(digest, true)} type="button">
                    {copy.acceptDigest}
                  </button>
                  <button className="secondary-link" onClick={() => void decide(digest, false)} type="button">
                    {copy.declineDigest}
                  </button>
                </>
              ) : (
                <small>{humanize(digest.state)}</small>
              )}
            </li>
          );
        })}
      </ul>
      <output aria-live="polite">{message}</output>
    </section>
  );
}
