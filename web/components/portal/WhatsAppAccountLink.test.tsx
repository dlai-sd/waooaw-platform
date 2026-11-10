import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { WhatsAppAccountLink } from './WhatsAppAccountLink';

jest.mock('@/components/auth/SignOutCommand', () => ({
  SignOutCommand: ({ label }: { label: string }) => <button type="button">{label}</button>,
}));

const pending = {
  linkId: '00000000-0000-4000-8000-000000000001',
  state: 'PENDING_PORTAL_APPROVAL',
  maskedMobile: '+1******0100',
  expiresAt: '2026-11-06T18:00:00Z',
};

function response(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe('WhatsApp account link', () => {
  const fetchMock = jest.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    global.fetch = fetchMock;
    localStorage.clear();
    sessionStorage.clear();
  });

  it('requires explicit portal approval and checks status without persisting the instruction', async () => {
    fetchMock
      .mockResolvedValueOnce(response(pending))
      .mockResolvedValueOnce(
        response({
          ...pending,
          state: 'PENDING_WHATSAPP_CONFIRMATION',
          whatsAppConfirmation: 'LINK synthetic-encrypted-instruction',
        })
      )
      .mockResolvedValueOnce(response({ ...pending, state: 'LINKED' }));
    render(<WhatsAppAccountLink />);
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Start WhatsApp link' }));
    fireEvent.click(
      await screen.findByRole('button', {
        name: 'Approve linking this number to my account',
      })
    );
    expect(await screen.findByLabelText('WhatsApp confirmation message')).toHaveValue(
      'LINK synthetic-encrypted-instruction'
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const start = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(start).toEqual({
      command: 'START',
      idempotencyKey: expect.any(String),
    });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      command: 'APPROVE',
      linkId: pending.linkId,
      idempotencyKey: expect.any(String),
    });
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(1);
    expect(sessionStorage.getItem('waooaw:whatsapp-account-link-id')).toBe(pending.linkId);
    expect(sessionStorage.getItem('waooaw:whatsapp-account-link-id')).not.toContain('LINK ');
    fireEvent.click(screen.getByRole('button', { name: 'Check link status' }));
    expect(await screen.findByText(/Your number is linked/)).toBeInTheDocument();
    expect(screen.queryByLabelText('WhatsApp confirmation message')).not.toBeInTheDocument();
    expect(JSON.parse(fetchMock.mock.calls[2][1].body).command).toBe('STATUS');
  });

  it('retries an uncertain start with the same idempotency key and does not approve automatically', async () => {
    fetchMock.mockRejectedValueOnce(new Error('synthetic network failure')).mockResolvedValueOnce(response(pending));
    render(<WhatsAppAccountLink />);
    fireEvent.click(screen.getByRole('button', { name: 'Start WhatsApp link' }));
    await screen.findByRole('alert');
    fireEvent.click(screen.getByRole('button', { name: 'Start WhatsApp link' }));
    await screen.findByRole('button', {
      name: 'Approve linking this number to my account',
    });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).idempotencyKey).toBe(
      JSON.parse(fetchMock.mock.calls[1][1].body).idempotencyKey
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('cancels the server challenge before offering a new request and preserves uncertain retry keys', async () => {
    fetchMock
      .mockResolvedValueOnce(response(pending))
      .mockRejectedValueOnce(new Error('synthetic cancellation uncertainty'))
      .mockResolvedValueOnce(response({ ...pending, state: 'CANCELLED' }));
    render(<WhatsAppAccountLink />);
    fireEvent.click(screen.getByRole('button', { name: 'Start WhatsApp link' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel this link request' }));
    await screen.findByRole('alert');
    expect(screen.queryByRole('button', { name: 'Start a new link request' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel this link request' }));
    await screen.findByRole('button', { name: 'Start a new link request' });
    const first = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(first).toEqual({
      command: 'CANCEL',
      linkId: pending.linkId,
      idempotencyKey: expect.any(String),
    });
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual(first);
  });

  it('offers fresh-sign-in recovery rather than implying linking succeeded', async () => {
    fetchMock.mockResolvedValue(response({ code: 'IDENTITY_STEP_UP_REQUIRED' }, 403));
    render(<WhatsAppAccountLink />);
    fireEvent.click(screen.getByRole('button', { name: 'Start WhatsApp link' }));
    expect(await screen.findByRole('button', { name: 'Sign out to sign in again' })).toBeInTheDocument();
    expect(screen.queryByText(/Your number is linked/)).not.toBeInTheDocument();
  });

  it('allows explicit recovery after the backend expires a pending approval', async () => {
    fetchMock
      .mockResolvedValueOnce(response(pending))
      .mockResolvedValueOnce(response({ code: 'IDENTITY_CHALLENGE_EXPIRED' }, 410));
    render(<WhatsAppAccountLink />);
    fireEvent.click(screen.getByRole('button', { name: 'Start WhatsApp link' }));
    fireEvent.click(
      await screen.findByRole('button', {
        name: 'Approve linking this number to my account',
      })
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Start a new link request' }));
    expect(await screen.findByRole('button', { name: 'Start WhatsApp link' })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('rejects a pending response without an actual confirmation instruction', async () => {
    fetchMock.mockResolvedValue(response({ ...pending, state: 'PENDING_WHATSAPP_CONFIRMATION' }));
    render(<WhatsAppAccountLink />);
    fireEvent.click(screen.getByRole('button', { name: 'Start WhatsApp link' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('could not be completed'));
    expect(screen.queryByLabelText('WhatsApp confirmation message')).not.toBeInTheDocument();
  });

  it('requires a separate checked consent before relationship channel binding', async () => {
    fetchMock
      .mockResolvedValueOnce(response(pending))
      .mockResolvedValueOnce(
        response({
          ...pending,
          state: 'PENDING_WHATSAPP_CONFIRMATION',
          whatsAppConfirmation: 'LINK synthetic-encrypted-instruction',
        })
      )
      .mockResolvedValueOnce(response({ ...pending, state: 'LINKED' }))
      .mockResolvedValueOnce(
        response({
          schemaVersion: '1.0',
          relationshipId: '00000000-0000-4000-8000-000000000002',
          bindingId: '00000000-0000-4000-8000-000000000003',
          channel: 'WHATSAPP',
          status: 'ACTIVE',
          assurance: 'TIER_4_PORTAL_FRESH',
        })
      );
    render(
      <WhatsAppAccountLink
        relationships={[
          {
            relationshipId: '00000000-0000-4000-8000-000000000002',
            label: 'Digital Marketing - active',
          },
        ]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Start WhatsApp link' }));
    fireEvent.click(
      await screen.findByRole('button', {
        name: 'Approve linking this number to my account',
      })
    );
    await screen.findByLabelText('WhatsApp confirmation message');
    fireEvent.click(screen.getByRole('button', { name: 'Check link status' }));
    fireEvent.change(await screen.findByLabelText('Choose an active relationship'), {
      target: { value: '00000000-0000-4000-8000-000000000002' },
    });

    const approveButton = screen.getByRole('button', {
      name: 'Approve WhatsApp channel access',
    });
    expect(approveButton).toBeDisabled();
    fireEvent.click(
      screen.getByLabelText(
        'I approve WhatsApp messages for this relationship. I understand guest history will not be transferred.'
      )
    );
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(4);
      expect(
        screen.getByText('WhatsApp is connected to this relationship. Guest history was not transferred.')
      ).toBeInTheDocument();
    });
    expect(fetchMock.mock.calls[3][0]).toBe('/api/relationships/00000000-0000-4000-8000-000000000002/whatsapp-channel');
    expect(JSON.parse(fetchMock.mock.calls[3][1].body)).toEqual({
      identityAccountLinkId: pending.linkId,
      consentToRelationshipChannel: true,
    });
  });
});
