/** @jest-environment node */

import { NextRequest } from 'next/server';

const accessTokenFromRequest = jest.fn();
const createVoiceContributionSession = jest.fn();
const getVoiceContributionSession = jest.fn();
const getVoiceContributionTranscript = jest.fn();
const uploadVoiceContributionAudio = jest.fn();
const submitVoiceContributionCorrection = jest.fn();
const sendVoiceContribution = jest.fn();
const cancelVoiceContributionSession = jest.fn();
const voiceProblem = jest.fn(async () => ({ status: 503, body: { code: 'VOICE_UNAVAILABLE' } }));

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest }));
jest.mock('@/lib/api/voice', () => ({
  voiceProblem,
  createVoiceApi: jest.fn(() => ({
    createVoiceContributionSession,
    getVoiceContributionSession,
    getVoiceContributionTranscript,
    uploadVoiceContributionAudio,
    submitVoiceContributionCorrection,
    sendVoiceContribution,
    cancelVoiceContributionSession,
  })),
}));

const relationshipId = '5f33925b-fb0c-4366-8414-7f85309639b9';
const sessionId = '11111111-1111-4111-8111-111111111111';
const idempotencyKey = '22222222-2222-4222-8222-222222222222';
const params = { params: Promise.resolve({ relationshipId }) };

function request(body: unknown) {
  return new NextRequest(`http://localhost/api/voice/${relationshipId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

describe('voice server boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    accessTokenFromRequest.mockResolvedValue('server-token');
  });

  it('requires a secure server session for reads and writes', async () => {
    accessTokenFromRequest.mockResolvedValue(undefined);
    const route = await import('./[relationshipId]/route');
    const read = await route.GET(new NextRequest(`http://localhost/api/voice/${relationshipId}?sessionId=${sessionId}`), params);
    const write = await route.POST(request({ action: 'create', idempotencyKey, locale: 'en-IN' }), params);

    expect(read.status).toBe(401);
    expect(write.status).toBe(401);
    expect(createVoiceContributionSession).not.toHaveBeenCalled();
  });

  it('gets session and transcript with no-store responses', async () => {
    getVoiceContributionSession.mockResolvedValue({ state: 'CREATED' });
    getVoiceContributionTranscript.mockResolvedValue({ state: 'REVIEW_REQUIRED' });
    const { GET } = await import('./[relationshipId]/route');
    const session = await GET(new NextRequest(`http://localhost/api/voice/${relationshipId}?sessionId=${sessionId}`), params);
    const transcript = await GET(new NextRequest(`http://localhost/api/voice/${relationshipId}?sessionId=${sessionId}&resource=transcript`), params);

    expect(session.status).toBe(200);
    expect(transcript.status).toBe(200);
    expect(getVoiceContributionSession).toHaveBeenCalledWith({ relationshipId, sessionId });
    expect(getVoiceContributionTranscript).toHaveBeenCalledWith({ relationshipId, sessionId });
    expect(transcript.headers.get('Cache-Control')).toBe('no-store');
  });

  it('rejects a read without a session identity', async () => {
    const { GET } = await import('./[relationshipId]/route');
    const response = await GET(new NextRequest(`http://localhost/api/voice/${relationshipId}`), params);
    expect(response.status).toBe(400);
  });

  it('creates only a supported locale session', async () => {
    createVoiceContributionSession.mockResolvedValue({ sessionId });
    const { POST } = await import('./[relationshipId]/route');
    const response = await POST(request({ action: 'create', idempotencyKey, locale: 'hi-IN' }), params);

    expect(response.status).toBe(201);
    expect(createVoiceContributionSession).toHaveBeenCalledWith({
      relationshipId,
      idempotencyKey,
      createVoiceContributionSessionRequestV1: { schemaVersion: '1.0.0', locale: 'hi-IN' },
    });
    const invalid = await POST(request({ action: 'create', idempotencyKey, locale: 'fr-FR' }), params);
    expect(invalid.status).toBe(400);
  });

  it('uploads multipart audio without exposing an upstream location', async () => {
    uploadVoiceContributionAudio.mockResolvedValue({ state: 'TRANSCRIBING' });
    const form = new FormData();
    form.set('audio', new Blob(['voice'], { type: 'audio/webm' }), 'voice.webm');
    form.set('sessionId', sessionId);
    form.set('idempotencyKey', idempotencyKey);
    const { POST } = await import('./[relationshipId]/route');
    const response = await POST(new NextRequest(`http://localhost/api/voice/${relationshipId}`, { method: 'POST', body: form }), params);

    expect(response.status).toBe(202);
    expect(uploadVoiceContributionAudio).toHaveBeenCalledWith(expect.objectContaining({ relationshipId, sessionId, idempotencyKey, audio: expect.any(Blob) }));
  });

  it('forwards correction, explicit send, and cancellation through generated operations', async () => {
    submitVoiceContributionCorrection.mockResolvedValue({ version: 2 });
    sendVoiceContribution.mockResolvedValue({ state: 'RECORDED' });
    cancelVoiceContributionSession.mockResolvedValue({ state: 'CANCELLED' });
    const { POST } = await import('./[relationshipId]/route');

    expect((await POST(request({ action: 'correct', sessionId, idempotencyKey, expectedVersion: 1, correctedText: 'corrected' }), params)).status).toBe(200);
    expect((await POST(request({ action: 'send', sessionId, idempotencyKey, acceptedTranscriptVersion: 2 }), params)).status).toBe(200);
    expect((await POST(request({ action: 'cancel', sessionId, idempotencyKey }), params)).status).toBe(200);
    expect(sendVoiceContribution).toHaveBeenCalledWith(expect.objectContaining({
      sendVoiceContributionRequestV1: { schemaVersion: '1.0.0', acceptedTranscriptVersion: 2, explicitSend: true },
    }));
  });

  it('rejects malformed commands and forwards privacy-safe BP failures', async () => {
    const { POST, GET } = await import('./[relationshipId]/route');
    expect((await POST(request({ action: 'unknown', idempotencyKey }), params)).status).toBe(400);
    expect((await POST(request({ action: 'send', idempotencyKey, sessionId, acceptedTranscriptVersion: 'two' }), params)).status).toBe(400);
    getVoiceContributionSession.mockRejectedValue(new Error('private upstream'));
    const failed = await GET(new NextRequest(`http://localhost/api/voice/${relationshipId}?sessionId=${sessionId}`), params);
    expect(failed.status).toBe(503);
    expect(await failed.json()).toEqual({ code: 'VOICE_UNAVAILABLE' });
  });
});