/** @jest-environment node */

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-04
// Constitutional basis: C-001, C-023, C-059, C-063, ADR-051

import { ResponseError } from '@/lib/api/generated/workbench-v1/src';
import { getWorkbench } from './workbench';

const getWorkbenchRaw = jest.fn();
const listGoals = jest.fn();
const getPlan = jest.fn();
const listCapabilities = jest.fn();
const getWallet = jest.fn();
const listEvidence = jest.fn();
const listWorkItems = jest.fn();

jest.mock('@/lib/api/generated/workbench-v1/src', () => {
  class FakeResponseError extends Error {
    constructor(public response: Response) {
      super('response');
    }
  }
  return {
    Configuration: jest.fn(),
    ResponseError: FakeResponseError,
    WorkbenchApi: jest.fn().mockImplementation(() => ({
      getWorkbenchRaw,
      listWorkbenchGoalsRaw: listGoals,
      getCurrentWorkbenchPlanRaw: getPlan,
      listWorkbenchCapabilitiesRaw: listCapabilities,
      getWorkbenchWalletRaw: getWallet,
      listWorkbenchEvidenceRaw: listEvidence,
      listWorkbenchWorkItemsRaw: listWorkItems,
    })),
  };
});

const relationshipId = '00000000-0000-4000-8000-000000000121';

function ok(body: unknown, headers: Record<string, string> = {}) {
  return { raw: new Response(JSON.stringify(body), { status: 200, headers }) };
}

function failure(status: number, body: unknown) {
  return new (ResponseError as unknown as new (response: Response) => Error)(
    new Response(JSON.stringify(body), { status })
  );
}

describe('workbench loader', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    for (const read of [listGoals, getPlan, listCapabilities, getWallet, listEvidence, listWorkItems]) {
      read.mockResolvedValue(ok({ items: [] }));
    }
  });

  it('loads the projection with its version and the panel data', async () => {
    getWorkbenchRaw.mockResolvedValue(ok({ audience: 'customer_owner', blocks: [] }, { ETag: '"relationship-7"' }));

    const result = await getWorkbench(relationshipId, 'access-token');

    expect(result.state).toBe('available');
    if (result.state !== 'available') return;
    expect(result.snapshot.version).toBe('relationship-7');
    expect(result.snapshot.wallet).toEqual({ items: [] });
    expect(getWorkbenchRaw).toHaveBeenCalledWith(
      expect.objectContaining({ relationshipId, xExperienceCapabilities: expect.stringContaining('channel=WEB') }),
      { cache: 'no-store' }
    );
  });

  it('does not read money data for a beneficiary', async () => {
    getWorkbenchRaw.mockResolvedValue(ok({ audience: 'beneficiary', blocks: [] }, { ETag: '"relationship-1"' }));

    const result = await getWorkbench(relationshipId, 'access-token');

    expect(getWallet).not.toHaveBeenCalled();
    expect(result.state === 'available' && result.snapshot.wallet).toBeNull();
  });

  it('keeps the workbench available with an honest gap when one panel read fails', async () => {
    getWorkbenchRaw.mockResolvedValue(ok({ audience: 'customer_owner', blocks: [] }, { ETag: '"relationship-2"' }));
    getWallet.mockRejectedValue(new Error('wbe down'));

    const result = await getWorkbench(relationshipId, 'access-token');

    expect(result.state === 'available' && result.snapshot.wallet).toBeNull();
    expect(result.state === 'available' && result.snapshot.goals).toEqual({ items: [] });
  });

  it('reports the disabled flag so the page can fall back to the legacy workspace', async () => {
    getWorkbenchRaw.mockRejectedValue(failure(404, { code: 'WORKBENCH_DISABLED' }));

    await expect(getWorkbench(relationshipId, 'access-token')).resolves.toEqual({ state: 'disabled' });
  });

  it('reports unavailable for any other failure or a missing version', async () => {
    getWorkbenchRaw.mockRejectedValueOnce(failure(503, { code: 'WORKBENCH_UNAVAILABLE' }));
    await expect(getWorkbench(relationshipId, 'access-token')).resolves.toEqual({ state: 'unavailable' });

    getWorkbenchRaw.mockResolvedValueOnce(ok({ audience: 'customer_owner', blocks: [] }));
    await expect(getWorkbench(relationshipId, 'access-token')).resolves.toEqual({ state: 'unavailable' });
  });
});
