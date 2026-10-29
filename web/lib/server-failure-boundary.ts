import 'server-only';

// Implements: work-contracts/WC-126-web-server-failure-logging.md §Requirements And Definition Of Done
// Constitutional basis: C-023, C-059, C-063

import { NextResponse } from 'next/server';
import {
  correlateFailureBody,
  failureCorrelationId,
  logServerFailure,
  serverFailureContext,
} from '@/lib/server-failure';

export class InvalidRequestJson extends Error {}

export async function readRequestJson(request: Request): Promise<unknown> {
  try {
    return await request.json();
  } catch (error) {
    if (
      error instanceof SyntaxError ||
      (error !== null && typeof error === 'object' && 'name' in error && error.name === 'SyntaxError')
    ) {
      throw new InvalidRequestJson();
    }
    logServerFailure('web.request.body_read_failed', error);
    throw error;
  }
}

export function withServerFailureBoundary<Args extends unknown[]>(
  event: string,
  handler: (...args: Args) => Promise<Response>
): (...args: Args) => Promise<Response> {
  return (...args) =>
    serverFailureContext.run({ correlationId: failureCorrelationId(), logged: false }, async () => {
      let response: Response;
      try {
        response = await handler(...args);
      } catch (error) {
        if (error instanceof InvalidRequestJson) {
          return NextResponse.json(
            { code: 'REQUEST_INVALID', title: 'Request is invalid.' },
            { status: 400, headers: { 'Cache-Control': 'no-store' } }
          );
        }
        const correlationId = logServerFailure(event, error);
        return NextResponse.json(
          {
            code: 'SERVICE_UNAVAILABLE',
            title: 'Request could not be completed.',
            correlationId,
          },
          {
            status: 503,
            headers: {
              'Cache-Control': 'no-store',
              'X-Correlation-ID': correlationId,
            },
          }
        );
      }
      if (response.status < 500) return response;
      const correlationId = failureCorrelationId();
      if (!serverFailureContext.getStore()?.logged) {
        logServerFailure(event, new Error('Server response failed'), {
          status: response.status,
        });
      }
      let body: unknown;
      try {
        body = await response.clone().json();
      } catch (error) {
        logServerFailure('web.server.failure_response_invalid', error, {
          status: response.status,
        });
        body = { title: 'Request could not be completed.' };
      }
      const headers = new Headers(response.headers);
      headers.set('X-Correlation-ID', correlationId);
      headers.delete('Content-Length');
      return NextResponse.json(correlateFailureBody(body, correlationId), {
        status: response.status,
        headers,
      });
    });
}
