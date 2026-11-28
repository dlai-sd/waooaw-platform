/** @jest-environment node */

// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R007, WC171-R008, WC171-R009
// Constitutional basis: C-001, C-023, C-059, C-063

import { NextRequest } from 'next/server';
import {
  alertControlRoutes,
  customerDataRequestRoutes,
  operationsRoutes,
  oversightRouteAllowed,
  proxyOversight,
} from './oversight-proxy';

const id = '0f5d4d3a-6f0c-4b6e-9f30-2d4f6a0c1b11';

describe('oversight route allow-list', () => {
  it.each([
    ['GET', ['alerts']],
    ['POST', ['alerts', id, 'snooze']],
    ['GET', ['categories']],
    ['PUT', ['categories', 'PACE_BELOW_TARGET']],
  ])('forwards the alert control %s %j', (method, segments) => {
    expect(oversightRouteAllowed(alertControlRoutes, method, segments)).toBe(true);
  });

  it.each([
    ['DELETE', ['alerts', id]],
    ['GET', ['alerts', id, 'snooze']],
    ['POST', ['alerts']],
    ['PUT', ['categories', 'lower']],
    ['GET', ['..', 'identity']],
    ['GET', ['overview']],
  ])('does not forward %s %j as an alert control', (method, segments) => {
    expect(oversightRouteAllowed(alertControlRoutes, method, segments)).toBe(false);
  });

  it.each([
    ['GET', ['overview']],
    ['GET', ['blocked-messages']],
    ['POST', ['blocked-messages', id, 'resolve']],
    ['GET', ['pages']],
    ['GET', ['customers']],
    ['GET', ['blocked-messages', 'history']],
    ['POST', ['pages', 'DEAD_LETTER_AGE_BREACH', 'acknowledge']],
    ['GET', ['relationships', id, 'work-timeline']],
    ['GET', ['relationships', id, 'spend-chain']],
    ['POST', ['relationships', id, 'spend-discrepancies', id, 'resolve']],
    ['GET', ['data-requests']],
    ['POST', ['data-requests', id, 'resolve']],
  ])('forwards the operation %s %j', (method, segments) => {
    expect(oversightRouteAllowed(operationsRoutes, method, segments)).toBe(true);
  });

  it.each([
    ['GET', []],
    ['POST', []],
  ])('forwards the customer data request %s %j', (method, segments) => {
    expect(oversightRouteAllowed(customerDataRequestRoutes, method, segments)).toBe(true);
  });

  it.each([
    ['DELETE', []],
    ['GET', [id]],
    ['PUT', []],
  ])('does not forward %s %j as a customer data request', (method, segments) => {
    expect(oversightRouteAllowed(customerDataRequestRoutes, method, segments)).toBe(false);
  });

  it.each([
    ['DELETE', ['blocked-messages', id]],
    ['PUT', ['blocked-messages', id, 'resolve']],
    ['GET', ['blocked-messages', id, 'resolve']],
    ['POST', ['overview']],
    ['GET', ['alerts']],
  ])('does not forward %s %j as an operation', (method, segments) => {
    expect(oversightRouteAllowed(operationsRoutes, method, segments)).toBe(false);
  });
});

describe('proxyOversight', () => {
  afterEach(() => jest.restoreAllMocks());

  it('answers 404 without calling the Business Platform for a route that is not allowed', async () => {
    const fetchMock = jest.spyOn(global, 'fetch');
    const response = await proxyOversight(
      new NextRequest('http://localhost/api/operations/anything', { method: 'GET' }),
      'token',
      '/api/v1/operations',
      operationsRoutes,
      ['anything']
    );
    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('forwards the bearer token, the idempotency key and only the named query values', async () => {
    const fetchMock = jest.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ resolutionId: 'r' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    );
    const key = '11111111-1111-4111-8111-111111111111';
    const response = await proxyOversight(
      new NextRequest(`http://localhost/api/operations/blocked-messages/${id}/resolve?tenantId=${id}&evil=1`, {
        method: 'POST',
        headers: { 'Idempotency-Key': key, 'Content-Type': 'application/json' },
        body: JSON.stringify({ schemaVersion: '1.0.0', action: 'RETRY', reason: 'Provider is back' }),
      }),
      'token',
      '/api/v1/operations',
      operationsRoutes,
      ['blocked-messages', id, 'resolve']
    );
    expect(response.status).toBe(201);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`http://localhost:5001/api/v1/operations/blocked-messages/${id}/resolve?tenantId=${id}`);
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer token');
    expect((init.headers as Record<string, string>)['Idempotency-Key']).toBe(key);
  });

  it('forwards customer filters in their own shape and drops anything else', async () => {
    const fetchMock = jest
      .spyOn(global, 'fetch')
      .mockResolvedValue(
        new Response(JSON.stringify({ items: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      );
    await proxyOversight(
      new NextRequest(
        'http://localhost/api/operations/customers?name=Asha%20Rao&contact=asha%40example.com&status=REGISTERED&cursor=abc_-1&pageSize=10&limit=%3Bdrop',
        { method: 'GET' }
      ),
      'token',
      '/api/v1/operations',
      operationsRoutes,
      ['customers']
    );
    const [url] = fetchMock.mock.calls[0] as [string];
    const forwarded = new URL(url).searchParams;
    expect(forwarded.get('name')).toBe('Asha Rao');
    expect(forwarded.get('contact')).toBe('asha@example.com');
    expect(forwarded.get('status')).toBe('REGISTERED');
    expect(forwarded.get('cursor')).toBe('abc_-1');
    expect(forwarded.get('pageSize')).toBe('10');
    expect(forwarded.has('limit')).toBe(false);
  });

  it('refuses a write with no body or a body that is too large', async () => {
    const response = await proxyOversight(
      new NextRequest('http://localhost/api/alert-controls/categories/PACE', { method: 'PUT' }),
      'token',
      '/api/v1/alert-controls',
      alertControlRoutes,
      ['categories', 'PACE']
    );
    expect(response.status).toBe(400);
  });

  it('says it is unavailable when the Business Platform cannot be reached', async () => {
    jest.spyOn(global, 'fetch').mockRejectedValue(new Error('down'));
    const response = await proxyOversight(
      new NextRequest('http://localhost/api/operations/overview', { method: 'GET' }),
      'token',
      '/api/v1/operations',
      operationsRoutes,
      ['overview']
    );
    expect(response.status).toBe(503);
  });
});
