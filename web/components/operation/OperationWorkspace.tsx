'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R003, R005, R027, R028, R029, R030, R031
// Constitutional basis: C-001, C-023, C-042, C-059, C-063

import { useCallback, useEffect, useState } from 'react';
import {
  labelFor,
  monthRange,
  operationApi,
  problemText,
  shiftMonth,
  type CalendarView,
  type FlyoutOption,
  type ItemView,
  type ModeId,
  type NavEntry,
  type NextStep,
  type OperationFrame,
  type ToolDecl,
} from '@/lib/agent-operation';
import { declaredSurfaceId } from '@/lib/navigation-model';
import type { OperationMessages } from '@/lib/operation-i18n';
import { CalendarBlock, type CalendarViewName } from './CalendarBlock';
import { ConversationDock } from './ConversationDock';
import { GoalsView } from './GoalsView';
import { PlatformsView, ProfileView } from './InductViews';
import { ModeRail, surfaceIdOf } from './ModeRail';
import { ApprovalsView, ImproveView, PublishedView, ResultsView } from './OperationsViews';
import { PlanTreeBlock } from './PlanTreeBlock';
import { ToolForm } from './ToolForm';

type Props = {
  relationshipId: string;
  initialFrame: OperationFrame;
  copy: OperationMessages;
  labels?: Record<string, string>;
  today: string;
  initialMode?: ModeId | null;
  initialSurface?: string | null;
  workbenchHref: string;
};

const viewNames: Record<string, keyof OperationMessages> = {
  MONTH: 'viewMonth',
  WEEK: 'viewWeek',
  PLATFORMS: 'viewPlatforms',
  STORYBOARD: 'viewStoryboard',
};

// Where each next step takes the customer. The step is the same one the conversation names.
const stepTargets: Record<string, { mode: ModeId; surface: string }> = {
  CONFIRM_LABELS: { mode: 'INDUCT', surface: 'kernel:profile' },
  ANSWER_PLATFORM: { mode: 'INDUCT', surface: 'kernel:presence' },
  SET_GOAL: { mode: 'GOALS', surface: 'kernel:goals' },
  CONFIRM_GOAL: { mode: 'GOALS', surface: 'kernel:goals' },
  OPEN_PLAN: { mode: 'GOALS', surface: 'kernel:plan_tree' },
  OPEN_APPROVALS: { mode: 'OPERATIONS', surface: 'kernel:approvals' },
  OPEN_SCHEDULE: { mode: 'OPERATIONS', surface: 'kernel:approvals' },
  OPEN_PUBLISHED: { mode: 'OPERATIONS', surface: 'kernel:published' },
  OPEN_RESULTS: { mode: 'OPERATIONS', surface: 'kernel:results' },
};

// The relationship's home: a calendar with a mode menu beside it and the agent's guidance always in view. The agent
// declares its modes, menus, tools, layers and plan levels as data; nothing here knows which agent it is.
export function OperationWorkspace({
  relationshipId,
  initialFrame,
  copy,
  labels = {},
  today,
  initialMode,
  initialSurface,
  workbenchHref,
}: Props) {
  const [frame, setFrame] = useState(initialFrame);
  const [mode, setMode] = useState<ModeId>(
    initialMode ??
      frame.lastMode ??
      frame.modes.find((item) => item.readiness.state !== 'READY')?.mode.modeId ??
      'OPERATIONS'
  );
  const [surface, setSurface] = useState(initialSurface ?? frame.lastSurface ?? 'kernel:calendar');
  const [view, setView] = useState<CalendarViewName>((frame.views[0] as CalendarViewName | undefined) ?? 'MONTH');
  const [cursor, setCursor] = useState({ year: Number(today.slice(0, 4)), month: Number(today.slice(5, 7)) });
  const [selected, setSelected] = useState<ItemView | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [tool, setTool] = useState<{ tool: ToolDecl; option?: FlyoutOption } | null>(null);
  const [limits, setLimits] = useState<CalendarView['limits']>([]);
  const [redoId, setRedoId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [tourOpen, setTourOpen] = useState(!initialFrame.tourSeen);

  const reload = useCallback(async () => {
    const result = await operationApi.frame(relationshipId);
    if (result.ok) setFrame(result.data);
  }, [relationshipId]);

  const changed = useCallback(() => {
    setRefreshKey((key) => key + 1);
    void reload();
  }, [reload]);

  // The conversation is docked in every mode: open the shell's dock once, then leave the customer's choice alone.
  useEffect(() => {
    if (window.sessionStorage.getItem(`waooaw:op-dock:${relationshipId}`)) return;
    window.sessionStorage.setItem(`waooaw:op-dock:${relationshipId}`, '1');
    window.dispatchEvent(new CustomEvent('waooaw:open-conversation'));
  }, [relationshipId]);

  const onLoaded = useCallback((calendar: CalendarView) => setLimits(calendar.limits), []);

  const active = frame.modes.find((item) => item.mode.modeId === mode) ?? frame.modes[0];
  const next = active.readiness.next ?? null;

  function go(target: ModeId, nextSurface: string) {
    setMode(target);
    setSurface(nextSurface);
    setTool(null);
    void operationApi.setMode(relationshipId, target, nextSurface);
  }

  function act(step: NextStep) {
    if (step.command === 'OPEN_CONVERSATION') {
      window.dispatchEvent(new CustomEvent('waooaw:open-conversation'));
      return;
    }
    const target = stepTargets[step.command];
    if (target) go(target.mode, target.surface);
  }

  function chooseEntry(entry: NavEntry) {
    setTool(null);
    setSurface(surfaceIdOf(entry));
    void operationApi.setMode(relationshipId, mode, surfaceIdOf(entry));
  }

  async function undo(id: string, rememberRedo: boolean) {
    const result = await operationApi.act(relationshipId, id, 'undo');
    if (result.ok) {
      setSelected(result.data);
      setRedoId(rememberRedo ? id : null);
      setNotice('');
      changed();
    } else {
      setNotice(problemText(result.problem));
    }
  }

  async function dismissTour() {
    setTourOpen(false);
    await operationApi.tourSeen(relationshipId);
  }

  const range = monthRange(cursor.year, cursor.month);
  const monthTitle = new Date(`${range.from}T00:00:00Z`).toLocaleDateString('en', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
  const firstLimit = limits[0];
  const blockEntry = surface.startsWith('block:')
    ? frame.modes.flatMap((item) => item.mode.entries).find((entry) => `block:${entry.entryId}` === surface)
    : undefined;
  const common = { relationshipId, copy, onChanged: changed, refreshKey };

  function renderSurface() {
    switch (surface) {
      case 'kernel:plan_tree':
        return (
          <PlanTreeBlock copy={copy} onChanged={changed} refreshKey={refreshKey} relationshipId={relationshipId} />
        );
      case 'kernel:profile':
        return <ProfileView {...common} />;
      case 'kernel:presence':
      case 'kernel:connections':
        return (
          <PlatformsView copy={copy} onChanged={changed} platforms={frame.platforms} relationshipId={relationshipId} />
        );
      case 'kernel:goals':
        return (
          <GoalsView
            approvalModes={frame.approvalModes}
            copy={copy}
            labels={labels}
            onChanged={changed}
            relationshipId={relationshipId}
            skills={frame.goalSkills}
          />
        );
      case 'kernel:approvals':
        return (
          <ApprovalsView {...common} onGoMode={(target) => go(target, 'kernel:calendar')} platforms={frame.platforms} />
        );
      case 'kernel:published':
        return (
          <PublishedView
            {...common}
            onGoMode={(target) => go(target, 'kernel:calendar')}
            publishAuthority={frame.publishAuthority}
          />
        );
      case 'kernel:results':
        return <ResultsView copy={copy} labels={labels} refreshKey={refreshKey} relationshipId={relationshipId} />;
      case 'kernel:improve':
        return <ImproveView {...common} />;
      default:
        return blockEntry ? (
          <p>
            <a
              className="secondary-link"
              href={`${workbenchHref.split('?')[0]}?surface=${declaredSurfaceId(blockEntry.entryId)}`}
            >
              {copy.workbenchEntry}: {labelFor(labels, blockEntry.labelKey, blockEntry.label)}
            </a>
          </p>
        ) : (
          <CalendarBlock
            copy={copy}
            month={cursor.month}
            onChanged={changed}
            onLoaded={onLoaded}
            onSelect={setSelected}
            platforms={frame.platforms}
            refreshKey={refreshKey}
            relationshipId={relationshipId}
            selectedId={selected?.itemId ?? null}
            today={today}
            view={view}
            year={cursor.year}
          />
        );
    }
  }

  return (
    <main className="op-shell">
      <header className="op-topbar">
        <div className="op-top-left">
          <h1>{copy.title}</h1>
          <button
            className="secondary-link"
            disabled={!selected || selected.versionNo < 2}
            onClick={() => selected && void undo(selected.itemId, true)}
            type="button"
          >
            ↶ {copy.undo}
          </button>
          <button
            className="secondary-link"
            disabled={redoId === null}
            onClick={() => redoId && void undo(redoId, false)}
            type="button"
          >
            ↷ {copy.redo}
          </button>
          <button
            aria-label={copy.previousMonth}
            className="secondary-link"
            onClick={() => setCursor(shiftMonth(cursor.year, cursor.month, -1))}
            type="button"
          >
            ‹
          </button>
          <strong aria-live="polite">{monthTitle}</strong>
          <button
            aria-label={copy.nextMonth}
            className="secondary-link"
            onClick={() => setCursor(shiftMonth(cursor.year, cursor.month, 1))}
            type="button"
          >
            ›
          </button>
          <button
            className="secondary-link"
            onClick={() => {
              setCursor({ year: Number(today.slice(0, 4)), month: Number(today.slice(5, 7)) });
              setSurface('kernel:calendar');
            }}
            type="button"
          >
            {copy.today}
          </button>
        </div>
        <div className="op-top-right">
          {firstLimit ? (
            <span className="op-meter">
              {firstLimit.label}: {firstLimit.known ? `${firstLimit.remaining} ${copy.limitLeft}` : copy.limitUnknown}
            </span>
          ) : null}
          <button className="secondary-link" onClick={() => setTourOpen(true)} type="button">
            ? {copy.help}
          </button>
        </div>
      </header>
      {/* biome-ignore lint/a11y/useSemanticElements: a fieldset here would add a border and legend semantics to a row of view chips */}
      <div aria-label={copy.viewsLabel} className="op-views" role="group">
        {frame.views.map((name) => (
          <button
            aria-pressed={view === name}
            className={view === name ? 'primary-command' : 'secondary-link'}
            key={name}
            onClick={() => {
              setView(name as CalendarViewName);
              setSurface('kernel:calendar');
            }}
            type="button"
          >
            {copy[viewNames[name] ?? 'viewMonth']}
          </button>
        ))}
        <span className="op-sync">✓ {copy.syncPill}</span>
        <output className="op-readiness-line">
          <span className="section-label">{copy.readiness}:</span> {active.readiness.line}
          {next ? (
            <button className="primary-command" onClick={() => act(next)} type="button">
              {next.primaryLabel}
            </button>
          ) : null}
        </output>
      </div>
      {tourOpen ? (
        // biome-ignore lint/a11y/useSemanticElements: a modal <dialog> needs showModal and would take focus away from the conversation dock; this is a non-modal tour panel
        <section aria-label={copy.tourTitle} className="op-tour" role="dialog">
          <h2>{copy.tourTitle}</h2>
          <p>{copy.tourBody}</p>
          <button className="primary-command" onClick={() => void dismissTour()} type="button">
            {copy.tourDone}
          </button>
        </section>
      ) : null}
      <div className="op-body">
        <ModeRail
          activeMode={mode}
          activeSurface={surface}
          copy={copy}
          labels={labels}
          modes={frame.modes}
          onMode={(target) => go(target, 'kernel:calendar')}
          onSurface={chooseEntry}
          onTool={(chosen, option) => {
            setSurface('kernel:calendar');
            setTool({ tool: chosen, option });
          }}
          workbenchHref={workbenchHref}
        />
        <div className="op-main">
          <output aria-live="polite">{notice}</output>
          {frame.stopped ? <p role="alert">{copy.stoppedBanner}</p> : null}
          {tool ? (
            <ToolForm
              copy={copy}
              layers={frame.layers}
              onClose={() => setTool(null)}
              onCreated={(item) => {
                setTool(null);
                setSelected(item);
                changed();
              }}
              onSchedule={() => go('OPERATIONS', 'kernel:approvals')}
              option={tool.option}
              planLevels={frame.planLevels}
              platforms={frame.platforms}
              relationshipId={relationshipId}
              today={today}
              tool={tool.tool}
            />
          ) : null}
          {renderSurface()}
        </div>
        <ConversationDock
          chats={frame.chats}
          copy={copy}
          next={next}
          onAct={act}
          onChats={(chats) => setFrame((current) => ({ ...current, chats }))}
          readinessLine={active.readiness.line}
          relationshipId={relationshipId}
          stopped={frame.stopped}
        />
      </div>
      <footer className="op-status">
        <span>{selected ? selected.title : copy.statusNothingSelected}</span>
        {selected ? (
          <span>
            {copy.statusLastEdited}: {selected.updatedAt.slice(0, 10)}
          </span>
        ) : null}
        {firstLimit ? (
          <span>
            {firstLimit.label}: {firstLimit.committed}
          </span>
        ) : null}
        <span>{copy.statusSynced}</span>
        <button className="secondary-link" onClick={() => setTourOpen(true)} type="button">
          {copy.tourReplay}
        </button>
      </footer>
    </main>
  );
}
