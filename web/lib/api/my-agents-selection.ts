import 'server-only';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export const myAgentsSelectionCookie = 'waooaw_my_agents_selection';

export interface MyAgentsSelectionCreated {
  handle: string;
  expiresAt: string;
}

export interface MyAgentsSelectionConsumed {
  relationshipId: string;
  outcomeKind: 'TRIAL_STARTED' | 'HIRE_PAID' | 'HIRE_ZERO_PRICE';
}

export async function createMyAgentsSelection(
  accessToken: string,
  relationshipId: string,
  outcomeKind: MyAgentsSelectionConsumed['outcomeKind']
): Promise<MyAgentsSelectionCreated> {
  const response = await fetch(
    `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/selection-flash`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ outcomeKind }),
      cache: 'no-store',
    }
  );
  if (!response.ok) throw new Error(`Selection handoff failed with ${response.status}.`);
  return response.json() as Promise<MyAgentsSelectionCreated>;
}

export async function consumeMyAgentsSelection(
  accessToken: string,
  handle: string
): Promise<MyAgentsSelectionConsumed | null> {
  const response = await fetch(`${businessPlatformUrl}/api/v1/employment/relationships/selection-flash/consume`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ handle }),
    cache: 'no-store',
  });
  if (response.status === 204) return null;
  if (!response.ok) throw new Error(`Selection consumption failed with ${response.status}.`);
  return response.json() as Promise<MyAgentsSelectionConsumed>;
}