// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003
// Constitutional basis: C-009, C-023, C-059, C-063

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { PlatformAccess } from '@/lib/platform-access';
import { RequestAccessPanel } from './RequestAccessPanel';

const access: PlatformAccess = {
  administrator: false,
  founder: false,
  emailVerified: true,
  email: 'asha@example.com',
  requestableRoles: ['pricing_admin', 'founder'],
  requests: [],
};

function fill(text: string) {
  fireEvent.change(screen.getByLabelText('Why do you need it?'), { target: { value: text } });
}

describe('RequestAccessPanel', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('asks for a verified email first', () => {
    render(<RequestAccessPanel access={{ ...access, emailVerified: false }} />);

    expect(screen.getByRole('alert')).toHaveTextContent('verified');
  });

  it('needs a real justification before it lets the request go', () => {
    render(<RequestAccessPanel access={access} />);
    const send = screen.getByRole('button', { name: 'Send request' });

    expect(send).toBeDisabled();
    fill('too short');
    expect(send).toBeDisabled();
    fill('I maintain the price list.');
    expect(send).toBeEnabled();
  });

  it('sends the chosen role and justification', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    render(<RequestAccessPanel access={access} />);
    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'founder' } });
    fill('  I maintain the price list.  ');

    fireEvent.click(screen.getByRole('button', { name: 'Send request' }));

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Request sent'));
    const [url, init] = jest.mocked(global.fetch).mock.calls[0];
    expect(url).toBe('/api/platform/access/access-requests');
    expect(JSON.parse(String(init?.body))).toEqual({ role: 'founder', justification: 'I maintain the price list.' });
  });

  it('shows the reason a request is refused, with a fallback', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'You already have a request.' }) })
      .mockResolvedValueOnce({ ok: false, json: async () => Promise.reject(new SyntaxError('not json')) })
      .mockRejectedValueOnce(new Error('offline'));
    render(<RequestAccessPanel access={access} />);
    fill('I maintain the price list.');
    const send = screen.getByRole('button', { name: 'Send request' });

    fireEvent.click(send);
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('You already have a request.'));
    fireEvent.click(send);
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('could not be sent.'));
    fireEvent.click(send);
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Try again.'));
  });

  it('lists earlier requests and blocks a second while one is pending', () => {
    render(
      <RequestAccessPanel
        access={{
          ...access,
          administrator: true,
          requests: [
            {
              requestId: 'r1',
              email: 'asha@example.com',
              role: 'pricing_admin',
              justification: '',
              status: 'PENDING',
              requestedAt: '',
            },
            {
              requestId: 'r2',
              email: 'asha@example.com',
              role: 'other',
              justification: '',
              status: 'REJECTED',
              requestedAt: '',
            },
          ],
        }}
      />
    );
    fill('I maintain the price list.');

    expect(screen.getByText('You already hold a staff role.')).toBeVisible();
    expect(screen.getByText('You already have a request waiting for a decision.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Send request' })).toBeDisabled();
    expect(screen.getByText('Pricing administrator: pending')).toBeVisible();
    expect(screen.getByText('other: rejected')).toBeVisible();
  });

  it('shows the person their own sign-in ID so the Founder can tie a role to it, and nothing when there is none', () => {
    const { rerender } = render(<RequestAccessPanel access={access} subject="8f1c2a7e-3b9d-4c55-a1f0-9a7d2c4e6b10" />);
    expect(screen.getByText('8f1c2a7e-3b9d-4c55-a1f0-9a7d2c4e6b10')).toBeVisible();
    expect(screen.getByText(/give this ID to the Founder/)).toBeVisible();

    rerender(<RequestAccessPanel access={access} subject={null} />);
    expect(screen.queryByText(/Your sign-in ID/)).not.toBeInTheDocument();
  });

  it('does not show the sign-in ID when the email is not verified', () => {
    render(
      <RequestAccessPanel access={{ ...access, emailVerified: false }} subject="8f1c2a7e-3b9d-4c55-a1f0-9a7d2c4e6b10" />
    );
    expect(screen.queryByText('8f1c2a7e-3b9d-4c55-a1f0-9a7d2c4e6b10')).not.toBeInTheDocument();
  });
});
