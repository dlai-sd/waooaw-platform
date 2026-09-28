'use client';

import { useState } from 'react';
import type {
  ContractJourneyProjection,
  EmploymentRelationship,
  RelationshipEvaluationProjection,
  RelationshipTimelineEntry,
} from '@/lib/api/relationships';
import type { EmploymentRelationshipSummaryV1 } from '@/lib/api/generated/models/EmploymentRelationshipSummaryV1';
import { ContractJourney } from './ContractJourney';
import { RelationshipEvaluation } from './RelationshipEvaluation';

interface Props {
  relationship: EmploymentRelationship;
  relationships: EmploymentRelationshipSummaryV1[];
  timeline: RelationshipTimelineEntry[];
  evaluation: RelationshipEvaluationProjection;
  contractJourney: ContractJourneyProjection | null;
  availableSkills: Array<{ skillId: string; displayName: string }>;
}

export function RelationshipPreActivation({
  relationship,
  relationships,
  timeline,
  evaluation,
  contractJourney,
  availableSkills,
}: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const configuring = relationship.state === 'CONFIGURING';

  async function submitSetup(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    const response = await fetch(`/api/relationships/${relationship.relationshipId}/hire-setup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({
        businessName: form.get('businessName'),
        location: form.get('location'),
        businessNature: form.get('businessNature'),
        goal: form.get('goal'),
        successMeasure: form.get('successMeasure'),
        budgetCeilingInrPaise: Math.round(Number(form.get('budgetCeilingInr')) * 100),
        selectedSkillIds: form.getAll('selectedSkillIds'),
        authorityScopeConfirmation: form.get('authorityScopeConfirmation'),
      }),
    });
    if (response.ok) {
      window.location.reload();
      return;
    }
    const body = (await response.json().catch(() => null)) as { detail?: string; title?: string } | null;
    setError(body?.detail ?? body?.title ?? 'Hire setup could not be completed. No contract was accepted.');
    setSubmitting(false);
  }

  return (
    <main className="workspace-shell relationship-workspace-grid">
      <header className="workspace-header">
        <div>
          <p className="brand">WAOOAW</p>
          <h1>{relationship.professionalType} relationship</h1>
        </div>
        <span className="state-banner trial">Hire / {relationship.state}</span>
      </header>

      <aside className="relationship-switcher" aria-label="Your agents">
        <p className="section-label">My Agents</p>
        <nav aria-label="Switch expert">
          {relationships.map((item) => (
            <a
              aria-current={item.relationshipId === relationship.relationshipId ? 'page' : undefined}
              href={`/relationships/${item.relationshipId}`}
              key={item.relationshipId}
            >
              <strong>{item.professionalDisplayName}</strong>
              <span>{item.lifecycleState.replaceAll('_', ' ').toLowerCase()}</span>
            </a>
          ))}
        </nav>
      </aside>

      <section className="relationship-summary" aria-labelledby="hire-progress-title">
        <div>
          <p className="section-label">Hire progress</p>
          <h2 id="hire-progress-title">{configuring ? 'Configure the professional' : 'Complete your contract'}</h2>
        </div>
        <p>
          {configuring
            ? 'Confirm the business outcome, capabilities, budget, and authority boundary before reviewing the exact contract.'
            : `${timeline.length} evidence events recorded. Review each remaining step below.`}
        </p>
      </section>

      <RelationshipEvaluation evaluation={evaluation} />

      {configuring ? (
        <section className="contract-journey" aria-labelledby="hire-setup-title">
          <p className="section-label">Business setup</p>
          <h2 id="hire-setup-title">Define the work before commitment</h2>
          <form className="portal-form onboard-form" onSubmit={submitSetup}>
            <label>
              Business name
              <input name="businessName" required maxLength={160} />
            </label>
            <label>
              Service location
              <input name="location" required maxLength={200} />
            </label>
            <label>
              What your business provides
              <textarea name="businessNature" required maxLength={1000} />
            </label>
            <label>
              Primary goal
              <textarea name="goal" required maxLength={1000} />
            </label>
            <label>
              How success will be measured
              <input name="successMeasure" required maxLength={500} />
            </label>
            <label>
              Monthly authority ceiling (INR)
              <input name="budgetCeilingInr" type="number" min="0" step="1" required />
            </label>
            <fieldset>
              <legend>Capabilities in scope</legend>
              {availableSkills.map((skill) => (
                <label key={skill.skillId}>
                  <input name="selectedSkillIds" type="checkbox" value={skill.skillId} />
                  {skill.displayName}
                </label>
              ))}
            </fieldset>
            <label>
              <input name="authorityScopeConfirmation" type="checkbox" value="CONFIRM_AUTHORITY_SCOPE" required />I
              confirm this budget and scope for contract preparation. This does not accept the contract or authorize
              payment.
            </label>
            {error ? <p role="alert">{error}</p> : null}
            <button className="primary-action" disabled={submitting} type="submit">
              {submitting ? 'Preparing contract...' : 'Prepare exact contract'}
            </button>
          </form>
        </section>
      ) : (
        <ContractJourney relationshipId={relationship.relationshipId} journey={contractJourney} />
      )}
    </main>
  );
}
