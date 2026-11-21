// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import type { PricingKind, PricingVersion } from '@/lib/pricing-admin-client';
import type { Simulation } from '@/lib/pricing-admin-types';

export const simulationFixture: Simulation = {
  draftId: 'd1',
  kind: 'PACKAGE',
  state: 'SIMULATED',
  simulatedAt: '2026-11-20T09:00:00Z',
  costFloorPaise: 80000,
  basePricePaise: 169492,
  gstPaise: 30508,
  priceInclGstPaise: 200000,
  marginPercent: 52.8,
  minimumCompliantPricePaise: 150000,
  diff: {
    changes: [
      { path: 'priceInclGstPaise', before: '180000', after: '200000' },
      { path: 'displayName', after: 'Starter' },
    ],
  },
  profiles: [
    { profile: 'TYPICAL', expectedMonthlyCostPaise: 90000, marginPercent: 46.9, dayOneExposurePaise: 3000 },
    {
      profile: 'CUSTOM',
      personaName: 'Busy salon',
      expectedMonthlyCostPaise: 110000,
      marginPercent: 35,
      proRataRefundPaise: 400,
    },
  ],
  warnings: [
    { code: 'NEEDS_SECOND_CONFIRMATION', componentId: 'posts', message: 'Price changes by more than 30 percent.' },
  ],
  affectedPackages: [
    {
      packageVersionId: 'p1',
      subjectKey: 'package:dma|v3|STARTER',
      currentFloorPaise: 80000,
      newFloorPaise: 210000,
      priceInclGstPaise: 200000,
      belowFloor: true,
    },
    {
      packageVersionId: 'p2',
      subjectKey: 'package:dma|v3|PRO',
      currentFloorPaise: 80000,
      newFloorPaise: 90000,
      priceInclGstPaise: 400000,
      belowFloor: false,
    },
  ],
};

export const versionId = '7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11';

export function fakeResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (name: string) => headers[name.toLowerCase()] ?? null },
    json: async () => {
      if (body === undefined) throw new Error('not json');
      return body;
    },
  } as unknown as Response;
}

export function versionFixture(overrides: Partial<PricingVersion> = {}): PricingVersion {
  const kind: PricingKind = overrides.kind ?? 'RATE';
  return {
    versionId,
    kind,
    subjectKey: 'thread:llm',
    versionNo: 2,
    state: 'DRAFT',
    body: { threadId: 'llm' },
    bodyDigest: 'abcdef0123456789abcdef',
    seed: false,
    effectiveFrom: null,
    evidenceId: null,
    needsSecondConfirmation: false,
    createdBy: 'admin-1',
    createdAt: '2026-11-20T09:00:00Z',
    ...overrides,
  };
}
