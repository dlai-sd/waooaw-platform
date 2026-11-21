// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { labelFor } from '@/lib/workbench-i18n';
import { BlockRenderer } from './BlockRenderer';
import { StartPanel } from './StartPanel';
import type { WorkbenchPanelProps } from './useWorkbenchCommand';

export function OverviewPanel(panel: WorkbenchPanelProps) {
  const { copy, snapshot } = panel;
  const { projection } = snapshot;
  const readiness: Array<[string, string]> = [
    [copy.readinessInduction, projection.readiness.induction],
    [copy.readinessPlan, projection.readiness.plan],
    [copy.readinessOperations, projection.readiness.operations],
    [copy.readinessPerformance, projection.readiness.performance],
  ];
  const blocks = projection.blocks.filter((block) => block.type !== 'FORM');
  return (
    <div className="workbench-stack">
      <section aria-labelledby="workbench-next-title" className="workbench-section">
        <h3 id="workbench-next-title">{copy.nextStep}</h3>
        {projection.recommendedNextAction ? (
          <p>
            <strong>{projection.recommendedNextAction.label}</strong> {projection.recommendedNextAction.reason}
          </p>
        ) : (
          <p>{copy.nothingNeeded}</p>
        )}
        <p className="workbench-hint">
          {labelFor(copy.phases, projection.phase)} · {copy.freshness}:{' '}
          {labelFor(copy.freshnessStates, projection.sourceFreshness)} · {copy.evidenceState}:{' '}
          {labelFor(copy.evidenceStates, projection.evidenceState)}
        </p>
      </section>
      <StartPanel {...panel} />
      <section aria-labelledby="workbench-readiness-title" className="workbench-section">
        <h3 id="workbench-readiness-title">{copy.readiness}</h3>
        <dl className="workbench-facts">
          {readiness.map(([name, value]) => (
            <div key={name}>
              <dt>{name}</dt>
              <dd>{labelFor(copy.states, value)}</dd>
            </div>
          ))}
        </dl>
      </section>
      {projection.alerts.length > 0 ? (
        <section aria-labelledby="workbench-alerts-title" className="workbench-section">
          <h3 id="workbench-alerts-title">{copy.alerts}</h3>
          <ul className="workbench-plain-list">
            {projection.alerts.map((alert, index) => (
              <li key={`${alert.alertId}-${index}`}>{alert.message}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {blocks.length > 0 ? (
        <section aria-label={copy.toolOverview} className="workbench-section">
          {blocks.map((block) => (
            <BlockRenderer block={block} copy={copy} key={block.id} />
          ))}
        </section>
      ) : null}
      {projection.limitations.length > 0 ? (
        <section aria-labelledby="workbench-limits-title" className="workbench-section">
          <h3 id="workbench-limits-title">{copy.limitations}</h3>
          <ul className="workbench-plain-list">
            {projection.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
