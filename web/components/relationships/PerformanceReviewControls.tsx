'use client';

import { useState } from 'react';
import type { PerformanceReviewWindowV1 } from '@/lib/api/generated/models/PerformanceReviewWindowV1';

const decisions = [
  ['CONTINUE_CURRENT_MANDATE', 'Continue current mandate'],
  ['REQUEST_REASSESSMENT', 'Request reassessment'],
  ['DISPUTE_ASSESSMENT', 'Dispute assessment'],
  ['PAUSE_AFFECTED_WORK', 'Pause affected work'],
  ['REQUEST_TERMINATION_OR_MIGRATION', 'Request termination or migration'],
] as const;

interface PerformanceReviewControlsProps {
  relationshipId: string;
  workspaceVersion: string;
  review: PerformanceReviewWindowV1;
}

export function PerformanceReviewControls({
  relationshipId,
  workspaceVersion,
  review,
}: PerformanceReviewControlsProps) {
  const [decision, setDecision] = useState<(typeof decisions)[number][0]>('CONTINUE_CURRENT_MANDATE');
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState('');

  async function submit() {
    const normalizedReason = reason.trim();
    if (decision !== 'CONTINUE_CURRENT_MANDATE' && !normalizedReason) {
      setMessage('Add a reason before recording this decision.');
      return;
    }
    setMessage('Recording your review decision...');
    const response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/performance-reviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        idempotencyKey: crypto.randomUUID(),
        command: {
          schemaVersion: '1.0',
          expectedWorkspaceVersion: workspaceVersion,
          expectedSubjectVersion: `performance-${review.reviewId}-${review.revision}`,
          payload: {
            commandKind: 'RESPOND_TO_PERFORMANCE_REVIEW',
            reviewId: review.reviewId,
            reviewRevision: review.revision,
            decision,
            ...(decision === 'CONTINUE_CURRENT_MANDATE' ? {} : { reason: normalizedReason }),
          },
        },
      }),
    });
    setMessage(
      response.ok
        ? 'Review decision recorded. Refreshing will show the authoritative state.'
        : 'Review decision could not be recorded. Refresh the relationship and try again.'
    );
  }

  return (
    <fieldset className="performance-review-controls">
      <legend>Your review decision</legend>
      <label>
        Decision
        <select value={decision} onChange={(event) => setDecision(event.target.value as typeof decision)}>
          {decisions.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {decision !== 'CONTINUE_CURRENT_MANDATE' ? (
        <label>
          Reason
          <textarea maxLength={500} required value={reason} onChange={(event) => setReason(event.target.value)} />
        </label>
      ) : null}
      <button className="primary-command" onClick={() => void submit()} type="button">
        Record review decision
      </button>
      <output>{message}</output>
    </fieldset>
  );
}
