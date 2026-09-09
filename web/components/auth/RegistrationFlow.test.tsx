// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-AUTH-01, §UX-AUTH-03, §UX-AUTH-06, §UX-PRIV-01
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RegistrationFlow } from './RegistrationFlow';
import { getIdentityMessages } from '@/lib/identity-messages';

const registrationId = '8f6f7550-98c7-4a8f-bd63-36f07ee15c9d';
const originalFetch = global.fetch;
const replace = jest.fn();
const refresh = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace, refresh }) }));
const draftKey = 'waooaw:identity:registration-draft';
const baseRegistration = {
  registrationId, state: 'PROFILE_COMPLETION_REQUIRED', nextAction: 'COMPLETE_PROFILE', authenticationPath: 'GOOGLE',
  emailVerified: true, mobileVerified: false, profile: {}, expiresAt: new Date(), updatedAt: new Date(),
};

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body } as Response);
}

describe('F2 registration flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
    Object.defineProperty(crypto, 'randomUUID', { configurable: true, value: jest.fn(() => '11111111-1111-4111-8111-111111111111') });
  });

  afterEach(() => {
    jest.useRealTimers();
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('restores and updates only non-secret profile draft fields', async () => {
    sessionStorage.setItem('waooaw:identity:registration-draft', JSON.stringify({ displayName: 'Asha', businessName: 'Field Co', businessDomain: 'Agriculture' }));
    global.fetch = jest.fn(() => jsonResponse(baseRegistration));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    expect(await screen.findByLabelText('Your name')).toHaveValue('Asha');
    fireEvent.change(screen.getByLabelText('Business name'), { target: { value: 'Field Works' } });
    expect(sessionStorage.getItem('waooaw:identity:registration-draft')).toContain('Field Works');
    expect(sessionStorage.getItem('waooaw:identity:registration-draft')).not.toMatch(/email|mobile|code/i);

    const profileForm = screen.getByLabelText('Your name').closest('form');
    expect(profileForm).not.toBeNull();
    fireEvent.submit(profileForm!);
    await waitFor(() => expect(jest.mocked(fetch)).toHaveBeenCalledTimes(2));
    const profileCommand = JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body));
    expect(profileCommand).toMatchObject({ action: 'profile', businessName: 'Field Works' });
  });

  it('never persists a one-time code and clears the challenge after confirmation', async () => {
    const verificationRequired = { ...baseRegistration, state: 'EMAIL_VERIFICATION_REQUIRED', nextAction: 'VERIFY_EMAIL', emailVerified: false };
    const challenge = { challengeId: '22222222-2222-4222-8222-222222222222', purpose: 'EMAIL', state: 'PENDING', maskedDestination: 'a***@example.com', expiresAt: new Date(), resendAfter: new Date() };
    global.fetch = jest.fn()
      .mockImplementationOnce(() => jsonResponse(verificationRequired))
      .mockImplementationOnce(() => jsonResponse(challenge))
      .mockImplementationOnce(() => jsonResponse(baseRegistration));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    fireEvent.change(await screen.findByLabelText('Email address'), { target: { value: 'asha@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /Send verification code/ }));
    fireEvent.change(await screen.findByLabelText('Six-digit code'), { target: { value: '123456' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify code/ }));
    await screen.findByLabelText('Your name');

    expect(JSON.stringify(sessionStorage)).not.toContain('123456');
    expect(screen.queryByText('a***@example.com')).not.toBeInTheDocument();
  });

  it('reuses the idempotency key when retrying an uncertain start outcome', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() => Promise.reject(new Error('network unavailable')))
      .mockImplementationOnce(() => jsonResponse(baseRegistration));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Try again' }));
    await screen.findByLabelText('Your name');
    const first = JSON.parse(String(jest.mocked(fetch).mock.calls[0][1]?.body));
    const second = JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body));
    expect(second.idempotencyKey).toBe(first.idempotencyKey);
  });

  it('allows optional mobile verification before completing registration', async () => {
    global.fetch = jest.fn(() => jsonResponse({
      ...baseRegistration,
      state: 'REGISTRATION_COMPLETION_REQUIRED',
      nextAction: 'COMPLETE_REGISTRATION',
    }));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Verify mobile now' }));

    expect(await screen.findByLabelText('Mobile number')).toBeInTheDocument();
  });

  it.each(['COMPLETE_REGISTRATION', 'CONTINUE_TO_DEFAULT_TARGET', 'NONE'])('requires confirmation before leaving %s', async (nextAction) => {
    sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
    global.fetch = jest.fn()
      .mockImplementationOnce(() => jsonResponse({ ...baseRegistration, nextAction }))
      .mockImplementationOnce(() => jsonResponse({ handoffConfirmed: true }));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.click(await screen.findByRole('button', { name: getIdentityMessages('en').complete }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/home'));
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(sessionStorage.getItem(draftKey)).toBeNull();
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body)).action).toBe('complete');
  });

  it('dispatches a server-confirmed returning session', async () => {
    sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
    global.fetch = jest.fn(() => jsonResponse({ handoffConfirmed: true }));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/home'));
    expect(sessionStorage.getItem(draftKey)).toBeNull();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it.each([{}, null, { handoffConfirmed: false }, { accountReference: 'other-account', defaultTarget: 'APPLICATION_HOME' }])('retains the draft and refuses unconfirmed completion: %p', async (body) => {
    sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
    global.fetch = jest.fn()
      .mockImplementationOnce(() => jsonResponse({ ...baseRegistration, nextAction: 'COMPLETE_REGISTRATION' }))
      .mockImplementationOnce(() => jsonResponse(body));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.click(await screen.findByRole('button', { name: getIdentityMessages('en').complete }));
    expect(await screen.findByRole('alert')).toHaveTextContent(getIdentityMessages('en').unavailable);
    expect(sessionStorage.getItem(draftKey)).toContain('Asha');
    expect(replace).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
  });

  it('shows a finite safe error and retries completion with the same key', async () => {
    sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
    global.fetch = jest.fn()
      .mockImplementationOnce(() => jsonResponse({ ...baseRegistration, nextAction: 'COMPLETE_REGISTRATION' }))
      .mockImplementationOnce(() => jsonResponse({ title: 'private-token other-account' }, 503))
      .mockImplementationOnce(() => jsonResponse({ handoffConfirmed: true }));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.click(await screen.findByRole('button', { name: getIdentityMessages('en').complete }));
    expect(await screen.findByRole('alert')).toHaveTextContent(getIdentityMessages('en').unavailable);
    expect(screen.queryByText(/private-token/)).not.toBeInTheDocument();
    expect(sessionStorage.getItem(draftKey)).toContain('Asha');
    expect(replace).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: getIdentityMessages('en').complete }));
    await waitFor(() => expect(replace).toHaveBeenCalledTimes(1));
    const commands = jest.mocked(fetch).mock.calls.slice(1).map(([, init]) => JSON.parse(String(init?.body)));
    expect(commands[0].idempotencyKey).toBe(commands[1].idempotencyKey);
  });

  it('aborts an unmounted completion and ignores even a late confirmed reply', async () => {
    sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
    let resolveCompletion!: (response: Response) => void;
    global.fetch = jest.fn()
      .mockImplementationOnce(() => jsonResponse({ ...baseRegistration, nextAction: 'COMPLETE_REGISTRATION' }))
      .mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveCompletion = resolve; }));
    const view = render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.click(await screen.findByRole('button', { name: getIdentityMessages('en').complete }));
    const signal = jest.mocked(fetch).mock.calls[1][1]?.signal;
    view.unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => resolveCompletion(await jsonResponse({ handoffConfirmed: true })));
    expect(replace).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(draftKey)).toContain('Asha');
  });

  it('aborts a pending handoff when another tab signs out', async () => {
    sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
    let resolveStart!: (response: Response) => void;
    global.fetch = jest.fn(() => new Promise<Response>((resolve) => { resolveStart = resolve; }));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    const signal = jest.mocked(fetch).mock.calls[0][1]?.signal;

    act(() => {
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'waooaw:identity:session-change',
        newValue: '{"action":"SIGN_OUT","nonce":"other-tab"}',
        storageArea: localStorage,
      }));
    });

    expect(signal?.aborted).toBe(true);
    expect(sessionStorage.getItem(draftKey)).toBeNull();
    expect(replace).toHaveBeenCalledWith('/');
    expect(refresh).toHaveBeenCalledTimes(1);
    await act(async () => resolveStart(await jsonResponse({ handoffConfirmed: true })));
    expect(replace).not.toHaveBeenCalledWith('/home');
  });

  it('discards a superseded start reply', async () => {
    let resolveStart!: (response: Response) => void;
    global.fetch = jest.fn()
      .mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveStart = resolve; }))
      .mockImplementationOnce(() => jsonResponse(baseRegistration));
    const view = render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    const signal = jest.mocked(fetch).mock.calls[0][1]?.signal;
    view.rerender(<RegistrationFlow locale="hi" messages={getIdentityMessages('en')} />);
    await screen.findByLabelText('Your name');
    expect(signal?.aborted).toBe(true);
    await act(async () => resolveStart(await jsonResponse({ handoffConfirmed: true })));
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Your name')).toBeInTheDocument();
  });

  it('ends a stalled completion after the bounded client deadline', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() => jsonResponse({ ...baseRegistration, nextAction: 'COMPLETE_REGISTRATION' }))
      .mockImplementationOnce((_url, init) => new Promise((_resolve, reject) => {
        init.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
      }));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    const completeButton = await screen.findByRole('button', { name: getIdentityMessages('en').complete });
    jest.useFakeTimers();
    fireEvent.click(completeButton);
    expect(completeButton).toBeDisabled();
    await act(async () => { jest.advanceTimersByTime(20_000); });
    expect(completeButton).not.toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent(getIdentityMessages('en').unavailable);
    expect(replace).not.toHaveBeenCalled();
  });
});