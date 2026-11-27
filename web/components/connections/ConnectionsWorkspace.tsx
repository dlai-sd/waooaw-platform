'use client';

// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R008, WC149-R009, WC149-R010; work-contracts/WC-167-acceptance-demo-readiness.md WC167-R002
// Constitutional basis: C-026, C-059, C-063

import { Facebook, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { PricingMessage, type PricingNotice } from '@/components/admin/pricing/usePricingCommand';
import { connectionCall } from '@/lib/provider-connections-call';
import {
  problemAction,
  problemText,
  type ConnectionStart,
  type ProblemAction,
  type ProviderConnection,
} from '@/lib/provider-connections-client';
import { ConnectionCard } from './ConnectionCard';
import { isSafeAuthorizationUrl, navigateTo } from './navigate';

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; text: string; action: ProblemAction | null }
  | { kind: 'account-required' }
  | { kind: 'ready'; connections: ProviderConnection[] };

type Props = { initialNotice?: PricingNotice | null; staff?: boolean };

export function ConnectionsWorkspace({ initialNotice = null, staff = false }: Props) {
  const noticeRef = useRef<HTMLDivElement>(null);
  const [load, setLoad] = useState<LoadState>({ kind: 'loading' });
  const [notice, setNotice] = useState<PricingNotice | null>(initialNotice);
  const [starting, setStarting] = useState(false);

  const refresh = useCallback(async () => {
    const result = await connectionCall<ProviderConnection[]>('GET', '');
    if (result.ok && Array.isArray(result.data)) {
      setLoad({ kind: 'ready', connections: result.data });
    } else if (!staff && !result.ok && result.problem.code === 'CONNECTION_ACCOUNT_REQUIRED') {
      // Not having an account yet is a normal first state, not a failure.
      setLoad((current) => (current.kind === 'ready' ? current : { kind: 'account-required' }));
    } else {
      setLoad((current) =>
        current.kind === 'ready'
          ? current
          : {
              kind: 'error',
              text: `Your connections could not be loaded. ${problemText(result.ok ? {} : result.problem, staff)}`,
              action: result.ok ? null : problemAction(result.problem, staff),
            }
      );
    }
  }, [staff]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (initialNotice) noticeRef.current?.focus();
  }, [initialNotice]);

  async function start() {
    setStarting(true);
    setNotice(null);
    const result = await connectionCall<ConnectionStart>('POST', '/meta/start', {});
    if (result.ok && isSafeAuthorizationUrl(result.data?.authorizationUrl)) {
      navigateTo(result.data.authorizationUrl);
      return;
    }
    setNotice({
      kind: 'error',
      text: result.ok
        ? 'Facebook could not be opened. Nothing was connected. Try again shortly.'
        : problemText(result.problem),
    });
    setStarting(false);
  }

  function revoked() {
    setNotice({ kind: 'success', text: 'Connection revoked. WAOOAW deleted its stored access.' });
    void refresh().then(() => noticeRef.current?.focus());
  }

  const connections = load.kind === 'ready' ? load.connections : [];
  const canConnect = !connections.some(
    (connection) => connection.status === 'CONNECTED' || connection.status === 'NEEDS_REPAIR'
  );
  return (
    <div className="workbench-stack">
      <section aria-labelledby="connections-privacy" className="workbench-section">
        <h2 id="connections-privacy">
          <ShieldCheck aria-hidden="true" size={20} /> Your access stays private
        </h2>
        <p>
          When you connect Facebook, WAOOAW stores the access in a private secret store. The agent never sees it and it
          is never shown on this page. Posts are published only when you approve the exact text, and you can revoke the
          connection at any time.
        </p>
        {load.kind === 'ready' && canConnect ? (
          <div className="workbench-actions">
            <button className="primary-command" disabled={starting} onClick={() => void start()} type="button">
              <Facebook aria-hidden="true" size={18} /> {starting ? 'Opening Facebook...' : 'Connect Facebook'}
            </button>
          </div>
        ) : null}
      </section>

      <div ref={noticeRef} tabIndex={-1}>
        <PricingMessage message={notice} />
      </div>

      {load.kind === 'loading' ? <output className="workbench-hint">Loading your connections...</output> : null}
      {load.kind === 'account-required' ? (
        <div className="workbench-stack">
          <p className="workbench-hint">
            You can connect your accounts after you have registered and started a Trial or Hire. Nothing is connected
            yet.
          </p>
          <div className="workbench-actions">
            <Link className="primary-command" href={`/register?returnTo=${encodeURIComponent('/connections')}`}>
              Complete registration
            </Link>
            <Link className="secondary-link" href="/marketplace">
              Browse the marketplace
            </Link>
          </div>
        </div>
      ) : null}
      {load.kind === 'error' ? (
        <div className="workbench-stack">
          <p className="workbench-message workbench-message-error" role="alert">
            {load.text}
          </p>
          <div className="workbench-actions">
            {load.action ? (
              <Link className="primary-command" href={load.action.href}>
                {load.action.label}
              </Link>
            ) : null}
            <button
              className="secondary-link"
              onClick={() => {
                setLoad({ kind: 'loading' });
                void refresh();
              }}
              type="button"
            >
              Try again
            </button>
          </div>
        </div>
      ) : null}
      {load.kind === 'ready' && connections.length === 0 ? (
        <p className="workbench-hint">You have not connected any accounts yet. Connect Facebook to get started.</p>
      ) : null}
      {connections.length > 0 ? (
        <ul aria-label="Connected accounts" className="connections-list">
          {connections.map((connection) => (
            <ConnectionCard
              connection={connection}
              key={connection.id}
              onChanged={() => void refresh()}
              onReconnect={() => void start()}
              onRevoked={revoked}
              starting={starting}
            />
          ))}
        </ul>
      ) : null}
    </div>
  );
}
