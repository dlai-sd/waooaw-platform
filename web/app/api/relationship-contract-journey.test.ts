/** @jest-environment node */

import { NextRequest } from 'next/server';

const accessTokenFromRequest = jest.fn();
jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest }));

const relationshipId = '5f33925b-fb0c-4366-8414-7f85309639b9';
const checkoutIntentId = '7bc5b28a-a674-4c77-b3e0-7da0f8bf1e50';
const params = { params: Promise.resolve({ relationshipId }) };

describe('relationship contract journey proxy', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    accessTokenFromRequest.mockResolvedValue('server-token');
  });

  afterEach(() => jest.restoreAllMocks());

  it('reconciles one exact checkout intent through the authenticated BP read', async () => {
    const fetchMock = jest.spyOn(global, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      outcomeKind: 'CAPTURED', checkoutIntentId,
    }), { status: 200 }));
    const { GET } = await import('./relationships/[relationshipId]/contract-journey/route');

    const response = await GET(new NextRequest(
      `http://localhost/api/relationships/${relationshipId}/contract-journey?checkoutIntentId=${checkoutIntentId}`,
    ), params);

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:5001/api/v1/employment/relationships/${relationshipId}/checkout-intents/${checkoutIntentId}`,
      expect.objectContaining({ cache: 'no-store' }),
    );
    const headers = new Headers(fetchMock.mock.calls[0][1]?.headers);
    expect(headers.get('Authorization')).toBe('Bearer server-token');
    expect(response.headers.get('Cache-Control')).toBe('no-store');
  });

  it('fails closed without a session or checkout intent identity', async () => {
    const fetchMock = jest.spyOn(global, 'fetch');
    const { GET } = await import('./relationships/[relationshipId]/contract-journey/route');
    accessTokenFromRequest.mockResolvedValue(undefined);
    expect((await GET(new NextRequest('http://localhost/'), params)).status).toBe(401);
    accessTokenFromRequest.mockResolvedValue('server-token');
    expect((await GET(new NextRequest('http://localhost/'), params)).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});