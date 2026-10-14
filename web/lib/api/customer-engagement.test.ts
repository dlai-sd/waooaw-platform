import { RelationshipWorkspaceApi } from '@/lib/api/generated/apis/RelationshipWorkspaceApi';
import { getCustomerEngagementProgress } from './customer-engagement';

const getProgress = jest.fn();

jest.mock('@/lib/api/generated/apis/RelationshipWorkspaceApi', () => ({
  RelationshipWorkspaceApi: jest.fn().mockImplementation(() => ({
    getCustomerEngagementProgress: getProgress,
  })),
}));

describe('customer engagement API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('requests the owner-backed projection without caching it', async () => {
    const projection = { relationshipId: '00000000-0000-0000-0000-000000000121' };
    getProgress.mockResolvedValue(projection);

    await expect(getCustomerEngagementProgress('00000000-0000-0000-0000-000000000121', 'access-token')).resolves.toBe(
      projection
    );
    expect(RelationshipWorkspaceApi).toHaveBeenCalledTimes(1);
    expect(getProgress).toHaveBeenCalledWith(
      { relationshipId: '00000000-0000-0000-0000-000000000121' },
      { cache: 'no-store' }
    );
  });
});
