'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { useId, useState, type FormEvent } from 'react';
import type { Wire } from '@/lib/api/workbench-types';
import type { WorkbenchTopupReceiptV1 } from '@/lib/api/generated/workbench-v1/src';
import { labelFor } from '@/lib/workbench-i18n';
import { CommandMessage, useWorkbenchCommand, type WorkbenchPanelProps } from './useWorkbenchCommand';

type Receipt = Wire<WorkbenchTopupReceiptV1>;

const rupees = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' });

export function WalletPanel(panel: WorkbenchPanelProps) {
  const { copy, snapshot } = panel;
  const wallet = snapshot.wallet;
  const identifier = useId();
  const command = useWorkbenchCommand(panel.relationshipId, copy, panel.onChanged);
  const [componentId, setComponentId] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const topUp = snapshot.projection.availableCommands.find((item) => item.commandId === 'top_up');
  const selected = componentId || wallet?.components[0]?.componentId || '';

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setReceipt(null);
    const result = await command.run<Receipt>('/topups', {
      schemaVersion: '1.0',
      expectedVersion: snapshot.version,
      componentId: selected,
      quantity: Number(quantity),
    });
    if (result.ok) setReceipt(result.data);
  }

  return (
    <section aria-labelledby="workbench-wallet-title" className="workbench-section">
      <h3 id="workbench-wallet-title">{copy.wallet}</h3>
      {wallet === null ? <p>{copy.problems.SPEND_COMMERCIAL_UNAVAILABLE}</p> : null}
      {wallet !== null && wallet.components.length === 0 ? <p>{copy.noComponents}</p> : null}
      {wallet !== null && wallet.components.length > 0 ? (
        <>
          <p className="workbench-hint">
            {copy.periodEnds}: {wallet.periodEnd.slice(0, 10)}
          </p>
          <ul className="workbench-cards">
            {wallet.components.map((component) => (
              <li className="workbench-card" key={component.componentId}>
                <h4>{component.label}</h4>
                <p className="workbench-metric">
                  {copy.remaining}: {component.remaining} / {component.quantity}
                </p>
              </li>
            ))}
          </ul>
          {wallet.askAccountOwner ? <p>{copy.askAccountOwner}</p> : null}
          {wallet.topUpAvailable && !wallet.askAccountOwner ? (
            <form aria-label={copy.topUp} className="workbench-form" onSubmit={submit}>
              <label htmlFor={`${identifier}-component`}>{copy.topUpComponent}</label>
              <select
                id={`${identifier}-component`}
                onChange={(event) => setComponentId(event.target.value)}
                value={selected}
              >
                {wallet.components.map((component) => (
                  <option key={component.componentId} value={component.componentId}>
                    {component.label}
                  </option>
                ))}
              </select>
              <label htmlFor={`${identifier}-quantity`}>{copy.topUpQuantity}</label>
              <input
                id={`${identifier}-quantity`}
                inputMode="numeric"
                min={1}
                onChange={(event) => setQuantity(event.target.value)}
                required
                step={1}
                type="number"
                value={quantity}
              />
              {topUp && !topUp.enabled && topUp.disabledReason ? (
                <p className="workbench-hint">{topUp.disabledReason}</p>
              ) : null}
              <button
                className="primary-command"
                disabled={command.busy || (topUp ? !topUp.enabled : false) || selected === ''}
                type="submit"
              >
                {command.busy ? copy.working : copy.topUp}
              </button>
            </form>
          ) : null}
        </>
      ) : null}
      {receipt ? (
        <output aria-live="polite">
          {labelFor(copy.topUpStates, receipt.status)} {copy.price}: {rupees.format(receipt.priceInclGstPaise / 100)}
        </output>
      ) : null}
      <CommandMessage message={command.message} />
    </section>
  );
}
