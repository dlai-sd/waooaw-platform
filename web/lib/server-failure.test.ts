/** @jest-environment node */

import { logServerFailure, readServerResponse, serverFailureContext } from './server-failure';
import { readRequestJson, withServerFailureBoundary } from './server-failure-boundary';

const originalDetail = process.env.WAOOAW_DIAGNOSTIC_DETAIL;

function records(): Record<string, unknown>[] {
  return jest.mocked(console.error).mock.calls.map(([record]) => JSON.parse(record));
}

describe('safe server failures', () => {
  beforeEach(() => {
    jest.spyOn(console, 'error').mockImplementation();
    Reflect.deleteProperty(process.env, 'WAOOAW_DIAGNOSTIC_DETAIL');
  });
  afterEach(() => {
    if (originalDetail === undefined) Reflect.deleteProperty(process.env, 'WAOOAW_DIAGNOSTIC_DETAIL');
    else process.env.WAOOAW_DIAGNOSTIC_DETAIL = originalDetail;
    jest.restoreAllMocks();
  });

  it.each(['true', 'false', undefined, 'TRUE'])('redacts arbitrary data with detail=%s', (detail) => {
    if (detail !== undefined) process.env.WAOOAW_DIAGNOSTIC_DETAIL = detail;
    const secret = 'customer@example.com Bearer private-token redis://user:password@host/0?access_token=secret';
    const cause = Object.assign(new Error(secret), { code: 'ECONNREFUSED' });
    const error = new Error(secret, { cause });
    error.name = secret;
    error.stack = `${secret}\n    at privateFunction (/app/.next/server/app/route.js:42:9)\n    at ${secret}`;
    const correlationId = logServerFailure('web.test.failed', error);

    expect(correlationId).toMatch(/^[a-f0-9-]{36}$/);
    expect(JSON.stringify(records())).not.toMatch(/customer|private-token|password|access_token|privateFunction/);
    expect(records()[0]).toMatchObject({
      event: 'web.test.failed',
      correlationId,
      error: { type: 'Error' },
    });
    const diagnostics = records()[0].error;
    if (detail === 'true') {
      expect(diagnostics).toMatchObject({
        message: '[REDACTED]',
        locations: [{ file: 'route.js', line: 42, column: 9 }],
        cause: { type: 'Error', code: 'ECONNREFUSED' },
      });
    } else {
      expect(diagnostics).not.toHaveProperty('message');
      expect(diagnostics).not.toHaveProperty('locations');
      expect(diagnostics).not.toHaveProperty('cause');
    }
  });

  it('bounds cycles and rejects untrusted identifiers and codes', () => {
    process.env.WAOOAW_DIAGNOSTIC_DETAIL = 'true';
    const error = Object.assign(new Error('secret'), {
      code: 'secret-code',
      cause: undefined as unknown,
    });
    error.cause = error;
    logServerFailure('secret\ninjected', error, {
      correlationId: 'secret\ninjected',
    });
    expect(records()[0]).toMatchObject({
      event: 'web.server.failure',
      error: { type: 'Error', cause: { type: 'TruncatedError' } },
    });
    expect(JSON.stringify(records())).not.toContain('secret');
    logServerFailure('web.test.unknown', { payload: 'private' });
    expect(records()[1].error).toEqual({ type: 'UnknownError' });
  });

  it('uses the request correlation in preference to untrusted upstream data', () => {
    serverFailureContext.run({ correlationId: 'request-123', logged: false }, () => {
      expect(
        logServerFailure('web.test.failed', new Error(), {
          correlationId: 'backend-456',
        })
      ).toBe('request-123');
    });
  });

  it('links upstream failures without copying their private problem body', async () => {
    const body = await readServerResponse(
      Response.json({ correlationId: 'upstream-123', detail: 'private problem' }, { status: 503 }),
      'web.test.upstream_failed'
    );
    expect(records()[0]).toMatchObject({ status: 503, upstreamCorrelationId: 'upstream-123' });
    expect(JSON.stringify(records())).not.toContain('private problem');
    expect(body).toMatchObject({ correlationId: records()[0].correlationId });
  });

  it('logs a malformed upstream failure and retains its failure status correlation', async () => {
    const response = new Response('private response', { status: 502 });
    const body = await readServerResponse(response, 'web.test.upstream_invalid', { title: 'Unavailable' });
    expect(body).toEqual({
      title: 'Unavailable',
      correlationId: records()[0].correlationId,
    });
    expect(JSON.stringify(records())).not.toContain('private response');
  });

  it('does not turn a malformed upstream success into a successful fallback', async () => {
    await expect(readServerResponse(new Response('invalid'), 'web.test.upstream_invalid')).rejects.toThrow();
    expect(records()).toHaveLength(1);
  });

  it('lets error mappers retain their canonical fallback when upstream JSON is unreadable', async () => {
    expect(
      await readServerResponse(new Response('invalid', { status: 503 }), 'web.test.upstream_invalid')
    ).toBeUndefined();
    expect(records()).toHaveLength(1);
  });

  it('silently rejects malformed request JSON without treating upstream SyntaxErrors as user input', async () => {
    const handler = withServerFailureBoundary('web.test.route_failed', async () => {
      await readRequestJson(new Request('https://web.example', { method: 'POST', body: 'invalid' }));
      return Response.json({});
    });
    expect((await handler()).status).toBe(400);
    expect(records()).toEqual([]);
    const upstream = withServerFailureBoundary('web.test.route_failed', async () => {
      throw new SyntaxError('private upstream response');
    });
    expect((await upstream()).status).toBe(503);
    expect(records()).toHaveLength(1);
  });

  it('logs non-syntax request body failures rather than silently rejecting them', async () => {
    const request = new Request('https://web.example', { method: 'POST', body: '{}' });
    jest.spyOn(request, 'json').mockRejectedValue(new Error('private transport failure'));
    await expect(readRequestJson(request)).rejects.toThrow('private transport failure');
    expect(records()[0].event).toBe('web.request.body_read_failed');
  });

  it('preserves expected upstream rejection and logs an unreadable rejection', async () => {
    expect(
      await readServerResponse(new Response('invalid', { status: 409 }), 'web.test.upstream_invalid', {
        code: 'CONFLICT',
      })
    ).toEqual({ code: 'CONFLICT' });
    expect(records()).toHaveLength(1);
  });

  it('returns a logged correlation for uncaught transport failures without leaking detail', async () => {
    const response = await withServerFailureBoundary('web.test.route_failed', async () => {
      throw new Error('Bearer private-token');
    })();
    const body = await response.json();
    expect(response.status).toBe(503);
    expect(body.correlationId).toBe(records()[0].correlationId);
    expect(response.headers.get('x-correlation-id')).toBe(body.correlationId);
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(JSON.stringify(body)).not.toContain('private-token');
    expect(records()).toHaveLength(1);
  });

  it.each([500, 502, 503, 504])('correlates an explicit %s without duplicate logging', async (status) => {
    const response = await withServerFailureBoundary('web.test.route_failed', async () => {
      logServerFailure('web.test.dependency_failed', new Error('private'));
      return Response.json({ code: 'UNAVAILABLE' }, { status, headers: { 'Retry-After': '10' } });
    })();
    expect(response.status).toBe(status);
    expect(response.headers.get('retry-after')).toBe('10');
    expect(await response.json()).toEqual({
      code: 'UNAVAILABLE',
      correlationId: records()[0].correlationId,
    });
    expect(records()).toHaveLength(1);
  });

  it('logs an explicit failure without an inner catch and handles non-JSON failures', async () => {
    const response = await withServerFailureBoundary(
      'web.test.route_failed',
      async () => new Response('private text', { status: 502 })
    )();
    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      title: 'Request could not be completed.',
      correlationId: records()[0].correlationId,
    });
    expect(records()).toHaveLength(2);
  });

  it.each([200, 202, 204, 400, 401, 403, 409])('preserves status %s without failure logging', async (status) => {
    const original = new Response(null, { status });
    const response = await withServerFailureBoundary('web.test.route_failed', async () => original)();
    expect(response).toBe(original);
    expect(records()).toEqual([]);
  });

  it('isolates correlations across concurrent requests', async () => {
    const handler = withServerFailureBoundary('web.test.route_failed', async (wait: boolean) => {
      if (wait) await new Promise((resolve) => setImmediate(resolve));
      logServerFailure('web.test.dependency_failed', new Error());
      return Response.json({}, { status: 503 });
    });
    const responses = await Promise.all([handler(true), handler(false)]);
    const ids = await Promise.all(responses.map(async (response) => (await response.json()).correlationId));
    expect(new Set(ids).size).toBe(2);
    expect(
      records()
        .map((record) => record.correlationId)
        .sort()
    ).toEqual(ids.sort());
  });
});
