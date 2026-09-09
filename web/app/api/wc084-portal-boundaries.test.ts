/** @jest-environment node */

import { NextRequest } from 'next/server';
import type { IdentityApi } from '@/lib/api/generated/apis/IdentityApi';

const accessTokenFromRequest = jest.fn();
const updateCustomerProfile = jest.fn();
const updateCustomerSettings = jest.fn();
const completeIdentityRegistration = jest.fn();
const getIdentitySession = jest.fn();
const startIdentityRegistration = jest.fn();
const createIdentityApi = jest.fn<Pick<IdentityApi, 'updateCustomerProfile' | 'updateCustomerSettings' | 'completeIdentityRegistration' | 'getIdentitySession' | 'startIdentityRegistration'>, [string]>(() => ({ updateCustomerProfile, updateCustomerSettings, completeIdentityRegistration, getIdentitySession, startIdentityRegistration }));
const markCustomerAlertRead = jest.fn();
const acknowledgeCustomerAlert = jest.fn();
const updateRelationshipOnboard = jest.fn();
const identityProblem = jest.fn(async () => ({ status: 503, body: { title: 'Identity unavailable' } }));

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest }));
jest.mock('server-only', () => ({}));
jest.mock('@/lib/api/identity', () => ({
  createIdentityApi,
  identityProblem,
}));
jest.mock('@/lib/api/generated/apis/NotificationsApi', () => ({ NotificationsApi: jest.fn(() => ({ markCustomerAlertRead, acknowledgeCustomerAlert })) }));
jest.mock('@/lib/api/generated/apis/ConfigurationApi', () => ({ ConfigurationApi: jest.fn(() => ({ updateRelationshipOnboard })) }));

function request(path: string, body: object) {
  return new NextRequest(`http://localhost${path}`, { method: 'PUT', body: JSON.stringify(body) });
}

describe('WC085 registration handoff', () => {
  const accountReference = '8f6f7550-98c7-4a8f-bd63-36f07ee15c9d';
  const completion = { outcome: 'ACCOUNT_CREATED', accountReference, assuranceLevel: 'AAL2_ACCOUNT', defaultTarget: 'APPLICATION_HOME' };
  const session = { accountReference, expiresAt: new Date(Date.now() + 600_000) };

  async function complete() {
    const { POST } = await import('./identity/registration/route');
    return POST(new NextRequest('http://localhost/api/identity/registration', {
      method: 'POST', body: JSON.stringify({ action: 'complete', registrationId: 'registration-1', idempotencyKey: 'key-1' }),
    }));
  }

  beforeEach(() => {
    jest.clearAllMocks();
    accessTokenFromRequest.mockResolvedValue('server-token');
    completeIdentityRegistration.mockResolvedValue(completion);
    getIdentitySession.mockResolvedValue(session);
  });

  it.each(['ACCOUNT_CREATED', 'ACCOUNT_REUSED'])('confirms %s with the same server token and no account or session payload', async (outcome) => {
    completeIdentityRegistration.mockResolvedValue({ ...completion, outcome, tenantId: 'private-tenant' });
    getIdentitySession.mockResolvedValue({ ...session, accessToken: 'private-token' });
    const response = await complete();
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ handoffConfirmed: true });
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    expect(accessTokenFromRequest).toHaveBeenCalledTimes(1);
    expect(createIdentityApi).toHaveBeenCalledTimes(1);
    expect(createIdentityApi).toHaveBeenCalledWith('server-token');
    expect(completeIdentityRegistration).toHaveBeenCalledWith({ registrationId: 'registration-1', idempotencyKey: 'key-1' }, expect.objectContaining({ cache: 'no-store', signal: expect.any(AbortSignal) }));
    expect(getIdentitySession).toHaveBeenCalledWith(expect.objectContaining({ cache: 'no-store', signal: expect.any(AbortSignal) }));
    expect(completeIdentityRegistration.mock.invocationCallOrder[0]).toBeLessThan(getIdentitySession.mock.invocationCallOrder[0]);
  });

  it.each([undefined, null, {}, { ...completion, accountReference: '' }, { ...completion, accountReference: ' ' }, { ...completion, outcome: 'PENDING' }])('rejects an incomplete completion result: %p', async (result) => {
    completeIdentityRegistration.mockResolvedValue(result);
    const response = await complete();
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' });
    expect(getIdentitySession).not.toHaveBeenCalled();
  });

  it.each([undefined, null, {}, { ...session, accountReference: '' }, { ...session, accountReference: 'other-account' }, { ...session, expiresAt: new Date(0) }, { ...session, expiresAt: new Date('invalid') }])('rejects an unconfirmed session without leaking completion: %p', async (result) => {
    getIdentitySession.mockResolvedValue(result);
    const response = await complete();
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' });
  });

  it.each(['completion', 'session'])('sanitizes raw %s failures', async (stage) => {
    const { ResponseError } = await import('@/lib/api/generated/runtime');
    const error = new ResponseError(new Response(JSON.stringify({ title: 'private-token private-tenant other-account', accountReference }), { status: 403 }));
    (stage === 'completion' ? completeIdentityRegistration : getIdentitySession).mockRejectedValue(error);
    const response = await complete();
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' });
    expect(identityProblem).not.toHaveBeenCalled();
  });

  it('requires a server session before completion', async () => {
    accessTokenFromRequest.mockResolvedValue(undefined);
    expect((await complete()).status).toBe(401);
    expect(completeIdentityRegistration).not.toHaveBeenCalled();
    expect(getIdentitySession).not.toHaveBeenCalled();
  });

  it.each(['matching', 'mismatched', 'unavailable'])('uses the generated client with the BP wire shape and a %s session', async (state) => {
    const realIdentity = jest.requireActual<typeof import('@/lib/api/identity')>('@/lib/api/identity');
    createIdentityApi.mockReturnValueOnce(realIdentity.createIdentityApi('server-token'));
    const wireSession = {
      accountReference: state === 'mismatched' ? 'other-account' : accountReference,
      roles: ['OWNER'], capabilities: [], assuranceLevel: 'AAL2_ACCOUNT', authenticationPath: 'PORTAL',
      emailVerified: true, mobileVerified: false, authenticatedAt: new Date().toISOString(),
      expiresAt: session.expiresAt.toISOString(), nextAction: 'CONTINUE_TO_DEFAULT_TARGET',
    };
    const fetchMock = jest.spyOn(global, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(completion)))
      .mockResolvedValueOnce(new Response(JSON.stringify(state === 'unavailable' ? { title: 'private-token other-account' } : wireSession), { status: state === 'unavailable' ? 503 : 200 }));
    try {
      const response = await complete();
      expect(response.status).toBe(state === 'matching' ? 200 : 503);
      expect(await response.json()).toEqual(state === 'matching'
        ? { handoffConfirmed: true }
        : { code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' });
      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(fetchMock.mock.calls.map(([, init]) => init?.method)).toEqual(['POST', 'GET']);
      for (const [, init] of fetchMock.mock.calls) {
        expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer server-token');
        expect(new Headers(init?.headers).has('x-tenant-id')).toBe(false);
        expect(init?.cache).toBe('no-store');
      }
      expect(fetchMock.mock.calls[0][1]?.signal).toBe(fetchMock.mock.calls[1][1]?.signal);
    } finally {
      fetchMock.mockRestore();
    }
  });

  it('leaves the generated direct GET registration operation unchanged', async () => {
    const realIdentity = jest.requireActual<typeof import('@/lib/api/identity')>('@/lib/api/identity');
    const registration = {
      registrationId: 'registration-1', state: 'REGISTRATION_COMPLETION_REQUIRED', nextAction: 'COMPLETE_REGISTRATION',
      authenticationPath: 'GOOGLE', emailVerified: true, mobileVerified: false, profile: {},
      expiresAt: session.expiresAt.toISOString(), updatedAt: new Date().toISOString(),
    };
    const fetchMock = jest.spyOn(global, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify(registration)));
    try {
      const result = await realIdentity.createIdentityApi('server-token').getIdentityRegistration({ registrationId: 'registration-1' }, { cache: 'no-store' });
      expect(result).toMatchObject({ ...registration, expiresAt: session.expiresAt, updatedAt: new Date(registration.updatedAt) });
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(fetchMock.mock.calls[0][1]?.method).toBe('GET');
      expect(getIdentitySession).not.toHaveBeenCalled();
      expect(completeIdentityRegistration).not.toHaveBeenCalled();
    } finally {
      fetchMock.mockRestore();
    }
  });

  it('shares a bounded deadline and rejects a cancelled handoff', async () => {
    const deadline = new AbortController();
    const timeout = jest.spyOn(AbortSignal, 'timeout').mockReturnValue(deadline.signal);
    getIdentitySession.mockImplementationOnce(async () => {
      deadline.abort();
      return session;
    });
    try {
      const response = await complete();
      expect(response.status).toBe(503);
      expect(await response.json()).toEqual({ code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' });
      expect(timeout).toHaveBeenCalledWith(15_000);
      expect(completeIdentityRegistration.mock.calls[0][1].signal).toBe(getIdentitySession.mock.calls[0][0].signal);
    } finally {
      timeout.mockRestore();
    }
  });

  it('sanitizes an upstream start error without forwarding its raw body', async () => {
    const { ResponseError } = await import('@/lib/api/generated/runtime');
    getIdentitySession.mockRejectedValue(new ResponseError(new Response(null, { status: 403 })));
    startIdentityRegistration.mockRejectedValue(new ResponseError(new Response(JSON.stringify({ title: 'private-token private-tenant', accountReference }), { status: 409 })));
    const { POST } = await import('./identity/registration/route');
    const response = await POST(new NextRequest('http://localhost/api/identity/registration', {
      method: 'POST', body: JSON.stringify({ action: 'start', languagePreference: 'en', idempotencyKey: 'key-1' }),
    }));
    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({ code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' });
    expect(identityProblem).not.toHaveBeenCalled();
  });

  it('leaves registration start responses unchanged', async () => {
    const { ResponseError } = await import('@/lib/api/generated/runtime');
    getIdentitySession.mockRejectedValue(new ResponseError(new Response(null, { status: 403 })));
    const { POST } = await import('./identity/registration/route');
    const registration = { registrationId: 'registration-1', nextAction: 'COMPLETE_PROFILE' };
    startIdentityRegistration.mockResolvedValue(registration);
    const response = await POST(new NextRequest('http://localhost/api/identity/registration', {
      method: 'POST', body: JSON.stringify({ action: 'start', languagePreference: 'en', idempotencyKey: 'key-1' }),
    }));
    expect(await response.json()).toEqual(registration);
    expect(getIdentitySession).toHaveBeenCalledTimes(1);
  });

  it('dispatches an existing session without starting registration or needing a tenant claim', async () => {
    const { POST } = await import('./identity/registration/route');
    const response = await POST(new NextRequest('http://localhost/api/identity/registration', {
      method: 'POST', body: JSON.stringify({ action: 'start', languagePreference: 'en', idempotencyKey: 'key-1' }),
    }));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ handoffConfirmed: true });
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    expect(createIdentityApi).toHaveBeenCalledWith('server-token');
    expect(startIdentityRegistration).not.toHaveBeenCalled();
    expect(completeIdentityRegistration).not.toHaveBeenCalled();
  });

  it.each([undefined, {}, { ...session, accountReference: '' }, { ...session, expiresAt: new Date(0) }, new Error('private-session')])('does not start registration on an unresolved session: %p', async (result) => {
    if (result instanceof Error) getIdentitySession.mockRejectedValue(result);
    else getIdentitySession.mockResolvedValue(result);
    const { POST } = await import('./identity/registration/route');
    const response = await POST(new NextRequest('http://localhost/api/identity/registration', {
      method: 'POST', body: JSON.stringify({ action: 'start', languagePreference: 'en', idempotencyKey: 'key-1' }),
    }));
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' });
    expect(startIdentityRegistration).not.toHaveBeenCalled();
  });
});

describe('WC084 portal server boundaries', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    accessTokenFromRequest.mockResolvedValue('server-token');
  });

  it('requires authentication before parsing a profile command', async () => {
    accessTokenFromRequest.mockResolvedValue(undefined);
    const { PUT } = await import('./identity/profile/route');
    expect((await PUT(request('/api/identity/profile', {}))).status).toBe(401);
    expect(updateCustomerProfile).not.toHaveBeenCalled();
  });

  it('validates and forwards a trimmed profile command', async () => {
    const { PUT } = await import('./identity/profile/route');
    expect((await PUT(request('/api/identity/profile', { displayName: '  ', organizationDisplayName: 'Acme', idempotencyKey: 'key' }))).status).toBe(400);
    updateCustomerProfile.mockResolvedValue({ displayName: 'Asha', organizationDisplayName: 'Acme' });
    const response = await PUT(request('/api/identity/profile', { displayName: ' Asha ', organizationDisplayName: ' Acme ', idempotencyKey: 'key' }));
    expect(response.status).toBe(200);
    expect(updateCustomerProfile).toHaveBeenCalledWith(expect.objectContaining({ idempotencyKey: 'key', updateCustomerProfileRequestV1: expect.objectContaining({ displayName: 'Asha', organizationDisplayName: 'Acme' }) }), { cache: 'no-store' });
  });

  it('preserves identity failures for profile and settings', async () => {
    updateCustomerProfile.mockRejectedValue(new Error('upstream'));
    updateCustomerSettings.mockRejectedValue(new Error('upstream'));
    const profile = await import('./identity/profile/route');
    const settings = await import('./identity/settings/route');
    expect((await profile.PUT(request('/api/identity/profile', { displayName: 'Asha', organizationDisplayName: 'Acme', idempotencyKey: 'key' }))).status).toBe(503);
    expect((await settings.PUT(request('/api/identity/settings', { settings: { schemaVersion: '1.0.0' }, idempotencyKey: 'key' }))).status).toBe(503);
  });

  it('validates and forwards settings with the server token', async () => {
    const { PUT } = await import('./identity/settings/route');
    expect((await PUT(request('/api/identity/settings', {}))).status).toBe(400);
    updateCustomerSettings.mockResolvedValue({ locale: 'en-IN' });
    const settings = { schemaVersion: '1.0.0', locale: 'en-IN', theme: 'SYSTEM', timestampVisibility: 'RELATIVE', notificationPreferences: {} };
    const response = await PUT(request('/api/identity/settings', { settings, idempotencyKey: 'key' }));
    expect(response.status).toBe(200);
    expect(updateCustomerSettings).toHaveBeenCalledWith({ idempotencyKey: 'key', updateCustomerSettingsRequestV1: settings }, { cache: 'no-store' });
  });

  it('validates and forwards alert read and acknowledge commands', async () => {
    const { POST } = await import('./alerts/[alertId]/route');
    const params = { params: Promise.resolve({ alertId: 'alert-1' }) };
    expect((await POST(new NextRequest('http://localhost/api/alerts/alert-1', { method: 'POST', body: '{}' }), params)).status).toBe(400);
    markCustomerAlertRead.mockResolvedValue({ alertId: 'alert-1', readState: 'READ' });
    acknowledgeCustomerAlert.mockResolvedValue({ alertId: 'alert-1', readState: 'ACKNOWLEDGED' });
    const read = new NextRequest('http://localhost/api/alerts/alert-1', { method: 'POST', body: JSON.stringify({ action: 'read', expectedAlertVersion: '1', idempotencyKey: 'key' }) });
    const acknowledge = new NextRequest('http://localhost/api/alerts/alert-1', { method: 'POST', body: JSON.stringify({ action: 'acknowledge', expectedAlertVersion: '2', idempotencyKey: 'key-2' }) });
    expect((await POST(read, params)).status).toBe(200);
    expect((await POST(acknowledge, params)).status).toBe(200);
    expect(markCustomerAlertRead).toHaveBeenCalledWith(expect.objectContaining({ alertId: 'alert-1', idempotencyKey: 'key' }), { cache: 'no-store' });
    expect(acknowledgeCustomerAlert).toHaveBeenCalled();
  });

  it('fails closed when an alert update is unresolved', async () => {
    markCustomerAlertRead.mockRejectedValue(new Error('upstream'));
    const { POST } = await import('./alerts/[alertId]/route');
    const response = await POST(new NextRequest('http://localhost/api/alerts/alert-1', { method: 'POST', body: JSON.stringify({ action: 'read', expectedAlertVersion: '1', idempotencyKey: 'key' }) }), { params: Promise.resolve({ alertId: 'alert-1' }) });
    expect(response.status).toBe(503);
  });

  it('validates and forwards Onboard preferences', async () => {
    const { PUT } = await import('./relationships/[relationshipId]/onboard/route');
    const params = { params: Promise.resolve({ relationshipId: 'relationship-1' }) };
    expect((await PUT(request('/api/relationships/relationship-1/onboard', {}), params)).status).toBe(400);
    const onboard = { schemaVersion: '1.0.0', themePreference: 'SYSTEM' };
    updateRelationshipOnboard.mockResolvedValue({ lifecyclePhase: 'INDUCT' });
    const response = await PUT(request('/api/relationships/relationship-1/onboard', { onboard, idempotencyKey: 'key' }), params);
    expect(response.status).toBe(200);
    expect(updateRelationshipOnboard).toHaveBeenCalledWith({ relationshipId: 'relationship-1', idempotencyKey: 'key', relationshipOnboardRequestV1: onboard }, { cache: 'no-store' });
  });

  it('requires authentication and fails closed for unresolved Onboard updates', async () => {
    const { PUT } = await import('./relationships/[relationshipId]/onboard/route');
    const params = { params: Promise.resolve({ relationshipId: 'relationship-1' }) };
    accessTokenFromRequest.mockResolvedValueOnce(undefined);
    expect((await PUT(request('/api/relationships/relationship-1/onboard', {}), params)).status).toBe(401);
    updateRelationshipOnboard.mockRejectedValue(new Error('upstream'));
    expect((await PUT(request('/api/relationships/relationship-1/onboard', { onboard: { schemaVersion: '1.0.0' }, idempotencyKey: 'key' }), params)).status).toBe(503);
  });
});