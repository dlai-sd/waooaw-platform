'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { useId, useState, type FormEvent } from 'react';
import type { Wire } from '@/lib/api/workbench-types';
import type { WorkbenchGoalV1 } from '@/lib/api/generated/workbench-v1/src';
import { readWorkbench } from '@/lib/workbench-client';
import { labelFor, plainWords } from '@/lib/workbench-i18n';
import { CommandMessage, useWorkbenchCommand, type WorkbenchPanelProps } from './useWorkbenchCommand';

type GoalDetail = Wire<WorkbenchGoalV1>;

function ReviseGoal({ goalId, panel }: { goalId: string; panel: WorkbenchPanelProps }) {
  const { copy, relationshipId, snapshot, onChanged } = panel;
  const identifier = useId();
  const [detail, setDetail] = useState<GoalDetail | null>(null);
  const [open, setOpen] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [title, setTitle] = useState('');
  const [values, setValues] = useState<Record<string, string>>({});
  const [reason, setReason] = useState('');
  const command = useWorkbenchCommand(relationshipId, copy, onChanged);

  async function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    const result = await readWorkbench<GoalDetail>(relationshipId, `/goals/${encodeURIComponent(goalId)}`);
    if (!result.ok) {
      setLoadFailed(true);
      return;
    }
    setLoadFailed(false);
    setDetail(result.data);
    setTitle(result.data.goal.title);
    setValues(result.data.parameters);
    setOpen(true);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = await command.run(`/goals/${encodeURIComponent(goalId)}/revisions`, {
      schemaVersion: '1.0',
      expectedVersion: snapshot.version,
      title: title.trim(),
      parameters: values,
      reason: reason.trim(),
    });
    if (result.ok) {
      setOpen(false);
      setReason('');
    }
  }

  return (
    <div>
      <button aria-expanded={open} className="secondary-link" onClick={toggle} type="button">
        {copy.reviseGoal}
      </button>
      {loadFailed ? <p role="alert">{copy.problems.WORKBENCH_UNAVAILABLE}</p> : null}
      {open && detail ? (
        <form aria-label={copy.reviseGoal} className="workbench-form" onSubmit={submit}>
          <label htmlFor={`${identifier}-title`}>{copy.goalName}</label>
          <input
            id={`${identifier}-title`}
            maxLength={160}
            onChange={(event) => setTitle(event.target.value)}
            required
            value={title}
          />
          {Object.keys(detail.parameters).map((name) => (
            <div key={name}>
              <label htmlFor={`${identifier}-${name}`}>{plainWords(name)}</label>
              <input
                id={`${identifier}-${name}`}
                maxLength={500}
                onChange={(event) => setValues({ ...values, [name]: event.target.value })}
                required
                value={values[name] ?? ''}
              />
            </div>
          ))}
          <label htmlFor={`${identifier}-reason`}>{copy.reasonForChange}</label>
          <input
            id={`${identifier}-reason`}
            maxLength={500}
            onChange={(event) => setReason(event.target.value)}
            required
            value={reason}
          />
          <button className="primary-command" disabled={command.busy} type="submit">
            {command.busy ? copy.working : copy.reviseGoal}
          </button>
        </form>
      ) : null}
      <CommandMessage message={command.message} />
    </div>
  );
}

function PlanSection(panel: WorkbenchPanelProps) {
  const { copy, snapshot } = panel;
  const { plan, projection } = snapshot;
  const [acknowledged, setAcknowledged] = useState(false);
  const identifier = useId();
  const command = useWorkbenchCommand(panel.relationshipId, copy, panel.onChanged);
  const propose = projection.availableCommands.find((item) => item.commandId === 'propose_plan');
  const accept = projection.availableCommands.find((item) => item.commandId === 'accept_plan');

  if (plan === null) {
    return (
      <section aria-labelledby={`${identifier}-plan`} className="workbench-section">
        <h3 id={`${identifier}-plan`}>{copy.plan}</h3>
        <p>{copy.noPlan}</p>
      </section>
    );
  }
  const goalId = projection.currentGoalRef;
  const canPropose = Boolean(propose?.enabled) && Boolean(goalId) && plan.milestones.length > 0;
  return (
    <section aria-labelledby={`${identifier}-plan`} className="workbench-section">
      <h3 id={`${identifier}-plan`}>
        {copy.plan} {plan.planVersion} · {labelFor(copy.planStates, plan.state)}
      </h3>
      {plan.milestones.length === 0 ? <p>{copy.noPlan}</p> : null}
      {plan.milestones.length > 0 ? (
        <ol aria-label={copy.milestones} className="workbench-plain-list">
          {plan.milestones.map((milestone) => (
            <li key={milestone.milestoneId}>
              <strong>{milestone.title}</strong> {milestone.dueMeaning} · {labelFor(copy.states, milestone.state)}
            </li>
          ))}
        </ol>
      ) : null}
      {plan.calendar.length > 0 ? (
        <ul aria-label={copy.calendar} className="workbench-plain-list">
          {plan.calendar.map((entry) => (
            <li key={`${entry.date}-${entry.title}`}>
              {entry.date.slice(0, 10)} {entry.title}
            </li>
          ))}
        </ul>
      ) : null}
      {plan.limitations.length > 0 ? (
        <ul aria-label={copy.limitations} className="workbench-plain-list">
          {plan.limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      ) : null}
      {canPropose && plan.state === 'DRAFT' ? (
        <button
          className="primary-command"
          disabled={command.busy}
          onClick={() =>
            command.run('/plans', {
              schemaVersion: '1.0',
              expectedVersion: snapshot.version,
              goalId,
              milestones: plan.milestones.map((milestone) => ({
                milestoneTypeId: milestone.milestoneTypeId,
                title: milestone.title,
              })),
            })
          }
          type="button"
        >
          {copy.proposePlan}
        </button>
      ) : null}
      {plan.state === 'READY_FOR_REVIEW' && accept ? (
        <div>
          <label>
            <input checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} type="checkbox" />{' '}
            {copy.acknowledgeLimits}
          </label>
          {!accept.enabled && accept.disabledReason ? <p className="workbench-hint">{accept.disabledReason}</p> : null}
          <button
            className="primary-command"
            disabled={command.busy || !accept.enabled || !acknowledged}
            onClick={() =>
              command.run(`/plans/${encodeURIComponent(plan.planVersion)}/accept`, {
                schemaVersion: '1.0',
                expectedVersion: snapshot.version,
                acknowledgedLimitations: acknowledged,
              })
            }
            type="button"
          >
            {copy.agreePlan}
          </button>
        </div>
      ) : null}
      <CommandMessage message={command.message} />
    </section>
  );
}

export function GoalPlanPanel(panel: WorkbenchPanelProps) {
  const { copy, snapshot } = panel;
  const goals = snapshot.goals?.items ?? [];
  const mayChange = snapshot.projection.availableCommands.some(
    (command) => command.commandId === 'create_goal' && command.enabled
  );
  return (
    <div className="workbench-stack">
      <section aria-labelledby="workbench-goals-title" className="workbench-section">
        <h3 id="workbench-goals-title">{copy.goals}</h3>
        {snapshot.goals === null ? <p>{copy.problems.WORKBENCH_UNAVAILABLE}</p> : null}
        {snapshot.goals !== null && goals.length === 0 ? <p>{copy.noGoals}</p> : null}
        <ul className="workbench-plain-list">
          {goals.map((goal) => (
            <li key={goal.goalId}>
              <strong>{goal.title}</strong> · {labelFor(copy.states, goal.state)} · {copy.goalVersion}{' '}
              {goal.currentVersion}
              {mayChange && goal.state === 'ACTIVE' ? <ReviseGoal goalId={goal.goalId} panel={panel} /> : null}
            </li>
          ))}
        </ul>
      </section>
      <PlanSection {...panel} />
    </div>
  );
}
