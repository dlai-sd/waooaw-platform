/** @jest-environment node */

import { describePortalFailure } from './portal-failure';
import { FetchError, ResponseError } from './generated/runtime';

jest.mock('server-only', () => ({}));

describe('portal failure diagnostics', () => {
  beforeEach(() => jest.spyOn(console, 'error').mockImplementation());
  afterEach(() => jest.restoreAllMocks());

  it('retains a safe backend correlation without logging response data', async () => {
    const response = new Response(JSON.stringify({ correlationId: 'abc-123', detail: 'private detail' }), {
      status: 503,
      headers: { 'content-type': 'application/json' },
    });

    await expect(describePortalFailure(new ResponseError(response), 'MARKETPLACE')).resolves.toEqual({
      correlationId: 'abc-123',
      reasonCode: 'SERVICE_UNAVAILABLE',
      statusClass: '5xx',
    });
    expect(console.error).toHaveBeenCalledWith('Portal projection failed.', {
      correlationId: 'abc-123',
      reasonCode: 'SERVICE_UNAVAILABLE',
      statusClass: '5xx',
      surface: 'MARKETPLACE',
    });
    expect(JSON.stringify(jest.mocked(console.error).mock.calls)).not.toContain('private detail');
  });

  it('classifies transport failure without exposing its message', async () => {
    const failure = await describePortalFailure(new FetchError(new Error('customer data')), 'MY_AGENTS');

    expect(failure.reasonCode).toBe('SERVICE_UNREACHABLE');
    expect(failure.statusClass).toBe('none');
    expect(JSON.stringify(jest.mocked(console.error).mock.calls)).not.toContain('customer data');
  });
});