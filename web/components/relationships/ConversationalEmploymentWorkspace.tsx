import type { EmploymentWorkspaceLoad } from '@/lib/api/employment-workspace';
import { OpenConversationCommand } from '@/components/conversation/OpenConversationCommand';

const label = (value: string) => value.replaceAll('_', ' ').toLowerCase();

export function ConversationalEmploymentWorkspace({
  employment,
}: {
  employment: EmploymentWorkspaceLoad;
}) {
  if (employment.state === 'unavailable') {
    return (
      <section className="lifecycle-panel" aria-labelledby="employment-workspace-title">
        <p className="section-label">Employment workspace</p>
        <h2 id="employment-workspace-title">Conversational employment is not available</h2>
        <section aria-live="polite">
          {employment.reason === 'candidate-disabled'
            ? 'The candidate capability is disabled. Existing relationship controls remain available.'
            : 'No conversational employment workspace has been established for this relationship.'}
        </section>
      </section>
    );
  }

  const { workspace } = employment;
  return (
    <section className="lifecycle-panel" aria-labelledby="employment-workspace-title">
      <div className="lifecycle-heading">
        <div>
          <p className="section-label">Employment workspace</p>
          <h2 id="employment-workspace-title">Induct, plan, operate and review</h2>
        </div>
        <span className="currency-state">version {workspace.workspaceVersion}</span>
      </div>

      <dl className="state-grid" aria-label="Employment readiness">
        <div>
          <dt>Induction</dt>
          <dd>{label(workspace.readiness.induction)}</dd>
        </div>
        <div>
          <dt>Plan</dt>
          <dd>{label(workspace.readiness.plan)}</dd>
        </div>
        <div>
          <dt>Operations</dt>
          <dd>{label(workspace.readiness.operations)}</dd>
        </div>
        <div>
          <dt>Performance</dt>
          <dd>{label(workspace.readiness.performance)}</dd>
        </div>
      </dl>

      <ol className="lifecycle-steps" aria-label="Employment phases">
        {workspace.phases.map((phase, index) => (
          <li key={phase.phase} data-state={phase.status.toLowerCase()}>
            <span>{index + 1}</span>
            <div>
              <strong>{label(phase.phase)}</strong>
              <small>
                {phase.progress.mandatoryCompleted} of {phase.progress.mandatoryTotal} mandatory requirements complete
              </small>
            </div>
          </li>
        ))}
      </ol>

      {workspace.limitations.length > 0 && (
        <section aria-live="polite">
          <h3>Known limitations</h3>
          <ul>
            {workspace.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </section>
      )}

      <p>
        <strong>Next action:</strong> {workspace.recommendedNextAction ?? 'Wait for owner-confirmed evidence.'}
      </p>
      {workspace.availableCommands.length > 0 && (
        <div>
          <h3>Available actions</h3>
          <ul className="decision-list">
            {workspace.availableCommands.map((command) => (
              <li key={`${command.kind}:${command.subjectRef}`}>
                <span>
                  <strong>{label(command.kind)}</strong>
                  <small>Continue in the governed conversation for {command.subjectRef}.</small>
                </span>
                <OpenConversationCommand label="Continue" />
              </li>
            ))}
          </ul>
        </div>
      )}
      <p>Emergency Stop and relationship rights remain available in the persistent application controls.</p>
    </section>
  );
}
