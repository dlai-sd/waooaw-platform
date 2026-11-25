'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R003, WC171-R004
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { ConnectionsWorkspace } from '@/components/connections/ConnectionsWorkspace';
import type { DeclaredEntry } from '@/lib/navigation-model';
import type { WorkbenchBlock } from '@/lib/api/workbench-types';
import type { WorkbenchMessages } from '@/lib/workbench-i18n';
import { BlockRenderer } from './BlockRenderer';

type Props = { entry: DeclaredEntry; blocks: WorkbenchBlock[]; copy: WorkbenchMessages; onOpenWork?: () => void };

// The platform draws every declared entry from kernel views and blocks it already owns. The agent names what to open;
// it never supplies markup, layout or code, so this component contains no agent-specific branch.
export function blocksForEntry(entry: DeclaredEntry, blocks: WorkbenchBlock[]): WorkbenchBlock[] {
  if (entry.surfaceKind === 'DOMAIN_BLOCK')
    return blocks.filter((block) => block.type === 'DOMAIN' && block.id === entry.target);
  if (entry.surfaceKind === 'BLOCK_COMPOSITION') return blocks.filter((block) => entry.blocks.includes(block.type));
  return [];
}

export function DeclaredSurface({ entry, blocks, copy, onOpenWork }: Props) {
  if (!entry.available) return <p>{copy.declaredNotAvailable}</p>;
  if (entry.surfaceKind === 'KERNEL_VIEW' && entry.target === 'connections') return <ConnectionsWorkspace />;
  const shown = blocksForEntry(entry, blocks);
  return (
    <section aria-label={entry.label} className="declared-surface">
      <h3>{entry.label}</h3>
      {shown.length === 0 ? (
        <>
          <p>{copy.declaredNothingYet}</p>
          {onOpenWork ? (
            <button className="secondary-link" onClick={onOpenWork} type="button">
              {copy.toolWork}
            </button>
          ) : null}
        </>
      ) : null}
      {shown.map((block) => (
        <BlockRenderer block={block} copy={copy} key={block.id} />
      ))}
    </section>
  );
}
