// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { buildBody, formSpecs, valuesFromBody } from './pricing-forms';

test('a rate form becomes the published body and the owner subject key', () => {
  const built = buildBody(formSpecs.RATE, {
    threadId: 'llm',
    provider: 'p',
    unit: 'token',
    rawCostPaise: '3',
    fxBufferPct: '2',
    opsOverheadPct: '5.5',
    riskPremiumPct: '0',
  });

  expect(built).toEqual({
    ok: true,
    subjectKey: 'thread:llm',
    body: {
      threadId: 'llm',
      provider: 'p',
      unit: 'token',
      rawCostPaise: 3,
      fxBufferPct: 2,
      opsOverheadPct: 5.5,
      riskPremiumPct: 0,
    },
  });
});

test('rupee fields are sent as paise and optional fields are left out', () => {
  const built = buildBody(formSpecs.BUDGET, {
    scope: 'ENVIRONMENT_CEILING',
    ref: 'demo',
    maximumPaise: '500',
    perVisitorMessages: '',
    perDayNewSessions: '',
  });

  expect(built).toEqual({
    ok: true,
    subjectKey: 'budget:ENVIRONMENT_CEILING|demo',
    body: { scope: 'ENVIRONMENT_CEILING', ref: 'demo', maximumPaise: 50000 },
  });
});

test('every problem is named against its field', () => {
  const built = buildBody(formSpecs.POLICY, {
    minimumMarginPct: '-1',
    paymentGraceDays: '1.5',
    sunsetNoticeDays: '',
    costToleranceFraction: 'x',
    upgradeTiming: 'SOMETIME',
  });

  expect(built.ok).toBe(false);
  if (!built.ok) {
    expect(Object.keys(built.errors)).toEqual(
      expect.arrayContaining([
        'minimumMarginPct',
        'paymentGraceDays',
        'sunsetNoticeDays',
        'costToleranceFraction',
        'upgradeTiming',
        'costAlertFraction',
      ])
    );
  }
});

test('a grant carries units as a JSON object of numbers', () => {
  const grant = {
    kind: 'TRIAL',
    agentType: 'dma',
    agentVersion: 'v3',
    paise: '',
    durationDays: '7',
    windowDays: '',
  };

  expect(buildBody(formSpecs.GRANT, { ...grant, units: '{"llm":100}' })).toMatchObject({
    ok: true,
    subjectKey: 'grant:TRIAL|dma|v3',
    body: { units: { llm: 100 }, durationDays: 7 },
  });
  for (const units of ['not json', '[1]', '{"llm":"x"}', '{"llm":-1}', 'null']) {
    expect(buildBody(formSpecs.GRANT, { ...grant, units }).ok).toBe(false);
  }
});

test('a coupon needs exactly one of percent or amount and a UTC expiry', () => {
  const coupon = {
    code: 'WELCOME',
    agentType: 'dma',
    agentVersion: 'v3',
    capPaise: '100',
    expiresAt: '2027-01-01T00:00',
    reason: 'Goodwill after an outage',
    maxRedemptions: '50',
  };

  expect(buildBody(formSpecs.COUPON, { ...coupon, percent: '10', amountPaise: '' })).toMatchObject({
    ok: true,
    body: { percent: 10, capPaise: 10000, expiresAt: '2027-01-01T00:00:00.000Z' },
  });
  expect(buildBody(formSpecs.COUPON, { ...coupon, percent: '10', amountPaise: '5' }).ok).toBe(false);
  expect(buildBody(formSpecs.COUPON, { ...coupon, percent: '', amountPaise: '' }).ok).toBe(false);
  expect(buildBody(formSpecs.COUPON, { ...coupon, percent: '10', amountPaise: '', expiresAt: 'soon' }).ok).toBe(false);
  expect(
    buildBody(formSpecs.COUPON, { ...coupon, percent: '', amountPaise: '5', expiresAt: '2027-01-01T00:00:00+05:30' })
  ).toMatchObject({
    ok: true,
    body: { amountPaise: 500 },
  });
  expect(buildBody(formSpecs.COUPON, { ...coupon, percent: '', amountPaise: '5.555' }).ok).toBe(false);
});

test('a stored body fills the form again', () => {
  expect(
    valuesFromBody(formSpecs.COUPON, {
      code: 'WELCOME',
      percent: 10,
      capPaise: 10000,
      expiresAt: '2027-01-01T00:00:00.000Z',
      maxRedemptions: 50,
    })
  ).toMatchObject({
    code: 'WELCOME',
    percent: '10',
    capPaise: '100.00',
    expiresAt: '2027-01-01T00:00',
    amountPaise: '',
  });
  expect(valuesFromBody(formSpecs.GRANT, { units: { llm: 1 } }).units).toBe('{"llm":1}');
  expect(valuesFromBody(formSpecs.RATE, undefined).threadId).toBe('');
});
