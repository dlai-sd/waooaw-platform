/** @jest-environment node */

// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R002, WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import { NextRequest } from 'next/server';
import { loadProviders, resetProviderWriteLimit } from '@/lib/provider-admin-server';
import { accessTokenFromRequest } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));

const providerId = '7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11';
const versionId = '9b1c2d3e-4f5a-4b6c-8d7e-0f1a2b3c4d5e';
const secret = 'sk-live-0123456789-never-log-me';

function token(claims: Record<string, unknown>): string {
  return `e30.${Buffer.from(JSON.stringify(claims)).toString('base64url')}.sig`;
}

const founder = token({
  sub: 'founder-1',
  realm_access: { roles: ['founder'] },
});

function context(path?: string[]) {
  return { params: Promise.resolve({ path }) };
}

function get(path: string) {
  return new NextRequest(`http://localhost/api/admin/providers/${path}`, {
    method: 'GET',
  });
}

function post(path: string, body: string, headers: Record<string, string> = {}) {
  return new NextRequest(`http://localhost/api/admin/providers/${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Origin: 'http://localhost',
      ...headers,
    },
    body,
  });
}

function upstream(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('provider admin proxy route', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.clearAllMocks();
    resetProviderWriteLimit();
    jest.mocked(accessTokenFromRequest).mockResolvedValue(founder);
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('requires a secure session before anything is forwarded', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue(undefined);
    global.fetch = jest.fn();
    const { GET, POST } = await import('./route');

    const read = await GET(get(''), context());
    const write = await POST(
      post(`${providerId}/credentials/test`, '{}'),
      context([providerId, 'credentials', 'test'])
    );

    expect(read.status).toBe(401);
    expect(write.status).toBe(401);
    expect(read.headers.get('cache-control')).toBe('no-store');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('forwards a read with the bearer token to the owner and never caches it', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(200, [{ id: providerId }]));
    const { GET } = await import('./route');

    const response = await GET(get(''), context());

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual([{ id: providerId }]);
    expect(response.headers.get('cache-control')).toBe('no-store');
    const [url, init] = jest.mocked(global.fetch).mock.calls[0];
    expect(url).toBe('http://localhost:5001/api/v1/admin/providers');
    expect(init?.headers).toMatchObject({ Authorization: `Bearer ${founder}` });
  });

  it.each([
    ['GET', `${providerId}/credentials`, [providerId, 'credentials']],
    ['POST', '', []],
    ['POST', `${providerId}/credentials/test`, [providerId, 'credentials', 'test']],
    ['POST', `${providerId}/credentials`, [providerId, 'credentials']],
    ['POST', `${providerId}/credentials/${versionId}/activate`, [providerId, 'credentials', versionId, 'activate']],
    ['POST', 'sarvam/test-answer', ['sarvam', 'test-answer']],
  ])('proxies the allowed operation %s /%s', async (method, path, segments) => {
    global.fetch = jest.fn().mockResolvedValue(upstream(200, {}));
    const { GET, POST } = await import('./route');

    const response =
      method === 'GET'
        ? await GET(get(path), context(segments))
        : await POST(post(path, '{"value":"x"}'), context(segments));

    expect(response.status).toBe(200);
    expect(jest.mocked(global.fetch).mock.calls[0][0]).toBe(
      `http://localhost:5001/api/v1/admin/providers${path === '' ? '' : `/${path}`}`
    );
  });

  it.each([
    ['GET', [providerId]],
    ['GET', ['not-a-uuid', 'credentials']],
    ['GET', [providerId, 'credentials', 'test']],
    ['POST', [providerId, 'credentials', 'not-a-uuid', 'activate']],
    ['POST', [providerId, 'credentials', versionId, 'deactivate']],
    ['POST', ['..', 'internal']],
    ['POST', ['Bad_Name', 'test-answer']],
    ['GET', ['sarvam', 'test-answer']],
    ['POST', ['sarvam', 'test-answer', 'extra']],
  ])('does not proxy anything outside the seven published operations (%s %j)', async (method, segments) => {
    global.fetch = jest.fn();
    const { GET, POST } = await import('./route');
    const path = segments.join('/');

    const response =
      method === 'GET' ? await GET(get(path), context(segments)) : await POST(post(path, '{}'), context(segments));

    expect(response.status).toBe(404);
    expect((await response.json()).code).toBe('PROVIDER_NOT_FOUND');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('refuses a cross-origin write before reading the body', async () => {
    global.fetch = jest.fn();
    const { POST } = await import('./route');

    const response = await POST(
      post('', JSON.stringify({ value: secret }), {
        Origin: 'https://evil.example',
        'Sec-Fetch-Site': 'cross-site',
      }),
      context()
    );

    expect(response.status).toBe(403);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('refuses a missing, malformed, array or oversized body', async () => {
    global.fetch = jest.fn();
    const { POST } = await import('./route');
    const path = [providerId, 'credentials'];

    expect((await POST(post(path.join('/'), 'not json'), context(path))).status).toBe(400);
    expect((await POST(post(path.join('/'), '[1]'), context(path))).status).toBe(400);
    expect((await POST(post(path.join('/'), 'null'), context(path))).status).toBe(400);
    const huge = JSON.stringify({ value: 'x'.repeat(21_000) });
    expect((await POST(post(path.join('/'), huge), context(path))).status).toBe(413);
    const declared = await POST(post(path.join('/'), '{}', { 'Content-Length': '99999' }), context(path));
    expect(declared.status).toBe(413);
    expect((await declared.json()).code).toBe('PROVIDER_INVALID');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('rate-limits writes to thirty a minute per signed-in subject', async () => {
    global.fetch = jest.fn().mockImplementation(async () => upstream(200, {}));
    const { POST } = await import('./route');
    const path = [providerId, 'credentials', 'test'];

    const statuses: number[] = [];
    for (let attempt = 0; attempt < 31; attempt += 1) {
      statuses.push((await POST(post(path.join('/'), '{"value":"x"}'), context(path))).status);
    }
    jest.mocked(accessTokenFromRequest).mockResolvedValue(token({ sub: 'founder-2' }));
    const other = await POST(post(path.join('/'), '{"value":"x"}'), context(path));

    expect(statuses.slice(0, 30).every((status) => status === 200)).toBe(true);
    expect(statuses[30]).toBe(429);
    expect(other.status).toBe(200);
  });

  it('relays an owner problem status, code and title but never its detail or the request body', async () => {
    global.fetch = jest.fn().mockResolvedValue(
      upstream(403, {
        type: 'about:blank',
        title: 'A fresh sign-in is required.',
        status: 403,
        code: 'PROVIDER_STEP_UP_REQUIRED',
        detail: `rejected ${secret}`,
      })
    );
    const { POST } = await import('./route');
    const path = [providerId, 'credentials'];

    const response = await POST(post(path.join('/'), JSON.stringify({ value: secret })), context(path));
    const text = await response.text();

    expect(response.status).toBe(403);
    expect(JSON.parse(text)).toMatchObject({
      code: 'PROVIDER_STEP_UP_REQUIRED',
      title: 'A fresh sign-in is required.',
      status: 403,
    });
    expect(text).not.toContain(secret);
  });

  it('relays the provider-probe-unavailable problem from the owner on a Test answer', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(
        upstream(503, { code: 'PROVIDER_PROBE_UNAVAILABLE', title: 'The provider probe is unavailable.' })
      );
    const { POST } = await import('./route');
    const path = ['sarvam', 'test-answer'];

    const response = await POST(post(path.join('/'), '{"model":null,"fallbackProviders":[]}'), context(path));

    expect(response.status).toBe(503);
    expect((await response.json()).code).toBe('PROVIDER_PROBE_UNAVAILABLE');
  });

  it('gives a published problem when the owner sends an unusable error', async () => {
    global.fetch = jest.fn().mockResolvedValue(upstream(409, { code: 'lower case', title: '' }));
    const { POST } = await import('./route');

    const response = await POST(post('', '{}'), context());

    expect(response.status).toBe(409);
    expect(await response.json()).toMatchObject({ code: 'PROVIDER_CONFLICT' });
  });

  it('turns an unreachable owner into a vault-unavailable problem without logging the body', async () => {
    const logged = jest.spyOn(console, 'error').mockImplementation(() => undefined);
    global.fetch = jest.fn().mockRejectedValue(new Error(`connect failed for ${secret}`));
    const { POST } = await import('./route');
    const path = [providerId, 'credentials'];

    const response = await POST(post(path.join('/'), JSON.stringify({ value: secret })), context(path));

    expect(response.status).toBe(503);
    expect((await response.json()).code).toBe('PROVIDER_VAULT_UNAVAILABLE');
    expect(logged).toHaveBeenCalled();
    expect(JSON.stringify(logged.mock.calls)).not.toContain(secret);
  });

  it('relays an unreadable owner failure as a 503-class problem', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => undefined);
    global.fetch = jest.fn().mockResolvedValue(new Response('<html>', { status: 502 }));
    const { GET } = await import('./route');

    const response = await GET(get(''), context());

    expect(response.status).toBe(502);
    expect((await response.json()).code).toBe('PROVIDER_VAULT_UNAVAILABLE');
  });
});

describe('provider list load for the server page', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('returns providers, a forbidden marker, or unavailable', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => undefined);
    global.fetch = jest.fn().mockResolvedValue(upstream(200, [{ id: providerId }]));
    expect(await loadProviders(founder)).toEqual({
      kind: 'ready',
      providers: [{ id: providerId }],
    });
    global.fetch = jest.fn().mockResolvedValue(upstream(200, { not: 'a list' }));
    expect(await loadProviders(founder)).toEqual({ kind: 'unavailable' });
    global.fetch = jest.fn().mockResolvedValue(upstream(403, {}));
    expect(await loadProviders(founder)).toEqual({ kind: 'forbidden' });
    global.fetch = jest.fn().mockResolvedValue(upstream(503, {}));
    expect(await loadProviders(founder)).toEqual({ kind: 'unavailable' });
    global.fetch = jest.fn().mockRejectedValue(new Error('down'));
    expect(await loadProviders(founder)).toEqual({ kind: 'unavailable' });
  });
});
