import type { ContractJourneyProjection, EmploymentRelationship, RelationshipEvaluationProjection, RelationshipTimelineEntry } from '@/lib/api/relationships';
import type { RelationshipWorkspaceViews } from '@/lib/api/relationship-workspace';
import { ConversationExperience } from '@/components/conversation/ConversationExperience';
import { RelationshipEvaluation } from './RelationshipEvaluation';
import { ContractJourney } from './ContractJourney';
import { EvidenceWindow } from './EvidenceWindow';
import { OnboardForm } from './OnboardForm';
import { SkillDecisionControls } from './SkillDecisionControls';
import type { EmploymentRelationshipSummaryV1 } from '@/lib/api/generated/models/EmploymentRelationshipSummaryV1';

interface RelationshipWorkspaceProps {
  relationship: EmploymentRelationship;
  relationships?: EmploymentRelationshipSummaryV1[];
  timeline: RelationshipTimelineEntry[];
  views: RelationshipWorkspaceViews;
  evaluation: RelationshipEvaluationProjection;
  contractJourney?: ContractJourneyProjection | null;
}

const stateLabel = (state: string) => state.replaceAll('_', ' ').toLowerCase();

export function RelationshipWorkspace({ relationship, relationships = [], timeline, views, evaluation, contractJourney = null }: RelationshipWorkspaceProps) {
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

      {relationships.length > 1 ? <nav className="workspace-nav" aria-label="Switch expert">{relationships.map((item) => <a aria-current={item.relationshipId === relationship.relationshipId ? 'page' : undefined} key={item.relationshipId} href={`/relationships/${item.relationshipId}`}>{item.professionalDisplayName}</a>)}</nav> : null}

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
      <SkillDecisionControls relationshipId={relationship.relationshipId} workspaceVersion={views.workspace.workspaceVersion} skills={evaluation.skills} />

      <ContractJourney relationshipId={relationship.relationshipId} journey={contractJourney} />

      <section className="lifecycle-panel" aria-labelledby="lifecycle-title">
        <div className="lifecycle-heading">
          <div><p className="section-label">Customer lifecycle</p><h2 id="lifecycle-title">From configuration to operations</h2></div>
          <span className="currency-state">{stateLabel(views.configuration.currencyState)}</span>
        </div>
        <ol className="lifecycle-steps">
          {views.configuration.items.map((item) => (
            <li key={item.stepKey} data-state={item.state.toLowerCase()}><span>{item.stepKey === 'ONBOARD' ? '1' : '2'}</span><div><strong>{item.label}</strong><small>{item.summary ?? stateLabel(item.state)}</small></div></li>
          ))}
          <li data-state={views.goals.activeGoals.every((goal) => goal.verificationStatus === 'VERIFIED') && views.goals.activeGoals.length ? 'complete' : 'locked'}><span>3</span><div><strong>Goal Verification</strong><small>{views.goals.activeGoals.length ? `${views.goals.activeGoals.filter((goal) => goal.verificationStatus === 'VERIFIED').length} of ${views.goals.activeGoals.length} verified` : 'No active goals'}</small></div></li>
          <li data-state={views.businessOutcomes.currencyState.toLowerCase()}><span>4</span><div><strong>Business Outcomes</strong><small>{views.businessOutcomes.items.length ? `${views.businessOutcomes.items.length} traced outcomes` : 'No supported outcomes available'}</small></div></li>
          <li data-state={views.operations.eligibilityState.toLowerCase()}><span>5</span><div><strong>Operations</strong><small>{stateLabel(views.operations.eligibilityState)}</small></div></li>
        </ol>
        <div className="lifecycle-details">
          <section><h3>Onboard</h3><OnboardForm relationshipId={relationship.relationshipId} summary={views.configuration.items.find((item) => item.stepKey === 'ONBOARD')?.summary} /></section>
          <section><h3>Induct</h3><p>Continue the agent-led induction in the conversation below. The confirmed context remains server-owned and shared across supported channels.</p><a className="secondary-link" href="#relationship-conversation">Continue induction</a></section>
          <section><h3>Goals</h3>{views.goals.activeGoals.length ? <ul className="decision-list">{views.goals.activeGoals.map((goal) => <li key={goal.goalId}><span><strong>{goal.skillLabel}</strong><small>{goal.measure} · {goal.frequency}</small></span><b>{stateLabel(goal.verificationStatus)}</b></li>)}</ul> : <p>No active goals are available.</p>}<p className="truth-note">Goal verification cannot be changed here because no canonical verification command exists.</p></section>
          <section><h3>Operations eligibility</h3><p><strong>{stateLabel(views.operations.eligibilityState)}</strong></p>{views.operations.blockedReasons?.length ? <ul>{views.operations.blockedReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul> : <p>No server-reported blockers.</p>}</section>
        </div>
      </section>

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