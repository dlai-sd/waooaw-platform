'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R007, R017, R030, R036
// Constitutional basis: C-001, C-023, C-042, C-059, C-063

import { useState } from 'react';
import { authorLabel, operationApi, problemText, type ItemView } from '@/lib/agent-operation';
import type { OperationMessages } from '@/lib/operation-i18n';

type Props = {
  relationshipId: string;
  item: ItemView;
  copy: OperationMessages;
  onChanged: (item: ItemView | null) => void;
};

const approvable = new Set(['PLAN_NODE', 'CONTENT']);

// One item, whoever made it: a suggestion waits for the customer, an approval is of one exact version, and hand over,
// take back and undo are always there. Every button calls the same command the conversation calls.
export function ItemCard({ relationshipId, item, copy, onChanged }: Props) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(item.title);
  const [body, setBody] = useState(item.body ?? '');
  const [date, setDate] = useState(item.startDate ?? '');
  const [moveDate, setMoveDate] = useState(item.startDate ?? '');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function run(action: () => ReturnType<typeof operationApi.act>) {
    setBusy(true);
    setMessage('');
    const result = await action();
    setBusy(false);
    if (result.ok) {
      setEditing(false);
      onChanged(result.data);
    } else {
      setMessage(problemText(result.problem));
    }
  }

  const owned = item.authorState === 'CUSTOMER_OWNED';
  const hidden = item.state === 'HIDDEN';
  return (
    <article aria-label={item.title} className="op-item" data-state={item.state}>
      <header>
        <h3>{item.title}</h3>
        <p className="op-item-meta">
          <span className="op-badge">{authorLabel(item.authorState)}</span>
          {item.isSuggestion ? <span className="op-badge op-badge-suggestion">{copy.suggestion}</span> : null}
          <span className="op-badge">{item.state.toLowerCase().replace(/_/g, ' ')}</span>
          {item.startDate ? <time dateTime={item.startDate}>{item.startDate}</time> : null}
        </p>
      </header>
      {item.body ? <p>{item.body}</p> : null}
      {item.isSuggestion && item.reason ? (
        <p className="op-item-reason">
          {copy.because}: {item.reason}
          {item.sourceRef ? (
            <>
              {' '}
              {copy.source}: <span>{item.sourceRef}</span>
            </>
          ) : null}
          {item.confidence != null ? (
            <>
              {' '}
              {copy.confidence}: {Math.round(item.confidence * 100)}%
            </>
          ) : null}
        </p>
      ) : null}
      {editing ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void run(() =>
              operationApi.edit(relationshipId, item.itemId, {
                title,
                body: body || undefined,
                startDate: date || undefined,
                expectedVersion: item.versionNo,
              })
            );
          }}
        >
          <label>
            {copy.titleField}
            <input maxLength={160} onChange={(event) => setTitle(event.target.value)} required value={title} />
          </label>
          <label>
            {copy.textField}
            <textarea maxLength={2000} onChange={(event) => setBody(event.target.value)} value={body} />
          </label>
          <label>
            {copy.dateField}
            <input onChange={(event) => setDate(event.target.value)} type="date" value={date} />
          </label>
          <button className="primary-command" disabled={busy} type="submit">
            {copy.save}
          </button>
          <button className="secondary-link" onClick={() => setEditing(false)} type="button">
            {copy.cancel}
          </button>
        </form>
      ) : (
        <div className="op-item-actions">
          {item.isSuggestion ? (
            <button
              className="primary-command"
              disabled={busy}
              onClick={() => void run(() => operationApi.act(relationshipId, item.itemId, 'accept', 'ACCEPTED'))}
              type="button"
            >
              {copy.accept}
            </button>
          ) : null}
          {approvable.has(item.kind) && !item.isApproved && !item.isSuggestion && item.state !== 'REJECTED' ? (
            <button
              className="primary-command"
              disabled={busy}
              onClick={() => void run(() => operationApi.approve(relationshipId, item.itemId, item.versionNo))}
              type="button"
            >
              {copy.approve}
            </button>
          ) : null}
          {approvable.has(item.kind) && item.state !== 'REJECTED' && !item.isApproved ? (
            <button
              className="secondary-link"
              disabled={busy}
              onClick={() => void run(() => operationApi.act(relationshipId, item.itemId, 'reject'))}
              type="button"
            >
              {copy.reject}
            </button>
          ) : null}
          <button className="secondary-link" disabled={busy} onClick={() => setEditing(true)} type="button">
            {copy.edit}
          </button>
          {hidden ? (
            <button
              className="secondary-link"
              disabled={busy}
              onClick={() => void run(() => operationApi.act(relationshipId, item.itemId, 'restore'))}
              type="button"
            >
              {copy.restore}
            </button>
          ) : (
            <button
              className="secondary-link"
              disabled={busy}
              onClick={() => void run(() => operationApi.act(relationshipId, item.itemId, 'hide'))}
              type="button"
            >
              {copy.hide}
            </button>
          )}
          {owned ? (
            <button
              className="secondary-link"
              disabled={busy}
              onClick={() => void run(() => operationApi.act(relationshipId, item.itemId, 'take-back', 'ASKED'))}
              type="button"
            >
              {copy.takeBack}
            </button>
          ) : (
            <button
              className="secondary-link"
              disabled={busy}
              onClick={() => void run(() => operationApi.act(relationshipId, item.itemId, 'hand-over', 'ASKED'))}
              type="button"
            >
              {copy.handOver}
            </button>
          )}
          {item.versionNo > 1 ? (
            <button
              className="secondary-link"
              disabled={busy}
              onClick={() => void run(() => operationApi.act(relationshipId, item.itemId, 'undo'))}
              type="button"
            >
              {copy.undoItem}
            </button>
          ) : null}
          {item.startDate ? (
            <label className="op-move">
              {copy.moveTo}
              <input onChange={(event) => setMoveDate(event.target.value)} type="date" value={moveDate} />
              <button
                className="secondary-link"
                disabled={busy || moveDate === '' || moveDate === item.startDate}
                onClick={() => void run(() => operationApi.move(relationshipId, item.itemId, moveDate))}
                type="button"
              >
                {copy.move}
              </button>
            </label>
          ) : null}
        </div>
      )}
      <output aria-live="polite">{message}</output>
    </article>
  );
}
