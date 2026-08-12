/** @jest-environment node */

jest.mock('server-only', () => ({}));

import { ResponseError } from '@/lib/api/generated/runtime';
import { createVoiceApi, voiceProblem } from './voice';

describe('voice generated client wrapper', () => {
  it('creates the server-side generated API', () => {
    expect(createVoiceApi('server-token').constructor.name).toBe('VoiceContributionsApi');
  });

  it('preserves canonical BP problems and hides unexpected failures', async () => {
    const response = new Response(JSON.stringify({ code: 'stopped', title: 'stopped' }), { status: 423 });
    expect(await voiceProblem(new ResponseError(response, 'failed'))).toEqual({
      status: 423,
      body: { code: 'stopped', title: 'stopped' },
    });
    expect(await voiceProblem(new Error('secret'))).toEqual({
      status: 503,
      body: { code: 'VOICE_UNAVAILABLE', title: 'Voice contribution could not be completed.' },
    });
  });
});