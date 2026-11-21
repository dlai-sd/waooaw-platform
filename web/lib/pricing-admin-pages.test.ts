/** @jest-environment node */

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { redirect } from 'next/navigation';
import { versionFixture } from '@/lib/pricing-admin-test-data';
import { catalogueFrom, loadVersions, periodFrom, requirePricingPage, wireShape } from '@/lib/pricing-admin-pages';
import { getServerAccessToken } from '@/lib/server-auth';

const mockListDrafts = jest.fn();
const mockListVersions = jest.fn();

jest.mock('next/navigation', () => ({
  redirect: jest.fn(() => {
    throw new Error('redirected');
  }),
}));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/lib/pricing-admin-server', () => ({
  pricingApis: () => ({
    drafts: { listPricingDrafts: mockListDrafts },
    versions: { listPricingVersions: mockListVersions },
  }),
}));

function token(roles: string[]): string {
  return `e30.${Buffer.from(JSON.stringify({ sub: 'u', realm_access: { roles } })).toString('base64url')}.sig`;
}

test('only pricing administrators and the Founder pass the page gate', async () => {
  jest.mocked(getServerAccessToken).mockResolvedValueOnce(undefined);
  await expect(requirePricingPage()).rejects.toThrow('redirected');
  jest.mocked(getServerAccessToken).mockResolvedValueOnce(token(['customer']));
  await expect(requirePricingPage()).rejects.toThrow('redirected');
  expect(redirect).toHaveBeenCalledWith('/home');

  const admin = token(['pricing_admin']);
  jest.mocked(getServerAccessToken).mockResolvedValueOnce(admin);
  await expect(requirePricingPage()).resolves.toEqual({ accessToken: admin, isFounder: false });
  const founder = token(['founder']);
  jest.mocked(getServerAccessToken).mockResolvedValueOnce(founder);
  await expect(requirePricingPage()).resolves.toEqual({ accessToken: founder, isFounder: true });
});

test('dates from the generated client become wire strings', () => {
  expect(wireShape({ at: new Date('2026-11-01T00:00:00Z') })).toEqual({ at: '2026-11-01T00:00:00.000Z' });
});

test('drafts and published versions merge by id and a draft wins', async () => {
  const published = versionFixture({ versionId: 'a', state: 'EFFECTIVE' });
  const newer = versionFixture({ versionId: 'a', state: 'SUPERSEDED' });
  const other = versionFixture({ versionId: 'b' });
  mockListVersions.mockResolvedValueOnce({ items: [published] });
  mockListDrafts.mockResolvedValueOnce({ items: [newer, other] });

  const merged = await loadVersions('t', 'RATE');

  expect(merged?.map((version) => `${version.versionId}:${version.state}`)).toEqual(['a:SUPERSEDED', 'b:DRAFT']);
});

test('an unreachable owner is reported as null, not as an empty list', async () => {
  mockListVersions.mockRejectedValueOnce(new Error('down'));
  mockListDrafts.mockResolvedValueOnce({ items: [] });
  await expect(loadVersions('t', 'RATE')).resolves.toBeNull();
});

test('the catalogue takes unit costs from effective rates and agents from packages and grants', () => {
  const effective = versionFixture({ state: 'EFFECTIVE', body: { threadId: 'llm', unit: 'token', rawCostPaise: 3 } });
  const draft = versionFixture({ state: 'DRAFT', body: { threadId: 'draft-only', unit: 'x', rawCostPaise: 1 } });
  const malformed = versionFixture({ state: 'EFFECTIVE', body: { threadId: 'bad' } });
  const agentA = versionFixture({ body: { agentType: 'dma', agentVersion: 'v3' } });
  const agentB = versionFixture({ body: { agentType: 'dma', agentVersion: 'v3' } });
  const noAgent = versionFixture({ body: {} });

  expect(catalogueFrom([effective, draft, malformed], [agentA, agentB, noAgent])).toEqual({
    agents: [{ agentType: 'dma', agentVersion: 'v3' }],
    threads: [{ threadId: 'llm', unit: 'token', rawCostPaise: 3 }],
  });
});

test('only a plain calendar date is accepted as a reporting period', () => {
  expect(periodFrom('2026-11-01')).toBe('2026-11-01');
  expect(periodFrom(['2026-11-02', 'x'])).toBe('2026-11-02');
  expect(periodFrom('yesterday')).toBe('');
  expect(periodFrom(undefined)).toBe('');
});
