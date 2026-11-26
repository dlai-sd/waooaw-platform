'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-023, C-042, C-059, C-063, ADR-051

import { useCallback, useEffect, useRef, useState } from 'react';
import { OpenConversationCommand } from '@/components/conversation/OpenConversationCommand';
import { AlertInbox } from '@/components/portal/AlertInbox';
import type {
  WorkbenchCapabilityList,
  WorkbenchEvidenceList,
  WorkbenchGoalList,
  WorkbenchHandoffConsumption,
  WorkbenchPlan,
  WorkbenchProjection,
  WorkbenchSnapshot,
  WorkbenchWallet,
  WorkbenchWorkItemList,
} from '@/lib/api/workbench-types';
import {
  contextSurfaces,
  declaredSurfaceId,
  LEGACY_TOOL_SURFACE,
  resolveSurface,
  type DeclaredEntry,
} from '@/lib/navigation-model';
import { readWorkbench, sendWorkbenchCommand } from '@/lib/workbench-client';
import type { WorkbenchMessages } from '@/lib/workbench-i18n';
import { AgentContextMenu, type ContextMenuItem } from './AgentContextMenu';
import { CapabilitiesPanel } from './CapabilitiesPanel';
import { ControlsBar } from './ControlsBar';
import { DeclaredSurface } from './DeclaredSurface';
import { DecisionQueue } from './DecisionQueue';
import { EvidencePanel } from './EvidencePanel';
import { GoalPlanPanel } from './GoalPlanPanel';
import { MonitorPanel } from './MonitorPanel';
import { OverviewPanel } from './OverviewPanel';
import { RealWorkPanel } from './RealWorkPanel';
import { WalletPanel } from './WalletPanel';
import type { WorkbenchPanelProps } from './useWorkbenchCommand';

type ToolId = 'overview' | 'goals' | 'capabilities' | 'decisions' | 'monitor' | 'work' | 'wallet' | 'evidence';

// The tool a redeemed handoff opens; the allowance is never opened for a beneficiary, who has no such tool.
export function toolForPurpose(purpose: string, beneficiary: boolean): ToolId {
  if (purpose === 'APPROVAL') return 'decisions';
  if (purpose === 'EVIDENCE') return 'evidence';
  if (purpose === 'PAYMENT' && !beneficiary) return 'wallet';
  return 'overview';
}

async function optional<T>(relationshipId: string, path: string): Promise<T | null> {
  const result = await readWorkbench<T>(relationshipId, path);
  return result.ok ? result.data : null;
}

export async function reloadSnapshot(
  relationshipId: string,
  current: WorkbenchSnapshot
): Promise<WorkbenchSnapshot | null> {
  const projection = await readWorkbench<WorkbenchProjection>(relationshipId);
  if (!projection.ok || projection.version === null) return null;
  const beneficiary = projection.data.audience === 'beneficiary';
  const [goals, plan, capabilities, wallet, evidence, workItems] = await Promise.all([
    optional<WorkbenchGoalList>(relationshipId, '/goals'),
    optional<WorkbenchPlan>(relationshipId, '/plans/current'),
    optional<WorkbenchCapabilityList>(relationshipId, '/capabilities'),
    beneficiary ? Promise.resolve(null) : optional<WorkbenchWallet>(relationshipId, '/wallet'),
    optional<WorkbenchEvidenceList>(relationshipId, '/evidence'),
    optional<WorkbenchWorkItemList>(relationshipId, '/work-items'),
  ]);
  return {
    projection: projection.data,
    version: projection.version,
    goals: goals ?? current.goals,
    plan: plan ?? current.plan,
    capabilities: capabilities ?? current.capabilities,
    wallet: beneficiary ? null : (wallet ?? current.wallet),
    evidence: evidence ?? current.evidence,
    workItems: workItems ?? current.workItems,
  };
}

export function WorkbenchShell({
  relationshipId,
  initial,
  copy,
  handoffToken,
  initialSurface,
  operationHref,
}: {
  relationshipId: string;
  initial: WorkbenchSnapshot;
  copy: WorkbenchMessages;
  handoffToken?: string;
  initialSurface?: string | null;
  operationHref?: string;
}) {
  const [snapshot, setSnapshot] = useState(initial);
  const [surface, setSurface] = useState<string>(() => resolveSurface(initialSurface, initial.projection.navigation));
  const [refreshing, setRefreshing] = useState(false);
  const [refreshFailed, setRefreshFailed] = useState(false);
  const [handoffFailed, setHandoffFailed] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const changedTool = useRef(false);
  const handoffRedeemed = useRef(false);
  const snapshotRef = useRef(snapshot);
  snapshotRef.current = snapshot;
  const beneficiaryView = initial.projection.audience === 'beneficiary';

  const refresh = useCallback(async () => {
    setRefreshing(true);
    const next = await reloadSnapshot(relationshipId, snapshotRef.current);
    if (next === null) {
      setRefreshFailed(true);
    } else {
      setRefreshFailed(false);
      setSnapshot(next);
    }
    setRefreshing(false);
  }, [relationshipId]);

  // A handoff link is single use: it is redeemed once, then removed from the address so a reload cannot replay it.
  useEffect(() => {
    if (!handoffToken || handoffRedeemed.current) return;
    handoffRedeemed.current = true;
    void (async () => {
      const result = await sendWorkbenchCommand<WorkbenchHandoffConsumption>(relationshipId, '/handoffs/consume', {
        schemaVersion: '1.0',
        destinationRef: handoffToken,
      });
      window.history.replaceState(null, '', window.location.pathname);
      if (!result.ok) {
        setHandoffFailed(true);
        return;
      }
      changedTool.current = true;
      setSurface(LEGACY_TOOL_SURFACE[toolForPurpose(result.data.purpose, beneficiaryView)]);
    })();
  }, [handoffToken, relationshipId, beneficiaryView]);

  useEffect(() => {
    if (changedTool.current) panelRef.current?.focus();
  }, [surface]);

  const beneficiary = snapshot.projection.audience === 'beneficiary';
  const pending = snapshot.projection.decisions.length;
  const declared: DeclaredEntry[] = snapshot.projection.navigation ?? [];
  const fixedLabels: Record<string, string> = {
    overview: copy.toolOverview,
    plan: copy.toolPlan,
    decisions: copy.toolDecisions,
    work: copy.toolWork,
    results: copy.surfaceResults,
    usage: copy.surfaceUsage,
    alerts: copy.surfaceAlerts,
    rights: copy.surfaceRights,
  };
  const surfaces = contextSurfaces(declared);
  const fixedItems: ContextMenuItem[] = surfaces
    .filter((item) => item.kind === 'fixed')
    // The allowance belongs to the owner; a beneficiary has no budget surface.
    .filter((item) => !(beneficiary && item.id === 'usage'))
    .map((item) => ({
      id: item.id,
      label: fixedLabels[item.id] ?? item.id,
      badge: item.id === 'decisions' ? pending : undefined,
    }));
  const declaredItems: ContextMenuItem[] = [...declared]
    .sort((left, right) => left.order - right.order || left.entryId.localeCompare(right.entryId))
    .map((entry) => ({ id: declaredSurfaceId(entry.entryId), label: entry.label, unavailable: !entry.available }));
  const declaredEntry = declared.find((entry) => declaredSurfaceId(entry.entryId) === surface);

  function choose(id: string) {
    changedTool.current = true;
    setSurface(id);
    // A deep link names the surface, so a reload or a shared link opens the same one.
    window.history.replaceState(null, '', `${window.location.pathname}?surface=${encodeURIComponent(id)}`);
  }

  const panel: WorkbenchPanelProps = { relationshipId, snapshot, copy, onChanged: refresh };

  return (
    <main className="workspace-shell workbench-shell">
      <header className="workspace-header">
        <h1>{copy.title}</h1>
        <div className="workbench-actions">
          {operationHref ? (
            <a className="secondary-link" href={operationHref}>
              Back to your calendar
            </a>
          ) : null}
          <OpenConversationCommand label={copy.talk} />
          <button className="secondary-link" disabled={refreshing} onClick={refresh} type="button">
            {refreshing ? copy.refreshing : copy.refresh}
          </button>
        </div>
      </header>
      <output aria-live="polite">
        {refreshFailed ? copy.refreshFailed : ''}
        {handoffFailed ? copy.handoffInvalid : ''}
      </output>
      <ControlsBar {...panel} />
      <div className="workbench-layout">
        <AgentContextMenu
          current={surface}
          declared={declaredItems}
          declaredLabel={copy.declaredMenuLabel}
          fixed={fixedItems}
          label={copy.agentMenuLabel}
          onChoose={choose}
        />
        <div aria-busy={refreshing} className="workbench-panel" ref={panelRef} tabIndex={-1}>
          {surface === 'overview' ? <OverviewPanel {...panel} /> : null}
          {surface === 'plan' ? <GoalPlanPanel {...panel} /> : null}
          {surface === 'decisions' ? <DecisionQueue {...panel} /> : null}
          {surface === 'work' ? <RealWorkPanel relationshipId={relationshipId} /> : null}
          {surface === 'results' ? <MonitorPanel {...panel} /> : null}
          {surface === 'usage' ? (
            <>
              <CapabilitiesPanel {...panel} />
              {beneficiary ? null : <WalletPanel {...panel} />}
            </>
          ) : null}
          {surface === 'alerts' ? <AlertInbox locale="en" relationshipId={relationshipId} /> : null}
          {surface === 'rights' ? <EvidencePanel {...panel} /> : null}
          {declaredEntry ? (
            <DeclaredSurface
              blocks={snapshot.projection.blocks}
              copy={copy}
              entry={declaredEntry}
              onOpenWork={() => choose('work')}
            />
          ) : null}
        </div>
      </div>
    </main>
  );
}
