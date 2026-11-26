// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R005, R027
// Constitutional basis: C-001, C-023, C-059, C-063
// Test data only: an agent-neutral declaration with three modes, used by every operation component test.

import type { ItemView, LayerView, ModeDecl, ModeId, OperationFrame, PlatformView } from '@/lib/agent-operation';

export const relationshipId = 'rel-1';

export function item(overrides: Partial<ItemView> = {}): ItemView {
  return {
    itemId: 'i1',
    kind: 'EVENT',
    title: 'Harvest festival',
    state: 'SUGGESTED',
    authorState: 'AGENT_SUGGESTED',
    versionNo: 1,
    approvedVersionNo: 0,
    isApproved: false,
    isSuggestion: true,
    origin: 'AGENT',
    payload: {},
    updatedAt: '2026-12-01T00:00:00Z',
    startDate: '2026-12-10',
    layer: 'FESTIVAL',
    reason: 'Fits the business.',
    confidence: 0.8,
    sourceRef: 'https://example.org/source',
    ...overrides,
  };
}

export function respond(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

const entry = (entryId: string, label: string, target: string, order: number) => ({
  entryId,
  labelKey: `NAV_${entryId}`,
  label,
  icon: 'profile',
  order,
  surface: { kind: 'KERNEL_VIEW', target },
  availabilityGate: 'ALWAYS',
});

export function modes(): ModeDecl[] {
  return [
    {
      modeId: 'INDUCT',
      labelKey: 'MODE_INDUCT',
      label: 'Get to know me',
      readinessSource: 'INDUCTION_SUMMARY',
      entries: [entry('BUSINESS', 'Business', 'profile', 10), entry('PLATFORMS', 'Platforms', 'presence', 20)],
      toolGroups: [],
      gates: [],
    },
    {
      modeId: 'GOALS',
      labelKey: 'MODE_GOALS',
      label: 'Set goals',
      readinessSource: 'GOAL_COVERAGE',
      entries: [
        entry('GOALS_LIST', 'Goals by skill', 'goals', 10),
        entry('CAL', 'Calendar', 'calendar', 20),
        entry('PLAN', 'Plan', 'plan_tree', 30),
      ],
      toolGroups: [
        {
          groupId: 'ANCHORS',
          labelKey: 'TOOLS_ANCHORS',
          label: 'Anchors',
          tools: [
            { toolId: 'EVENT', labelKey: 'TOOL_EVENT', label: 'Event', icon: 'calendar', command: 'ADD_EVENT' },
            {
              toolId: 'PLACEHOLDER',
              labelKey: 'TOOL_PLACEHOLDER',
              label: 'Placeholder',
              icon: 'calendar',
              command: 'ADD_PLACEHOLDER',
            },
          ],
        },
        {
          groupId: 'PLAN',
          labelKey: 'TOOLS_PLAN',
          label: 'Plan',
          tools: [
            {
              toolId: 'THEME',
              labelKey: 'TOOL_THEME',
              label: 'Monthly theme',
              icon: 'plan',
              command: 'ADD_PLAN_NODE',
              planLevel: 'LEVEL_ONE',
            },
          ],
        },
        {
          groupId: 'CONTENT',
          labelKey: 'TOOLS_CONTENT',
          label: 'Content',
          tools: [
            {
              toolId: 'POST',
              labelKey: 'TOOL_POST',
              label: 'Post',
              icon: 'work',
              command: 'ADD_CONTENT',
              componentId: 'POSTS',
              flyout: [
                { optionId: 'IMAGE', labelKey: 'OPTION_IMAGE', label: 'Image' },
                { optionId: 'TEXT', labelKey: 'OPTION_TEXT', label: 'Text' },
              ],
            },
          ],
        },
      ],
      gates: [{ action: 'PUBLISH', requiresMode: 'GOALS', messageKey: 'GATE_SET_GOALS' }],
    },
    {
      modeId: 'OPERATIONS',
      labelKey: 'MODE_OPERATIONS',
      label: 'Run and improve',
      readinessSource: 'OPERATION_STATUS',
      entries: [
        entry('APPR', 'Approvals', 'approvals', 10),
        entry('PUB', 'Published', 'published', 20),
        entry('RES', 'Results', 'results', 30),
        entry('IMP', 'Improve', 'improve', 40),
      ],
      toolGroups: [],
      gates: [],
    },
  ];
}

export function layers(): LayerView[] {
  return [
    { layerId: 'FESTIVAL', labelKey: 'LAYER_FESTIVAL', label: 'Festivals', sensitive: false, on: true, custom: false },
    { layerId: 'SEASON', labelKey: 'LAYER_SEASON', label: 'Seasons', sensitive: false, on: false, custom: false },
    { layerId: 'RELIGION', labelKey: 'LAYER_RELIGION', label: 'Religion', sensitive: true, on: false, custom: false },
  ];
}

export function platforms(): PlatformView[] {
  return [
    {
      platformId: 'FACEBOOK',
      labelKey: 'P_FB',
      label: 'Facebook',
      connector: 'META_FACEBOOK',
      presence: 'PRESENT',
      canConnect: true,
      note: 'You can connect it.',
    },
    {
      platformId: 'INSTAGRAM',
      labelKey: 'P_IG',
      label: 'Instagram',
      connector: 'META_INSTAGRAM',
      presence: 'NOT_YET_CONNECTABLE',
      canConnect: false,
      note: 'Not yet.',
    },
    {
      platformId: 'WEBSITE',
      labelKey: 'P_WEB',
      label: 'Website',
      connector: 'NONE',
      presence: 'UNANSWERED',
      canConnect: false,
      note: '',
    },
  ];
}

export function frameFixture(overrides: Partial<OperationFrame> = {}): OperationFrame {
  const confirmStep = {
    modeId: 'INDUCT' as const,
    textKey: 'OP_NEXT_CONFIRM_PROFILE',
    text: 'Confirm what I understood about your business.',
    primaryLabel: 'Confirm profile',
    command: 'CONFIRM_LABELS',
  };
  const readiness = (
    modeId: ModeId,
    state: 'NOT_STARTED' | 'IN_PROGRESS' | 'READY',
    line: string,
    next: typeof confirmStep | null = null
  ) => ({
    modeId,
    state,
    done: 3,
    total: 17,
    line,
    next,
  });
  const decls = modes();
  return {
    schemaVersion: '1.0',
    modesDeclared: true,
    modes: [
      { mode: decls[0], readiness: readiness('INDUCT', 'IN_PROGRESS', '3 of 17 items confirmed', confirmStep) },
      { mode: decls[1], readiness: readiness('GOALS', 'NOT_STARTED', '0 of 5 goals set') },
      { mode: decls[2], readiness: readiness('OPERATIONS', 'NOT_STARTED', '0 to approve') },
    ],
    layers: layers(),
    planLevels: [
      { levelId: 'LEVEL_ONE', labelKey: 'L1', label: 'Monthly theme' },
      { levelId: 'LEVEL_TWO', labelKey: 'L2', label: 'Weekly theme' },
    ],
    platforms: platforms(),
    views: ['MONTH', 'WEEK', 'PLATFORMS', 'STORYBOARD'],
    lastMode: null,
    lastSurface: null,
    tourSeen: true,
    next: {
      modeId: 'INDUCT',
      textKey: 'OP_NEXT_CONFIRM_PROFILE',
      text: 'Confirm what I understood about your business.',
      primaryLabel: 'Confirm profile',
      command: 'CONFIRM_LABELS',
    },
    chats: { allowed: 1000, used: 10, remaining: 990, reached: false },
    publishAuthority: false,
    stopped: false,
    generatedAt: '2026-12-01T00:00:00Z',
    goalSkills: [
      { skillId: 'SKILL_ONE', state: 'NOT_SET' },
      { skillId: 'SKILL_TWO', state: 'NOT_SET' },
    ],
    approvalModes: ['CUSTOMER_APPROVAL', 'EXCEPTION_APPROVAL'],
    ...overrides,
  };
}

export type FetchCall = {
  method: string;
  path: string;
  body: Record<string, unknown> | null;
  headers: Record<string, string>;
};
type Reply = unknown | ((call: FetchCall) => unknown);

// Routes are "METHOD path-prefix" → a reply (a body, a Response, or a function of the call). The first match wins and
// an unmatched call is a 404, so a test never passes by accident.
export function installOperationFetch(routes: [string, Reply][]) {
  const calls: FetchCall[] = [];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const path = url.replace(/^.*?\/operation\//, '');
    const call: FetchCall = {
      method: init?.method ?? 'GET',
      path,
      body: init?.body ? JSON.parse(String(init.body)) : null,
      headers: (init?.headers ?? {}) as Record<string, string>,
    };
    calls.push(call);
    const match = routes.find(([key]) => `${call.method} ${path}`.startsWith(key));
    if (!match) return respond(404, { code: 'OPERATION_NOT_FOUND' });
    const reply = typeof match[1] === 'function' ? (match[1] as (value: FetchCall) => unknown)(call) : match[1];
    if (reply && typeof reply === 'object' && 'status' in reply && 'ok' in reply) return reply as Response;
    return respond(200, reply);
  }) as jest.Mock;
  return calls;
}

export function refused(status: number, code: string, detail: string, nextMode?: string) {
  return respond(status, { code, detail, nextMode });
}
