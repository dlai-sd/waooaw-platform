/** @jest-environment node */

import { NextRequest } from 'next/server';

const accessTokenFromRequest = jest.fn();
jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest }));

const relationshipId = '5f33925b-fb0c-4366-8414-7f85309639b9';
const command = {
  schemaVersion: '1.0', expectedWorkspaceVersion: 'relationship-2', expectedSubjectVersion: 'skill-4',
  payload: { commandKind: 'ACCEPT_SKILL', configurationId: '8aa7370d-b226-459e-9c86-2dbbe4705aa8', skillId: 'local-seo', skillVersion: '1.0.0' },
};

async function submit(body: object) {
  const { POST } = await import('./relationships/[relationshipId]/skill-decisions/route');
  return POST(new NextRequest('http://localhost/api/relationships/current/skill-decisions', {
    method: 'POST', body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' },
  }), { params: Promise.resolve({ relationshipId }) });
}

describe('relationship skill decision proxy', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    accessTokenFromRequest.mockResolvedValue('server-token');
  });

  afterEach(() => jest.restoreAllMocks());

  it('forwards the exact relationship command and idempotency key server-side', async () => {
    const fetchMock = jest.spyOn(global, 'fetch').mockResolvedValue(new Response(JSON.stringify({ commandId: 'command-1' }), { status: 202 }));

    const response = await submit({ idempotencyKey: 'key-1', command });

    expect(response.status).toBe(202);
    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:5001/api/v1/employment/relationships/${relationshipId}/workspace/commands`,
      expect.objectContaining({ method: 'POST', body: JSON.stringify(command), cache: 'no-store' }),
    );
    const headers = new Headers(fetchMock.mock.calls[0][1]?.headers);
    expect(headers.get('Authorization')).toBe('Bearer server-token');
    expect(headers.get('Idempotency-Key')).toBe('key-1');
  });

  it('fails closed without a session or complete command envelope', async () => {
    const fetchMock = jest.spyOn(global, 'fetch');
    accessTokenFromRequest.mockResolvedValue(undefined);
    expect((await submit({ idempotencyKey: 'key-1', command })).status).toBe(401);
    accessTokenFromRequest.mockResolvedValue('server-token');
    expect((await submit({ command })).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});