'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { useState, type FormEvent } from 'react';
import { versionTag, type PricingVersion } from '@/lib/pricing-admin-client';
import { buildBody, valuesFromBody, type FormSpec, type FormValues } from '@/lib/pricing-forms';
import { PricingMessage, usePricingCommand } from './usePricingCommand';

type Props = {
  spec: FormSpec;
  draft: PricingVersion | null;
  seedBody?: Record<string, unknown>;
  onSaved: (version: PricingVersion) => void;
};

const editable = new Set(['DRAFT', 'SIMULATED']);

// Shared by the rate, policy, grant, budget and coupon editors; the package editor has its own table.
export function DraftForm({ spec, draft, seedBody, onSaved }: Props) {
  const target = draft !== null && editable.has(draft.state) ? draft : null;
  const [values, setValues] = useState<FormValues>(() => valuesFromBody(spec, (draft ?? { body: seedBody }).body));
  const [reason, setReason] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { busy, message, run, setMessage } = usePricingCommand();

  async function save(event: FormEvent) {
    event.preventDefault();
    const built = buildBody(spec, values);
    if (!built.ok) {
      setErrors(built.errors);
      setMessage({ kind: 'error', text: 'Some fields need attention. They are marked below.' });
      return;
    }
    setErrors({});
    const result = target
      ? await run<PricingVersion>(
          'PUT',
          `drafts/${target.versionId}`,
          {
            schemaVersion: '1.0',
            expectedVersion: versionTag(target),
            body: built.body,
            ...(reason ? { reason } : {}),
          },
          'Draft saved.'
        )
      : await run<PricingVersion>(
          'POST',
          'drafts',
          {
            schemaVersion: '1.0',
            kind: spec.kind,
            subjectKey: built.subjectKey,
            body: built.body,
            ...(reason ? { reason } : {}),
          },
          'Draft created.'
        );
    if (result.ok) onSaved(result.data);
  }

  return (
    <form
      aria-label={`${spec.title} draft`}
      className="workbench-form"
      noValidate
      onSubmit={(event) => void save(event)}
    >
      <h3>{target ? `Edit draft version ${target.versionNo}` : `New ${spec.title.toLowerCase()} draft`}</h3>
      {spec.fields.map((field) => {
        const id = `${spec.kind}-${field.name}`;
        const error = errors[field.name];
        const common = {
          id,
          'aria-invalid': error ? true : undefined,
          'aria-describedby': error ? `${id}-error` : undefined,
          value: values[field.name] ?? '',
        };
        const change = (value: string) => setValues((current) => ({ ...current, [field.name]: value }));
        return (
          <div key={field.name}>
            <label htmlFor={id}>
              {field.label}
              {field.optional ? ' (optional)' : ''}
            </label>
            {field.type === 'select' ? (
              <select {...common} onChange={(event) => change(event.target.value)}>
                <option value="">Choose</option>
                {field.options?.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            ) : (
              <input
                {...common}
                inputMode={
                  field.type === 'int' || field.type === 'number' || field.type === 'inr' ? 'decimal' : undefined
                }
                onChange={(event) => change(event.target.value)}
                type={field.type === 'datetime' ? 'datetime-local' : 'text'}
              />
            )}
            {error ? (
              <p className="workbench-message workbench-message-error" id={`${id}-error`}>
                {error}
              </p>
            ) : null}
          </div>
        );
      })}
      <div>
        <label htmlFor={`${spec.kind}-reason`}>Reason for the change (optional)</label>
        <input
          id={`${spec.kind}-reason`}
          onChange={(event) => setReason(event.target.value)}
          type="text"
          value={reason}
        />
      </div>
      <button className="primary-command" disabled={busy} type="submit">
        {target ? 'Save draft' : 'Create draft'}
      </button>
      <PricingMessage message={message} />
    </form>
  );
}
