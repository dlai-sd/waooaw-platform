// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063, C-065

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { AccessApprovals } from './AccessApprovals';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const request = {
  requestId: 'r1',
  email: 'asha@example.com',
  role: 'pricing_admin',
  justification: 'I maintain the price list.',
  status: 'PENDING',
  requestedAt: '',
};
const grants = [
  { grantId: 'g1', email: 'yk@example.com', role: 'founder', source: 'CONFIG', revocable: false },
  { grantId: 'g2', email: 'asha@example.com', role: 'pricing_admin', source: 'APPROVAL', revocable: true },
];

type Answer = { status: number; body: unknown };

// Reads answer from the listing; every POST answers with `onPost`.
function serve(onPost: Answer | null, pending: unknown[] = [request], listingStatus = 200) {
  const mock = jest.fn(async (url: string, init?: RequestInit) => {
    const answer: Answer =
      init?.method === 'POST'
        ? (onPost ?? { status: 200, body: {} })
        : { status: listingStatus, body: url.includes('grants') ? { grants } : { requests: pending } };
    return { ok: answer.status < 400, status: answer.status, json: async () => answer.body };
  });
  global.fetch = mock as unknown as typeof fetch;
  return mock;
}

function posted(mock: ReturnType<typeof serve>) {
  return mock.mock.calls.find(([, init]) => init?.method === 'POST');
}

describe('AccessApprovals', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('shows who is waiting and who already holds a role', async () => {
    serve(null);
    render(<AccessApprovals />);

    expect(await screen.findByText('asha@example.com', { selector: 'strong' })).toBeVisible();
    expect(screen.getByText(/yk@example.com: founder \(set in the environment\)/)).toBeVisible();
    expect(screen.getAllByRole('button', { name: 'Remove' })).toHaveLength(1);
  });

  it('says so when nobody is waiting and when the list cannot be loaded', async () => {
    serve(null, []);
    const { unmount } = render(<AccessApprovals />);
    expect(await screen.findByText('No requests are waiting.')).toBeVisible();
    unmount();

    serve(null, [], 500);
    render(<AccessApprovals />);
    expect(await screen.findByText('Access management could not be loaded.')).toBeVisible();
  });

  it('approves and reloads', async () => {
    const mock = serve(null);
    render(<AccessApprovals />);

    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }));

    expect(await screen.findByText('asha@example.com: approved.')).toBeVisible();
    expect(posted(mock)?.[0]).toBe('/api/platform/access/access-requests/r1/decision');
    expect(JSON.parse(String(posted(mock)?.[1]?.body))).toEqual({ decision: 'APPROVE' });
  });

  it('rejects', async () => {
    serve(null);
    render(<AccessApprovals />);

    fireEvent.click(await screen.findByRole('button', { name: 'Reject' }));

    expect(await screen.findByText('asha@example.com: rejected.')).toBeVisible();
  });

  it('offers a multi-factor sign-in when the approval needs a fresh strong sign-in', async () => {
    serve({ status: 403, body: { code: 'PLATFORM_ACCESS_STEP_UP_REQUIRED', detail: 'Confirm with a second factor.' } });
    render(<AccessApprovals />);

    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Confirm with multi-factor sign-in' }));

    expect(screen.getByText('Confirm with a second factor.')).toBeVisible();
    expect(signIn).toHaveBeenCalledWith('keycloak', expect.objectContaining({ waooawIntent: 'LOGIN' }), {
      prompt: 'login',
      max_age: '0',
      acr_values: '2',
    });
  });

  it('shows another refusal without offering the sign-in', async () => {
    serve({ status: 500, body: {} });
    render(<AccessApprovals />);

    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }));

    expect(await screen.findByText('The decision could not be saved.')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Confirm with multi-factor sign-in' })).toBeNull();
  });

  it('removes a grant only with a reason', async () => {
    const mock = serve(null);
    const prompt = jest.spyOn(window, 'prompt');
    render(<AccessApprovals />);
    const remove = await screen.findByRole('button', { name: 'Remove' });

    prompt.mockReturnValueOnce('  ');
    fireEvent.click(remove);
    prompt.mockReturnValueOnce(null);
    fireEvent.click(remove);
    expect(posted(mock)).toBeUndefined();

    prompt.mockReturnValueOnce('left the team');
    fireEvent.click(remove);
    expect(await screen.findByText('asha@example.com: access removed.')).toBeVisible();
    expect(posted(mock)?.[0]).toBe('/api/platform/access/grants/g2/revoke');
    expect(JSON.parse(String(posted(mock)?.[1]?.body))).toEqual({ reason: 'left the team' });
  });

  it('reports a refused removal, with a fallback', async () => {
    serve({ status: 409, body: { detail: 'Protected.' } });
    jest.spyOn(window, 'prompt').mockReturnValue('reason');
    render(<AccessApprovals />);

    fireEvent.click(await screen.findByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(screen.getByText('Protected.')).toBeVisible());

    serve({ status: 500, body: {} });
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(screen.getByText('Not removed.')).toBeVisible());
  });
});
