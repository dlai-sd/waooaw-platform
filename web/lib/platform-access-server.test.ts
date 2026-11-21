/** @jest-environment node */

// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063

import { NextRequest } from 'next/server';
import { proxyPlatformAccess, resolvePlatformAccess } from './platform-access-server';

const id = '7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11';

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function post(path: string, body: string) {
  return new NextRequest(`http://localhost/api/platform/access/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  });
}

describe('platform access server', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('asks the Business Platform who the caller is and sends the bearer', async () => {
    global.fetch = jest.fn().mockResolvedValue(json(200, { founder: true, emailVerified: true }));

    const access = await resolvePlatformAccess('tok');

    expect(access).toMatchObject({ founder: true, administrator: true });
    const [url, init] = jest.mocked(global.fetch).mock.calls[0];
    expect(url).toBe('http://localhost:5001/api/v1/platform/me/roles');
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer tok' });
  });

  it('grants nothing without a token, on refusal or when the Business Platform is unreachable', async () => {
    global.fetch = jest.fn();
    expect((await resolvePlatformAccess(undefined)).administrator).toBe(false);
    expect(global.fetch).not.toHaveBeenCalled();

    global.fetch = jest.fn().mockResolvedValue(json(403, {}));
    expect((await resolvePlatformAccess('tok')).administrator).toBe(false);

    global.fetch = jest.fn().mockRejectedValue(new Error('down'));
    expect((await resolvePlatformAccess('tok')).administrator).toBe(false);
  });

  it('forwards an allowed request with only a clean status filter', async () => {
    global.fetch = jest.fn().mockResolvedValue(json(200, { requests: [] }));
    const request = new NextRequest('http://localhost/api/platform/access/access-requests?status=PENDING&x=1');

    const response = await proxyPlatformAccess(request, 'tok', ['access-requests']);

    expect(response.status).toBe(200);
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(jest.mocked(global.fetch).mock.calls[0][0]).toBe(
      'http://localhost:5001/api/v1/platform/access-requests?status=PENDING'
    );
  });

  it('drops a malformed status filter', async () => {
    global.fetch = jest.fn().mockResolvedValue(json(200, {}));
    const request = new NextRequest('http://localhost/api/platform/access/access-requests?status=a;b');

    await proxyPlatformAccess(request, 'tok', ['access-requests']);

    expect(jest.mocked(global.fetch).mock.calls[0][0]).toBe('http://localhost:5001/api/v1/platform/access-requests');
  });

  it('forwards a write body and relays the upstream refusal', async () => {
    global.fetch = jest.fn().mockResolvedValue(json(403, { code: 'PLATFORM_ACCESS_STEP_UP_REQUIRED' }));

    const response = await proxyPlatformAccess(
      post(`access-requests/${id}/decision`, '{"decision":"APPROVE"}'),
      'tok',
      ['access-requests', id, 'decision']
    );

    expect(response.status).toBe(403);
    expect((await response.json()).code).toBe('PLATFORM_ACCESS_STEP_UP_REQUIRED');
    expect(jest.mocked(global.fetch).mock.calls[0][1]).toMatchObject({
      method: 'POST',
      body: '{"decision":"APPROVE"}',
    });
  });

  it('refuses routes that are not published, empty bodies and oversized bodies', async () => {
    global.fetch = jest.fn();

    expect((await proxyPlatformAccess(post('grants', '{}'), 'tok', ['grants'])).status).toBe(404);
    expect((await proxyPlatformAccess(post('access-requests', 'nope'), 'tok', ['access-requests'])).status).toBe(400);
    const big = JSON.stringify({ justification: 'x'.repeat(9000) });
    expect((await proxyPlatformAccess(post('access-requests', big), 'tok', ['access-requests'])).status).toBe(400);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('answers 503 when the Business Platform cannot be reached', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('down'));
    const request = new NextRequest('http://localhost/api/platform/access/grants');

    const response = await proxyPlatformAccess(request, 'tok', ['grants']);

    expect(response.status).toBe(503);
    expect((await response.json()).code).toBe('PLATFORM_ACCESS_UNAVAILABLE');
  });
});
