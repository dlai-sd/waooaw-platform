import 'server-only';

// Implements: architecture/reference/components/identity-boundary.md §7 Canonical Public API
// Constitutional basis: C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { IdentityApi } from '@/lib/api/generated/apis/IdentityApi';
import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';
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
  | { kind: 'expired' }
  | { kind: 'step-up' }
  | { kind: 'unauthorized' }
  | { kind: 'unavailable' };

export async function getIdentitySession(accessToken: string): Promise<IdentitySessionResult> {
  try {
    const session = await createIdentityApi(accessToken).getIdentitySession({ cache: 'no-store' });
    return session.expiresAt.getTime() > Date.now()
      ? { kind: 'ready', session }
      : { kind: 'expired' };
  } catch (error) {
    if (error instanceof ResponseError) {
      if (error.response.status === 401) return { kind: 'unauthorized' };
      if (error.response.status === 403) return { kind: 'step-up' };
    }
    return { kind: 'unavailable' };
  }
}

export async function getCustomerProfile(accessToken: string): Promise<CustomerProfileV1> {
  return createIdentityApi(accessToken).getCustomerProfile({ cache: 'no-store' });
}

export async function getCustomerSettings(accessToken: string): Promise<CustomerSettingsV1> {
  return createIdentityApi(accessToken).getCustomerSettings({ cache: 'no-store' });
}

export async function listCustomerLoginMethods(accessToken: string): Promise<CustomerLoginMethodCollectionV1> {
  return createIdentityApi(accessToken).listCustomerLoginMethods({ cache: 'no-store' });
}

const unavailableProviders: IdentityProvider[] = [
  { id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'UNAVAILABLE', unavailableReason: 'TEMPORARILY_UNAVAILABLE' },
  { id: 'FACEBOOK', displayName: 'Facebook', authenticationPath: 'META', availability: 'UNAVAILABLE', unavailableReason: 'TEMPORARILY_UNAVAILABLE' },
  { id: 'APPLE', displayName: 'Apple', authenticationPath: 'APPLE', availability: 'UNAVAILABLE', unavailableReason: 'TEMPORARILY_UNAVAILABLE' },
  { id: 'EMAIL', displayName: 'Email', authenticationPath: 'CREDENTIAL', availability: 'UNAVAILABLE', unavailableReason: 'TEMPORARILY_UNAVAILABLE' },
];

export async function listIdentityProviders(): Promise<IdentityProvider[]> {
  try {
    const api = new IdentityApi(new Configuration({ basePath: businessPlatformUrl }));
    return (await api.listIdentityProviders({ cache: 'no-store' })).providers;
  } catch {
    return unavailableProviders;
  }
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