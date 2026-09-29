/** @jest-environment node */

import { NextRequest } from 'next/server';
import { consumeMyAgentsSelection } from '@/lib/api/my-agents-selection';
import { listEmploymentRelationships } from '@/lib/api/relationships';
import { accessTokenFromRequest } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));
jest.mock('@/lib/api/my-agents-selection', () => ({
  consumeMyAgentsSelection: jest.fn(),
  myAgentsSelectionCookie: 'waooaw_my_agents_selection',
}));
jest.mock('@/lib/api/relationships', () => ({ listEmploymentRelationships: jest.fn() }));

const relationshipId = '22222222-2222-4222-8222-222222222222';
const request = (withCookie = true) =>
  new NextRequest('http://localhost/professionals/mine/selection', {
    method: 'POST',
    headers: withCookie ? { cookie: `waooaw_my_agents_selection=${'a'.repeat(64)}` } : undefined,
  });
const relationship = (overrides: Record<string, unknown> = {}) => ({
  relationshipId,
  acquisitionMode: 'TRIAL',
  lifecycleState: 'TRIAL_ACTIVE',
  trialStatus: 'ACTIVE',
  nextActionLabel: 'Open conversation',
  ...overrides,
});

describe('My Agents authoritative selection boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(accessTokenFromRequest).mockResolvedValue('access-token');
    jest.mocked(consumeMyAgentsSelection).mockResolvedValue({ relationshipId, outcomeKind: 'TRIAL_STARTED' });
    jest.mocked(listEmploymentRelationships).mockResolvedValue({ items: [relationship()] } as never);
  });

  it('derives Trial confirmation only from an active authoritative card and clears the cookie', async () => {
    const { POST } = await import('./route');

    const response = await POST(request());

    expect(await response.json()).toEqual({
      relationshipId,
      confirmation: 'Trial started',
      nextActionLabel: 'Open conversation',
    });
    expect(response.headers.get('set-cookie')).toEqual(
      expect.stringMatching(
        /waooaw_my_agents_selection=;.*Path=\/professionals\/mine;.*Max-Age=0;.*Secure;.*HttpOnly;.*SameSite=strict/i
      )
    );
  });

  it.each([
    ['navigation alone', false, { items: [relationship()] }, true],
    ['expired or replayed flash', true, { items: [relationship()] }, false],
    ['missing authoritative card', true, { items: [] }, true],
    ['non-active Trial state', true, { items: [relationship({ trialStatus: 'UNRESOLVED' })] }, true],
  ])('emits no success for %s', async (_name, withCookie, page, consumed) => {
    jest
      .mocked(consumeMyAgentsSelection)
      .mockResolvedValue(consumed ? { relationshipId, outcomeKind: 'TRIAL_STARTED' } : null);
    jest.mocked(listEmploymentRelationships).mockResolvedValue(page as never);
    const { POST } = await import('./route');

    const response = await POST(request(withCookie));

    expect(response.status).toBe(204);
  });

  it.each([
    ['HIRE_PAID', 'Payment confirmed. Professional hired.'],
    ['HIRE_ZERO_PRICE', 'Professional hired. No payment was due.'],
  ] as const)('uses the authoritative %s commercial outcome text', async (outcomeKind, confirmation) => {
    jest.mocked(consumeMyAgentsSelection).mockResolvedValue({ relationshipId, outcomeKind });
    jest.mocked(listEmploymentRelationships).mockResolvedValue({
      items: [relationship({ acquisitionMode: 'HIRE', lifecycleState: 'CONFIGURING', trialStatus: null })],
    } as never);
    const { POST } = await import('./route');

    expect(await (await POST(request())).json()).toEqual(expect.objectContaining({ confirmation }));
  });
});
