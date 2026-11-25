'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R002, WC171-R004
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import type { KeyboardEvent } from 'react';

export type ContextMenuItem = { id: string; label: string; badge?: number; unavailable?: boolean };

type Props = {
  label: string;
  declaredLabel: string;
  fixed: ContextMenuItem[];
  declared: ContextMenuItem[];
  current: string;
  onChoose: (id: string) => void;
};

function moveWithArrows(event: KeyboardEvent<HTMLElement>) {
  const keys = ['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight'];
  if (!keys.includes(event.key)) return;
  const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not([disabled])'));
  const index = buttons.findIndex((button) => button === document.activeElement);
  if (index < 0) return;
  event.preventDefault();
  const step = event.key === 'ArrowDown' || event.key === 'ArrowRight' ? 1 : -1;
  buttons[(index + step + buttons.length) % buttons.length]?.focus();
}

// The platform's fixed surfaces come first, in one order and wording for every agent; the agent's own entries follow.
export function AgentContextMenu({ label, declaredLabel, fixed, declared, current, onChoose }: Props) {
  function renderItem(item: ContextMenuItem) {
    return (
      <button
        aria-current={current === item.id ? 'page' : undefined}
        className={current === item.id ? 'primary-command' : 'secondary-link'}
        data-surface={item.id}
        key={item.id}
        onClick={() => onChoose(item.id)}
        type="button"
      >
        {item.label}
        {item.badge ? <span> ({item.badge})</span> : null}
      </button>
    );
  }
  return (
    <nav aria-label={label} className="workbench-rail" onKeyDown={moveWithArrows}>
      {fixed.map(renderItem)}
      {declared.length > 0 ? (
        <>
          <p className="section-label workbench-rail-group">{declaredLabel}</p>
          {declared.map(renderItem)}
        </>
      ) : null}
    </nav>
  );
}
