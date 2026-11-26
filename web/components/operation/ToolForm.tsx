'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R036, R027
// Constitutional basis: C-001, C-023, C-042, C-059, C-061, C-063

import { useEffect, useState } from 'react';
import {
  operationApi,
  problemText,
  type FlyoutOption,
  type ItemView,
  type LayerView,
  type PlatformView,
  type ToolDecl,
} from '@/lib/agent-operation';
import type { OperationMessages } from '@/lib/operation-i18n';

type Props = {
  relationshipId: string;
  tool: ToolDecl;
  option?: FlyoutOption;
  layers: LayerView[];
  platforms: PlatformView[];
  planLevels: { levelId: string; label: string }[];
  today: string;
  copy: OperationMessages;
  onCreated: (item: ItemView) => void;
  onClose: () => void;
  onSchedule: () => void;
};

const kindOf: Record<ToolDecl['command'], string> = {
  ADD_EVENT: 'EVENT',
  ADD_PLACEHOLDER: 'PLACEHOLDER',
  ADD_PLAN_NODE: 'PLAN_NODE',
  ADD_CONTENT: 'CONTENT',
  ADD_SLOT: 'SLOT',
  ADD_NOTE: 'NOTE',
};

// The customer's own events, themes, stories, posts and notes: the same command the conversation uses, the same
// states and approvals as anything the agent makes. A slot is scheduled from an approved post, so that tool says so.
export function ToolForm({
  relationshipId,
  tool,
  option,
  layers,
  platforms,
  planLevels,
  today,
  copy,
  onCreated,
  onClose,
  onSchedule,
}: Props) {
  const [title, setTitle] = useState(option ? `${option.label}: ` : '');
  const [body, setBody] = useState('');
  const [date, setDate] = useState(today);
  const [layer, setLayer] = useState(layers.find((value) => value.on)?.layerId ?? '');
  const [platformId, setPlatformId] = useState(platforms[0]?.platformId ?? '');
  const [parentId, setParentId] = useState('');
  const [parents, setParents] = useState<ItemView[]>([]);
  const [message, setMessage] = useState('');

  const levelIndex = planLevels.findIndex((level) => level.levelId === tool.planLevel);
  const needsParent = tool.command === 'ADD_PLAN_NODE' && levelIndex > 0;

  useEffect(() => {
    if (!needsParent) return;
    void operationApi.planTree(relationshipId).then((result) => {
      if (result.ok)
        setParents(result.data.nodes.filter((node) => node.levelId === planLevels[levelIndex - 1]?.levelId));
    });
  }, [needsParent, relationshipId, planLevels, levelIndex]);

  if (tool.command === 'ADD_SLOT') {
    return (
      <section aria-label={tool.label} className="op-tool-form">
        <p>{copy.scheduleTitle}</p>
        <button className="primary-command" onClick={onSchedule} type="button">
          {copy.schedule}
        </button>
        <button className="secondary-link" onClick={onClose} type="button">
          {copy.cancel}
        </button>
      </section>
    );
  }

  async function submit() {
    const result = await operationApi.create(relationshipId, {
      kind: kindOf[tool.command],
      title,
      body: body || undefined,
      layer: tool.command === 'ADD_EVENT' && layer ? layer : undefined,
      levelId: tool.planLevel ?? undefined,
      parentId: parentId || undefined,
      startDate: tool.command === 'ADD_NOTE' ? undefined : date || undefined,
      platformId: tool.command === 'ADD_CONTENT' ? platformId || undefined : undefined,
      componentId: tool.command === 'ADD_CONTENT' ? (tool.componentId ?? undefined) : undefined,
      route: 'TOOL',
    });
    if (result.ok) onCreated(result.data);
    else setMessage(problemText(result.problem));
  }

  return (
    <form
      aria-label={tool.label}
      className="op-tool-form"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <h3>{tool.label}</h3>
      <label>
        {copy.titleField}
        <input maxLength={160} onChange={(event) => setTitle(event.target.value)} required value={title} />
      </label>
      {tool.command === 'ADD_CONTENT' || tool.command === 'ADD_NOTE' || tool.command === 'ADD_PLAN_NODE' ? (
        <label>
          {copy.textField}
          <textarea maxLength={2000} onChange={(event) => setBody(event.target.value)} value={body} />
        </label>
      ) : null}
      {tool.command === 'ADD_NOTE' ? null : (
        <label>
          {copy.dateField}
          <input
            onChange={(event) => setDate(event.target.value)}
            required={tool.command === 'ADD_EVENT'}
            type="date"
            value={date}
          />
        </label>
      )}
      {tool.command === 'ADD_EVENT' ? (
        <label>
          {copy.layersLabel}
          <select onChange={(event) => setLayer(event.target.value)} value={layer}>
            {layers.map((value) => (
              <option key={value.layerId} value={value.layerId}>
                {value.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {tool.command === 'ADD_CONTENT' ? (
        <label>
          {copy.platformsTitle}
          <select onChange={(event) => setPlatformId(event.target.value)} value={platformId}>
            {platforms.map((value) => (
              <option key={value.platformId} value={value.platformId}>
                {value.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {needsParent ? (
        <label>
          {planLevels[levelIndex - 1]?.label}
          <select onChange={(event) => setParentId(event.target.value)} required value={parentId}>
            <option value="">—</option>
            {parents.map((node) => (
              <option key={node.itemId} value={node.itemId}>
                {node.title}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <button className="primary-command" type="submit">
        {copy.save}
      </button>
      <button className="secondary-link" onClick={onClose} type="button">
        {copy.cancel}
      </button>
      <output aria-live="polite">{message}</output>
    </form>
  );
}
