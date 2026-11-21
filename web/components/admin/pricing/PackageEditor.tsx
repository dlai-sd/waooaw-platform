'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { useState, type FormEvent } from 'react';
import { formatInr, paiseFromInr, versionTag, type PricingVersion } from '@/lib/pricing-admin-client';
import type { PackageCatalogue, Simulation } from '@/lib/pricing-admin-types';
import {
  allocationTotalPaise,
  buildPackage,
  derivedPrice,
  emptyComponent,
  emptyPackage,
  packageFromBody,
  type PackageState,
} from '@/lib/pricing-package';
import { ComponentRow, type AvailabilityNote } from './ComponentRow';
import { PricingMessage, usePricingCommand } from './usePricingCommand';

type Props = {
  draft: PricingVersion | null;
  catalogue: PackageCatalogue;
  simulation: Simulation | null;
  onSaved: (version: PricingVersion) => void;
};

const editable = new Set(['DRAFT', 'SIMULATED']);

function allocationStatus(price: number | null, allocated: number): string {
  if (price === null) return `Allocated ${formatInr(allocated)}. Enter the package price to compare.`;
  if (allocated === price) return `Allocated ${formatInr(allocated)} of ${formatInr(price)}: matches the price.`;
  if (allocated < price)
    return `Allocated ${formatInr(allocated)} of ${formatInr(price)}: short by ${formatInr(price - allocated)}.`;
  return `Allocated ${formatInr(allocated)} of ${formatInr(price)}: over by ${formatInr(allocated - price)}.`;
}

export function PackageEditor({ draft, catalogue, simulation, onSaved }: Props) {
  const target = draft !== null && editable.has(draft.state) ? draft : null;
  const [state, setState] = useState<PackageState>(() => (draft ? packageFromBody(draft.body) : emptyPackage()));
  const [problems, setProblems] = useState<string[]>([]);
  const { busy, message, run, setMessage } = usePricingCommand();

  const price = paiseFromInr(state.priceInr);
  const derived = derivedPrice(state.priceInr, state.gstRatePercent);
  const allocated = allocationTotalPaise(state.components);
  const agentTypes = [...new Set(catalogue.agents.map((agent) => agent.agentType))];
  const agentVersions = [...new Set(catalogue.agents.map((agent) => agent.agentVersion))];
  const set = (patch: Partial<PackageState>) => setState((current) => ({ ...current, ...patch }));

  const availabilityFor = (componentId: string): AvailabilityNote => {
    if (simulation === null) return 'UNCHECKED';
    const flagged = simulation.warnings.some(
      (warning) => warning.code === 'PACKAGE_COMPONENT_NOT_AVAILABLE' && warning.componentId === componentId
    );
    return flagged ? 'UNAVAILABLE' : 'CHECKED';
  };

  async function save(event: FormEvent) {
    event.preventDefault();
    const built = buildPackage(state);
    if (!built.ok) {
      setProblems(built.errors);
      setMessage({ kind: 'error', text: 'The package needs attention. The items are listed below.' });
      return;
    }
    setProblems([]);
    const result = target
      ? await run<PricingVersion>(
          'PUT',
          `drafts/${target.versionId}`,
          { schemaVersion: '1.0', expectedVersion: versionTag(target), body: built.body },
          'Draft saved.'
        )
      : await run<PricingVersion>(
          'POST',
          'drafts',
          { schemaVersion: '1.0', kind: 'PACKAGE', subjectKey: built.subjectKey, body: built.body },
          'Draft created.'
        );
    if (result.ok) onSaved(result.data);
  }

  const text = (
    label: string,
    field: keyof Omit<PackageState, 'components'>,
    extra: { list?: string; inputMode?: 'numeric' | 'decimal' } = {}
  ) => (
    <div>
      <label htmlFor={`package-${field}`}>{label}</label>
      <input
        id={`package-${field}`}
        inputMode={extra.inputMode}
        list={extra.list}
        onChange={(event) => set({ [field]: event.target.value } as Partial<PackageState>)}
        type="text"
        value={state[field]}
      />
    </div>
  );

  return (
    <form aria-label="Package draft" className="workbench-form" noValidate onSubmit={(event) => void save(event)}>
      <h3>{target ? `Edit package draft version ${target.versionNo}` : 'New package draft'}</h3>
      {text('Agent type', 'agentType', { list: 'package-agent-types' })}
      {text('Agent version', 'agentVersion', { list: 'package-agent-versions' })}
      <datalist id="package-agent-types">
        {agentTypes.map((agentType) => (
          <option key={agentType} value={agentType} />
        ))}
      </datalist>
      <datalist id="package-agent-versions">
        {agentVersions.map((agentVersion) => (
          <option key={agentVersion} value={agentVersion} />
        ))}
      </datalist>
      {text('Package code', 'packageCode')}
      {text('Package name', 'displayName')}
      {text('Billing period (days)', 'billingPeriodDays', { inputMode: 'numeric' })}
      {text('Price including GST (INR)', 'priceInr', { inputMode: 'decimal' })}
      {text('GST rate (%)', 'gstRatePercent', { inputMode: 'numeric' })}
      {text('Infrastructure share (INR)', 'infrastructureInr', { inputMode: 'decimal' })}
      <output aria-live="polite">
        {derived
          ? `Derived base price ${formatInr(derived.basePaise)} plus GST ${formatInr(derived.gstPaise)}. The owner confirms the cost floor and margin when you simulate.`
          : 'Enter the price and GST rate to see the derived base price and GST.'}
      </output>
      {state.components.map((row, index) => (
        <ComponentRow
          availability={availabilityFor(row.componentId)}
          index={index}
          key={row.key}
          onChange={(changed) =>
            set({ components: state.components.map((item) => (item.key === row.key ? changed : item)) })
          }
          onRemove={() => set({ components: state.components.filter((item) => item.key !== row.key) })}
          row={row}
          threads={catalogue.threads}
        />
      ))}
      <button
        className="secondary-link"
        onClick={() => set({ components: [...state.components, emptyComponent()] })}
        type="button"
      >
        Add component
      </button>
      <output aria-live="polite">{allocationStatus(price, allocated)}</output>
      <button className="primary-command" disabled={busy} type="submit">
        {target ? 'Save draft' : 'Create draft'}
      </button>
      {problems.length > 0 ? (
        <ul aria-label="Package problems" className="workbench-plain-list">
          {problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      ) : null}
      <PricingMessage message={message} />
    </form>
  );
}
