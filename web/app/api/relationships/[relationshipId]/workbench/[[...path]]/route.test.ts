/** @jest-environment node */

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-04
// Constitutional basis: C-001, C-023, C-059, C-063, ADR-051

import { NextRequest } from 'next/server';
import { workbenchExperienceCapabilities, workbenchRouteAllowed } from '@/lib/api/workbench-proxy';
import { accessTokenFromRequest } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));

const relationshipId = '00000000-0000-4000-8000-000000000121';
const key = '11111111-1111-4111-8111-111111111111';
const correlation = '22222222-2222-4222-8222-222222222222';

function context(path?: string[]) {
  return { params: Promise.resolve({ relationshipId, path }) };
}

function get(path: string) {
  return new NextRequest(`http://localhost/api/relationships/${relationshipId}/workbench${path}`, { method: 'GET' });
}

function post(path: string, body: string, headers: Record<string, string> = {}) {
  return new NextRequest(`http://localhost/api/relationships/${relationshipId}/workbench${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Origin: 'http://localhost', ...headers },
    body,
  });
}

function upstream(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
}

describe('workbench proxy route', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(accessTokenFromRequest).mockResolvedValue('access-token');
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('requires a secure session', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue(undefined);
    const { GET } = await import('./route');

    expect((await GET(get(''), context())).status).toBe(401);
  });

  it('forwards the projection read with the web capability header and returns the ETag', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(200, { schemaVersion: '1.0' }, { ETag: '"relationship-4"' }));
    const { GET } = await import('./route');

    const response = await GET(get(''), context());

    expect(response.status).toBe(200);
    expect(response.headers.get('etag')).toBe('"relationship-4"');
    expect(response.headers.get('cache-control')).toBe('no-store');
    const [url, init] = jest.mocked(global.fetch).mock.calls[0];
    expect(url).toBe(`http://localhost:5001/api/v1/employment/relationships/${relationshipId}/workbench`);
    expect(init?.headers).toMatchObject({
      Authorization: 'Bearer access-token',
      'X-Experience-Capabilities': workbenchExperienceCapabilities,
    });
  });

  it('forwards only the paging query and rejects paths outside the contract', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(200, { items: [] }));
    const { GET } = await import('./route');

    await GET(get('/goals?limit=20&cursor=abc&other=1'), context(['goals']));
    expect(jest.mocked(global.fetch).mock.calls[0][0]).toBe(
      `http://localhost:5001/api/v1/employment/relationships/${relationshipId}/workbench/goals?cursor=abc&limit=20`
    );

    const response = await GET(get('/subscription/changes'), context(['subscription', 'changes']));
    expect(response.status).toBe(404);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it('rejects a command without an idempotency key or from another origin', async () => {
    global.fetch = jest.fn();
    const { POST } = await import('./route');

    expect((await POST(post('/goals', '{}'), context(['goals']))).status).toBe(400);
    const foreign = await POST(
      post('/goals', '{}', { Origin: 'https://evil.example', 'Idempotency-Key': key }),
      context(['goals'])
    );
    expect(foreign.status).toBe(403);
    expect((await POST(post('/goals', 'not-json', { 'Idempotency-Key': key }), context(['goals']))).status).toBe(400);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('forwards a command with its idempotency key and correlation and passes the problem through', async () => {
    const problem = {
      type: 'about:blank',
      title: 'Conflict',
      status: 409,
      code: 'WORKBENCH_VERSION_CONFLICT',
      correlationId: correlation,
    };
    global.fetch = jest.fn().mockResolvedValue(upstream(409, problem));
    const { POST } = await import('./route');

    const response = await POST(
      post('/decisions/abc/resolve', '{"resolution":"APPROVE"}', {
        'Idempotency-Key': key,
        'X-Correlation-ID': correlation,
      }),
      context(['decisions', 'abc', 'resolve'])
    );

    expect(response.status).toBe(409);
    expect(await response.json()).toMatchObject({ code: 'WORKBENCH_VERSION_CONFLICT' });
    const [, init] = jest.mocked(global.fetch).mock.calls[0];
    expect(init?.headers).toMatchObject({ 'Idempotency-Key': key, 'X-Correlation-ID': correlation });
    expect(init?.body).toBe('{"resolution":"APPROVE"}');
  });

  it('maps an unreachable business platform to an honest unavailable problem', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('connect refused'));
    const { GET } = await import('./route');

    const response = await GET(get('/wallet'), context(['wallet']));

    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({ code: 'WORKBENCH_UNAVAILABLE' });
  });

  it('allows only the contract routes with the matching method', () => {
    expect(workbenchRouteAllowed('GET', [])).toBe(true);
    expect(workbenchRouteAllowed('POST', ['controls', 'stop'])).toBe(true);
    expect(workbenchRouteAllowed('POST', ['handoffs', 'consume'])).toBe(true);
    expect(workbenchRouteAllowed('GET', ['handoffs', 'consume'])).toBe(false);
    expect(workbenchRouteAllowed('POST', ['wallet'])).toBe(false);
    expect(workbenchRouteAllowed('GET', ['goals', '..'])).toBe(false);
    expect(workbenchRouteAllowed('GET', ['goals', 'a', 'b', 'c'])).toBe(false);
  });
});
