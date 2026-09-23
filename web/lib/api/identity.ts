import 'server-only';

// Implements: architecture/reference/components/identity-boundary.md §7 Canonical Public API
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R013, WC105-R017
// Constitutional basis: C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { cache } from 'react';
import { IdentityApi } from '@/lib/api/generated/apis/IdentityApi';
import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';
import type { IdentityManagedSession } from '@/lib/api/generated/models/IdentityManagedSession';
import type { IdentitySessionRevocation } from '@/lib/api/generated/models/IdentitySessionRevocation';
import type { IdentitySession } from '@/lib/api/generated/models/IdentitySession';
import type { CustomerLoginMethodCollectionV1 } from '@/lib/api/generated/models/CustomerLoginMethodCollectionV1';
import type { CustomerProfileV1 } from '@/lib/api/generated/models/CustomerProfileV1';
import type { CustomerSettingsV1 } from '@/lib/api/generated/models/CustomerSettingsV1';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export function createIdentityApi(accessToken: string): IdentityApi {
  return new IdentityApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
}

export type IdentitySessionResult =
  | { kind: 'ready'; session: IdentitySession }
  | { kind: 'registration-required' }
  | { kind: 'expired' }
  | { kind: 'step-up'; correlationId?: string }
  | { kind: 'forbidden'; code: string; correlationId?: string }
  | { kind: 'unauthorized' }
  | { kind: 'unavailable'; correlationId?: string };

type IdentityProblem = { code?: unknown; correlationId?: unknown };

async function readIdentityProblem(response: Response): Promise<IdentityProblem | undefined> {
  if (typeof response.clone !== 'function') return undefined;
  return (await response
    .clone()
    .json()
    .catch(() => undefined)) as IdentityProblem | undefined;
}

async function loadIdentitySession(accessToken: string): Promise<IdentitySessionResult> {
  try {
    const session = await createIdentityApi(accessToken).getIdentitySession({ cache: 'no-store' });
    return session.expiresAt.getTime() > Date.now() ? { kind: 'ready', session } : { kind: 'expired' };
  } catch (error) {
    if (error instanceof ResponseError) {
      if (error.response.status === 401) return { kind: 'unauthorized' };
      const problem = await readIdentityProblem(error.response);
      const correlationId = typeof problem?.correlationId === 'string' ? problem.correlationId : undefined;
      if (error.response.status === 403) {
        if (problem?.code === 'IDENTITY_STEP_UP_REQUIRED') {
          return { kind: 'step-up', ...(correlationId ? { correlationId } : {}) };
        }
        return {
          kind: 'forbidden',
          code: typeof problem?.code === 'string' ? problem.code : 'IDENTITY_ACTION_DENIED',
          ...(correlationId ? { correlationId } : {}),
        };
      }
      if (error.response.status === 409) {
        if (problem?.code === 'REGISTRATION_REQUIRED') return { kind: 'registration-required' };
      }
      return { kind: 'unavailable', ...(correlationId ? { correlationId } : {}) };
    }
    return { kind: 'unavailable' };
  }
}

export const getIdentitySession = cache(loadIdentitySession);

export async function getCustomerProfile(accessToken: string): Promise<CustomerProfileV1> {
  return createIdentityApi(accessToken).getCustomerProfile({ cache: 'no-store' });
}

export async function getCustomerSettings(accessToken: string): Promise<CustomerSettingsV1> {
  return createIdentityApi(accessToken).getCustomerSettings({ cache: 'no-store' });
}

export async function listCustomerLoginMethods(accessToken: string): Promise<CustomerLoginMethodCollectionV1> {
  return createIdentityApi(accessToken).listCustomerLoginMethods({ cache: 'no-store' });
}

export async function listIdentitySessions(accessToken: string): Promise<IdentityManagedSession[]> {
  return (await createIdentityApi(accessToken).listIdentitySessions({ cache: 'no-store' })).sessions;
}

export async function revokeIdentitySession(
  accessToken: string,
  sessionId: string,
  idempotencyKey: string
): Promise<IdentitySessionRevocation> {
  return createIdentityApi(accessToken).revokeIdentitySession({ sessionId, idempotencyKey }, { cache: 'no-store' });
}

export async function revokeAllIdentitySessions(
  accessToken: string,
  idempotencyKey: string
): Promise<IdentitySessionRevocation> {
  return createIdentityApi(accessToken).revokeAllIdentitySessions({ idempotencyKey }, { cache: 'no-store' });
}

const unavailableProviders: IdentityProvider[] = [
  {
    id: 'GOOGLE',
    displayName: 'Google',
    authenticationPath: 'GOOGLE',
    availability: 'UNAVAILABLE',
    unavailableReason: 'TEMPORARILY_UNAVAILABLE',
  },
  {
    id: 'FACEBOOK',
    displayName: 'Facebook',
    authenticationPath: 'META',
    availability: 'UNAVAILABLE',
    unavailableReason: 'TEMPORARILY_UNAVAILABLE',
  },
  {
    id: 'APPLE',
    displayName: 'Apple',
    authenticationPath: 'APPLE',
    availability: 'UNAVAILABLE',
    unavailableReason: 'TEMPORARILY_UNAVAILABLE',
  },
  {
    id: 'EMAIL',
    displayName: 'Email',
    authenticationPath: 'CREDENTIAL',
    availability: 'UNAVAILABLE',
    unavailableReason: 'TEMPORARILY_UNAVAILABLE',
  },
];

export async function listIdentityProviders(): Promise<IdentityProvider[]> {
  const api = new IdentityApi(new Configuration({ basePath: businessPlatformUrl }));
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    try {
      const signal = typeof AbortSignal.timeout === 'function' ? AbortSignal.timeout(12_000) : undefined;
      return (await api.listIdentityProviders({ cache: 'no-store', ...(signal ? { signal } : {}) })).providers;
    } catch (error) {
      // biome-ignore lint/suspicious/noConsole: Provider readiness failures must remain observable until structured server logging is available.
      console.warn('Identity provider readiness projection unavailable.', {
        attempt,
        error: error instanceof Error ? error.name : 'UnknownError',
      });
    }
  }
  return unavailableProviders;
}

export async function identityProblem(error: unknown): Promise<{ status: number; body: unknown }> {
  if (error instanceof ResponseError) {
    const body = await error.response.json().catch(() => undefined);
    return {
      status: error.response.status,
      body: body ?? { code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' },
    };
  }
  return {
    status: 503,
    body: { code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' },
  };
}
