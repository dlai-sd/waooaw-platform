'use client';

import { ArrowRight, BellRing, Check, Info } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

export interface PortalAlert {
  alertId: string;
  version: string;
  alertType: 'ACTIONABLE' | 'INFORMATIONAL';
  severity: string;
  source: string;
  occurredAt: string;
  dueMeaning?: string;
  readState: 'UNREAD' | 'READ' | 'ACKNOWLEDGED';
  availableAction?: 'OPEN' | 'ACKNOWLEDGE' | 'NONE';
  href: string;
}

export function AlertFeed({ initialAlerts, locale }: { initialAlerts: PortalAlert[]; locale: string }) {
  const [alerts, setAlerts] = useState(initialAlerts);
  const [pendingId, setPendingId] = useState<string>();
  const [error, setError] = useState<string>();

  async function mutate(alert: PortalAlert, action: 'read' | 'acknowledge') {
    setPendingId(alert.alertId);
    setError(undefined);
    try {
      const response = await fetch(`/api/alerts/${encodeURIComponent(alert.alertId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, expectedAlertVersion: alert.version, idempotencyKey: crypto.randomUUID() }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.title === 'string' ? result.title : 'Alert update could not be completed.');
      setAlerts((current) => current.map((item) => item.alertId === alert.alertId ? {
        ...item,
        version: result.version,
        readState: result.readState,
        availableAction: result.availableAction,
      } : item));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Alert update could not be completed.');
    } finally {
      setPendingId(undefined);
    }
  }

  return (
    <>
      {error ? <p className="portal-error" role="alert">{error}</p> : null}
      <ul className="portal-list alert-list">
        {alerts.map((alert) => (
          <li key={alert.alertId} className="portal-list-item">
            <div className="alert-summary">
              {alert.alertType === 'ACTIONABLE' ? <BellRing aria-hidden="true" /> : <Info aria-hidden="true" />}
              <div><div className="portal-item-heading"><h2>{alert.source.replaceAll('_', ' ')}</h2><span className="status-label">{alert.alertType.toLowerCase()}</span><span className="status-label">{alert.readState.toLowerCase()}</span></div><p>{alert.dueMeaning ?? 'No deadline or due meaning was supplied.'}</p><small>{new Date(alert.occurredAt).toLocaleString(locale)} · {alert.severity.toLowerCase()} severity</small></div>
            </div>
            <div className="alert-actions">
              {alert.readState === 'UNREAD' ? <button className="secondary-command" disabled={pendingId === alert.alertId} onClick={() => void mutate(alert, 'read')} type="button">Mark read</button> : null}
              {alert.availableAction === 'ACKNOWLEDGE' && alert.readState !== 'ACKNOWLEDGED' ? <button className="secondary-command" disabled={pendingId === alert.alertId} onClick={() => void mutate(alert, 'acknowledge')} type="button"><Check aria-hidden="true" size={18} />Acknowledge</button> : null}
              {alert.availableAction === 'OPEN' ? <Link className="secondary-link" href={alert.href}>Open <ArrowRight aria-hidden="true" size={18} /></Link> : null}
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}