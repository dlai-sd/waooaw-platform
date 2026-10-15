import type { NextRequest } from 'next/server';

function normalizedOrigin(value: string | null): string | undefined {
  if (!value) return undefined;
  try {
    return new URL(value).origin;
  } catch {
    return undefined;
  }
}

function firstForwardedValue(value: string | null): string | undefined {
  return value?.split(',')[0]?.trim() || undefined;
}

export function isSameOriginRequest(request: NextRequest, applicationOrigin: string): boolean {
  const expectedOrigin = normalizedOrigin(applicationOrigin);
  if (!expectedOrigin) return false;

  const requestOrigin = normalizedOrigin(request.headers.get('origin'));
  if (requestOrigin === expectedOrigin) return true;
  if (request.headers.get('sec-fetch-site') !== 'same-origin') return false;

  const forwardedHost = firstForwardedValue(request.headers.get('x-forwarded-host'));
  const forwardedProto = firstForwardedValue(request.headers.get('x-forwarded-proto'));
  if (forwardedHost && forwardedProto) {
    const forwardedOrigin = normalizedOrigin(`${forwardedProto}://${forwardedHost}`);
    if (forwardedOrigin === expectedOrigin) return true;
  }

  const refererOrigin = normalizedOrigin(request.headers.get('referer'));
  if (refererOrigin === expectedOrigin) return true;
  return requestOrigin === undefined;
}
