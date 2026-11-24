/** @jest-environment node */

// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R007, WC149-R008, WC149-R009
// Constitutional basis: C-026, C-059, C-063, C-083

import { NextRequest } from 'next/server';
import { resetConnectionWriteLimit } from '@/lib/provider-connections-server';
import { accessTokenFromRequest } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));

const connectionId = '7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11';
const providerMessage = 'Facebook said: token EAAB-secret-token is invalid';

function token(claims: Record<string, unknown>): string {
  return `e30.${Buffer.from(JSON.stringify(claims)).toString('base64url')}.sig`;
}

const customer = token({ sub: 'customer-1' });

function context(path?: string[]) {
  return { params: Promise.resolve({ path }) };
}

function get(path: string) {
  return new NextRequest(`http://localhost/api/provider-connections/${path}`, { method: 'GET' });
}

function post(path: string, body: string, headers: Record<string, string> = {}) {
  return new NextRequest(`http://localhost/api/provider-connections/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Origin: 'http://localhost', ...headers },
    body,
  });
}

function upstream(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('provider connections proxy route', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.clearAllMocks();
    resetConnectionWriteLimit();
    jest.mocked(accessTokenFromRequest).mockResolvedValue(customer);
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('requires a secure session before anything is forwarded', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue(undefined);
    global.fetch = jest.fn();
    const { GET, POST } = await import('./route');

    expect((await GET(get(''), context())).status).toBe(401);
    expect((await POST(post('meta/start', '{}'), context(['meta', 'start']))).status).toBe(401);
    expect((await (await GET(get(''), context())).json()).code).toBe('CONNECTION_SIGN_IN_REQUIRED');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('forwards the list with the tenant user token and never caches it', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(200, [{ id: connectionId }]));
    const { GET } = await import('./route');

    const response = await GET(get(''), context());

    expect(response.status).toBe(200);
    expect(response.headers.get('cache-control')).toBe('no-store');
    const [url, init] = jest.mocked(global.fetch).mock.calls[0];
    expect(url).toBe('http://localhost:5001/api/v1/provider-connections');
    expect(init?.headers).toMatchObject({ Authorization: `Bearer ${customer}` });
  });

  it.each([
    ['meta/start', ['meta', 'start'], '{}'],
    [`${connectionId}/revoke`, [connectionId, 'revoke'], '{}'],
    [`${connectionId}/publish`, [connectionId, 'publish'], '{"message":"Hi","approved":true,"approvalNote":"ok"}'],
  ])('proxies the allowed write /%s', async (path, segments, body) => {
    global.fetch = jest.fn().mockResolvedValue(upstream(200, { authorizationUrl: 'https://facebook.example/x' }));
    const { POST } = await import('./route');

    const response = await POST(post(path, body), context(segments));

    expect(response.status).toBe(200);
    const [url, init] = jest.mocked(global.fetch).mock.calls[0];
    expect(url).toBe(`http://localhost:5001/api/v1/provider-connections/${path}`);
    expect(init?.body).toBe(body);
  });

  it('answers a revoke 204 without a body', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(204));
    const { POST } = await import('./route');

    const response = await POST(post(`${connectionId}/revoke`, '{}'), context([connectionId, 'revoke']));

    expect(response.status).toBe(204);
    expect(await response.text()).toBe('');
  });

  it.each([
    ['GET', ['meta', 'start']],
    ['POST', []],
    ['POST', ['meta', 'callback']],
    ['POST', ['not-a-uuid', 'revoke']],
    ['POST', [connectionId, 'secret']],
    ['GET', [connectionId, 'publish']],
    ['POST', ['..', 'internal']],
  ])('does not proxy anything outside the four published operations (%s %j)', async (method, segments) => {
    global.fetch = jest.fn();
    const { GET, POST } = await import('./route');
    const path = segments.join('/');

    const response =
      method === 'GET' ? await GET(get(path), context(segments)) : await POST(post(path, '{}'), context(segments));

    expect(response.status).toBe(404);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('refuses a cross-origin write before reading the body', async () => {
    global.fetch = jest.fn();
    const { POST } = await import('./route');

    const response = await POST(
      post('meta/start', '{}', { Origin: 'https://evil.example', 'Sec-Fetch-Site': 'cross-site' }),
      context(['meta', 'start'])
    );

    expect(response.status).toBe(403);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('refuses a malformed, array or oversized body', async () => {
    global.fetch = jest.fn();
    const { POST } = await import('./route');
    const path = ['meta', 'start'];

    expect((await POST(post('meta/start', 'not json'), context(path))).status).toBe(400);
    expect((await POST(post('meta/start', '[1]'), context(path))).status).toBe(400);
    expect((await POST(post('meta/start', JSON.stringify({ x: 'y'.repeat(21_000) })), context(path))).status).toBe(413);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('rate-limits writes to thirty a minute per signed-in subject', async () => {
    global.fetch = jest.fn().mockImplementation(async () => upstream(200, {}));
    const { POST } = await import('./route');
    const path = ['meta', 'start'];

    const statuses: number[] = [];
    for (let attempt = 0; attempt < 31; attempt += 1) {
      statuses.push((await POST(post('meta/start', '{}'), context(path))).status);
    }
    jest.mocked(accessTokenFromRequest).mockResolvedValue(token({ sub: 'customer-2' }));
    const other = await POST(post('meta/start', '{}'), context(path));

    expect(statuses.slice(0, 30).every((status) => status === 200)).toBe(true);
    expect(statuses[30]).toBe(429);
    expect(other.status).toBe(200);
  });

  it('relays CONNECTION_NEEDS_REPAIR on publish but never the provider message', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(
        upstream(409, { code: 'CONNECTION_NEEDS_REPAIR', title: providerMessage, detail: providerMessage })
      );
    const { POST } = await import('./route');
    const path = [connectionId, 'publish'];

    const response = await POST(post(path.join('/'), '{"message":"Hi","approved":true}'), context(path));
    const text = await response.text();

    expect(response.status).toBe(409);
    expect(JSON.parse(text)).toMatchObject({ code: 'CONNECTION_NEEDS_REPAIR', status: 409 });
    expect(text).not.toContain('EAAB');
    expect(text).not.toContain('Facebook said');
  });

  it('maps an unknown or inherited upstream code to a published problem', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(403, { code: 'constructor' }));
    const { POST } = await import('./route');

    const response = await POST(post('meta/start', '{}'), context(['meta', 'start']));

    expect(response.status).toBe(403);
    expect((await response.json()).code).toBe('CONNECTION_FORBIDDEN');
  });

  it('tells a person with no active customer account apart from one who is not permitted', async () => {
    const { GET } = await import('./route');

    global.fetch = jest
      .fn()
      .mockResolvedValue(upstream(403, { code: 'IDENTITY_ACTION_DENIED', title: 'internal text' }));
    const denied = await GET(get(''), context());
    expect(denied.status).toBe(403);
    expect(await denied.json()).toMatchObject({ code: 'CONNECTION_ACCOUNT_REQUIRED' });

    global.fetch = jest.fn().mockResolvedValue(upstream(409, { code: 'REGISTRATION_REQUIRED' }));
    const registration = await GET(get(''), context());
    expect(registration.status).toBe(409);
    expect((await registration.json()).code).toBe('CONNECTION_ACCOUNT_REQUIRED');

    global.fetch = jest.fn().mockResolvedValue(upstream(401, {}));
    expect((await (await GET(get(''), context())).json()).code).toBe('CONNECTION_SIGN_IN_REQUIRED');
  });

  it('turns an unreachable owner into an unavailable problem', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => undefined);
    global.fetch = jest.fn().mockRejectedValue(new Error(providerMessage));
    const { GET } = await import('./route');

    const response = await GET(get(''), context());

    expect(response.status).toBe(503);
    expect((await response.json()).code).toBe('CONNECTION_UNAVAILABLE');
  });
});
