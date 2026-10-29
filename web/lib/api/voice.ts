import 'server-only';
import { correlateFailureBody, logServerFailure, readServerResponse } from '@/lib/server-failure';

// Implements: architecture/reference/components/wc062-voice-solution-contract.md
// Constitutional basis: C-026, C-042, C-059, C-063

import { VoiceContributionsApi } from '@/lib/api/generated/apis/VoiceContributionsApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export function createVoiceApi(accessToken: string): VoiceContributionsApi {
  return new VoiceContributionsApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
}

export async function voiceProblem(error: unknown): Promise<{ status: number; body: unknown }> {
  const correlationId = logServerFailure('web.voice.request_failed', error);
  if (error instanceof ResponseError) {
    const body = await readServerResponse(error.response, 'web.api.voice.response_invalid', undefined);
    return {
      status: error.response.status,
      body:
        error.response.status >= 500
          ? correlateFailureBody(
              body ?? {
                code: 'VOICE_UNAVAILABLE',
                title: 'Voice contribution could not be completed.',
              },
              correlationId
            )
          : (body ?? {
              code: 'VOICE_UNAVAILABLE',
              title: 'Voice contribution could not be completed.',
            }),
    };
  }
  return {
    status: 503,
    body: {
      code: 'VOICE_UNAVAILABLE',
      title: 'Voice contribution could not be completed.',
      correlationId,
    },
  };
}
