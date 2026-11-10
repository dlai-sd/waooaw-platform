import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { WhatsAppPhoneChange } from './WhatsAppPhoneChange';

jest.mock('@/components/auth/SignOutCommand', () => ({
  SignOutCommand: ({ label }: { label: string }) => <button type="button">{label}</button>,
}));

const pending = {
  challengeId: '00000000-0000-4000-8000-000000000001',
  state: 'OTP_REQUIRED',
  maskedMobile: '+1******0100',
  expiresAt: '2026-11-07T10:00:00Z',
  relationshipApprovalRequired: true,
};
const response = (value: unknown, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => value,
});

describe('Customer-initiated phone change', () => {
  const fetchMock = jest.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    global.fetch = fetchMock;
    sessionStorage.clear();
    localStorage.clear();
  });

  it('does not initiate verification on page load', () => {
    render(<WhatsAppPhoneChange onCompleted={jest.fn()} />);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByText(/not account ownership/)).toBeInTheDocument();
  });

  it('requires explicit consent, preserves history policy, and never stores phone or OTP', async () => {
    const completed = jest.fn();
    fetchMock
      .mockResolvedValueOnce(response(null, 204))
      .mockResolvedValueOnce(response(pending))
      .mockResolvedValueOnce(response({ ...pending, state: 'COMPLETED' }));
    render(<WhatsAppPhoneChange onCompleted={completed} />);
    fireEvent.click(screen.getByRole('button', { name: 'Change number' }));
    await waitFor(() => expect(screen.getByLabelText('New WhatsApp number')).toBeEnabled());
    fireEvent.change(screen.getByLabelText('New WhatsApp number'), {
      target: { value: '+14155550100' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send verification code' }));
    const input = await screen.findByLabelText('New number verification code');
    fireEvent.change(input, { target: { value: '123456' } });
    expect(screen.getByRole('button', { name: 'Verify and change number' })).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Verify and change number' }));
    await waitFor(() => expect(completed).toHaveBeenCalledTimes(1));
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toMatchObject({
      command: 'CONFIRM',
      challengeId: pending.challengeId,
      code: '123456',
      consent: true,
    });
    expect(sessionStorage.length).toBe(0);
    expect(localStorage.length).toBe(0);
    expect(screen.getByText(/approve each professional relationship separately/)).toBeInTheDocument();
  });

  it('recovers an unknown committed confirmation through status, without resending OTP', async () => {
    const completed = jest.fn();
    fetchMock
      .mockResolvedValueOnce(response(pending))
      .mockRejectedValueOnce(new Error('synthetic lost response'))
      .mockResolvedValueOnce(response({ ...pending, state: 'COMPLETED' }));
    render(<WhatsAppPhoneChange onCompleted={completed} />);
    fireEvent.click(screen.getByRole('button', { name: 'Change number' }));
    fireEvent.change(await screen.findByLabelText('New number verification code'), { target: { value: '123456' } });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Verify and change number' }));
    await screen.findByRole('alert');
    expect(completed).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Check phone-change status' }));
    await waitFor(() => expect(completed).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls.map((call) => JSON.parse(call[1].body).command)).toEqual([
      'STATUS',
      'CONFIRM',
      'STATUS',
    ]);
  });

  it('provides recovery when even the start response is lost', async () => {
    fetchMock.mockResolvedValueOnce(response(null, 204)).mockRejectedValueOnce(new Error('synthetic lost start'));
    render(<WhatsAppPhoneChange onCompleted={jest.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Change number' }));
    await waitFor(() => expect(screen.getByLabelText('New WhatsApp number')).toBeEnabled());
    fireEvent.change(screen.getByLabelText('New WhatsApp number'), {
      target: { value: '+14155550100' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send verification code' }));
    await screen.findByRole('alert');
    expect(screen.getByRole('button', { name: 'Check phone-change status' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Send verification code' })).toBeDisabled();
  });

  it('surfaces fresh sign-in and cancellation without claiming the number changed', async () => {
    const completed = jest.fn();
    fetchMock
      .mockResolvedValueOnce(response(pending))
      .mockResolvedValueOnce(response({ code: 'IDENTITY_STEP_UP_REQUIRED' }, 403))
      .mockResolvedValueOnce(response({ ...pending, state: 'EXPIRED' }));
    render(<WhatsAppPhoneChange onCompleted={completed} />);
    fireEvent.click(screen.getByRole('button', { name: 'Change number' }));
    await screen.findByLabelText('New number verification code');
    fireEvent.click(screen.getByRole('button', { name: 'Cancel phone change' }));
    expect(
      await screen.findByRole('button', {
        name: 'Sign out, then sign in again',
      })
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel phone change' }));
    await screen.findByLabelText('New WhatsApp number');
    expect(completed).not.toHaveBeenCalled();
  });
});
