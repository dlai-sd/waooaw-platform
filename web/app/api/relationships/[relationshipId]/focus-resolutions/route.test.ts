/** @jest-environment node */

import { NextRequest } from 'next/server';
import { RelationshipWorkspaceApi } from '@/lib/api/generated/apis/RelationshipWorkspaceApi';
import { accessTokenFromRequest } from '@/lib/server-auth';

const resolveFocus = jest.fn();

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));
jest.mock('@/lib/api/generated/apis/RelationshipWorkspaceApi', () => ({
  RelationshipWorkspaceApi: jest.fn().mockImplementation(() => ({
    resolveWorkspaceFocus: resolveFocus,
  })),
}));

const relationshipId = '00000000-0000-0000-0000-000000000121';
const params = { params: Promise.resolve({ relationshipId }) };

function request(body: string) {
  return new NextRequest(`http://localhost/api/relationships/${relationshipId}/focus-resolutions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  });
}

describe('focus resolution proxy', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('requires a secure session', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue(undefined);
    const { POST } = await import('./route');

    expect((await POST(request('{}'), params)).status).toBe(401);
  });

  it('rejects malformed focus input', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue('access-token');
    const { POST } = await import('./route');

    expect((await POST(request('not-json'), params)).status).toBe(400);
  });

  it('resolves focus through the authenticated canonical client', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue('access-token');
    resolveFocus.mockResolvedValue({
      relationshipId,
      destination: 'OPERATION',
      canonicalRoute: `/relationships/${relationshipId}#operations`,
    });
    const { POST } = await import('./route');

    const response = await POST(request(JSON.stringify({ focusToken: 'protected-token' })), params);

    expect(response.status).toBe(200);
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    expect(RelationshipWorkspaceApi).toHaveBeenCalledTimes(1);
    expect(resolveFocus).toHaveBeenCalledWith(
      {
        relationshipId,
        resolveWorkspaceFocusRequestV1: { focusToken: 'protected-token' },
      },
      { cache: 'no-store' }
    );
  });
});
