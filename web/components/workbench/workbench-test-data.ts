// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-059, C-063, ADR-051

import type { WorkbenchSnapshot } from '@/lib/api/workbench-types';

export const relationshipId = '0f5d4d3a-6f0c-4b6e-9f30-2d4f6a0c1b11';

export function fakeResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (name: string) => headers[name.toLowerCase()] ?? null },
    json: async () => body,
  } as unknown as Response;
}

const command = (commandId: string, enabled = true, disabledReason?: string) => ({
  commandId,
  label: commandId,
  enabled,
  ...(disabledReason ? { disabledReason } : {}),
});

export function snapshotFixture(overrides: Record<string, unknown> = {}): WorkbenchSnapshot {
  return {
    version: 'relationship-7',
    projection: {
      schemaVersion: '1.0',
      relationshipRef: relationshipId,
      audience: 'customer_owner',
      phase: 'OPERATIONS',
      readiness: { induction: 'READY', plan: 'AGREED', operations: 'ELIGIBLE', performance: 'ASSURED' },
      decisions: [
        {
          decisionId: 'decision-1',
          version: 'decision-version-3',
          effect: 'Publish the weekly update',
          authority: 'You',
          cost: 'One publishing credit',
          confirmLabel: 'Approve publish',
          cancelLabel: 'Decline publish',
          expiresAt: '2026-06-02T10:00:00Z',
          owner: 'customer',
          freshness: 'CURRENT',
        },
      ],
      tiles: [
        {
          tileId: 'tile-1',
          measureId: 'reach',
          label: 'Reach this week',
          value: '120',
          unit: 'people',
          target: '200',
          trend: 'UP',
          freshness: 'CURRENT',
          owner: 'agent',
          blockType: 'METRIC',
        },
      ],
      alerts: [
        {
          alertId: 'alert-1',
          signal: 'allowance_low',
          severity: 'WARNING',
          message: 'Your allowance is running low.',
          raisedAt: '2026-06-01T10:00:00Z',
          freshness: 'CURRENT',
        },
      ],
      evidenceState: 'AVAILABLE',
      sourceFreshness: 'CURRENT',
      limitations: ['Performance figures lag by one day.'],
      recommendedNextAction: {
        commandId: 'resolve_decision',
        label: 'Review a decision',
        reason: 'One decision is waiting.',
      },
      availableCommands: [
        command('create_goal'),
        command('propose_plan'),
        command('accept_plan'),
        command('resolve_decision'),
        command('change_capability'),
        command('top_up'),
        command('export_evidence'),
        command('pause'),
      ],
      blocks: [
        {
          id: 'goal-form-grow',
          type: 'FORM',
          version: 1,
          sensitivity: 'CUSTOMER',
          label: 'Grow reach',
          data: {
            formId: 'goal:grow',
            fields: [{ fieldId: 'audience', label: 'Audience', type: 'TEXT', required: true }],
          },
          fallback: [{ type: 'TEXT', data: { text: 'Open the workbench to set this goal.' } }],
        },
        {
          id: 'text-1',
          type: 'TEXT',
          version: 1,
          sensitivity: 'CUSTOMER',
          data: { text: 'Welcome back.' },
          fallback: [{ type: 'TEXT', data: { text: 'Welcome back.' } }],
        },
      ],
    },
    goals: { schemaVersion: '1.0', items: [] },
    plan: null,
    capabilities: {
      schemaVersion: '1.0',
      items: [
        {
          skillId: 'weekly-post',
          label: 'Weekly post',
          availability: 'AVAILABLE',
          state: 'NOT_ENABLED',
          approvalMode: 'ASK_FIRST',
          componentIds: ['posts'],
        },
        {
          skillId: 'reports',
          label: 'Reports',
          availability: 'UNAVAILABLE',
          state: 'NOT_ENABLED',
          approvalMode: 'ASK_FIRST',
          componentIds: [],
          limitation: 'Reports are not available on this package.',
        },
      ],
    },
    wallet: {
      schemaVersion: '1.0',
      relationshipRef: relationshipId,
      periodEnd: '2026-06-30T00:00:00Z',
      components: [
        { componentId: 'posts', label: 'Posts', remaining: 4, quantity: 10, periodEnd: '2026-06-30T00:00:00Z' },
      ],
      topUpAvailable: true,
      askAccountOwner: false,
    },
    evidence: {
      schemaVersion: '1.0',
      evidenceState: 'AVAILABLE',
      items: [
        {
          evidenceRef: 'ev-1',
          kind: 'WORK_PRODUCT',
          summary: 'Weekly post published',
          producedAt: '2026-05-30T10:00:00Z',
          freshness: 'CURRENT',
        },
      ],
    },
    workItems: {
      schemaVersion: '1.0',
      items: [
        {
          itemRef: 'wi-1',
          workItemType: 'TASK',
          label: 'Draft the weekly post',
          state: 'IN_PROGRESS',
          owner: 'agent',
          freshness: 'CURRENT',
          updatedAt: '2026-06-01T10:00:00Z',
        },
      ],
    },
    ...overrides,
  } as unknown as WorkbenchSnapshot;
}

export function present<T>(value: T | null | undefined): T {
  if (value === null || value === undefined) throw new Error('Expected the test fixture to hold a value.');
  return value;
}
