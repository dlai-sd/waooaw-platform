'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R014, R015
// Constitutional basis: C-001, C-023, C-042, C-059, C-063

import { useCallback, useEffect, useState } from 'react';
import { buildTree, operationApi, type ItemView, type PlanTreeView, type TreeNode } from '@/lib/agent-operation';
import type { OperationMessages } from '@/lib/operation-i18n';
import { ItemCard } from './ItemCard';

type Props = { relationshipId: string; copy: OperationMessages; refreshKey: number; onChanged: () => void };

function Branch({
  nodes,
  levels,
  depth,
  selectedId,
  onSelect,
}: {
  nodes: TreeNode[];
  levels: PlanTreeView['levels'];
  depth: number;
  selectedId: string | null;
  onSelect: (item: ItemView) => void;
}) {
  return (
    <ul>
      {nodes.map(({ item, children }) => (
        <li key={item.itemId}>
          <button
            aria-expanded={children.length > 0 ? true : undefined}
            aria-pressed={selectedId === item.itemId}
            className="op-node"
            onClick={() => onSelect(item)}
            type="button"
          >
            <span className="op-level">
              {levels.find((level) => level.levelId === item.levelId)?.label ?? item.levelId}
            </span>{' '}
            {item.title}
            <small>
              {' '}
              {item.isApproved ? '✔ approved' : item.state.toLowerCase().replace(/_/g, ' ')}
              {item.startDate ? ` · ${item.startDate}` : ''}
            </small>
          </button>
          {children.length > 0 ? (
            <Branch depth={depth + 1} levels={levels} nodes={children} onSelect={onSelect} selectedId={selectedId} />
          ) : null}
        </li>
      ))}
    </ul>
  );
}

// Any agent's plan as a tree of its own levels. Each level is approved before the next is built.
export function PlanTreeBlock({ relationshipId, copy, refreshKey, onChanged }: Props) {
  const [tree, setTree] = useState<PlanTreeView | null>(null);
  const [failed, setFailed] = useState(false);
  const [selected, setSelected] = useState<ItemView | null>(null);

  const load = useCallback(async () => {
    const result = await operationApi.planTree(relationshipId);
    setFailed(!result.ok);
    if (result.ok) setTree(result.data);
  }, [relationshipId]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  if (failed)
    return (
      <div role="alert">
        <p>{copy.failed}</p>
        <button className="secondary-link" onClick={() => void load()} type="button">
          {copy.retry}
        </button>
      </div>
    );
  if (tree === null) return <p aria-busy="true">{copy.loading}</p>;
  const current = selected ? (tree.nodes.find((node) => node.itemId === selected.itemId) ?? null) : null;
  return (
    <section aria-label={copy.planTitle} className="op-plan">
      <h2>{copy.planTitle}</h2>
      <p>{tree.levels.map((level) => level.label).join(' → ')}</p>
      {tree.nodes.length === 0 ? (
        <p>{copy.nothingYet}</p>
      ) : (
        <Branch
          depth={0}
          levels={tree.levels}
          nodes={buildTree(tree.nodes)}
          onSelect={setSelected}
          selectedId={selected?.itemId ?? null}
        />
      )}
      {current ? (
        <ItemCard
          copy={copy}
          item={current}
          key={`${current.itemId}-${current.versionNo}`}
          onChanged={(next) => {
            setSelected(next);
            onChanged();
            void load();
          }}
          relationshipId={relationshipId}
        />
      ) : null}
    </section>
  );
}
