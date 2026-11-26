'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R022, R028, R032
// Constitutional basis: C-023, C-042, C-059, C-063, C-088

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { StepUpCommand } from '@/components/admin/StepUpCommand';
import type { OperationMessages } from '@/lib/operation-i18n';
import { stepUpResumingText, useResumeAfterStepUp } from '@/lib/step-up-resume';

export type OperationSettings = {
  chatAllowanceDefault: number;
  chatAllowanceByProfessionalType: Record<string, number>;
  instagramConnectEnabled: boolean;
  publishSandboxOnly: boolean;
  sandboxAccountIds: string[];
  registryReadsEnabled: boolean;
};
type ShareDay = { day: string; asked: number; accepted: number; tool: number; assistantShare: number | null };
type Share = { days: ShareDay[]; relationshipsCounted: number; assistantShare: number | null };
type Attention = { relationshipRef: string; metric: string; total: number; lastDay: string };

type Remote<T> = { status: 'loading' } | { status: 'loaded'; data: T } | { status: 'failed' };

const base = '/api/admin/agent-operation';
const settingsKey = 'agent-operation.settings';

async function read<T>(path: string): Promise<Remote<T>> {
  try {
    const response = await fetch(`${base}/${path}`, {
      cache: 'no-store',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    });
    return response.ok ? { status: 'loaded', data: (await response.json()) as T } : { status: 'failed' };
  } catch {
    return { status: 'failed' };
  }
}

function asSettings(value: unknown): OperationSettings | null {
  const candidate = value as Partial<OperationSettings> | null;
  if (
    !candidate ||
    typeof candidate.chatAllowanceDefault !== 'number' ||
    typeof candidate.instagramConnectEnabled !== 'boolean' ||
    typeof candidate.publishSandboxOnly !== 'boolean' ||
    typeof candidate.registryReadsEnabled !== 'boolean' ||
    !Array.isArray(candidate.sandboxAccountIds) ||
    !candidate.chatAllowanceByProfessionalType ||
    typeof candidate.chatAllowanceByProfessionalType !== 'object'
  )
    return null;
  return candidate as OperationSettings;
}

export function parseOverrides(text: string): Record<string, number> | null {
  const entries: Record<string, number> = {};
  for (const line of text
    .split('\n')
    .map((value) => value.trim())
    .filter(Boolean)) {
    const [name, amount, ...rest] = line.split('=').map((value) => value.trim());
    const quantity = Number(amount);
    if (!name || rest.length > 0 || !Number.isInteger(quantity) || quantity < 1 || quantity > 1_000_000) return null;
    entries[name] = quantity;
  }
  return entries;
}

function percent(value: number | null): string {
  return value === null ? '—' : `${Math.round(value * 100)}%`;
}

// The Founder's screen for Agent Operation: the conversation allowance per package (default 1,000), the connector and
// sandbox switches, how work is reached (counts only) and what needs the operator.
export function AgentOperationSettings({ initial, copy }: { initial: OperationSettings; copy: OperationMessages }) {
  const [allowance, setAllowance] = useState(String(initial.chatAllowanceDefault));
  const [overrides, setOverrides] = useState(
    Object.entries(initial.chatAllowanceByProfessionalType)
      .map(([name, amount]) => `${name}=${amount}`)
      .join('\n')
  );
  const [instagram, setInstagram] = useState(initial.instagramConnectEnabled);
  const [sandboxOnly, setSandboxOnly] = useState(initial.publishSandboxOnly);
  const [accounts, setAccounts] = useState(initial.sandboxAccountIds.join('\n'));
  const [registry, setRegistry] = useState(initial.registryReadsEnabled);
  const [message, setMessage] = useState('');
  const [stepUp, setStepUp] = useState<OperationSettings | null>(null);
  const [shareRead, setShareRead] = useState<Remote<Share>>({ status: 'loading' });
  const [attentionRead, setAttentionRead] = useState<Remote<Attention[]>>({ status: 'loading' });

  const loadShare = useCallback(async () => setShareRead(await read<Share>('share')), []);
  const loadAttention = useCallback(async () => setAttentionRead(await read<Attention[]>('attention')), []);

  useEffect(() => {
    void loadShare();
    void loadAttention();
  }, [loadShare, loadAttention]);

  async function send(body: OperationSettings) {
    setStepUp(null);
    let response: Response;
    try {
      response = await fetch(`${base}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(body),
      });
    } catch {
      setMessage(copy.failed);
      return;
    }
    if (response.ok) setMessage(copy.settingsSaved);
    else if (response.status === 403) {
      setMessage(copy.stepUpNeeded);
      setStepUp(body);
    } else setMessage(copy.failed);
  }

  const resuming = useResumeAfterStepUp<unknown>(settingsKey, async (payload) => {
    const body = asSettings(payload);
    if (!body) return;
    setAllowance(String(body.chatAllowanceDefault));
    setOverrides(
      Object.entries(body.chatAllowanceByProfessionalType)
        .map(([name, amount]) => `${name}=${amount}`)
        .join('\n')
    );
    setInstagram(body.instagramConnectEnabled);
    setSandboxOnly(body.publishSandboxOnly);
    setAccounts(body.sandboxAccountIds.join('\n'));
    setRegistry(body.registryReadsEnabled);
    await send(body);
  });

  async function save(event: FormEvent) {
    event.preventDefault();
    const quantity = Number(allowance);
    const byType = parseOverrides(overrides);
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 1_000_000 || byType === null) {
      setMessage('The conversation allowance must be a whole number from 1 to 1,000,000.');
      return;
    }
    await send({
      chatAllowanceDefault: quantity,
      chatAllowanceByProfessionalType: byType,
      instagramConnectEnabled: instagram,
      publishSandboxOnly: sandboxOnly,
      sandboxAccountIds: accounts
        .split('\n')
        .map((value) => value.trim())
        .filter(Boolean),
      registryReadsEnabled: registry,
    });
  }

  return (
    <div className="op-settings">
      <form aria-label={copy.settingsTitle} noValidate onSubmit={(event) => void save(event)}>
        <label>
          {copy.allowanceDefault}
          <input
            min={1}
            onChange={(event) => setAllowance(event.target.value)}
            required
            type="number"
            value={allowance}
          />
        </label>
        <label>
          {copy.allowanceByType}
          <textarea
            onChange={(event) => setOverrides(event.target.value)}
            placeholder="AGENT_TYPE=500"
            value={overrides}
          />
        </label>
        <label>
          <input checked={instagram} onChange={(event) => setInstagram(event.target.checked)} type="checkbox" />
          {copy.instagramSwitch}
        </label>
        <label>
          <input checked={sandboxOnly} onChange={(event) => setSandboxOnly(event.target.checked)} type="checkbox" />
          {copy.sandboxOnly}
        </label>
        <label>
          {copy.sandboxAccounts}
          <textarea onChange={(event) => setAccounts(event.target.value)} value={accounts} />
        </label>
        <label>
          <input checked={registry} onChange={(event) => setRegistry(event.target.checked)} type="checkbox" />
          {copy.registrySwitch}
        </label>
        <button className="primary-command" type="submit">
          {copy.saveSettings}
        </button>
        <output aria-live="polite">{resuming ? stepUpResumingText : message}</output>
        {stepUp ? <StepUpCommand payload={stepUp} pendingKey={settingsKey} /> : null}
      </form>
      <section aria-label={copy.shareTitle}>
        <h2>{copy.shareTitle}</h2>
        <p>{copy.shareNote}</p>
        {shareRead.status === 'loading' ? <output aria-busy="true">{copy.loading}</output> : null}
        {shareRead.status === 'failed' ? (
          <div>
            <p role="alert">{copy.failed}</p>
            <button
              className="secondary-link"
              onClick={() => {
                setShareRead({ status: 'loading' });
                void loadShare();
              }}
              type="button"
            >
              {copy.retry}
            </button>
          </div>
        ) : null}
        {shareRead.status === 'loaded' && shareRead.data.days.length === 0 ? <p>{copy.nothingYet}</p> : null}
        {shareRead.status === 'loaded' && shareRead.data.days.length > 0 ? (
          <>
            <p>
              {percent(shareRead.data.assistantShare)} · {shareRead.data.relationshipsCounted}
            </p>
            <table>
              <thead>
                <tr>
                  <th scope="col">Day</th>
                  <th scope="col">Asked</th>
                  <th scope="col">Accepted</th>
                  <th scope="col">Tool</th>
                  <th scope="col">Assistant share</th>
                </tr>
              </thead>
              <tbody>
                {shareRead.data.days.map((day) => (
                  <tr key={day.day}>
                    <th scope="row">{day.day}</th>
                    <td>{day.asked}</td>
                    <td>{day.accepted}</td>
                    <td>{day.tool}</td>
                    <td>{percent(day.assistantShare)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
      </section>
      <section aria-label={copy.attentionTitle}>
        <h2>{copy.attentionTitle}</h2>
        {attentionRead.status === 'loading' ? <output aria-busy="true">{copy.loading}</output> : null}
        {attentionRead.status === 'failed' ? (
          <div>
            <p role="alert">{copy.failed}</p>
            <button
              className="secondary-link"
              onClick={() => {
                setAttentionRead({ status: 'loading' });
                void loadAttention();
              }}
              type="button"
            >
              {copy.retry}
            </button>
          </div>
        ) : null}
        {attentionRead.status === 'loaded' && attentionRead.data.length === 0 ? <p>{copy.nothingYet}</p> : null}
        <ul>
          {(attentionRead.status === 'loaded' ? attentionRead.data : []).map((row) => (
            <li key={`${row.relationshipRef}-${row.metric}`}>
              {row.metric.toLowerCase().replace(/_/g, ' ')} × {row.total} · {row.relationshipRef} · {row.lastDay}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
