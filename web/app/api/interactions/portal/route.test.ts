/** @jest-environment node */

import { NextRequest } from 'next/server';
import { GET, POST } from './route';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { createConversationApi } from '@/lib/api/conversation';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));
jest.mock('@/lib/api/conversation', () => ({ createConversationApi: jest.fn(), conversationProblem: jest.fn() }));

const mockAccessToken = jest.mocked(accessTokenFromRequest);
const mockCreateApi = jest.mocked(createConversationApi);

describe('portal interaction boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAccessToken.mockResolvedValue('server-token');
  });

  it('forwards only validated portal context through the authenticated generated client', async () => {
    const sendPortalInteractionMessage = jest.fn().mockResolvedValue({ scope: 'PORTAL' });
    mockCreateApi.mockReturnValue({ sendPortalInteractionMessage } as never);
    const response = await POST(
      new NextRequest('http://localhost/api/interactions/portal', {
        method: 'POST',
        body: JSON.stringify({
          idempotencyKey: 'key-1',
          clientMessageId: 'message-1',
          text: 'Show agents',
          locale: 'en-IN',
          currentSurface: 'MY_AGENTS',
        }),
      })
    );

    expect(response.status).toBe(200);
    expect(mockCreateApi).toHaveBeenCalledWith('server-token');
    expect(sendPortalInteractionMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        idempotencyKey: 'key-1',
        sendPortalInteractionMessageRequestV1: expect.objectContaining({ currentSurface: 'MY_AGENTS' }),
      })
    );
  });

  it('fails closed without a session or with a browser-invented surface', async () => {
    mockAccessToken.mockResolvedValueOnce(undefined);
    expect((await GET(new NextRequest('http://localhost/api/interactions/portal'))).status).toBe(401);
    mockAccessToken.mockResolvedValueOnce('server-token');
    const invalid = await POST(
      new NextRequest('http://localhost/api/interactions/portal', {
        method: 'POST',
        body: JSON.stringify({
          idempotencyKey: 'key-1',
          clientMessageId: 'message-1',
          text: 'Do work',
          locale: 'en-IN',
          currentSurface: 'ADMIN',
        }),
      })
    );
    expect(invalid.status).toBe(400);
    expect(mockCreateApi).not.toHaveBeenCalled();
  });
});
