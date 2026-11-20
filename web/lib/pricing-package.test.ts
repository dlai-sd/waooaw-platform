// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import {
  allocationTotalPaise,
  buildPackage,
  derivedPrice,
  emptyComponent,
  emptyPackage,
  packageFromBody,
  PROACTIVE_COMPONENT_ID,
  type PackageState,
} from './pricing-package';

function validPackage(): PackageState {
  const base = emptyPackage();
  return {
    ...base,
    agentType: 'dma',
    agentVersion: 'v3',
    packageCode: 'STARTER',
    displayName: 'Starter',
    billingPeriodDays: '30',
    priceInr: '2000',
    gstRatePercent: '18',
    infrastructureInr: '0',
    components: [
      {
        ...emptyComponent('CONTENT_DRAFT'),
        quantity: '4',
        allocationInr: '1500',
        recipe: [{ threadId: 'llm', unitsPerUnit: '3' }],
      },
      { ...base.components[0], allocationInr: '500' },
    ],
  };
}

test('a new package starts with the fixed proactive row and no invented price', () => {
  const state = emptyPackage();

  expect(state.components).toHaveLength(1);
  expect(state.components[0]).toMatchObject({ componentId: PROACTIVE_COMPONENT_ID, quantity: '30' });
  expect(state.priceInr).toBe('');
  expect(state.gstRatePercent).toBe('');
});

test('a valid package builds the published body and subject key', () => {
  const built = buildPackage(validPackage());

  expect(built.ok).toBe(true);
  if (built.ok) {
    expect(built.subjectKey).toBe('package:dma|v3|STARTER');
    expect(built.body).toMatchObject({
      priceInclGstPaise: 200000,
      gstRatePercent: 18,
      infrastructureSharePaise: 0,
      billingPeriodDays: 30,
    });
    expect(built.body.components).toEqual([
      expect.objectContaining({
        componentId: 'CONTENT_DRAFT',
        quantity: 4,
        priceAllocationPaise: 150000,
        recipe: [{ threadId: 'llm', unitsPerUnit: 3 }],
      }),
      expect.objectContaining({
        componentId: 'PROACTIVE_MESSAGE',
        quantity: 30,
        priceAllocationPaise: 50000,
        recipe: [],
      }),
    ]);
  }
});

test('every problem is reported together', () => {
  const state = validPackage();
  state.agentType = '';
  state.priceInr = '0';
  state.billingPeriodDays = '400';
  state.gstRatePercent = '101';
  state.infrastructureInr = 'x';
  state.components = [
    {
      ...emptyComponent(''),
      quantity: '0',
      allocationInr: 'x',
      selectableMaximum: '0',
      recipe: [{ threadId: ' ', unitsPerUnit: '0' }],
    },
    { ...emptyComponent(PROACTIVE_COMPONENT_ID), quantity: '29', allocationInr: '1' },
  ];

  const built = buildPackage(state);

  expect(built.ok).toBe(false);
  if (!built.ok) {
    const text = built.errors.join('\n');
    for (const fragment of [
      'Agent type is required.',
      'Price including GST',
      'Billing period',
      'GST rate',
      'Infrastructure share',
      'component identifier is required',
      'quantity must be',
      'price allocation must be',
      'selectable maximum',
      'every recipe row needs a thread',
      'recipe units',
      'fixed at 30',
    ]) {
      expect(text).toContain(fragment);
    }
  }
});

test('a package with no components is refused', () => {
  const built = buildPackage({ ...validPackage(), components: [] });
  expect(built).toEqual({ ok: false, errors: ['Add at least one component.'] });
});

test('a stored body round trips through the editor state', () => {
  const built = buildPackage(validPackage());
  if (!built.ok) throw new Error('expected a valid package');

  const rebuilt = buildPackage(packageFromBody(built.body));

  expect(rebuilt).toEqual(built);
  expect(packageFromBody({}).components).toEqual([]);
  expect(packageFromBody({ components: [{ componentId: 'A', topupAllowed: true }] }).components[0]).toMatchObject({
    cadence: 'SPREAD',
    topupAllowed: true,
    recipe: [],
  });
});

test('allocations are summed in paise and the base price is derived for display', () => {
  expect(allocationTotalPaise(validPackage().components)).toBe(200000);
  expect(allocationTotalPaise([{ ...emptyComponent('A'), allocationInr: 'bad' }])).toBe(0);
  expect(derivedPrice('118', '18')).toEqual({ basePaise: 10000, gstPaise: 1800 });
  expect(derivedPrice('', '18')).toBeNull();
  expect(derivedPrice('118', 'x')).toBeNull();
});
