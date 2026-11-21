// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { labelFor } from '@/lib/workbench-i18n';
import type { WorkbenchPanelProps } from './useWorkbenchCommand';

const trendSymbols: Record<string, string> = { UP: '↑', DOWN: '↓', FLAT: '→' };

export function MonitorPanel({ copy, snapshot }: WorkbenchPanelProps) {
  const { tiles, alerts, sourceFreshness } = snapshot.projection;
  const items = snapshot.workItems?.items ?? [];
  return (
    <div className="workbench-stack">
      <section aria-labelledby="workbench-monitor-title" className="workbench-section">
        <h3 id="workbench-monitor-title">{copy.monitor}</h3>
        <p className="workbench-hint">
          {copy.freshness}: {labelFor(copy.freshnessStates, sourceFreshness)}
        </p>
        {tiles.length === 0 ? <p>{copy.noTiles}</p> : null}
        <ul className="workbench-cards">
          {tiles.map((tile) => (
            <li className="workbench-card" key={tile.tileId}>
              <h4>{tile.label}</h4>
              <p className="workbench-metric">
                {tile.value} {tile.unit}
                {tile.trend ? (
                  <span aria-label={`${copy.trend}: ${labelFor({}, tile.trend)}`} role="img">
                    {' '}
                    {trendSymbols[tile.trend]}
                  </span>
                ) : null}
              </p>
              {tile.target ? (
                <p>
                  {copy.target}: {tile.target}
                </p>
              ) : null}
              <p className="workbench-hint">
                {labelFor(copy.freshnessStates, tile.freshness)} · {copy.owner}: {tile.owner}
              </p>
            </li>
          ))}
        </ul>
      </section>
      {alerts.length > 0 ? (
        <section aria-labelledby="workbench-monitor-alerts" className="workbench-section">
          <h3 id="workbench-monitor-alerts">{copy.alerts}</h3>
          <ul className="workbench-plain-list">
            {alerts.map((alert) => (
              <li key={alert.alertId}>{alert.message}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <section aria-labelledby="workbench-work-items" className="workbench-section">
        <h3 id="workbench-work-items">{copy.workItems}</h3>
        {snapshot.workItems === null ? <p>{copy.problems.WORKBENCH_UNAVAILABLE}</p> : null}
        {snapshot.workItems !== null && items.length === 0 ? <p>{copy.noWorkItems}</p> : null}
        <ul className="workbench-plain-list">
          {items.map((item) => (
            <li key={item.itemRef}>
              <strong>{item.label}</strong> · {labelFor(copy.states, item.state)} · {copy.owner}: {item.owner}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
