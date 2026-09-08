/** @jest-environment node */

import { NextRequest } from 'next/server';

const accessTokenFromRequest = jest.fn();
const updateCustomerProfile = jest.fn();
const updateCustomerSettings = jest.fn();
const markCustomerAlertRead = jest.fn();
const acknowledgeCustomerAlert = jest.fn();
const updateRelationshipOnboard = jest.fn();
const identityProblem = jest.fn(async () => ({ status: 503, body: { title: 'Identity unavailable' } }));

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest }));
jest.mock('@/lib/api/identity', () => ({
  createIdentityApi: () => ({ updateCustomerProfile, updateCustomerSettings }),
  identityProblem,
}));
jest.mock('@/lib/api/generated/apis/NotificationsApi', () => ({ NotificationsApi: jest.fn(() => ({ markCustomerAlertRead, acknowledgeCustomerAlert })) }));
jest.mock('@/lib/api/generated/apis/ConfigurationApi', () => ({ ConfigurationApi: jest.fn(() => ({ updateRelationshipOnboard })) }));

function request(path: string, body: object) {
  return new NextRequest(`http://localhost${path}`, { method: 'PUT', body: JSON.stringify(body) });
}

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