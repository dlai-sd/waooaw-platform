/** @jest-environment node */

// Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R005, WC170-R006

import { NextRequest } from 'next/server';

const accessTokenFromRequest = jest.fn();
jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest }));

const relationshipId = '5f33925b-fb0c-4366-8414-7f85309639b9';
const artifactId = '8aa7370d-b226-459e-9c86-2dbbe4705aa8';
const digest = 'b'.repeat(64);
const commandId = 'c3a3a1b0-8d3f-4a43-9c5b-0d2f0f5f4e11';
const commandContext = { workspaceVersion: 'workspace-3', manifestVersion: 'manifest-1', decisionSpaceVersion: 4 };

async function read(id = relationshipId) {
  const { GET } = await import('./[relationshipId]/real-work/route');
  return GET(new NextRequest(`http://localhost/api/relationships/${id}/real-work`), {
    params: Promise.resolve({ relationshipId: id }),
  });
}

async function decide(body: object) {
  const { POST } = await import('./[relationshipId]/real-work/route');
  return POST(
    new NextRequest(`http://localhost/api/relationships/${relationshipId}/real-work`, {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    }),
    { params: Promise.resolve({ relationshipId }) }
  );
}

describe('real work proxy', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    accessTokenFromRequest.mockResolvedValue('server-token');
  });

  afterEach(() => jest.restoreAllMocks());

  it('requires a signed-in customer and a real relationship id', async () => {
    accessTokenFromRequest.mockResolvedValueOnce(null);
    expect((await read()).status).toBe(401);
    expect((await read('not-a-uuid')).status).toBe(404);
    accessTokenFromRequest.mockResolvedValueOnce(null);
    expect((await decide({})).status).toBe(401);
  });

  it('reads artifacts, timeline and outcomes together and tolerates one being unavailable', async () => {
    const fetchMock = jest.spyOn(global, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/timeline')) return new Response('{}', { status: 503 });
      return new Response(JSON.stringify({ from: url.split('/').pop() }), { status: 200 });
    });

    const response = await read();

    expect(await response.json()).toEqual({
      artifacts: { from: 'artifacts' },
      timeline: null,
      outcomes: { from: 'outcomes' },
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      `/api/v1/employment/relationships/${relationshipId}/real-work/`
    );
  });

  it('turns an approval into the one closed command that quotes back the exact artifact id and digest', async () => {
    const fetchMock = jest
      .spyOn(global, 'fetch')
      .mockResolvedValue(new Response(JSON.stringify({ commandId: 'command-1', state: 'ACCEPTED' }), { status: 202 }));

    const response = await decide({
      idempotencyKey: commandId,
      kind: 'ACCEPT_ARTIFACT_VERSION',
      artifactId,
      artifactDigest: digest,
      commandContext,
    });

    expect(response.status).toBe(202);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe(
      `http://localhost:5001/api/v1/employment/relationships/${relationshipId}/workspace/employment/commands`
    );
    const command = JSON.parse(String(init?.body));
    expect(command).toEqual({
      schemaVersion: '1.0',
      kind: 'ACCEPT_ARTIFACT_VERSION',
      subjectRef: artifactId,
      expectedWorkspaceVersion: 'workspace-3',
      expectedManifestVersion: 'manifest-1',
      expectedArtifactId: artifactId,
      expectedArtifactDigest: digest,
      acknowledgement: 'I approve this exact version.',
    });
    const headers = new Headers(init?.headers);
    expect(headers.get('Authorization')).toBe('Bearer server-token');
    expect(headers.get('Idempotency-Key')).toBe(commandId);
  });

  it('adds the decision space version only to the scope confirmation', async () => {
    const fetchMock = jest.spyOn(global, 'fetch').mockResolvedValue(new Response('{}', { status: 202 }));

    await decide({
      idempotencyKey: commandId,
      kind: 'CONFIRM_SCOPE_BOUNDARY',
      artifactId,
      artifactDigest: digest,
      commandContext,
    });

    const command = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(command.kind).toBe('CONFIRM_SCOPE_BOUNDARY');
    expect(command.expectedDecisionSpaceVersion).toBe(4);
  });

  it.each([
    ['an unknown command kind', { kind: 'ACCEPT_PLAN_VERSION' }],
    ['a bad artifact id', { artifactId: 'x' }],
    ['a bad digest', { artifactDigest: 'abc' }],
    ['no idempotency key', { idempotencyKey: undefined }],
    ['no command context', { commandContext: undefined }],
  ])('refuses %s before anything is sent', async (_name, change) => {
    const fetchMock = jest.spyOn(global, 'fetch');

    const response = await decide({
      idempotencyKey: commandId,
      kind: 'ACCEPT_ARTIFACT_VERSION',
      artifactId,
      artifactDigest: digest,
      commandContext,
      ...change,
    });

    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
