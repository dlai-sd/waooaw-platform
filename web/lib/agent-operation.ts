'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R005, R007, R013, R030, R031
// Constitutional basis: C-001, C-023, C-042, C-059, C-063

export type ModeId = 'INDUCT' | 'GOALS' | 'OPERATIONS';
export type OperationRoute = 'ASKED' | 'ACCEPTED' | 'TOOL';

export type NavEntry = {
  entryId: string;
  labelKey: string;
  label: string;
  icon: string;
  order: number;
  surface: { kind: string; target?: string | null; blocks?: string[] };
  availabilityGate: string;
};
export type FlyoutOption = { optionId: string; labelKey: string; label: string };
export type ToolDecl = {
  toolId: string;
  labelKey: string;
  label: string;
  icon: string;
  command: 'ADD_EVENT' | 'ADD_PLACEHOLDER' | 'ADD_PLAN_NODE' | 'ADD_CONTENT' | 'ADD_SLOT' | 'ADD_NOTE';
  planLevel?: string | null;
  componentId?: string | null;
  flyout?: FlyoutOption[];
};
export type ToolGroupDecl = { groupId: string; labelKey: string; label: string; tools: ToolDecl[] };
export type ModeDecl = {
  modeId: ModeId;
  labelKey: string;
  label: string;
  readinessSource: string;
  entries: NavEntry[];
  toolGroups: ToolGroupDecl[];
  gates: { action: string; requiresMode: ModeId; messageKey: string }[];
};
export type NextStep = {
  modeId: ModeId;
  textKey: string;
  text: string;
  primaryLabel: string;
  command: string;
  target?: string | null;
};
export type ModeReadiness = {
  modeId: ModeId;
  state: 'NOT_STARTED' | 'IN_PROGRESS' | 'READY';
  done: number;
  total: number;
  line: string;
  next?: NextStep | null;
};
export type LayerView = {
  layerId: string;
  labelKey: string;
  label: string;
  sensitive: boolean;
  on: boolean;
  custom: boolean;
};
export type PlatformView = {
  platformId: string;
  labelKey: string;
  label: string;
  connector: string;
  presence: string;
  canConnect: boolean;
  connectionId?: string | null;
  accountName?: string | null;
  note: string;
};
export type ChatAllowance = { allowed: number; used: number; remaining: number; reached: boolean };
export type GoalSkill = {
  skillId: string;
  state: 'NOT_SET' | 'PROPOSED' | 'PENDING_CONFIRMATION' | 'CONFIRMED' | 'REJECTED';
  goal?: ItemView | null;
};
export type OperationFrame = {
  schemaVersion: string;
  modesDeclared: boolean;
  modes: { mode: ModeDecl; readiness: ModeReadiness }[];
  layers: LayerView[];
  planLevels: { levelId: string; labelKey: string; label: string }[];
  platforms: PlatformView[];
  views: string[];
  lastMode?: ModeId | null;
  lastSurface?: string | null;
  tourSeen: boolean;
  next?: NextStep | null;
  chats: ChatAllowance;
  publishAuthority: boolean;
  stopped: boolean;
  generatedAt: string;
  goalSkills: GoalSkill[];
  approvalModes: string[];
};
export type ItemView = {
  itemId: string;
  kind: string;
  layer?: string | null;
  levelId?: string | null;
  parentId?: string | null;
  title: string;
  body?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  state: string;
  authorState: 'AGENT_SUGGESTED' | 'CUSTOMER_EDITED' | 'CUSTOMER_OWNED' | 'APPROVED_VERSION';
  versionNo: number;
  approvedVersionNo: number;
  isApproved: boolean;
  isSuggestion: boolean;
  origin: string;
  sourceRef?: string | null;
  reason?: string | null;
  confidence?: number | null;
  platformId?: string | null;
  componentId?: string | null;
  payload: Record<string, unknown>;
  updatedAt: string;
};
export type LimitView = {
  componentId: string;
  label: string;
  remaining?: number | null;
  committed: number;
  known: boolean;
};
export type CalendarView = {
  from: string;
  to: string;
  entries: ItemView[];
  layers: LayerView[];
  limits: LimitView[];
  evidenceState: string;
  sourceFreshness?: string | null;
};
export type PlanTreeView = { levels: { levelId: string; labelKey: string; label: string }[]; nodes: ItemView[] };
export type OperationContext = {
  mode?: string | null;
  view?: string | null;
  selected?: ItemView | null;
  gap?: NextStep | null;
  chats: ChatAllowance;
  limits: LimitView[];
  pendingSuggestions: number;
  customerOwned: number;
};

export type OperationProblem = { code: string; detail?: string; nextMode?: ModeId | null };
export type OperationResult<T> = { ok: true; data: T } | { ok: false; status: number; problem: OperationProblem };

async function call<T>(
  relationshipId: string,
  method: 'GET' | 'POST' | 'PUT' | 'PATCH',
  path: string,
  body?: unknown
): Promise<OperationResult<T>> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (method !== 'GET') {
    headers['Content-Type'] = 'application/json';
    // Every action gets its own key, so a double click replays instead of repeating.
    headers['Idempotency-Key'] = crypto.randomUUID();
  }
  let response: Response;
  try {
    response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/operation/${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      cache: 'no-store',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    return { ok: false, status: 0, problem: { code: 'OPERATION_UNAVAILABLE' } };
  }
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (response.ok) return { ok: true, data: payload as T };
  const source = payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {};
  return {
    ok: false,
    status: response.status,
    problem: {
      code: typeof source.code === 'string' ? source.code : 'OPERATION_UNAVAILABLE',
      detail: typeof source.detail === 'string' ? source.detail : undefined,
      nextMode: (source.nextMode as ModeId | null | undefined) ?? null,
    },
  };
}

const id = encodeURIComponent;

export const operationApi = {
  frame: (relationshipId: string, mode?: ModeId) =>
    call<OperationFrame>(relationshipId, 'GET', `frame${mode ? `?mode=${mode}` : ''}`),
  calendar: (relationshipId: string, from: string, to: string) =>
    call<CalendarView>(relationshipId, 'GET', `calendar?from=${from}&to=${to}`),
  planTree: (relationshipId: string) => call<PlanTreeView>(relationshipId, 'GET', 'plan-tree'),
  items: (relationshipId: string, kind: string) => call<ItemView[]>(relationshipId, 'GET', `items?kind=${id(kind)}`),
  context: (relationshipId: string, query: { mode?: string; view?: string; selected?: string }) => {
    const parameters = new URLSearchParams();
    for (const [name, value] of Object.entries(query)) if (value) parameters.set(name, value);
    return call<OperationContext>(relationshipId, 'GET', `context?${parameters.toString()}`);
  },
  setMode: (relationshipId: string, modeId: ModeId, surface?: string) =>
    call<{ ok: boolean }>(relationshipId, 'PUT', 'mode', { modeId, surface }),
  tourSeen: (relationshipId: string) => call<{ ok: boolean }>(relationshipId, 'POST', 'tour-seen'),
  setLayer: (relationshipId: string, layerId: string, on: boolean) =>
    call<{ layerId: string; on: boolean }>(relationshipId, 'PUT', `layers/${id(layerId)}`, { on, route: 'TOOL' }),
  addLayer: (relationshipId: string, label: string) => call<LayerView>(relationshipId, 'POST', 'layers', { label }),
  create: (
    relationshipId: string,
    body: {
      kind: string;
      title: string;
      body?: string;
      layer?: string;
      levelId?: string;
      parentId?: string;
      startDate?: string;
      platformId?: string;
      componentId?: string;
      route?: OperationRoute;
    }
  ) => call<ItemView>(relationshipId, 'POST', 'items', body),
  edit: (
    relationshipId: string,
    itemId: string,
    body: { title?: string; body?: string; startDate?: string; expectedVersion: number }
  ) => call<ItemView>(relationshipId, 'PATCH', `items/${id(itemId)}`, { ...body, route: 'TOOL' }),
  act: (
    relationshipId: string,
    itemId: string,
    action: 'accept' | 'hide' | 'restore' | 'hand-over' | 'take-back' | 'undo' | 'reject',
    route: OperationRoute = 'TOOL'
  ) => call<ItemView>(relationshipId, 'POST', `items/${id(itemId)}/${action}`, { route }),
  approve: (relationshipId: string, itemId: string, version: number) =>
    call<ItemView>(relationshipId, 'POST', `items/${id(itemId)}/approve`, { version, route: 'TOOL' }),
  move: (relationshipId: string, itemId: string, start: string) =>
    call<ItemView>(relationshipId, 'POST', `items/${id(itemId)}/move`, { start, route: 'TOOL' }),
  confirmLabel: (relationshipId: string, itemId: string, correctedTitle?: string) =>
    call<ItemView>(relationshipId, 'POST', `labels/${id(itemId)}/confirm`, { correctedTitle, route: 'TOOL' }),
  answerPlatform: (relationshipId: string, platformId: string, answer: 'PRESENT' | 'NOT_PRESENT' | 'PUBLIC_ONLY') =>
    call<PlatformView>(relationshipId, 'PUT', `platforms/${id(platformId)}/answer`, { answer, route: 'TOOL' }),
  testPlatform: (relationshipId: string, platformId: string) =>
    call<PlatformView>(relationshipId, 'POST', `platforms/${id(platformId)}/test`),
  setGoal: (
    relationshipId: string,
    skillId: string,
    goal: { baseline: string; target: string; evidenceSource: string; cadence: string; authorityState: string }
  ) => call<ItemView>(relationshipId, 'PUT', `goals/${id(skillId)}`, { ...goal, route: 'TOOL' }),
  decideGoal: (relationshipId: string, skillId: string, accept: boolean) =>
    call<ItemView>(relationshipId, 'POST', `goals/${id(skillId)}/decision`, { accept, route: 'TOOL' }),
  decideDigest: (relationshipId: string, digestId: string, accept: boolean) =>
    call<ItemView>(relationshipId, 'POST', `digests/${id(digestId)}/decision`, { accept, route: 'TOOL' }),
  schedule: (relationshipId: string, contentId: string, platformId: string, date: string) =>
    call<ItemView>(relationshipId, 'POST', 'schedule', { contentId, platformId, date, route: 'TOOL' }),
  publishAuthority: (relationshipId: string, granted: boolean) =>
    call<{ granted: boolean }>(relationshipId, 'PUT', 'publish-authority', { granted }),
  publish: (relationshipId: string, slotId: string) =>
    call<ItemView>(relationshipId, 'POST', `slots/${id(slotId)}/publish`),
  recordChat: (relationshipId: string) => call<ChatAllowance>(relationshipId, 'POST', 'conversation/chats'),
};

// ───────────────────────── pure helpers ─────────────────────────

export const MODE_ORDER: readonly ModeId[] = ['INDUCT', 'GOALS', 'OPERATIONS'];

// The agent's words win; a regional-language table can replace them by key without a code change.
export function labelFor(table: Record<string, string>, key: string, fallback: string): string {
  return table[key] ?? fallback;
}

export function monthRange(year: number, month: number): { from: string; to: string } {
  const pad = (value: number) => String(value).padStart(2, '0');
  const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return { from: `${year}-${pad(month)}-01`, to: `${year}-${pad(month)}-${pad(last)}` };
}

export function shiftMonth(year: number, month: number, by: number): { year: number; month: number } {
  const index = year * 12 + (month - 1) + by;
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

export type DayCell = { date: string; day: number; inMonth: boolean; entries: ItemView[] };

// Weeks start on Monday; the grid always holds whole weeks so the month never jumps.
export function monthGrid(year: number, month: number, entries: ItemView[]): DayCell[][] {
  const first = new Date(Date.UTC(year, month - 1, 1));
  const offset = (first.getUTCDay() + 6) % 7;
  const start = new Date(Date.UTC(year, month - 1, 1 - offset));
  const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const weeks = Math.ceil((offset + last) / 7);
  const rows: DayCell[][] = [];
  for (let week = 0; week < weeks; week += 1) {
    const row: DayCell[] = [];
    for (let day = 0; day < 7; day += 1) {
      const cell = new Date(start.getTime() + (week * 7 + day) * 86_400_000);
      const date = cell.toISOString().slice(0, 10);
      row.push({
        date,
        day: cell.getUTCDate(),
        inMonth: cell.getUTCMonth() === month - 1,
        entries: entries.filter((entry) => {
          const from = entry.startDate ?? '';
          const to = entry.endDate ?? from;
          return from !== '' && from <= date && date <= to;
        }),
      });
    }
    rows.push(row);
  }
  return rows;
}

export type TreeNode = { item: ItemView; children: TreeNode[] };

export function buildTree(nodes: ItemView[]): TreeNode[] {
  const byParent = new Map<string | null, ItemView[]>();
  const known = new Set(nodes.map((node) => node.itemId));
  for (const node of nodes) {
    const parent = node.parentId && known.has(node.parentId) ? node.parentId : null;
    byParent.set(parent, [...(byParent.get(parent) ?? []), node]);
  }
  const grow = (parent: string | null): TreeNode[] =>
    (byParent.get(parent) ?? []).map((item) => ({ item, children: grow(item.itemId) }));
  return grow(null);
}

// Skill ids are data; this only turns one into words (the agent can supply its own through the label table).
export function humanize(identifier: string): string {
  const words = identifier.toLowerCase().split('_').filter(Boolean).join(' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function authorLabel(state: ItemView['authorState']): string {
  switch (state) {
    case 'AGENT_SUGGESTED':
      return 'Suggested by your agent';
    case 'CUSTOMER_EDITED':
      return 'Edited by you';
    case 'CUSTOMER_OWNED':
      return 'Yours — your agent leaves it alone';
    default:
      return 'Approved version';
  }
}

export function presenceLabel(presence: string): string {
  switch (presence) {
    case 'PRESENT':
      return 'Present';
    case 'NOT_PRESENT':
      return 'Not present';
    case 'PUBLIC_ONLY':
      return 'Public information only';
    case 'CONNECTED_TESTED':
      return 'Connected and tested';
    case 'NEEDS_REPAIR':
      return 'Needs to be reconnected';
    case 'NOT_YET_CONNECTABLE':
      return 'Not yet connectable';
    default:
      return 'Not answered yet';
  }
}

export function problemText(problem: OperationProblem): string {
  return problem.detail ?? 'That did not work. Nothing was changed; try again.';
}

export function legacySurface(surface: string | null | undefined): boolean {
  return (
    typeof surface === 'string' &&
    ['overview', 'plan', 'decisions', 'work', 'results', 'usage', 'alerts', 'rights'].includes(surface)
  );
}
