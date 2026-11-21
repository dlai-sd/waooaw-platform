/** @jest-environment node */

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { NextRequest } from 'next/server';
import { resetPricingWriteLimit } from '@/lib/pricing-admin-server';
import { accessTokenFromRequest } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));

const id = '7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11';
const key = '11111111-1111-4111-8111-111111111111';

function token(claims: Record<string, unknown>): string {
  return `e30.${Buffer.from(JSON.stringify(claims)).toString('base64url')}.sig`;
}

const admin = token({ sub: 'admin-1', realm_access: { roles: ['pricing_admin'] } });
const founder = token({ sub: 'founder-1', realm_access: { roles: ['founder'] } });

function context(path?: string[]) {
  return { params: Promise.resolve({ path }) };
}

function get(path: string) {
  return new NextRequest(`http://localhost/api/admin/pricing/${path}`, { method: 'GET' });
}

function write(method: 'POST' | 'PUT', path: string, body: string, headers: Record<string, string> = {}) {
  return new NextRequest(`http://localhost/api/admin/pricing/${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', Origin: 'http://localhost', 'Idempotency-Key': key, ...headers },
    body,
  });
}

function upstream(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
}

describe('pricing admin proxy route', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.clearAllMocks();
    resetPricingWriteLimit();
    jest.mocked(accessTokenFromRequest).mockResolvedValue(admin);
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('requires a secure session', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue(undefined);
    const { GET } = await import('./route');

    expect((await GET(get('drafts'), context(['drafts']))).status).toBe(401);
  });

  it('refuses a customer session on every route', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue(token({ realm_access: { roles: ['employer'] } }));
    global.fetch = jest.fn();
    const { GET } = await import('./route');

    const response = await GET(get('drafts'), context(['drafts']));

    expect(response.status).toBe(403);
    expect((await response.json()).code).toBe('PRICING_FORBIDDEN');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('forwards an allowed read with the bearer, the allowed query only and the ETag back', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(200, { items: [] }, { ETag: '"1:DRAFT:abc"' }));
    const { GET } = await import('./route');

    const response = await GET(get('drafts?kind=RATE&evil=1&state=DRAFT'), context(['drafts']));

    expect(response.status).toBe(200);
    expect(response.headers.get('etag')).toBe('"1:DRAFT:abc"');
    expect(response.headers.get('cache-control')).toBe('no-store');
    const [url, init] = jest.mocked(global.fetch).mock.calls[0];
    expect(url).toBe('http://localhost:5001/api/v1/admin/pricing/drafts?kind=RATE&state=DRAFT');
    expect(init?.headers).toMatchObject({ Authorization: `Bearer ${admin}` });
  });

  it('does not proxy anything outside the eighteen published operations', async () => {
    global.fetch = jest.fn();
    const { GET } = await import('./route');

    expect((await GET(get('drafts/not-a-uuid'), context(['drafts', 'not-a-uuid']))).status).toBe(404);
    expect((await GET(get(''), context())).status).toBe(404);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('refuses a cross-origin write and a write without an idempotency key', async () => {
    global.fetch = jest.fn();
    const { POST } = await import('./route');
    const crossOrigin = write('POST', 'drafts', '{}', {
      Origin: 'https://evil.example',
      'Sec-Fetch-Site': 'cross-site',
    });

    expect((await POST(crossOrigin, context(['drafts']))).status).toBe(403);
    expect((await POST(write('POST', 'drafts', '{}', { 'Idempotency-Key': 'x' }), context(['drafts']))).status).toBe(
      400
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('forwards a write with the key and refuses a missing or oversized body', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(201, { versionId: id }));
    const { POST } = await import('./route');

    const created = await POST(write('POST', 'drafts', '{"schemaVersion":"1.0"}'), context(['drafts']));
    const [, init] = jest.mocked(global.fetch).mock.calls[0];

    expect(created.status).toBe(201);
    expect(init?.headers).toMatchObject({ 'Idempotency-Key': key, 'Content-Type': 'application/json' });
    expect(init?.body).toBe('{"schemaVersion":"1.0"}');
    const huge = JSON.stringify({ filler: 'x'.repeat(300_000) });
    expect((await POST(write('POST', 'drafts', huge), context(['drafts']))).status).toBe(400);
    expect((await POST(write('POST', 'drafts', 'not json'), context(['drafts']))).status).toBe(400);
  });

  it('lets only the Founder reach authorize and activate-for-sale', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(200, { state: 'EFFECTIVE' }));
    const { POST } = await import('./route');
    const path = ['drafts', id, 'authorize'];

    expect((await POST(write('POST', path.join('/'), '{}'), context(path))).status).toBe(403);
    expect(global.fetch).not.toHaveBeenCalled();
    jest.mocked(accessTokenFromRequest).mockResolvedValue(founder);

    expect((await POST(write('POST', path.join('/'), '{}'), context(path))).status).toBe(200);
  });

  it('rate-limits state-changing calls per signed-in subject', async () => {
    global.fetch = jest.fn().mockImplementation(async () => upstream(200, {}));
    const { PUT } = await import('./route');
    const path = ['drafts', id];

    let last = 200;
    for (let attempt = 0; attempt < 31; attempt += 1) {
      last = (await PUT(write('PUT', path.join('/'), '{}'), context(path))).status;
    }

    expect(last).toBe(429);
  });

  it('turns an unreachable or unreadable owner into a published problem', async () => {
    const { GET } = await import('./route');
    global.fetch = jest.fn().mockRejectedValue(new Error('down'));

    const unreachable = await GET(get('live-margin'), context(['live-margin']));

    expect(unreachable.status).toBe(503);
    expect((await unreachable.json()).code).toBe('PRICING_UNAVAILABLE');
    global.fetch = jest.fn().mockResolvedValue(new Response('<html>', { status: 502 }));
    expect((await GET(get('live-margin'), context(['live-margin']))).status).toBe(502);
  });

  it('passes an owner problem through unchanged', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(409, { code: 'PRICING_VERSION_CONFLICT', blockingPaise: 5 }));
    const { PUT } = await import('./route');

    const response = await PUT(write('PUT', `drafts/${id}`, '{}'), context(['drafts', id]));

    expect(response.status).toBe(409);
    expect(await response.json()).toMatchObject({ code: 'PRICING_VERSION_CONFLICT', blockingPaise: 5 });
  });
});
