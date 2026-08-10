import type { EmploymentRelationship, RelationshipTimelineEntry } from '@/lib/api/relationships';
import { ConversationExperience } from '@/components/conversation/ConversationExperience';

interface RelationshipWorkspaceProps {
  relationship: EmploymentRelationship;
  timeline: RelationshipTimelineEntry[];
}

export function RelationshipWorkspace({ relationship, timeline }: RelationshipWorkspaceProps) {
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

      <ConversationExperience relationshipId={relationship.relationshipId} />

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