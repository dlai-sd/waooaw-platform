// Implements: architecture/reference/components/wc062-voice-solution-contract.md
// Constitutional basis: C-023, C-026, C-042, C-059, C-063

import { NextRequest, NextResponse } from 'next/server';
import { createVoiceApi, voiceProblem } from '@/lib/api/voice';
import {
  CreateVoiceContributionSessionRequestV1LocaleEnum,
  type CreateVoiceContributionSessionRequestV1LocaleEnum as VoiceLocale,
} from '@/lib/api/generated/models/CreateVoiceContributionSessionRequestV1';
import { accessTokenFromRequest } from '@/lib/server-auth';

type CommandBody = Record<string, unknown> & { action?: unknown };

class InvalidVoiceRequest extends Error {}

function requiredString(body: CommandBody, name: string): string {
  const value = body[name];
  if (typeof value !== 'string' || value.length === 0) throw new InvalidVoiceRequest();
  return value;
}

function requiredInteger(body: CommandBody, name: string): number {
  const value = body[name];
  if (typeof value !== 'number' || !Number.isInteger(value)) throw new InvalidVoiceRequest();
  return value;
}

function requiredLocale(body: CommandBody): VoiceLocale {
  const value = requiredString(body, 'locale');
  const supported = Object.values(CreateVoiceContributionSessionRequestV1LocaleEnum);
  if (!supported.includes(value as VoiceLocale)) throw new InvalidVoiceRequest();
  return value as VoiceLocale;
}

function sessionRequired() {
  return NextResponse.json({ code: 'VOICE_SESSION_REQUIRED', title: 'Secure sign in is required.' }, { status: 401 });
}

function invalidRequest() {
  return NextResponse.json({ code: 'VOICE_REQUEST_INVALID', title: 'Voice contribution request is invalid.' }, { status: 400 });
}

export async function GET(request: NextRequest, { params }: { params: { relationshipId: string } }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return sessionRequired();
  const sessionId = request.nextUrl.searchParams.get('sessionId');
  if (!sessionId) return invalidRequest();
  try {
    const api = createVoiceApi(accessToken);
    const result = request.nextUrl.searchParams.get('resource') === 'transcript'
      ? await api.getVoiceContributionTranscript({ relationshipId: params.relationshipId, sessionId })
      : await api.getVoiceContributionSession({ relationshipId: params.relationshipId, sessionId });
    return NextResponse.json(result, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    const problem = await voiceProblem(error);
    return NextResponse.json(problem.body, { status: problem.status, headers: { 'Cache-Control': 'no-store' } });
  }
}

export async function POST(request: NextRequest, { params }: { params: { relationshipId: string } }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return sessionRequired();
  try {
    const api = createVoiceApi(accessToken);
    if (request.headers.get('content-type')?.startsWith('multipart/form-data')) {
      const form = await request.formData();
      const audio = form.get('audio');
      if (!(audio instanceof Blob)) throw new InvalidVoiceRequest();
      return NextResponse.json(await api.uploadVoiceContributionAudio({
        relationshipId: params.relationshipId,
        sessionId: requiredString(Object.fromEntries(form), 'sessionId'),
        idempotencyKey: requiredString(Object.fromEntries(form), 'idempotencyKey'),
        audio,
      }), { status: 202 });
    }

    const body = await request.json() as CommandBody;
    const action = requiredString(body, 'action');
    const idempotencyKey = requiredString(body, 'idempotencyKey');
    switch (action) {
      case 'create':
        return NextResponse.json(await api.createVoiceContributionSession({
          relationshipId: params.relationshipId,
          idempotencyKey,
          createVoiceContributionSessionRequestV1: { schemaVersion: '1.0.0', locale: requiredLocale(body) },
        }), { status: 201 });
      case 'correct':
        return NextResponse.json(await api.submitVoiceContributionCorrection({
          relationshipId: params.relationshipId,
          sessionId: requiredString(body, 'sessionId'),
          idempotencyKey,
          voiceCorrectionRequestV1: { schemaVersion: '1.0.0', expectedVersion: requiredInteger(body, 'expectedVersion'), correctedText: requiredString(body, 'correctedText') },
        }));
      case 'send':
        return NextResponse.json(await api.sendVoiceContribution({
          relationshipId: params.relationshipId,
          sessionId: requiredString(body, 'sessionId'),
          idempotencyKey,
          sendVoiceContributionRequestV1: { schemaVersion: '1.0.0', acceptedTranscriptVersion: requiredInteger(body, 'acceptedTranscriptVersion'), explicitSend: true },
        }));
      case 'cancel':
        return NextResponse.json(await api.cancelVoiceContributionSession({
          relationshipId: params.relationshipId,
          sessionId: requiredString(body, 'sessionId'),
          idempotencyKey,
          cancelVoiceContributionRequestV1: { schemaVersion: '1.0.0' },
        }));
      default:
        throw new InvalidVoiceRequest();
    }
  } catch (error) {
    if (error instanceof InvalidVoiceRequest || error instanceof SyntaxError) return invalidRequest();
    const problem = await voiceProblem(error);
    return NextResponse.json(problem.body, { status: problem.status, headers: { 'Cache-Control': 'no-store' } });
  }
}