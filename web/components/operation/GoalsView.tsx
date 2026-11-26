'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R013, R014
// Constitutional basis: C-001, C-023, C-042, C-059, C-063

import { useState } from 'react';
import { humanize, operationApi, problemText, type GoalSkill } from '@/lib/agent-operation';
import type { OperationMessages } from '@/lib/operation-i18n';

const cadences = ['DAILY', 'WEEKLY', 'MONTHLY', 'TWO_MONTHLY', 'QUARTERLY'] as const;

type Props = {
  relationshipId: string;
  skills: GoalSkill[];
  approvalModes: string[];
  copy: OperationMessages;
  labels: Record<string, string>;
  onChanged: () => void;
};

function field(goal: GoalSkill['goal'], name: string): string {
  const value = goal?.payload?.[name];
  return typeof value === 'string' ? value : '';
}

function GoalCard({
  skill,
  approvalModes,
  relationshipId,
  copy,
  labels,
  onChanged,
}: { skill: GoalSkill } & Omit<Props, 'skills'>) {
  const [baseline, setBaseline] = useState(field(skill.goal, 'baseline'));
  const [target, setTarget] = useState(field(skill.goal, 'target'));
  const [source, setSource] = useState(field(skill.goal, 'evidenceSource'));
  const [cadence, setCadence] = useState(field(skill.goal, 'cadence') || 'MONTHLY');
  const [authority, setAuthority] = useState(field(skill.goal, 'authorityState') || approvalModes[0] || '');
  const [message, setMessage] = useState('');
  const pending =
    skill.state === 'PENDING_CONFIRMATION'
      ? (skill.goal?.payload?.pending as Record<string, string> | undefined)
      : undefined;

  async function save() {
    const result = await operationApi.setGoal(relationshipId, skill.skillId, {
      baseline,
      target,
      evidenceSource: source,
      cadence,
      authorityState: authority,
    });
    if (result.ok) {
      setMessage('');
      onChanged();
    } else {
      setMessage(problemText(result.problem));
    }
  }

  async function decide(accept: boolean) {
    const result = await operationApi.decideGoal(relationshipId, skill.skillId, accept);
    if (result.ok) onChanged();
    else setMessage(problemText(result.problem));
  }

  const name = labels[skill.skillId] ?? humanize(skill.skillId);
  return (
    <li className="op-goal" data-state={skill.state}>
      <form
        aria-label={name}
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <h3>
          {name}{' '}
          <small className="op-badge">{skill.state === 'CONFIRMED' ? copy.confirmed : humanize(skill.state)}</small>
        </h3>
        <label>
          {copy.baseline}
          <input maxLength={160} onChange={(event) => setBaseline(event.target.value)} required value={baseline} />
        </label>
        <label>
          {copy.target}
          <input maxLength={160} onChange={(event) => setTarget(event.target.value)} required value={target} />
        </label>
        <label>
          {copy.evidenceSource}
          <input maxLength={160} onChange={(event) => setSource(event.target.value)} required value={source} />
        </label>
        <label>
          {copy.cadence}
          <select onChange={(event) => setCadence(event.target.value)} value={cadence}>
            {cadences.map((value) => (
              <option key={value} value={value}>
                {humanize(value)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {copy.authority}
          <select onChange={(event) => setAuthority(event.target.value)} value={authority}>
            {approvalModes.map((mode) => (
              <option key={mode} value={mode}>
                {humanize(mode)}
              </option>
            ))}
          </select>
        </label>
        <button className="primary-command" type="submit">
          {copy.saveGoal}
        </button>
      </form>
      {skill.state === 'PROPOSED' || skill.state === 'PENDING_CONFIRMATION' ? (
        <div className="op-pending">
          <p>
            {copy.pendingGoal}
            {pending?.target ? `: ${pending.target}` : ''}
          </p>
          <button className="primary-command" onClick={() => void decide(true)} type="button">
            {copy.accept}
          </button>
          <button className="secondary-link" onClick={() => void decide(false)} type="button">
            {copy.declineDigest}
          </button>
        </div>
      ) : null}
      <output aria-live="polite">{message}</output>
    </li>
  );
}

// A goal for each skill with the fields every live action depends on. A material change waits for the customer.
export function GoalsView({ skills, ...rest }: Props) {
  return (
    <section aria-label={rest.copy.goalsTitle} className="op-goals">
      <h2>{rest.copy.goalsTitle}</h2>
      <ul>
        {skills.map((skill) => (
          <GoalCard key={`${skill.skillId}-${skill.goal?.versionNo ?? 0}`} skill={skill} {...rest} />
        ))}
      </ul>
    </section>
  );
}
