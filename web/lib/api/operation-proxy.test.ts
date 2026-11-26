/** @jest-environment node */

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R028, R030, R032
// Constitutional basis: C-001, C-023, C-059, C-063

import { NextRequest } from 'next/server';
import { operationRouteAllowed, proxyOperation, proxyOperationAdmin } from './operation-proxy';

const relationship = '7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11';
const item = '8d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a22';
const replayId = '9d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a33';

function request(method: string, path: string, body?: unknown, headers: Record<string, string> = {}) {
  return new NextRequest(`http://localhost/api/relationships/${relationship}/operation/${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function upstream(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('operationRouteAllowed', () => {
  it('allows exactly the customer routes of Agent Operation and nothing else', () => {
    for (const [method, path] of [
      ['GET', 'frame'],
      ['GET', 'calendar'],
      ['GET', `items/${item}/versions`],
      ['PUT', 'mode'],
      ['PUT', 'layers/RELIGION'],
      ['PUT', 'platforms/FACEBOOK/answer'],
      ['PUT', 'goals/SKILL_ONE'],
      ['PATCH', `items/${item}`],
      ['POST', 'items'],
      ['POST', `items/${item}/approve`],
      ['POST', `labels/${item}/confirm`],
      ['POST', 'platforms/FACEBOOK/test'],
      ['POST', 'goals/SKILL_ONE/decision'],
      ['POST', `digests/${item}/decision`],
      ['POST', 'schedule'],
      ['POST', `slots/${item}/publish`],
      ['POST', 'conversation/chats'],
    ]) {
      expect([method, path, operationRouteAllowed(method, path.split('/'))]).toEqual([method, path, true]);
    }
    for (const [method, path] of [
      ['DELETE', `items/${item}`],
      ['GET', 'settings'],
      ['POST', 'items/not-a-uuid/approve'],
      ['POST', `items/${item}/delete`],
      ['PUT', 'layers/a/b'],
      ['GET', '../../admin'],
    ]) {
      expect(operationRouteAllowed(method, path.split('/'))).toBe(false);
    }
  });

  it('keeps the Founder routes apart from the customer routes', () => {
    expect(operationRouteAllowed('GET', ['settings'], true)).toBe(true);
    expect(operationRouteAllowed('PUT', ['settings'], true)).toBe(true);
    expect(operationRouteAllowed('GET', ['share'], true)).toBe(true);
    expect(operationRouteAllowed('POST', ['settings'], true)).toBe(false);
    expect(operationRouteAllowed('GET', ['frame'], true)).toBe(false);
  });
});

describe('proxyOperation', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('forwards a read with the bearer token and only the known query values', async () => {
    const fetchMock = jest.fn(async () => upstream(200, { modesDeclared: true }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const response = await proxyOperation(
      request('GET', 'calendar?from=2026-12-01&to=2026-12-31&evil=1&mode=GOALS%20x'),
      'token-1',
      relationship,
      ['calendar']
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ modesDeclared: true });
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(
      `http://localhost:5001/api/v1/employment/relationships/${relationship}/operation/calendar?from=2026-12-01&to=2026-12-31`
    );
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer token-1');
    expect(init.body).toBeUndefined();
    expect(response.headers.get('Cache-Control')).toBe('no-store');
  });

  it('passes a write with its idempotency key and body and never invents a key', async () => {
    const fetchMock = jest.fn(async () => upstream(201, { itemId: 'x' }));
    global.fetch = fetchMock as unknown as typeof fetch;

    await proxyOperation(
      request('POST', 'items', { kind: 'NOTE', title: 'Hello' }, { 'Idempotency-Key': replayId }),
      't',
      relationship,
      ['items']
    );
    await proxyOperation(
      request('POST', 'items', { kind: 'NOTE', title: 'Hello' }, { 'Idempotency-Key': 'nope' }),
      't',
      relationship,
      ['items']
    );

    const first = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
    const second = (fetchMock.mock.calls[1] as unknown as [string, RequestInit])[1];
    expect((first.headers as Record<string, string>)['Idempotency-Key']).toBe(replayId);
    expect(JSON.parse(String(first.body))).toEqual({ kind: 'NOTE', title: 'Hello' });
    expect((second.headers as Record<string, string>)['Idempotency-Key']).toBeUndefined();
  });

  it('refuses an unknown route, a bad relationship and an oversized body without calling the platform', async () => {
    const fetchMock = jest.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    expect((await proxyOperation(request('DELETE', 'items'), 't', relationship, ['items'])).status).toBe(404);
    expect((await proxyOperation(request('GET', 'frame'), 't', 'not-a-uuid', ['frame'])).status).toBe(404);
    const big = await proxyOperation(request('POST', 'items', { title: 'x'.repeat(70_000) }), 't', relationship, [
      'items',
    ]);

    expect(big.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('relays only a known code, the plain detail and the mode that fixes a gate, never the platform’s internals', async () => {
    global.fetch = jest.fn(async () =>
      upstream(409, {
        code: 'OPERATION_GATE_BLOCKED',
        detail: 'Finish this first: Confirm profile',
        nextMode: 'INDUCT',
        stack: 'secret trace',
        title: 'internal',
      })
    ) as unknown as typeof fetch;

    const response = await proxyOperation(
      request('POST', 'schedule', {}, { 'Idempotency-Key': replayId }),
      't',
      relationship,
      ['schedule']
    );
    const body = await response.json();

    expect(response.status).toBe(409);
    expect(body).toMatchObject({
      code: 'OPERATION_GATE_BLOCKED',
      detail: 'Finish this first: Confirm profile',
      nextMode: 'INDUCT',
      status: 409,
    });
    expect(JSON.stringify(body)).not.toContain('secret trace');
    expect(JSON.stringify(body)).not.toContain('internal');
  });

  it('falls back to a plain unavailable code for an unreadable refusal and for an unreachable platform', async () => {
    global.fetch = jest.fn(async () =>
      upstream(500, { code: 'lowercase', detail: 'x'.repeat(500), nextMode: 'bad' })
    ) as unknown as typeof fetch;
    const refused = await proxyOperation(request('GET', 'frame'), 't', relationship, ['frame']);
    expect(await refused.json()).toMatchObject({ code: 'OPERATION_UNAVAILABLE', status: 500 });

    global.fetch = jest.fn(async () => {
      throw new Error('connection refused');
    }) as unknown as typeof fetch;
    const down = await proxyOperation(request('GET', 'frame'), 't', relationship, ['frame']);
    expect(down.status).toBe(503);
    expect(await down.json()).toMatchObject({ code: 'OPERATION_UNAVAILABLE' });
  });

  it('forwards the Founder routes to the admin endpoint', async () => {
    const fetchMock = jest.fn(async () => upstream(200, { chatAllowanceDefault: 1000 }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const response = await proxyOperationAdmin(
      new NextRequest('http://localhost/api/admin/agent-operation/settings', { method: 'GET' }),
      't',
      ['settings']
    );

    expect(response.status).toBe(200);
    expect((fetchMock.mock.calls[0] as unknown as [string])[0]).toBe(
      'http://localhost:5001/api/v1/admin/agent-operation/settings'
    );
    const denied = await proxyOperationAdmin(
      new NextRequest('http://localhost/api/admin/agent-operation/frame', { method: 'GET' }),
      't',
      ['frame']
    );
    expect(denied.status).toBe(404);
  });
});
