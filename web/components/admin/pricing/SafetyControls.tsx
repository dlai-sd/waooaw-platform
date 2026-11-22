'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { useState, type FormEvent, type ReactNode } from 'react';
import { paiseFromInr, type PricingVersion } from '@/lib/pricing-admin-client';
import { formSpecs } from '@/lib/pricing-forms';
import { PricingMessage, usePricingCommand } from './usePricingCommand';

type SafetyResult = { direction: string; state: string; founderNotified: boolean };

type ActionProps = {
  title: string;
  hint: string;
  path: string;
  submitLabel: string;
  successText: string;
  children: ReactNode;
  buildBody: () => Record<string, unknown> | string;
};

function SafetyAction({ title, hint, path, submitLabel, successText, children, buildBody }: ActionProps) {
  const { busy, message, run, setMessage } = usePricingCommand();

  async function send(event: FormEvent) {
    event.preventDefault();
    const body = buildBody();
    if (typeof body === 'string') {
      setMessage({ kind: 'error', text: body });
      return;
    }
    const result = await run<SafetyResult>('POST', path, { schemaVersion: '1.0', ...body });
    if (result.ok) {
      setMessage({
        kind: 'success',
        text: `${successText} It took effect now.${result.data.founderNotified ? ' The Founder was notified.' : ''}`,
      });
    }
  }

  return (
    <form aria-label={title} className="workbench-form" noValidate onSubmit={(event) => void send(event)}>
      <h3>{title}</h3>
      <p className="workbench-hint">{hint}</p>
      {children}
      <button className="secondary-link" disabled={busy} type="submit">
        {submitLabel}
      </button>
      <PricingMessage message={message} />
    </form>
  );
}

type Props = { packages: PricingVersion[]; grants: PricingVersion[] };

const budgetScopes = formSpecs.BUDGET.fields.find((field) => field.name === 'scope')?.options ?? [];

export function SafetyControls({ packages, grants }: Props) {
  const [scope, setScope] = useState('');
  const [ref, setRef] = useState('');
  const [maximum, setMaximum] = useState('');
  const [ceilingReason, setCeilingReason] = useState('');
  const [packageId, setPackageId] = useState('');
  const [packageReason, setPackageReason] = useState('');
  const [grantKey, setGrantKey] = useState('');
  const [grantReason, setGrantReason] = useState('');

  return (
    <section aria-label="Safety controls" className="workbench-section">
      <h2>Safety controls</h2>
      <div className="pricing-action-grid">
        <SafetyAction
          hint="This takes effect now, without waiting for the Founder. Only lowering is possible here."
          buildBody={() => {
            const paise = paiseFromInr(maximum);
            if (scope === '' || ref.trim() === '') return 'Choose a scope and give its reference.';
            if (paise === null) return 'The new maximum must be an amount with at most two decimals.';
            if (ceilingReason.trim() === '') return 'Give a reason.';
            return { scope, ref: ref.trim(), newMaximumPaise: paise, reason: ceilingReason.trim() };
          }}
          path="safety/lower-ceiling"
          submitLabel="Lower ceiling now"
          successText="The ceiling was lowered."
          title="Lower a ceiling"
        >
          <label htmlFor="safety-scope">Ceiling scope</label>
          <select id="safety-scope" onChange={(event) => setScope(event.target.value)} value={scope}>
            <option value="">Choose</option>
            {budgetScopes.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <label htmlFor="safety-ref">Scope reference</label>
          <input id="safety-ref" onChange={(event) => setRef(event.target.value)} type="text" value={ref} />
          <label htmlFor="safety-maximum">New maximum (INR)</label>
          <input
            id="safety-maximum"
            inputMode="decimal"
            onChange={(event) => setMaximum(event.target.value)}
            type="text"
            value={maximum}
          />
          <label htmlFor="safety-ceiling-reason">Reason for lowering</label>
          <input
            id="safety-ceiling-reason"
            onChange={(event) => setCeilingReason(event.target.value)}
            type="text"
            value={ceilingReason}
          />
        </SafetyAction>
        <SafetyAction
          buildBody={() => {
            if (packageId === '') return 'Choose the package to close.';
            if (packageReason.trim() === '') return 'Give a reason.';
            return { packageId, reason: packageReason.trim() };
          }}
          path="safety/close-package"
          submitLabel="Close to new customers now"
          successText="The package is closed to new customers. Existing customers keep it."
          title="Close a package to new customers"
          hint="This takes effect now, without waiting for the Founder. Existing customers keep the package."
        >
          <label htmlFor="safety-package">Package</label>
          <select id="safety-package" onChange={(event) => setPackageId(event.target.value)} value={packageId}>
            <option value="">Choose</option>
            {packages.map((version) => (
              <option key={version.versionId} value={version.versionId}>
                {version.subjectKey} (version {version.versionNo})
              </option>
            ))}
          </select>
          <label htmlFor="safety-package-reason">Reason for closing</label>
          <input
            id="safety-package-reason"
            onChange={(event) => setPackageReason(event.target.value)}
            type="text"
            value={packageReason}
          />
        </SafetyAction>
        <SafetyAction
          buildBody={() => {
            if (grantKey === '') return 'Choose the grant to disable.';
            if (grantReason.trim() === '') return 'Give a reason.';
            return { subjectKey: grantKey, reason: grantReason.trim() };
          }}
          path="safety/disable-grant"
          submitLabel="Disable grant now"
          successText="The grant is disabled for new relationships."
          title="Disable a grant"
          hint="This takes effect now, without waiting for the Founder. New relationships stop receiving the grant."
        >
          <label htmlFor="safety-grant">Grant</label>
          <select id="safety-grant" onChange={(event) => setGrantKey(event.target.value)} value={grantKey}>
            <option value="">Choose</option>
            {[...new Set(grants.map((version) => version.subjectKey))].map((subjectKey) => (
              <option key={subjectKey} value={subjectKey}>
                {subjectKey}
              </option>
            ))}
          </select>
          <label htmlFor="safety-grant-reason">Reason for disabling</label>
          <input
            id="safety-grant-reason"
            onChange={(event) => setGrantReason(event.target.value)}
            type="text"
            value={grantReason}
          />
        </SafetyAction>
      </div>
    </section>
  );
}
