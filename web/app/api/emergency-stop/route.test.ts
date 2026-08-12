/** @jest-environment node */

import { NextRequest } from 'next/server';

const accessTokenFromRequest = jest.fn();
jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest }));

describe('Emergency Stop server boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    accessTokenFromRequest.mockResolvedValue('server-token');
  });

  it('delegates confirmation to the relationship-wide Stop orchestrator', async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ state: 'STOPPED_EMERGENCY' }), { status: 200 }));
    const { POST } = await import('./route');
    const request = new NextRequest('http://localhost/api/emergency-stop', {
      method: 'POST',
      body: JSON.stringify({ contractId: '5f33925b-fb0c-4366-8414-7f85309639b9', activeSessionIds: [] }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/employment/relationships/5f33925b-fb0c-4366-8414-7f85309639b9/emergency-stop'),
      expect.objectContaining({ method: 'POST' }));
  });

  it('does not claim confirmation when relationship Stop remains unresolved', async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ title: 'Evidence unavailable' }), { status: 503 }));
    const { POST } = await import('./route');
    const request = new NextRequest('http://localhost/api/emergency-stop', {
      method: 'POST',
      body: JSON.stringify({ contractId: '5f33925b-fb0c-4366-8414-7f85309639b9' }),
    });

    const response = await POST(request);

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ title: 'Evidence unavailable' });
  });
});