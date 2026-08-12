import type { ContractJourneyProjection, EmploymentRelationship, RelationshipEvaluationProjection, RelationshipTimelineEntry } from '@/lib/api/relationships';
import type { RelationshipWorkspaceViews } from '@/lib/api/relationship-workspace';
import { ConversationExperience } from '@/components/conversation/ConversationExperience';
import { RelationshipEvaluation } from './RelationshipEvaluation';
import { ContractJourney } from './ContractJourney';
import { EvidenceWindow } from './EvidenceWindow';

interface RelationshipWorkspaceProps {
  relationship: EmploymentRelationship;
  timeline: RelationshipTimelineEntry[];
  views: RelationshipWorkspaceViews;
  evaluation: RelationshipEvaluationProjection;
  contractJourney?: ContractJourneyProjection | null;
}

const stateLabel = (state: string) => state.replaceAll('_', ' ').toLowerCase();

export function RelationshipWorkspace({ relationship, timeline, views, evaluation, contractJourney = null }: RelationshipWorkspaceProps) {
  const live = relationship.state === 'ACTIVE';

  return (
    <main className="workspace-shell">
      <header className="workspace-header">
        <div>
          <p className="brand">WAOOAW</p>
          <h1>{relationship.professionalType} relationship</h1>
        </div>
        <span className={`state-banner ${live ? 'live' : 'trial'}`}>{live ? 'Live' : 'Evaluation'} · {relationship.state}</span>
      </header>

      <section className="relationship-summary" aria-labelledby="relationship-summary-title">
        <div>
          <p className="section-label">Relationship</p>
          <h2 id="relationship-summary-title">Current constitutional state</h2>
        </div>
        <dl className="state-grid">
          <div><dt>State</dt><dd>{relationship.state.replaceAll('_', ' ')}</dd></div>
          <div><dt>Version</dt><dd>{relationship.stateVersion}</dd></div>
          <div><dt>Evidence events</dt><dd>{timeline.length}</dd></div>
          <div><dt>Last updated</dt><dd>{new Date(relationship.updatedAt).toLocaleString('en-IN')}</dd></div>
        </dl>
      </section>

      <RelationshipEvaluation evaluation={evaluation} />

      <ContractJourney relationshipId={relationship.relationshipId} journey={contractJourney} />

      <nav className="workspace-nav" aria-label="Relationship workspace views">
        {['Plan', 'Needs your attention', 'Work', 'Results', 'Usage & budget', 'Rights & control'].map((label) => (
          <a key={label} href={`#${label.toLowerCase().replaceAll(' ', '-').replace('&', 'and')}`}>{label}</a>
        ))}
      </nav>

      <section className="workspace-family attention-family" id="needs-your-attention" aria-labelledby="attention-title">
        <div><p className="section-label">Needs your attention</p><h2 id="attention-title">Decisions in authoritative order</h2></div>
        <span className="currency-state">{stateLabel(views.attention.currencyState)}</span>
        {views.attention.items.length === 0 ? <p className="empty-meaning">Nothing currently requires your response.</p> : (
          <ol>{views.attention.items.map((item) => <li key={item.attentionItemId}><strong>{item.reason}</strong><span>{item.consequence}</span></li>)}</ol>
        )}
      </section>

      <div className="workspace-families">
        <section className="workspace-family" id="plan"><p className="section-label">Plan</p><h2>Goals and priority work</h2><span className="currency-state">{stateLabel(views.plan.currencyState)}</span><p>{views.plan.goals?.length ? views.plan.goals.join(' · ') : 'Plan details are not yet authoritatively available.'}</p></section>
        <section className="workspace-family" id="work"><p className="section-label">Work</p><h2>Execution and deliverables</h2><span className="currency-state">{stateLabel(views.work.currencyState)}</span><p>{views.work.items.length ? `${views.work.items.length} work items` : 'Execution facts are not yet authoritatively available.'}</p></section>
        <section className="workspace-family" id="results"><p className="section-label">Results</p><h2>Business outcomes</h2><span className="currency-state">{stateLabel(views.results.currencyState)}</span><p>{views.results.outcomes.length ? `${views.results.outcomes.length} evidenced outcomes` : 'No supported business outcome is available yet.'}</p></section>
        <section className="workspace-family" id="usage-and-budget"><p className="section-label">Usage &amp; budget</p><h2>Commercial truth</h2><span className="currency-state">{stateLabel(views.usageBudget.currencyState)}</span><dl><div><dt>Actual</dt><dd>{views.usageBudget.actualAmount}</dd></div><div><dt>Forecast</dt><dd>{views.usageBudget.forecastRange}</dd></div></dl></section>
        <section className="workspace-family" id="rights-and-control"><p className="section-label">Rights &amp; control</p><h2>Scope, authority and lifecycle</h2><span className="currency-state">{stateLabel(views.rightsControls.currencyState)}</span><p>{stateLabel(views.rightsControls.lifecycleState)} · Emergency Stop {views.rightsControls.emergencyStopReachable ? 'available' : 'unavailable'}</p></section>
      </div>

      <div id="relationship-conversation">
        <ConversationExperience
          relationshipId={relationship.relationshipId}
          relationshipStopped={relationship.state === 'STOPPED_EMERGENCY'}
        />
      </div>

      <EvidenceWindow relationshipId={relationship.relationshipId} evidence={views.evidence} />

      <section className="timeline" aria-labelledby="timeline-title">
        <p className="section-label">Evidence timeline</p>
        <h2 id="timeline-title">Relationship history</h2>
        <ol>
          {timeline.map((entry) => (
            <li key={entry.evidenceId}>
              <span>{entry.toState.replaceAll('_', ' ')}</span>
              <time dateTime={entry.occurredAt.toISOString()}>{entry.occurredAt.toLocaleString('en-IN')}</time>
            </li>
          ))}
        </ol>
      </section>

    </main>
  );
}