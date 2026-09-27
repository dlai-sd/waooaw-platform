import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AcquisitionContinuation, type AcquisitionContinuationProps } from './AcquisitionContinuation';

const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }));
const originalFetch = global.fetch;
const props: AcquisitionContinuationProps = {
  professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
  professionalVersion: '1.0.0',
  intent: 'trial',
  disclosureRevision: '1.0.0',
  termsVersion: '2026-07-18',
  idempotencyKey: '11111111-1111-4111-8111-111111111111',
};

describe('AcquisitionContinuation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('submits the accepted binding and follows only the server resume path', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ resumePath: '/relationships/22222222-2222-4222-8222-222222222222' }),
    });
    render(<AcquisitionContinuation {...props} />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith('/relationships/22222222-2222-4222-8222-222222222222'));
    expect(jest.mocked(fetch)).toHaveBeenCalledWith(
      '/api/acquisition/continue',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(props),
      })
    );
  });

  it('makes an uncertain outcome retryable without changing the idempotency key', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ title: 'Unavailable' }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ resumePath: '/relationships/22222222-2222-4222-8222-222222222222' }),
      });
    render(<AcquisitionContinuation {...props} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Try same request again' }));
    await waitFor(() => expect(replace).toHaveBeenCalled());
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[0][1]?.body)).idempotencyKey).toBe(props.idempotencyKey);
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body)).idempotencyKey).toBe(props.idempotencyKey);
  });

  it('does not offer a retry for a known unavailable Trial and directs the customer to My Agents', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ title: 'Trial is currently unavailable' }),
    });
    render(<AcquisitionContinuation {...props} />);

    expect(await screen.findByRole('heading', { name: 'Trial is currently unavailable' })).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View My Agents' })).toHaveAttribute('href', '/professionals/mine');
  });

  it('requires registration without implying that a professional was started', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ code: 'REGISTRATION_REQUIRED', title: 'Complete registration first' }),
    });
    render(<AcquisitionContinuation {...props} />);

    expect(await screen.findByRole('heading', { name: 'Complete registration first' })).toBeInTheDocument();
    expect(screen.getByText('The request was not accepted and no professional was started.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Complete registration' })).toHaveAttribute('href', '/register');
    expect(screen.queryByRole('link', { name: 'View My Agents' })).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it('requires sign in after an expired session without implying success', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ title: 'Secure sign in is required.' }),
    });
    render(<AcquisitionContinuation {...props} />);

    expect(await screen.findByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
    expect(screen.queryByRole('link', { name: 'View My Agents' })).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
});
