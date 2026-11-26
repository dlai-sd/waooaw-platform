'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R008, R010, R011, R012
// Constitutional basis: C-001, C-023, C-042, C-048, C-059, C-063, C-083

import { useCallback, useEffect, useState } from 'react';
import { connectionCall } from '@/lib/provider-connections-call';
import type { ConnectionStart } from '@/lib/provider-connections-client';
import { operationApi, presenceLabel, problemText, type ItemView, type PlatformView } from '@/lib/agent-operation';
import type { OperationMessages } from '@/lib/operation-i18n';

type Common = { relationshipId: string; copy: OperationMessages; onChanged: () => void; refreshKey: number };

function LabelChip({
  label,
  relationshipId,
  copy,
  onChanged,
}: { label: ItemView; relationshipId: string; copy: OperationMessages; onChanged: () => void }) {
  const [correcting, setCorrecting] = useState(false);
  const [text, setText] = useState(label.title);
  const [message, setMessage] = useState('');

  async function confirm(corrected?: string) {
    const result = await operationApi.confirmLabel(relationshipId, label.itemId, corrected);
    if (result.ok) {
      setCorrecting(false);
      onChanged();
    } else {
      setMessage(problemText(result.problem));
    }
  }

  async function remove() {
    const result = await operationApi.act(relationshipId, label.itemId, 'hide');
    if (result.ok) onChanged();
    else setMessage(problemText(result.problem));
  }

  const confirmed = label.state === 'CONFIRMED';
  return (
    <li className={`op-label${confirmed ? ' op-label-confirmed' : ''}`}>
      {correcting ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void confirm(text);
          }}
        >
          <label>
            {copy.titleField}
            <input maxLength={160} onChange={(event) => setText(event.target.value)} required value={text} />
          </label>
          <button className="primary-command" type="submit">
            {copy.save}
          </button>
        </form>
      ) : (
        <>
          <mark>{label.title}</mark>
          <small>{confirmed ? copy.confirmed : label.reason}</small>
          {confirmed ? null : (
            <>
              <button className="primary-command" onClick={() => void confirm()} type="button">
                {copy.confirm}
              </button>
              <button className="secondary-link" onClick={() => setCorrecting(true)} type="button">
                {copy.correct}
              </button>
            </>
          )}
          <button className="secondary-link" onClick={() => void remove()} type="button">
            {copy.hide}
          </button>
        </>
      )}
      <output aria-live="polite">{message}</output>
    </li>
  );
}

// The business as highlighted labels the customer confirms or corrects; what was inferred stays apart from what was confirmed.
export function ProfileView({ relationshipId, copy, onChanged, refreshKey }: Common) {
  const [labels, setLabels] = useState<ItemView[] | null>(null);
  const [findings, setFindings] = useState<ItemView[]>([]);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    const [labelResult, findingResult] = await Promise.all([
      operationApi.items(relationshipId, 'PROFILE_LABEL'),
      operationApi.items(relationshipId, 'FINDING'),
    ]);
    setFailed(!labelResult.ok);
    if (labelResult.ok) setLabels(labelResult.data.filter((label) => label.state !== 'HIDDEN'));
    if (findingResult.ok) setFindings(findingResult.data.filter((finding) => finding.state !== 'HIDDEN'));
  }, [relationshipId]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  function changed() {
    onChanged();
    void load();
  }

  if (failed)
    return (
      <div role="alert">
        <p>{copy.failed}</p>
        <button className="secondary-link" onClick={() => void load()} type="button">
          {copy.retry}
        </button>
      </div>
    );
  if (labels === null) return <p aria-busy="true">{copy.loading}</p>;
  const inferred = labels.filter((label) => label.state !== 'CONFIRMED');
  const confirmed = labels.filter((label) => label.state === 'CONFIRMED');
  return (
    <section aria-label={copy.profileTitle} className="op-profile">
      <h2>{copy.profileTitle}</h2>
      {labels.length === 0 ? <p>{copy.nothingYet}</p> : null}
      {inferred.length > 0 ? (
        <ul aria-label="To confirm">
          {inferred.map((label) => (
            <LabelChip
              copy={copy}
              key={label.itemId}
              label={label}
              onChanged={changed}
              relationshipId={relationshipId}
            />
          ))}
        </ul>
      ) : null}
      {confirmed.length > 0 ? (
        <ul aria-label="Confirmed">
          {confirmed.map((label) => (
            <LabelChip
              copy={copy}
              key={label.itemId}
              label={label}
              onChanged={changed}
              relationshipId={relationshipId}
            />
          ))}
        </ul>
      ) : null}
      {findings.length > 0 ? (
        <ul aria-label="Found on public pages">
          {findings.map((finding) => (
            <li key={finding.itemId}>
              <strong>{finding.title}</strong>: {finding.body}{' '}
              <small>
                {finding.sourceRef} — {finding.reason}
              </small>
              <button
                className="secondary-link"
                onClick={() => {
                  void operationApi.act(relationshipId, finding.itemId, 'hide').then(changed);
                }}
                type="button"
              >
                {copy.hide}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

const answers = [
  { value: 'PRESENT', key: 'answerPresent' },
  { value: 'NOT_PRESENT', key: 'answerAbsent' },
  { value: 'PUBLIC_ONLY', key: 'answerPublic' },
] as const;

function PlatformRow({
  platform,
  relationshipId,
  copy,
  onChanged,
  navigate,
}: {
  platform: PlatformView;
  relationshipId: string;
  copy: OperationMessages;
  onChanged: () => void;
  navigate: (url: string) => void;
}) {
  const [message, setMessage] = useState('');

  async function answer(value: 'PRESENT' | 'NOT_PRESENT' | 'PUBLIC_ONLY') {
    const result = await operationApi.answerPlatform(relationshipId, platform.platformId, value);
    if (result.ok) onChanged();
    else setMessage(problemText(result.problem));
  }

  async function connect() {
    const result = await connectionCall<ConnectionStart>('POST', '/meta/start');
    if (result.ok) navigate(result.data.authorizationUrl);
    else setMessage(problemText({ code: 'OPERATION_UNAVAILABLE' }));
  }

  async function test() {
    const result = await operationApi.testPlatform(relationshipId, platform.platformId);
    if (result.ok) onChanged();
    else setMessage(problemText(result.problem));
  }

  async function revoke() {
    if (!platform.connectionId) return;
    const result = await connectionCall<unknown>('POST', `/${platform.connectionId}/revoke`);
    if (result.ok) onChanged();
    else setMessage(problemText({ code: 'OPERATION_UNAVAILABLE' }));
  }

  const connected = platform.presence === 'CONNECTED_TESTED' || platform.presence === 'NEEDS_REPAIR';
  return (
    <li className="op-platform" data-presence={platform.presence}>
      <strong>{platform.label}</strong> <span className="op-badge">{presenceLabel(platform.presence)}</span>
      {platform.accountName ? <span> {platform.accountName}</span> : null}
      <p>{platform.note}</p>
      {/* biome-ignore lint/a11y/useSemanticElements: a fieldset would add default borders to the platform card */}
      <div role="group" aria-label={platform.label}>
        {answers.map((option) => (
          <button
            aria-pressed={platform.presence === option.value}
            className="secondary-link"
            key={option.value}
            onClick={() => void answer(option.value)}
            type="button"
          >
            {copy[option.key]}
          </button>
        ))}
        {platform.canConnect ? (
          <button className="primary-command" onClick={() => void connect()} type="button">
            {copy.connect}
          </button>
        ) : null}
        {connected ? (
          <>
            <button className="secondary-link" onClick={() => void test()} type="button">
              {copy.test}
            </button>
            <button className="secondary-link" onClick={() => void revoke()} type="button">
              {copy.revoke}
            </button>
          </>
        ) : null}
      </div>
      <output aria-live="polite">{message}</output>
    </li>
  );
}

// Every listed platform gets an explicit answer; connecting is offered, never required, and no password is ever typed.
export function PlatformsView({
  platforms,
  relationshipId,
  copy,
  onChanged,
  navigate = (url) => window.location.assign(url),
}: { platforms: PlatformView[]; navigate?: (url: string) => void } & Omit<Common, 'refreshKey'>) {
  return (
    <section aria-label={copy.platformsTitle} className="op-platforms">
      <h2>{copy.platformsTitle}</h2>
      <p>{copy.noPasswords}</p>
      <ul>
        {platforms.map((platform) => (
          <PlatformRow
            copy={copy}
            key={platform.platformId}
            navigate={navigate}
            onChanged={onChanged}
            platform={platform}
            relationshipId={relationshipId}
          />
        ))}
      </ul>
    </section>
  );
}
