/** @jest-environment node */

// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063

import { NextRequest } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));

function context(path?: string[]) {
  return { params: Promise.resolve({ path }) };
}

describe('platform access route', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(accessTokenFromRequest).mockResolvedValue('tok');
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('requires a secure session', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue(undefined);
    const { GET } = await import('./route');

    const response = await GET(
      new NextRequest('http://localhost/api/platform/access/me/roles'),
      context(['me', 'roles'])
    );

    expect(response.status).toBe(401);
  });

  it('forwards a signed-in read', async () => {
    global.fetch = jest.fn().mockResolvedValue(new Response('{"founder":false}', { status: 200 }));
    const { GET } = await import('./route');

    const response = await GET(
      new NextRequest('http://localhost/api/platform/access/me/roles'),
      context(['me', 'roles'])
    );

    expect(response.status).toBe(200);
  });

  it('refuses a cross-origin write before anything is sent', async () => {
    global.fetch = jest.fn();
    const { POST } = await import('./route');
    const request = new NextRequest('http://localhost/api/platform/access/access-requests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Origin: 'https://evil.example', 'Sec-Fetch-Site': 'cross-site' },
      body: '{}',
    });

    expect((await POST(request, context(['access-requests']))).status).toBe(403);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('serves nothing for an empty path', async () => {
    global.fetch = jest.fn();
    const { GET } = await import('./route');

    expect((await GET(new NextRequest('http://localhost/api/platform/access'), context())).status).toBe(404);
  });
});
