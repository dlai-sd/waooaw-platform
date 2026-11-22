/** @jest-environment node */

// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R007, WC149-R008
// Constitutional basis: C-026, C-059, C-063, C-083

import { NextRequest } from 'next/server';
import { resetConnectionWriteLimit } from '@/lib/provider-connections-server';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { GET } from './route';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));

const code = 'AQD-secret-authorization-code-123';
const state = 'state_0123456789abcdef';
const customer = `e30.${Buffer.from(JSON.stringify({ sub: 'customer-1' })).toString('base64url')}.sig`;

function callback(query: string) {
  return new NextRequest(`http://localhost/api/provider-connections/meta/callback?${query}`);
}

function upstream(status: number, body: unknown = {}) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function location(response: Response): string {
  return response.headers.get('location') ?? '';
}

describe('Meta callback route', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.clearAllMocks();
    resetConnectionWriteLimit();
    jest.mocked(accessTokenFromRequest).mockResolvedValue(customer);
    global.fetch = jest.fn().mockResolvedValue(upstream(200, { id: 'c1' }));
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('completes the connection with the user session token and redirects to connected', async () => {
    const response = await GET(callback(`code=${code}&state=${state}`));

    expect(response.status).toBe(303);
    expect(location(response)).toBe('http://localhost/connections?connected=meta');
    expect(response.headers.get('cache-control')).toBe('no-store');
    const [url, init] = jest.mocked(global.fetch).mock.calls[0];
    expect(url).toBe('http://localhost:5001/api/v1/provider-connections/meta/callback');
    expect(init?.method).toBe('POST');
    expect(init?.headers).toMatchObject({ Authorization: `Bearer ${customer}` });
    expect(JSON.parse(String(init?.body))).toEqual({ code, state });
  });

  it.each([
    ['error=access_denied&error_reason=user_denied&state=abc', 'denied'],
    ['error_reason=user_denied', 'denied'],
  ])('redirects a Meta refusal (%s) with error=denied and never calls the owner', async (query, expected) => {
    const response = await GET(callback(query));

    expect(location(response)).toBe(`http://localhost/connections?error=${expected}`);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it.each([
    [`state=${state}`],
    [`code=${code}`],
    [`code=${code}&state=short`],
    [`code=${code}&state=${encodeURIComponent('<script>alert(1)</script>')}`],
    [`code=${'x'.repeat(3000)}&state=${state}`],
  ])('rejects an incomplete or malformed callback (%s) without calling the owner', async (query) => {
    const response = await GET(callback(query));

    expect(location(response)).toBe('http://localhost/connections?error=invalid_request');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('sends a visitor without a session back to the screen without calling the owner', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue(undefined);

    const response = await GET(callback(`code=${code}&state=${state}`));

    expect(location(response)).toBe('http://localhost/connections?error=signin_required');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it.each([
    [400, 'state_invalid'],
    [409, 'state_invalid'],
    [401, 'signin_required'],
    [403, 'signin_required'],
    [502, 'unavailable'],
    [422, 'failed'],
  ])('maps an owner %i to a fixed error code', async (status, expected) => {
    jest.spyOn(console, 'error').mockImplementation(() => undefined);
    global.fetch = jest.fn().mockResolvedValue(upstream(status, { detail: `bad code ${code}` }));

    const response = await GET(callback(`code=${code}&state=${state}`));

    expect(response.status).toBe(303);
    expect(location(response)).toBe(`http://localhost/connections?error=${expected}`);
  });

  it('never echoes the code, the state or a provider message when the owner is unreachable', async () => {
    const logged = jest.spyOn(console, 'error').mockImplementation(() => undefined);
    global.fetch = jest.fn().mockRejectedValue(new Error(`connect failed for ${code}`));

    const response = await GET(callback(`code=${code}&state=${state}&error_description=Evil+message`));

    expect(location(response)).toBe('http://localhost/connections?error=unavailable');
    expect(location(response)).not.toContain(code);
    expect(location(response)).not.toContain(state);
    expect(response.headers.get('referrer-policy')).toBe('no-referrer');
    expect(JSON.stringify(logged.mock.calls)).not.toContain(code);
  });

  it('applies the write limit to callbacks', async () => {
    let last = '';
    for (let attempt = 0; attempt < 31; attempt += 1) {
      last = location(await GET(callback(`code=${code}&state=${state}`)));
    }

    expect(last).toBe('http://localhost/connections?error=unavailable');
    expect(jest.mocked(global.fetch)).toHaveBeenCalledTimes(30);
  });
});
