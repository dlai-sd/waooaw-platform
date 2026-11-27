/** @jest-environment node */

// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R024
// Constitutional basis: C-001, C-023, C-059, C-063

import { NextRequest } from 'next/server';
import { professionalApprovalRouteAllowed, proxyProfessionalApprovals } from './professional-approvals-proxy';

function request(method: string, path: string, body?: unknown) {
  return new NextRequest(`http://localhost/api/admin/professionals/${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

describe('professionalApprovalRouteAllowed', () => {
  it('allows the list and the three decisions and nothing else', () => {
    expect(professionalApprovalRouteAllowed('GET', [])).toBe(true);
    for (const action of ['approve', 'suspend', 'retire'])
      expect(professionalApprovalRouteAllowed('POST', ['TYPE_A', 'versions', '1.0.0', action])).toBe(true);
    for (const [method, path] of [
      ['POST', ['TYPE_A', 'versions', '1.0.0', 'delete']],
      ['DELETE', ['TYPE_A', 'versions', '1.0.0', 'approve']],
      ['GET', ['TYPE_A']],
      ['POST', ['..', 'versions', '1.0.0', 'approve']],
      ['POST', []],
    ] as const)
      expect(professionalApprovalRouteAllowed(method, path)).toBe(false);
  });
});

describe('proxyProfessionalApprovals', () => {
  afterEach(() => jest.restoreAllMocks());

  it('refuses a route that is not allowed without calling the platform', async () => {
    const fetchMock = jest.spyOn(global, 'fetch');

    const response = await proxyProfessionalApprovals(request('POST', 'x/versions/1/delete', {}), 'token', [
      'x',
      'versions',
      '1',
      'delete',
    ]);

    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('forwards a decision with the Founder token and relays a known failure code only', async () => {
    const fetchMock = jest.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ code: 'PROFESSIONAL_APPROVAL_STEP_UP_REQUIRED', secret: 'x' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const response = await proxyProfessionalApprovals(
      request('POST', 'TYPE_A/versions/1.0.0/approve', { reason: null }),
      'founder-token',
      ['TYPE_A', 'versions', '1.0.0', 'approve']
    );

    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/v1/admin/professionals/TYPE_A/versions/1.0.0/approve');
    expect((fetchMock.mock.calls[0][1]?.headers as Record<string, string>).Authorization).toBe('Bearer founder-token');
    const body = await response.json();
    expect(response.status).toBe(403);
    expect(body.code).toBe('PROFESSIONAL_APPROVAL_STEP_UP_REQUIRED');
    expect(body.secret).toBeUndefined();
  });

  it('reports the platform as unavailable when it cannot be reached', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => undefined);
    jest.spyOn(global, 'fetch').mockRejectedValue(new Error('offline'));

    const response = await proxyProfessionalApprovals(request('GET', ''), 'token', []);

    expect(response.status).toBe(503);
  });
});
