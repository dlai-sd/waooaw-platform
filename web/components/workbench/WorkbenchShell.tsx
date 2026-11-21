'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-023, C-042, C-059, C-063, ADR-051

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { OpenConversationCommand } from '@/components/conversation/OpenConversationCommand';
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
import { readWorkbench, sendWorkbenchCommand } from '@/lib/workbench-client';
import type { WorkbenchMessages } from '@/lib/workbench-i18n';
import { CapabilitiesPanel } from './CapabilitiesPanel';
import { ControlsBar } from './ControlsBar';
import { DecisionQueue } from './DecisionQueue';
import { EvidencePanel } from './EvidencePanel';
import { GoalPlanPanel } from './GoalPlanPanel';
import { MonitorPanel } from './MonitorPanel';
import { OverviewPanel } from './OverviewPanel';
import { WalletPanel } from './WalletPanel';
import type { WorkbenchPanelProps } from './useWorkbenchCommand';

type ToolId = 'overview' | 'goals' | 'capabilities' | 'decisions' | 'monitor' | 'wallet' | 'evidence';

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
}: {
  relationshipId: string;
  initial: WorkbenchSnapshot;
  copy: WorkbenchMessages;
  handoffToken?: string;
}) {
  const [snapshot, setSnapshot] = useState(initial);
  const [tool, setTool] = useState<ToolId>('overview');
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
      setTool(toolForPurpose(result.data.purpose, beneficiaryView));
    })();
  }, [handoffToken, relationshipId, beneficiaryView]);

  useEffect(() => {
    if (changedTool.current) panelRef.current?.focus();
  }, [tool]);

  const beneficiary = snapshot.projection.audience === 'beneficiary';
  const pending = snapshot.projection.decisions.length;
  const tools: Array<{ id: ToolId; label: string }> = [
    { id: 'overview', label: copy.toolOverview },
    { id: 'goals', label: copy.toolGoals },
    { id: 'capabilities', label: copy.toolCapabilities },
    { id: 'decisions', label: copy.toolDecisions },
    { id: 'monitor', label: copy.toolMonitor },
    ...(beneficiary ? [] : [{ id: 'wallet' as const, label: copy.toolWallet }]),
    { id: 'evidence', label: copy.toolEvidence },
  ];

  function choose(id: ToolId) {
    changedTool.current = true;
    setTool(id);
  }

  function moveWithArrows(event: KeyboardEvent<HTMLElement>) {
    const keys = ['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight'];
    if (!keys.includes(event.key)) return;
    const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('button'));
    const index = buttons.findIndex((button) => button === document.activeElement);
    if (index < 0) return;
    event.preventDefault();
    const step = event.key === 'ArrowDown' || event.key === 'ArrowRight' ? 1 : -1;
    buttons[(index + step + buttons.length) % buttons.length]?.focus();
  }

  const panel: WorkbenchPanelProps = { relationshipId, snapshot, copy, onChanged: refresh };

  return (
    <main className="workspace-shell workbench-shell">
      <header className="workspace-header">
        <h1>{copy.title}</h1>
        <div className="workbench-actions">
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
        <nav aria-label={copy.toolsLabel} className="workbench-rail" onKeyDown={moveWithArrows}>
          {tools.map((item) => (
            <button
              aria-current={tool === item.id ? 'page' : undefined}
              className={tool === item.id ? 'primary-command' : 'secondary-link'}
              key={item.id}
              onClick={() => choose(item.id)}
              type="button"
            >
              {item.label}
              {item.id === 'decisions' && pending > 0 ? <span> ({pending})</span> : null}
            </button>
          ))}
        </nav>
        <div aria-busy={refreshing} className="workbench-panel" ref={panelRef} tabIndex={-1}>
          {tool === 'overview' ? <OverviewPanel {...panel} /> : null}
          {tool === 'goals' ? <GoalPlanPanel {...panel} /> : null}
          {tool === 'capabilities' ? <CapabilitiesPanel {...panel} /> : null}
          {tool === 'decisions' ? <DecisionQueue {...panel} /> : null}
          {tool === 'monitor' ? <MonitorPanel {...panel} /> : null}
          {tool === 'wallet' && !beneficiary ? <WalletPanel {...panel} /> : null}
          {tool === 'evidence' ? <EvidencePanel {...panel} /> : null}
        </div>
      </div>
    </main>
  );
}
