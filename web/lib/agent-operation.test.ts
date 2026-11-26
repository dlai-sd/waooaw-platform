// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R005, R015, R030
// Constitutional basis: C-001, C-023, C-059, C-063

import {
  authorLabel,
  buildTree,
  humanize,
  labelFor,
  legacySurface,
  monthGrid,
  monthRange,
  operationApi,
  presenceLabel,
  problemText,
  shiftMonth,
} from './agent-operation';
import { item, respond } from '@/components/operation/operation-test-data';

const base = '/api/relationships/rel-1/operation';

describe('agent operation client', () => {
  afterEach(() => jest.restoreAllMocks());

  it('reads without an idempotency key and gives every action its own key', async () => {
    const fetchMock = jest.fn(async () => respond(200, { ok: true }));
    global.fetch = fetchMock as unknown as typeof fetch;

    await operationApi.frame('rel-1', 'GOALS');
    await operationApi.setMode('rel-1', 'GOALS', 'calendar');
    await operationApi.tourSeen('rel-1');

    const calls = fetchMock.mock.calls as unknown as [string, RequestInit][];
    expect(calls[0][0]).toBe(`${base}/frame?mode=GOALS`);
    expect((calls[0][1].headers as Record<string, string>)['Idempotency-Key']).toBeUndefined();
    expect(calls[1][0]).toBe(`${base}/mode`);
    expect(JSON.parse(String(calls[1][1].body))).toEqual({ modeId: 'GOALS', surface: 'calendar' });
    expect((calls[1][1].headers as Record<string, string>)['Idempotency-Key']).toBeTruthy();
    expect(calls[2][1].body).toBeUndefined();
  });

  it('maps every command to its route, method and body', async () => {
    const fetchMock = jest.fn(async () => respond(200, {}));
    global.fetch = fetchMock as unknown as typeof fetch;

    await operationApi.frame('rel-1');
    await operationApi.calendar('rel-1', '2026-12-01', '2026-12-31');
    await operationApi.planTree('rel-1');
    await operationApi.items('rel-1', 'CONTENT');
    await operationApi.context('rel-1', { mode: 'GOALS', view: 'MONTH', selected: '' });
    await operationApi.setLayer('rel-1', 'RELIGION', true);
    await operationApi.addLayer('rel-1', 'Family dates');
    await operationApi.create('rel-1', { kind: 'NOTE', title: 'Hello' });
    await operationApi.edit('rel-1', 'i1', { title: 'New', expectedVersion: 2 });
    await operationApi.act('rel-1', 'i1', 'accept', 'ACCEPTED');
    await operationApi.approve('rel-1', 'i1', 3);
    await operationApi.move('rel-1', 'i1', '2026-12-20');
    await operationApi.confirmLabel('rel-1', 'i1', 'Corrected');
    await operationApi.answerPlatform('rel-1', 'FACEBOOK', 'PRESENT');
    await operationApi.testPlatform('rel-1', 'FACEBOOK');
    await operationApi.setGoal('rel-1', 'SKILL', {
      baseline: 'a',
      target: 'b',
      evidenceSource: 'c',
      cadence: 'MONTHLY',
      authorityState: 'CUSTOMER_APPROVAL',
    });
    await operationApi.decideGoal('rel-1', 'SKILL', true);
    await operationApi.decideDigest('rel-1', 'd1', false);
    await operationApi.schedule('rel-1', 'c1', 'FACEBOOK', '2026-12-05');
    await operationApi.publishAuthority('rel-1', true);
    await operationApi.publish('rel-1', 's1');
    await operationApi.recordChat('rel-1');

    const seen = (fetchMock.mock.calls as unknown as [string, RequestInit][]).map(
      ([url, init]) => `${init.method} ${url.replace(base, '')}`
    );
    expect(seen).toEqual([
      'GET /frame',
      'GET /calendar?from=2026-12-01&to=2026-12-31',
      'GET /plan-tree',
      'GET /items?kind=CONTENT',
      'GET /context?mode=GOALS&view=MONTH',
      'PUT /layers/RELIGION',
      'POST /layers',
      'POST /items',
      'PATCH /items/i1',
      'POST /items/i1/accept',
      'POST /items/i1/approve',
      'POST /items/i1/move',
      'POST /labels/i1/confirm',
      'PUT /platforms/FACEBOOK/answer',
      'POST /platforms/FACEBOOK/test',
      'PUT /goals/SKILL',
      'POST /goals/SKILL/decision',
      'POST /digests/d1/decision',
      'POST /schedule',
      'PUT /publish-authority',
      'POST /slots/s1/publish',
      'POST /conversation/chats',
    ]);
  });

  it('turns a refusal into a problem with plain words and the mode that fixes it', async () => {
    global.fetch = jest.fn(async () =>
      respond(409, { code: 'OPERATION_GATE_BLOCKED', detail: 'Finish this first: Confirm profile', nextMode: 'INDUCT' })
    ) as unknown as typeof fetch;

    const result = await operationApi.schedule('rel-1', 'c1', 'FACEBOOK', '2026-12-05');

    expect(result).toEqual({
      ok: false,
      status: 409,
      problem: { code: 'OPERATION_GATE_BLOCKED', detail: 'Finish this first: Confirm profile', nextMode: 'INDUCT' },
    });
    expect(problemText((result as { problem: { code: string; detail?: string } }).problem)).toBe(
      'Finish this first: Confirm profile'
    );
    expect(problemText({ code: 'X' })).toMatch(/Nothing was changed/);
  });

  it('survives an unreachable service and an unreadable body', async () => {
    global.fetch = jest.fn(async () => {
      throw new Error('offline');
    }) as unknown as typeof fetch;
    expect(await operationApi.frame('rel-1')).toEqual({
      ok: false,
      status: 0,
      problem: { code: 'OPERATION_UNAVAILABLE' },
    });

    global.fetch = jest.fn(
      async () =>
        ({ ok: false, status: 502, json: async () => Promise.reject(new Error('html')) }) as unknown as Response
    ) as unknown as typeof fetch;
    const result = await operationApi.frame('rel-1');
    expect(result).toMatchObject({ ok: false, status: 502, problem: { code: 'OPERATION_UNAVAILABLE' } });
  });
});

describe('agent operation model', () => {
  it('builds whole Monday-first weeks and places multi-day items on every day they cover', () => {
    const grid = monthGrid(2026, 12, [
      item({ itemId: 'a', startDate: '2026-12-10' }),
      item({ itemId: 'b', startDate: '2026-12-14', endDate: '2026-12-16' }),
      item({ itemId: 'c', startDate: null }),
    ]);

    expect(grid).toHaveLength(5);
    expect(grid.every((week) => week.length === 7)).toBe(true);
    expect(grid[0][0]).toMatchObject({ date: '2026-11-30', inMonth: false });
    expect(grid[0][1]).toMatchObject({ date: '2026-12-01', inMonth: true, day: 1 });
    const flat = grid.flat();
    expect(flat.find((cell) => cell.date === '2026-12-10')?.entries.map((entry) => entry.itemId)).toEqual(['a']);
    expect(flat.filter((cell) => cell.entries.some((entry) => entry.itemId === 'b')).map((cell) => cell.date)).toEqual([
      '2026-12-14',
      '2026-12-15',
      '2026-12-16',
    ]);
    expect(flat.some((cell) => cell.entries.some((entry) => entry.itemId === 'c'))).toBe(false);
  });

  it('computes month ranges and shifts across years', () => {
    expect(monthRange(2028, 2)).toEqual({ from: '2028-02-01', to: '2028-02-29' });
    expect(shiftMonth(2026, 12, 1)).toEqual({ year: 2027, month: 1 });
    expect(shiftMonth(2026, 1, -1)).toEqual({ year: 2025, month: 12 });
  });

  it('shows a plan as a tree and keeps an orphan visible at the top', () => {
    const tree = buildTree([
      item({ itemId: 'm', kind: 'PLAN_NODE' }),
      item({ itemId: 'w', parentId: 'm', kind: 'PLAN_NODE' }),
      item({ itemId: 'lost', parentId: 'gone', kind: 'PLAN_NODE' }),
    ]);

    expect(tree.map((node) => node.item.itemId)).toEqual(['m', 'lost']);
    expect(tree[0].children.map((node) => node.item.itemId)).toEqual(['w']);
  });

  it('words ids, states and labels plainly and lets a table replace the agent label by key', () => {
    expect(humanize('CONTENT_STRATEGY_AND_CALENDAR')).toBe('Content strategy and calendar');
    expect(labelFor({ MODE_GOALS: 'लक्ष्य' }, 'MODE_GOALS', 'Set my goals')).toBe('लक्ष्य');
    expect(labelFor({}, 'MODE_GOALS', 'Set my goals')).toBe('Set my goals');
    expect(authorLabel('AGENT_SUGGESTED')).toMatch(/Suggested/);
    expect(authorLabel('CUSTOMER_EDITED')).toMatch(/Edited/);
    expect(authorLabel('CUSTOMER_OWNED')).toMatch(/Yours/);
    expect(authorLabel('APPROVED_VERSION')).toMatch(/Approved/);
    for (const [presence, text] of [
      ['PRESENT', 'Present'],
      ['NOT_PRESENT', 'Not present'],
      ['PUBLIC_ONLY', 'Public information only'],
      ['CONNECTED_TESTED', 'Connected and tested'],
      ['NEEDS_REPAIR', 'Needs to be reconnected'],
      ['NOT_YET_CONNECTABLE', 'Not yet connectable'],
      ['UNANSWERED', 'Not answered yet'],
    ]) {
      expect(presenceLabel(presence)).toBe(text);
    }
  });

  it('keeps old workbench links working by recognising their surface names', () => {
    expect(legacySurface('decisions')).toBe(true);
    expect(legacySurface('calendar')).toBe(false);
    expect(legacySurface(null)).toBe(false);
  });
});
