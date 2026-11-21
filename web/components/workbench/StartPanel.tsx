'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { useId, useState, type FormEvent } from 'react';
import type { WorkbenchBlock } from '@/lib/api/workbench-types';
import { CommandMessage, useWorkbenchCommand, type WorkbenchPanelProps } from './useWorkbenchCommand';

const goalFormPrefix = 'goal:';

type Field = { fieldId: string; label: string };

function goalForms(blocks: WorkbenchBlock[]) {
  return blocks.flatMap((block) => {
    if (block.type !== 'FORM' || block.version > 1) return [];
    const data = block.data as { formId?: unknown; fields?: unknown };
    if (typeof data.formId !== 'string' || !data.formId.startsWith(goalFormPrefix) || !Array.isArray(data.fields))
      return [];
    const fields: Field[] = data.fields.flatMap((field: { fieldId?: unknown; label?: unknown }) =>
      typeof field?.fieldId === 'string' && typeof field.label === 'string'
        ? [{ fieldId: field.fieldId, label: field.label }]
        : []
    );
    return fields.length === 0
      ? []
      : [{ id: block.id, goalTypeId: data.formId.slice(goalFormPrefix.length), title: block.label ?? '', fields }];
  });
}

function GoalForm({
  form,
  disabledReason,
  panel,
}: {
  form: ReturnType<typeof goalForms>[number];
  disabledReason: string | null;
  panel: WorkbenchPanelProps;
}) {
  const { copy, relationshipId, snapshot, onChanged } = panel;
  const identifier = useId();
  const [title, setTitle] = useState(form.title);
  const [values, setValues] = useState<Record<string, string>>({});
  const command = useWorkbenchCommand(relationshipId, copy, onChanged);
  const disabled = command.busy || disabledReason !== null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await command.run('/goals', {
      schemaVersion: '1.0',
      expectedVersion: snapshot.version,
      goalTypeId: form.goalTypeId,
      title: title.trim(),
      parameters: Object.fromEntries(form.fields.map((field) => [field.fieldId, (values[field.fieldId] ?? '').trim()])),
    });
  }

  return (
    <form aria-labelledby={`${identifier}-legend`} className="workbench-form" onSubmit={submit}>
      <h4 id={`${identifier}-legend`}>{form.title || form.goalTypeId}</h4>
      <label htmlFor={`${identifier}-title`}>{copy.goalName}</label>
      <input
        id={`${identifier}-title`}
        maxLength={160}
        onChange={(event) => setTitle(event.target.value)}
        required
        value={title}
      />
      {form.fields.map((field) => (
        <div key={field.fieldId}>
          <label htmlFor={`${identifier}-${field.fieldId}`}>{field.label}</label>
          <input
            id={`${identifier}-${field.fieldId}`}
            maxLength={500}
            onChange={(event) => setValues({ ...values, [field.fieldId]: event.target.value })}
            required
            value={values[field.fieldId] ?? ''}
          />
        </div>
      ))}
      {disabledReason ? <p className="workbench-hint">{disabledReason}</p> : null}
      <button className="primary-command" disabled={disabled} type="submit">
        {command.busy ? copy.working : copy.saveGoal}
      </button>
      <CommandMessage message={command.message} />
    </form>
  );
}

// The agent declares which goals it can take; this panel only draws what the declaration sent.
export function StartPanel(panel: WorkbenchPanelProps) {
  const forms = goalForms(panel.snapshot.projection.blocks);
  if (forms.length === 0 || panel.snapshot.projection.currentGoalRef) return null;
  const create = panel.snapshot.projection.availableCommands.find((command) => command.commandId === 'create_goal');
  const disabledReason =
    create && !create.enabled ? (create.disabledReason ?? panel.copy.problems.WORKBENCH_UNAVAILABLE) : null;
  return (
    <section aria-labelledby="workbench-start-title" className="workbench-section">
      <h3 id="workbench-start-title">{panel.copy.startGoal}</h3>
      {forms.map((form) => (
        <GoalForm disabledReason={disabledReason} form={form} key={form.id} panel={panel} />
      ))}
    </section>
  );
}
