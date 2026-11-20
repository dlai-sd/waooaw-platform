// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { fakeResponse } from '@/components/workbench/workbench-test-data';
import { problemText, readWorkbench, sendWorkbenchCommand } from './workbench-client';
import { labelFor, plainWords, workbenchMessages } from './workbench-i18n';

const copy = workbenchMessages('en');

describe('workbench browser client', () => {
  afterEach(() => jest.restoreAllMocks());

  it('reads through the same-origin route and exposes the version from the ETag', async () => {
    const fetchMock = jest.fn(async () => fakeResponse(200, { ok: true }, { etag: 'W/"relationship-9"' }));
    global.fetch = fetchMock as unknown as typeof fetch;
    const result = await readWorkbench<{ ok: boolean }>('rel-1', '/goals');
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/relationships/rel-1/workbench/goals',
      expect.objectContaining({ method: 'GET', cache: 'no-store', credentials: 'same-origin' })
    );
    expect(result).toMatchObject({ ok: true, status: 200, version: 'relationship-9', data: { ok: true } });
  });

  it('sends a distinct idempotency key and correlation id per command', async () => {
    const fetchMock = jest.fn(async () => fakeResponse(200, {}));
    global.fetch = fetchMock as unknown as typeof fetch;
    await sendWorkbenchCommand(
      'rel-1',
      '/controls/pause',
      { schemaVersion: '1.0' },
      '11111111-1111-4111-8111-111111111111'
    );
    const init = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
    const headers = init.headers as Record<string, string>;
    expect(init.method).toBe('POST');
    expect(headers['Idempotency-Key']).toBe('11111111-1111-4111-8111-111111111111');
    expect(headers['X-Correlation-ID']).toMatch(/^[0-9a-f-]{36}$/);
    expect(init.body).toBe('{"schemaVersion":"1.0"}');
  });

  it('turns a problem response into a typed failure and detects the strong sign-in requirement', async () => {
    global.fetch = jest.fn(async () =>
      fakeResponse(403, {
        code: 'WORKBENCH_REQUEST_INVALID',
        detail: 'A fresh strong sign-in is required for this action.',
      })
    ) as unknown as typeof fetch;
    const result = await sendWorkbenchCommand('rel-1', '/topups', {});
    expect(result).toMatchObject({ ok: false, status: 403, strongAuthRequired: true });
    if (!result.ok) expect(problemText(copy, result)).toBe(copy.strongAuth);
  });

  it('reports a network failure and an unreadable body as unavailable', async () => {
    global.fetch = jest.fn(async () => {
      throw new TypeError('offline');
    }) as unknown as typeof fetch;
    const offline = await readWorkbench('rel-1');
    expect(offline).toMatchObject({ ok: false, status: 0, problem: { code: 'WORKBENCH_UNAVAILABLE' } });

    global.fetch = jest.fn(async () => ({
      ok: false,
      status: 500,
      headers: { get: () => null },
      json: async () => {
        throw new SyntaxError('bad');
      },
    })) as unknown as typeof fetch;
    const unreadable = await readWorkbench('rel-1');
    expect(unreadable).toMatchObject({ ok: false, status: 500, strongAuthRequired: false });
    if (!unreadable.ok) expect(problemText(copy, unreadable)).toBe(copy.problems.WORKBENCH_UNAVAILABLE);
  });

  it('maps a known problem code to plain customer words', () => {
    expect(problemText(copy, { problem: { code: 'WORKBENCH_VERSION_CONFLICT' }, strongAuthRequired: false })).toBe(
      copy.problems.WORKBENCH_VERSION_CONFLICT
    );
    expect(problemText(copy, { problem: { code: 'NOT_A_REAL_CODE' }, strongAuthRequired: false })).toBe(
      copy.problems.WORKBENCH_UNAVAILABLE
    );
  });
});

describe('workbench vocabulary', () => {
  it('never shows a raw identifier', () => {
    expect(plainWords('WAITING_ON_CUSTOMER')).toBe('Waiting on customer');
    expect(plainWords('a-b_c')).toBe('A b c');
    expect(plainWords('')).toBe('');
    expect(labelFor(copy.states, 'IN_PROGRESS')).toBe('In progress');
    expect(labelFor(copy.states, 'SOMETHING_NEW')).toBe('Something new');
  });

  it('falls back to English for a locale without a catalog and overrides Hindi keys', () => {
    expect(workbenchMessages('ta')).toBe(workbenchMessages('en'));
    expect(workbenchMessages('hi').toolsLabel).not.toBe(copy.toolsLabel);
    expect(workbenchMessages('hi').stop).toBeTruthy();
  });

  it('carries a message for every problem code the workbench can return', () => {
    for (const code of [
      'WORKBENCH_DISABLED',
      'WORKBENCH_REQUEST_INVALID',
      'WORKBENCH_VERSION_CONFLICT',
      'WORKBENCH_IDEMPOTENCY_CONFLICT',
      'WORKBENCH_UNAVAILABLE',
      'SPEND_COMMERCIAL_UNAVAILABLE',
      'WALLET_INSUFFICIENT',
    ]) {
      expect(copy.problems[code]).toBeTruthy();
    }
  });
});
