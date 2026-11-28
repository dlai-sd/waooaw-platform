'use client';

// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R007
// Constitutional basis: C-001, C-042, C-049, C-059, C-063

import { BellRing, Info } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import {
  alertControlsCopy as copy,
  alertHref,
  listCategories,
  listInbox,
  setCategoryMute,
  snoozeAlert,
  type Categories,
  type InboxAlert,
} from '@/lib/alert-controls-client';

type Agent = { id: string; name: string };
type Props = { agents?: Agent[]; relationshipId?: string; showControls?: boolean; locale?: string };

const humanize = (value: string) => value.replaceAll('_', ' ').toLowerCase();

// A customer can switch off the phone messages of any kind of alert that is allowed to be switched off: the ones that
// exist in the inbox plus the ones already switched off. Floor categories are never offered.
export function categoryRows(
  alerts: InboxAlert[],
  categories: Categories
): Array<{ category: string; muted: boolean }> {
  const rows = new Map<string, boolean>();
  for (const alert of alerts) if (alert.mutable) rows.set(alert.category, false);
  for (const item of categories.items) rows.set(item.category, item.muted);
  for (const floor of categories.floorCategories) rows.delete(floor);
  return [...rows.entries()]
    .map(([category, muted]) => ({ category, muted }))
    .sort((left, right) => left.category.localeCompare(right.category));
}

async function acknowledge(alert: InboxAlert): Promise<boolean> {
  try {
    const response = await fetch(`/api/alerts/${encodeURIComponent(alert.alertId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'acknowledge',
        expectedAlertVersion: alert.version,
        idempotencyKey: crypto.randomUUID(),
      }),
    });
    return response.ok;
  } catch {
    return false;
  }
}

export function AlertInbox({ agents, relationshipId, showControls = false, locale = 'en' }: Props) {
  const [filter, setFilter] = useState<string | undefined>(relationshipId);
  const [alerts, setAlerts] = useState<InboxAlert[] | null>(null);
  const [categories, setCategories] = useState<Categories | null>(null);
  const [message, setMessage] = useState<string>();
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    const result = await listInbox(filter);
    if (result.ok) {
      setAlerts(result.data.items);
      setFailed(false);
    } else setFailed(true);
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (!showControls) return;
    void listCategories().then((result) => {
      if (result.ok) setCategories(result.data);
    });
  }, [showControls]);

  async function snooze(alert: InboxAlert) {
    setMessage(undefined);
    const result = await snoozeAlert(alert, new Date(Date.now() + 24 * 60 * 60 * 1000));
    if (result.ok) await load();
    else setMessage(result.reason === 'not-mutable' ? copy.cannotMute : copy.failed);
  }

  async function acknowledgeAlert(alert: InboxAlert) {
    setMessage(undefined);
    if (await acknowledge(alert)) await load();
    else setMessage(copy.failed);
  }

  async function toggleCategory(category: string, muted: boolean) {
    setMessage(undefined);
    const result = await setCategoryMute(category, muted);
    if (!result.ok) {
      setMessage(result.reason === 'not-mutable' ? copy.cannotMute : copy.failed);
      return;
    }
    setCategories((current) =>
      current
        ? {
            ...current,
            items: [...current.items.filter((item) => item.category !== category), { category, muted }],
          }
        : current
    );
  }

  return (
    <div className="alert-inbox">
      {!relationshipId && agents && agents.length > 0 ? (
        <label className="alert-filter">
          <span>{copy.filterLabel}</span>
          <select value={filter ?? ''} onChange={(event) => setFilter(event.target.value || undefined)}>
            <option value="">{copy.allAgents}</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <output aria-live="polite">{message ?? ''}</output>
      {alerts === null && !failed ? <output>{copy.loading}</output> : null}
      {failed ? (
        <div role="alert">
          <p>{copy.loadFailed}</p>
          <button className="secondary-link" onClick={() => void load()} type="button">
            {copy.retry}
          </button>
        </div>
      ) : null}
      {alerts !== null && alerts.length === 0 && !failed ? <p>{copy.empty}</p> : null}
      <ul className="portal-list alert-list">
        {(alerts ?? []).map((alert) => (
          <li className="portal-list-item" key={alert.alertId}>
            <div className="alert-summary">
              {alert.alertClass === 'ACTION_REQUIRED' || alert.alertClass === 'FLOOR' ? (
                <BellRing aria-hidden="true" />
              ) : (
                <Info aria-hidden="true" />
              )}
              <div>
                <div className="portal-item-heading">
                  <h2>{humanize(alert.category)}</h2>
                  <span className="status-label">{copy.classes[alert.alertClass] ?? humanize(alert.alertClass)}</span>
                  <span className="status-label">{humanize(alert.readState)}</span>
                  {alert.snoozedUntil && new Date(alert.snoozedUntil) > new Date() ? (
                    <span className="status-label">{copy.snoozed}</span>
                  ) : null}
                </div>
                <p>{alert.dueMeaning ?? ''}</p>
                <small>{new Date(alert.occurredAt).toLocaleString(locale)}</small>
              </div>
            </div>
            <div className="alert-actions">
              <Link className="secondary-link" href={alertHref(alert)}>
                {copy.open}
              </Link>
              {alert.readState !== 'ACKNOWLEDGED' ? (
                <button className="secondary-link" onClick={() => void acknowledgeAlert(alert)} type="button">
                  {copy.acknowledge}
                </button>
              ) : null}
              {alert.mutable ? (
                <button className="secondary-link" onClick={() => void snooze(alert)} type="button">
                  {copy.snooze}
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
      {showControls && categories ? (
        <section aria-labelledby="alert-mutes">
          <h2 id="alert-mutes">{copy.mutedSection}</h2>
          <p>{copy.mutedHelp}</p>
          <p>{copy.floorNote}</p>
          <ul className="portal-list">
            {categoryRows(alerts ?? [], categories).map((item) => (
              <li className="portal-list-item" key={item.category}>
                <label>
                  <input
                    checked={item.muted}
                    onChange={(event) => void toggleCategory(item.category, event.target.checked)}
                    type="checkbox"
                  />{' '}
                  {humanize(item.category)}
                </label>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
