/** @jest-environment node */

import { NextRequest } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));

const relationshipId = '77699132-98cf-4cb2-b53d-6a2e1f0c7f92';
const params = { params: Promise.resolve({ relationshipId }) };

function request() {
  return new NextRequest(`http://localhost/api/relationships/${relationshipId}/hire-setup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': 'setup-key' },
    body: JSON.stringify({ businessName: 'North Star Dental' }),
  });
}

describe('Hire setup proxy', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.restoreAllMocks();
  });

  it('rejects a request without a secure session', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue(undefined);
    const { POST } = await import('./route');

    expect((await POST(request(), params)).status).toBe(401);
  });

  it('forwards the server access token and idempotency key', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue('access-token');
    const fetchMock = jest.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ contractId: 'contract-1' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
    const { POST } = await import('./route');

    const response = await POST(request(), params);

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/api/v1/employment/relationships/${relationshipId}/hire-setup`),
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer access-token',
          'Idempotency-Key': 'setup-key',
        }),
      })
    );
  });
});