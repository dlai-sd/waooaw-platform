import 'server-only';

// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R024
// Constitutional basis: C-001, C-023, C-059, C-063

import { NextResponse, type NextRequest } from 'next/server';
import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { readRequestJson } from '@/lib/server-failure-boundary';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const noStore = { 'Cache-Control': 'no-store' } as const;
const uuidPattern = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
const decision =
  /^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\/versions\/[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\/(approve|suspend|retire)$/;
const maximumBodyLength = 4_096;

// The Founder list and the three decisions; nothing else is proxied.
export function professionalApprovalRouteAllowed(method: string, segments: readonly string[]): boolean {
  const path = segments.join('/');
  return (method === 'GET' && path === '') || (method === 'POST' && decision.test(path));
}

function problem(status: number, code: string, title: string, correlationId: string) {
  return NextResponse.json(
    { type: 'about:blank', title, status, code, correlationId },
    { status, headers: { ...noStore, 'X-Correlation-ID': correlationId } }
  );
}

export async function proxyProfessionalApprovals(
  request: NextRequest,
  accessToken: string,
  segments: readonly string[]
): Promise<Response> {
  const method = request.method.toUpperCase();
  const header = request.headers.get('x-correlation-id');
  const correlationId = header && uuidPattern.test(header) ? header : crypto.randomUUID();
  if (!professionalApprovalRouteAllowed(method, segments))
    return problem(404, 'PROFESSIONAL_APPROVAL_REQUEST_INVALID', 'That route was not found.', correlationId);
  const headers: Record<string, string> = {
    Accept: 'application/json',
    Authorization: `Bearer ${accessToken}`,
    'X-Correlation-ID': correlationId,
  };
  let body: string | undefined;
  if (method !== 'GET') {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(await readRequestJson(request));
    if (body.length > maximumBodyLength)
      return problem(400, 'PROFESSIONAL_APPROVAL_REQUEST_INVALID', 'The request is too large.', correlationId);
  }
  const url = `${businessPlatformUrl}/api/v1/admin/professionals${segments.length > 0 ? `/${segments.join('/')}` : ''}`;
  let upstream: Response;
  try {
    upstream = await fetch(url, { method, headers, body, cache: 'no-store' });
  } catch (error) {
    logServerFailure('web.professional_approvals.request_failed', error);
    return problem(
      503,
      'PROFESSIONAL_APPROVAL_UNAVAILABLE',
      'Professionals are temporarily unavailable.',
      correlationId
    );
  }
  const payload = await readServerResponse(upstream, 'web.professional_approvals.response_invalid', {
    code: 'PROFESSIONAL_APPROVAL_UNAVAILABLE',
    status: upstream.status,
  });
  if (upstream.status < 400)
    return NextResponse.json(payload ?? {}, {
      status: upstream.status,
      headers: { ...noStore, 'X-Correlation-ID': correlationId },
    });
  const source = payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {};
  const code =
    typeof source.code === 'string' && /^[A-Z_]{3,64}$/.test(source.code)
      ? source.code
      : 'PROFESSIONAL_APPROVAL_UNAVAILABLE';
  return NextResponse.json(
    { type: 'about:blank', status: upstream.status, code, correlationId },
    { status: upstream.status, headers: { ...noStore, 'X-Correlation-ID': correlationId } }
  );
}
