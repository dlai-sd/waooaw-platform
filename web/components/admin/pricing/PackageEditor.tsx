'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { type PricingVersion, formatInr, inrFromPaise, paiseFromInr, versionTag } from '@/lib/pricing-admin-client';
import type { PackageCatalogue, Simulation } from '@/lib/pricing-admin-types';
import {
  MAXIMUM_DESCRIPTION,
  type PackageState,
  allocationTotalPaise,
  buildPackage,
  derivedPrice,
  emptyComponent,
  emptyPackage,
  packageFromBody,
} from '@/lib/pricing-package';
import { type FormEvent, useState } from 'react';
import { Breadcrumb } from '@/components/admin/master-detail/Breadcrumb';
import { type AvailabilityNote, ComponentRow } from './ComponentRow';
import { ComponentTable } from './ComponentTable';
import { PackageBuildUp } from './PackageBuildUp';
import { SaleReadiness } from './SaleReadiness';
import { PricingMessage, usePricingCommand } from './usePricingCommand';

export type PackageTab = 'details' | 'components' | 'review';

type Props = {
  draft: PricingVersion | null;
  // A new draft that starts from the values of an existing version.
  seed?: PricingVersion | null;
  catalogue: PackageCatalogue;
  simulation: Simulation | null;
  tab?: PackageTab;
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

export function PackageEditor({ draft, seed = null, catalogue, simulation, tab = 'details', onSaved }: Props) {
  const target = draft !== null && editable.has(draft.state) ? draft : null;
  const [state, setState] = useState<PackageState>(() => {
    const source = draft ?? seed;
    return source ? packageFromBody(source.body) : emptyPackage();
  });
  const [problems, setProblems] = useState<string[]>([]);
  // The component being edited on its own page; null shows the list of components.
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const { busy, message, run, setMessage } = usePricingCommand();

  const price = paiseFromInr(state.priceInr);
  const derived = derivedPrice(state.priceInr, state.gstRatePercent);
  const allocated = allocationTotalPaise(state.components);
  const agentTypes = [...new Set(catalogue.agents.map((agent) => agent.agentType))];
  const agentVersions = [...new Set(catalogue.agents.map((agent) => agent.agentVersion))];
  const set = (patch: Partial<PackageState>) => setState((current) => ({ ...current, ...patch }));
  const editingIndex = state.components.findIndex((row) => row.key === editingKey);
  const editing = editingIndex >= 0 ? state.components[editingIndex] : undefined;

  function addComponent() {
    const added = emptyComponent();
    set({ components: [...state.components, added] });
    setEditingKey(added.key);
  }

  function removeEditing() {
    if (!editing) return;
    set({ components: state.components.filter((item) => item.key !== editing.key) });
    setEditingKey(null);
  }

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
    extra: { list?: string; inputMode?: 'numeric' | 'decimal'; wide?: boolean } = {}
  ) => (
    <div className={extra.wide ? 'package-field package-field-wide' : 'package-field'}>
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

  const componentLabel = (row: { componentId: string }, index: number) =>
    row.componentId.trim() === '' ? `Component ${index + 1}` : row.componentId;

  return (
    <form
      aria-label="Package draft"
      className="workbench-form package-editor"
      noValidate
      onSubmit={(event) => void save(event)}
    >
      {tab === 'details' ? (
        <div className="package-fields">
          {text('Package code', 'packageCode')}
          {text('Package name', 'displayName', { wide: true })}
          {text('Agent type', 'agentType', { list: 'package-agent-types' })}
          {text('Agent version', 'agentVersion', { list: 'package-agent-versions' })}
          {text('Billing period (days)', 'billingPeriodDays', { inputMode: 'numeric' })}
          {text('Price including GST (INR)', 'priceInr', { inputMode: 'decimal' })}
          {text('GST rate (%)', 'gstRatePercent', { inputMode: 'numeric' })}
          {text('Infrastructure share (INR)', 'infrastructureInr', { inputMode: 'decimal' })}
          {text('Target margin for this package (%)', 'targetMarginPct', { inputMode: 'decimal' })}
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
          <div className="package-field package-field-full">
            <label htmlFor="package-description">Description (the customer maturity this package suits)</label>
            <textarea
              id="package-description"
              maxLength={MAXIMUM_DESCRIPTION}
              onChange={(event) => set({ description: event.target.value })}
              rows={3}
              value={state.description}
            />
          </div>
          <p className="workbench-hint package-field-full">
            Margin is a share of the price, from 0 up to but not including 100. A cost of INR 100 at 50% margin sells
            for INR 200 before GST; markup percentages above 100 are not accepted here.
          </p>
          <output aria-live="polite" className="package-field-full">
            {derived
              ? `Derived base price ${formatInr(derived.basePaise)} plus GST ${formatInr(derived.gstPaise)}. The owner confirms the cost floor and margin when you simulate.`
              : 'Enter the price and GST rate to see the derived base price and GST.'}
          </output>
        </div>
      ) : null}
      {tab === 'components' && editing ? (
        <>
          <Breadcrumb
            trail={[
              { label: 'Components', onSelect: () => setEditingKey(null) },
              { label: componentLabel(editing, editingIndex) },
            ]}
          />
          <ComponentRow
            availability={availabilityFor(editing.componentId)}
            index={editingIndex}
            key={editing.key}
            onChange={(changed) =>
              set({ components: state.components.map((item) => (item.key === editing.key ? changed : item)) })
            }
            onRemove={removeEditing}
            row={editing}
            threads={catalogue.threads}
          />
          <button className="secondary-link" onClick={() => setEditingKey(null)} type="button">
            Back to components
          </button>
        </>
      ) : null}
      {tab === 'components' && !editing ? (
        <>
          <div className="master-detail-heading">
            <h3>Components</h3>
            <button className="primary-command" onClick={addComponent} type="button">
              Add component
            </button>
          </div>
          <ComponentTable availabilityFor={availabilityFor} components={state.components} onSelect={setEditingKey} />
          <output aria-live="polite">{allocationStatus(price, allocated)}</output>
        </>
      ) : null}
      {tab === 'review' ? (
        <>
          <output aria-live="polite">{allocationStatus(price, allocated)}</output>
          <SaleReadiness simulation={simulation} state={state} versionState={draft?.state ?? null} />
          <PackageBuildUp
            onUseSuggestedPrice={(paise) => set({ priceInr: inrFromPaise(paise) })}
            simulation={simulation}
            typedPriceInclGstPaise={price}
          />
        </>
      ) : null}
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
