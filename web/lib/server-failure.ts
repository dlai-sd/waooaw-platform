import 'server-only';

// Implements: work-contracts/WC-126-web-server-failure-logging.md §Requirements And Definition Of Done
// Constitutional basis: C-023, C-059, C-063

import { AsyncLocalStorage } from 'node:async_hooks';
import { randomUUID } from 'node:crypto';
import { trace } from '@opentelemetry/api';

type FailureContext = { correlationId: string; logged: boolean };
export const serverFailureContext = new AsyncLocalStorage<FailureContext>();

const safeId = /^[a-zA-Z0-9-]{1,64}$/;
const errorNames = new Set([
  'Error',
  'TypeError',
  'SyntaxError',
  'RangeError',
  'ReferenceError',
  'AggregateError',
  'AbortError',
  'TimeoutError',
  'ResponseError',
  'FetchError',
]);
const errorCodes = new Set([
  'ECONNREFUSED',
  'ECONNRESET',
  'ECONNABORTED',
  'ENOTFOUND',
  'EAI_AGAIN',
  'ETIMEDOUT',
  'EPIPE',
  'UND_ERR_CONNECT_TIMEOUT',
  'UND_ERR_HEADERS_TIMEOUT',
  'UND_ERR_SOCKET',
  'CERT_HAS_EXPIRED',
  'ERR_TLS_CERT_ALTNAME_INVALID',
  'DEPTH_ZERO_SELF_SIGNED_CERT',
  'ERR_INVALID_URL',
  'ENOENT',
  'EACCES',
  'EMFILE',
  'ENOSPC',
]);
const safeReasons = new Map([
  ['Readiness configuration is incomplete', 'READINESS_CONFIGURATION_INCOMPLETE'],
  ['Session readiness configuration is incomplete', 'SESSION_CONFIGURATION_INCOMPLETE'],
  ['Redis command timed out', 'REDIS_TIMEOUT'],
  ['REDIS_URL is required', 'REDIS_CONFIGURATION_MISSING'],
  ['REDIS_URL must use redis or rediss', 'REDIS_PROTOCOL_INVALID'],
  ['REDIS_URL database is invalid', 'REDIS_DATABASE_INVALID'],
  ['Redis password configuration is invalid', 'REDIS_AUTH_CONFIGURATION_INVALID'],
  ['Redis returned an unsupported response', 'REDIS_RESPONSE_INVALID'],
  ['fetch failed', 'FETCH_FAILED'],
]);

export function failureCorrelationId(candidate?: unknown): string {
  return (
    serverFailureContext.getStore()?.correlationId ??
    (typeof candidate === 'string' && safeId.test(candidate) ? candidate : randomUUID())
  );
}

function diagnostics(error: unknown, detail: boolean, seen = new Set<unknown>()): Record<string, unknown> {
  if (!(error instanceof Error)) return { type: 'UnknownError' };
  if (seen.has(error) || seen.size >= 4) return { type: 'TruncatedError' };
  seen.add(error);
  const code = 'code' in error && typeof error.code === 'string' && errorCodes.has(error.code) ? error.code : undefined;
  const type = errorNames.has(error.name) ? error.name : 'Error';
  const reason = safeReasons.get(error.message);
  const response = 'response' in error ? error.response : undefined;
  const status = typeof Response !== 'undefined' && response instanceof Response ? response.status : undefined;
  const upstreamCorrelationId =
    typeof Response !== 'undefined' && response instanceof Response
      ? response.headers.get('x-correlation-id')
      : undefined;
  // Error text can contain arbitrary customer data. Project only known codes and
  // numeric bundle locations, never the message, source path or function name.
  const locations =
    detail && typeof error.stack === 'string'
      ? error.stack
          .split('\n')
          .slice(1, 21)
          .flatMap((line) => {
            const location = line.match(/(?:^|[/\\])([a-zA-Z0-9_-]+\.(?:js|ts|mjs|cjs)):(\d{1,8}):(\d{1,8})\)?$/);
            if (!location) return [];
            const file = /^(?:\d+|page|route|layout|webpack-runtime)\.js$/.test(location[1])
              ? location[1]
              : '[REDACTED]';
            return [{ file, line: Number(location[2]), column: Number(location[3]) }];
          })
          .slice(0, 8)
      : undefined;
  return {
    type,
    ...(code ? { code } : {}),
    ...(reason ? { reason } : {}),
    ...(status ? { status } : {}),
    ...(upstreamCorrelationId && safeId.test(upstreamCorrelationId) ? { upstreamCorrelationId } : {}),
    ...(detail ? { message: '[REDACTED]', locations } : {}),
    ...(detail && error.cause !== undefined ? { cause: diagnostics(error.cause, true, seen) } : {}),
  };
}

export function logServerFailure(
  event: string,
  error: unknown,
  options: { correlationId?: string; status?: number; surface?: string; upstreamCorrelationId?: unknown } = {}
): string {
  const correlationId = failureCorrelationId(options.correlationId);
  const context = serverFailureContext.getStore();
  if (context) context.logged = true;
  const span = trace.getActiveSpan()?.spanContext();
  const status =
    Number.isInteger(options.status) && Number(options.status) >= 100 && Number(options.status) <= 599
      ? options.status
      : undefined;
  // This is the single server failure sink; its schema deliberately excludes
  // arbitrary metadata, URLs, request/response bodies and error messages.
  // biome-ignore lint/suspicious/noConsole: The sole structured, redacted server failure sink writes to Azure stdout/stderr collection.
  console.error(
    JSON.stringify({
      event: /^web\.[a-z0-9_.]{1,120}$/.test(event) ? event : 'web.server.failure',
      correlationId,
      ...(span && /^[0-9a-f]{32}$/.test(span.traceId) && !/^0+$/.test(span.traceId)
        ? { traceId: span.traceId, spanId: span.spanId }
        : {}),
      ...(status ? { status } : {}),
      ...(typeof options.upstreamCorrelationId === 'string' && safeId.test(options.upstreamCorrelationId)
        ? { upstreamCorrelationId: options.upstreamCorrelationId }
        : {}),
      ...(['HOME', 'MARKETPLACE', 'MY_AGENTS'].includes(options.surface ?? '') ? { surface: options.surface } : {}),
      error: diagnostics(error, process.env.WAOOAW_DIAGNOSTIC_DETAIL === 'true'),
    })
  );
  return correlationId;
}

export function correlateFailureBody(body: unknown, correlationId: string): Record<string, unknown> {
  return {
    ...(body && typeof body === 'object' && !Array.isArray(body) ? body : {}),
    correlationId,
  };
}

export async function readServerResponse(
  response: Response,
  event: string,
  fallback: unknown = undefined
): Promise<unknown> {
  try {
    const body: unknown = await response.json();
    if (response.status >= 500) {
      const correlationId = logServerFailure(event, new Error('Upstream request failed'), {
        status: response.status,
        upstreamCorrelationId:
          body && typeof body === 'object' && 'correlationId' in body
            ? body.correlationId
            : response.headers.get('x-correlation-id'),
      });
      return correlateFailureBody(body, correlationId);
    }
    return body;
  } catch (error) {
    const correlationId = logServerFailure(event, error, {
      status: response.status,
    });
    if (response.ok) throw error;
    return response.status >= 500 && fallback !== undefined ? correlateFailureBody(fallback, correlationId) : fallback;
  }
}
