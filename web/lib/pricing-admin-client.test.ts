// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import {
  formatInr,
  inrFromPaise,
  packageSubjectKey,
  paiseFromInr,
  problemText,
  subjectKeyFor,
  versionTag,
} from './pricing-admin-client';
import { pricingCall } from './pricing-admin-call';
import { fakeResponse } from './pricing-admin-test-data';

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
});

test('the version tag matches the owner ETag', () => {
  expect(versionTag({ versionNo: 3, state: 'DRAFT', bodyDigest: 'abcdef0123456789ffff' })).toBe(
    '3:DRAFT:abcdef0123456789'
  );
});

test('rupees become whole paise and anything finer is refused', () => {
  expect(paiseFromInr('2000')).toBe(200000);
  expect(paiseFromInr(' 19.99 ')).toBe(1999);
  expect(paiseFromInr('0.5')).toBe(50);
  expect(paiseFromInr('1.234')).toBeNull();
  expect(paiseFromInr('-1')).toBeNull();
  expect(paiseFromInr('abc')).toBeNull();
  expect(paiseFromInr('')).toBeNull();
  expect(inrFromPaise(200000)).toBe('2000.00');
  expect(inrFromPaise('x')).toBe('');
  expect(formatInr(200000)).toBe('INR 2,000.00');
});

test('problems read in plain language and carry the owner numbers', () => {
  expect(problemText({ code: 'PRICING_BELOW_FLOOR', minimumCompliantPricePaise: 123400 })).toBe(
    'The price is below the cost floor. Lowest compliant price: INR 1,234.00.'
  );
  expect(problemText({ code: 'PRICING_CEILING_BELOW_OPEN_RESERVATIONS', blockingPaise: 2200 })).toContain('INR 22.00');
  expect(problemText({ code: 'PACKAGE_COMPONENT_NOT_AVAILABLE', componentId: 'posts' })).toContain('Component: posts.');
  expect(problemText({ code: 'SOMETHING_UNPUBLISHED' })).toBe(problemText({ code: 'PRICING_UNAVAILABLE' }));
  expect(problemText({})).toContain('unavailable');
});

test('subject keys follow the owner convention', () => {
  expect(subjectKeyFor('RATE', { threadId: 'llm' })).toBe('thread:llm');
  expect(subjectKeyFor('POLICY', {})).toBe('policy:platform');
  expect(subjectKeyFor('GRANT', { kind: 'SETUP', agentType: 'dma', agentVersion: 'v3' })).toBe('grant:SETUP|dma|v3');
  expect(subjectKeyFor('BUDGET', { scope: 'ENVIRONMENT_CEILING', ref: 'demo' })).toBe(
    'budget:ENVIRONMENT_CEILING|demo'
  );
  expect(subjectKeyFor('COUPON', { code: 'WELCOME' })).toBe('coupon:WELCOME');
  expect(packageSubjectKey({ agentType: 'dma', agentVersion: 'v3', packageCode: 'STARTER' })).toBe(
    'package:dma|v3|STARTER'
  );
});

test('a read sends no idempotency key and a write sends one with a correlation id', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, { ok: 1 }, { etag: '"1:DRAFT:abc"' }));

  const read = await pricingCall('GET', 'drafts?kind=RATE');
  const write = await pricingCall('POST', 'drafts', { a: 1 });

  expect(read).toMatchObject({ ok: true, status: 200, etag: '"1:DRAFT:abc"', data: { ok: 1 } });
  expect(write.ok).toBe(true);
  const [readUrl, readInit] = jest.mocked(global.fetch).mock.calls[0];
  const [, writeInit] = jest.mocked(global.fetch).mock.calls[1];
  expect(readUrl).toBe('/api/admin/pricing/drafts?kind=RATE');
  expect((readInit?.headers as Record<string, string>)['Idempotency-Key']).toBeUndefined();
  expect((writeInit?.headers as Record<string, string>)['Idempotency-Key']).toMatch(/[0-9a-f-]{36}/);
  expect(writeInit?.body).toBe('{"a":1}');
});

test('failures become problems and an unreachable server becomes unavailable', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(409, { code: 'PRICING_VERSION_CONFLICT' }));
  expect(await pricingCall('PUT', 'drafts/x', {})).toEqual({
    ok: false,
    status: 409,
    problem: { code: 'PRICING_VERSION_CONFLICT' },
  });
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(502, undefined));
  expect(await pricingCall('GET', 'live-margin')).toEqual({ ok: false, status: 502, problem: {} });
  global.fetch = jest.fn().mockRejectedValue(new Error('offline'));
  expect(await pricingCall('GET', 'live-margin')).toEqual({
    ok: false,
    status: 0,
    problem: { code: 'PRICING_UNAVAILABLE' },
  });
});
