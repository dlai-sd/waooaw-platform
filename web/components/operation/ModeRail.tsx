'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R003, R027
// Constitutional basis: C-001, C-042, C-059, C-063

import { useState } from 'react';
import {
  labelFor,
  type FlyoutOption,
  type ModeDecl,
  type ModeId,
  type ModeReadiness,
  type NavEntry,
  type ToolDecl,
} from '@/lib/agent-operation';
import type { OperationMessages } from '@/lib/operation-i18n';

type Props = {
  modes: { mode: ModeDecl; readiness: ModeReadiness }[];
  activeMode: ModeId;
  activeSurface: string;
  labels: Record<string, string>;
  copy: OperationMessages;
  workbenchHref: string;
  onMode: (mode: ModeId) => void;
  onSurface: (entry: NavEntry) => void;
  onTool: (tool: ToolDecl, option?: FlyoutOption) => void;
};

const icons: Record<ModeId, string> = { INDUCT: '◐', GOALS: '◎', OPERATIONS: '▶' };

export function surfaceIdOf(entry: NavEntry): string {
  return entry.surface.kind === 'KERNEL_VIEW' ? `kernel:${entry.surface.target}` : `block:${entry.entryId}`;
}

// Two levels beside the workspace, like a code editor's side bar: a narrow rail of the three modes, then the chosen
// mode's menus and tools in the order a person builds. Both fold away; the WAOOAW menu stays in the header.
export function ModeRail({
  modes,
  activeMode,
  activeSurface,
  labels,
  copy,
  workbenchHref,
  onMode,
  onSurface,
  onTool,
}: Props) {
  const [railOpen, setRailOpen] = useState(true);
  const [panelOpen, setPanelOpen] = useState(true);
  const [flyout, setFlyout] = useState<string | null>(null);
  const active = modes.find((item) => item.mode.modeId === activeMode) ?? modes[0];

  return (
    <div className="op-rail-wrap">
      {railOpen ? (
        <nav aria-label={copy.modesLabel} className="op-icon-rail">
          {modes.map(({ mode, readiness }) => (
            <button
              aria-current={mode.modeId === activeMode ? 'true' : undefined}
              className={mode.modeId === activeMode ? 'primary-command' : 'secondary-link'}
              key={mode.modeId}
              onClick={() => onMode(mode.modeId)}
              title={readiness.line}
              type="button"
            >
              <span aria-hidden="true">{icons[mode.modeId]}</span> {labelFor(labels, mode.labelKey, mode.label)}
            </button>
          ))}
        </nav>
      ) : null}
      <button
        aria-expanded={railOpen}
        className="secondary-link op-fold"
        onClick={() => setRailOpen(!railOpen)}
        type="button"
      >
        {railOpen ? copy.collapseRail : copy.expandRail}
      </button>
      {panelOpen && active ? (
        <aside aria-label={copy.modePanelLabel} className="op-mode-panel">
          <h2>{labelFor(labels, active.mode.labelKey, active.mode.label)}</h2>
          <p className="op-readiness">{active.readiness.line}</p>
          <nav aria-label={labelFor(labels, active.mode.labelKey, active.mode.label)}>
            {[...active.mode.entries]
              .sort((left, right) => left.order - right.order || left.entryId.localeCompare(right.entryId))
              .map((entry) => (
                <button
                  aria-current={surfaceIdOf(entry) === activeSurface ? 'page' : undefined}
                  className={surfaceIdOf(entry) === activeSurface ? 'primary-command' : 'secondary-link'}
                  key={entry.entryId}
                  onClick={() => onSurface(entry)}
                  type="button"
                >
                  {labelFor(labels, entry.labelKey, entry.label)}
                </button>
              ))}
          </nav>
          {active.mode.toolGroups.map((group) => (
            <section
              aria-label={labelFor(labels, group.labelKey, group.label)}
              className="op-tool-group"
              key={group.groupId}
            >
              <h3 className="section-label">{labelFor(labels, group.labelKey, group.label)}</h3>
              {group.tools.map((tool) => (
                <div key={tool.toolId}>
                  <button
                    aria-expanded={tool.flyout?.length ? flyout === tool.toolId : undefined}
                    className="secondary-link"
                    onClick={() =>
                      tool.flyout?.length ? setFlyout(flyout === tool.toolId ? null : tool.toolId) : onTool(tool)
                    }
                    type="button"
                  >
                    {labelFor(labels, tool.labelKey, tool.label)}
                  </button>
                  {tool.flyout?.length && flyout === tool.toolId ? (
                    // biome-ignore lint/a11y/useSemanticElements: a flyout list of options is not a form field set
                    <div aria-label={labelFor(labels, tool.labelKey, tool.label)} className="op-flyout" role="group">
                      {tool.flyout.map((option) => (
                        <button
                          className="secondary-link"
                          key={option.optionId}
                          onClick={() => {
                            setFlyout(null);
                            onTool(tool, option);
                          }}
                          type="button"
                        >
                          {labelFor(labels, option.labelKey, option.label)}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </section>
          ))}
          {active.mode.modeId === 'OPERATIONS' ? (
            <a className="secondary-link" href={workbenchHref}>
              {copy.workbenchEntry}
            </a>
          ) : null}
        </aside>
      ) : null}
      <button
        aria-expanded={panelOpen}
        className="secondary-link op-fold"
        onClick={() => setPanelOpen(!panelOpen)}
        type="button"
      >
        {panelOpen ? copy.collapsePanel : copy.expandPanel}
      </button>
    </div>
  );
}
