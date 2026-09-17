'use client';

import { useState } from 'react';
import type { RelationshipGoalV1 } from '@/lib/api/generated/models/RelationshipGoalV1';

interface GoalVerificationControlsProps {
  relationshipId: string;
  workspaceVersion: string;
  goals: RelationshipGoalV1[];
}

export function GoalVerificationControls({ relationshipId, workspaceVersion, goals }: GoalVerificationControlsProps) {
  const [correctionReasons, setCorrectionReasons] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');

  async function decide(goal: RelationshipGoalV1, verificationDecision: 'VERIFIED' | 'CHANGES_REQUESTED') {
    const correctionReason = correctionReasons[goal.goalId]?.trim();
    if (verificationDecision === 'CHANGES_REQUESTED' && !correctionReason) {
      setMessage('Add a correction reason before requesting changes.');
      return;
    }
    setMessage('Saving goal verification...');
    const response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/goal-verifications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        idempotencyKey: crypto.randomUUID(),
        command: {
          schemaVersion: '1.0',
          expectedWorkspaceVersion: workspaceVersion,
          expectedSubjectVersion: goal.goalVersion,
          payload: {
            commandKind: 'VERIFY_GOAL',
            goalId: goal.goalId,
            goalVersion: goal.goalVersion,
            verificationDecision,
            ...(verificationDecision === 'CHANGES_REQUESTED' ? { correctionReason } : {}),
          },
        },
      }),
    });
    setMessage(response.ok
      ? 'Goal verification recorded.'
      : 'Goal verification could not be recorded. Re-authentication or refreshed data may be required.');
  }

  const pendingGoals = goals.filter((goal) => goal.verificationStatus !== 'VERIFIED');
  if (!pendingGoals.length) return null;
  return <div className="goal-verification-controls">
    {pendingGoals.map((goal) => <fieldset key={goal.goalId}>
      <legend>{goal.skillLabel}</legend>
      <label>Correction reason
        <input
          maxLength={500}
          onChange={(event) => setCorrectionReasons((current) => ({ ...current, [goal.goalId]: event.target.value }))}
          value={correctionReasons[goal.goalId] ?? ''}
        />
      </label>
      <div className="command-row">
        <button className="primary-command" onClick={() => void decide(goal, 'VERIFIED')} type="button">Verify goal</button>
        <button className="secondary-link" onClick={() => void decide(goal, 'CHANGES_REQUESTED')} type="button">Request changes</button>
      </div>
    </fieldset>)}
    <p role="status">{message}</p>
  </div>;
}