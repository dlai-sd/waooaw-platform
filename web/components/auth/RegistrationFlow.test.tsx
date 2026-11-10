// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-AUTH-01, §UX-AUTH-03, §UX-AUTH-06, §UX-PRIV-01
// Implements: work-contracts/WC-107-requirements.yaml WC107-R002, WC107-R008
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { RegistrationFlow } from './RegistrationFlow';
import { getIdentityMessages } from '@/lib/identity-messages';

const registrationId = '8f6f7550-98c7-4a8f-bd63-36f07ee15c9d';
const originalFetch = global.fetch;
const replace = jest.fn();
const refresh = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace, refresh }),
}));
jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));
const draftKey = 'waooaw:identity:registration-draft';
const baseRegistration = {
  registrationId,
  state: 'PROFILE_COMPLETION_REQUIRED',
  nextAction: 'COMPLETE_PROFILE',
  authenticationPath: 'GOOGLE',
  providerLabel: 'google',
  emailVerified: true,
  mobileVerified: false,
  maskedEmail: 'a***@example.com',
  profile: {},
  expiresAt: new Date(),
  updatedAt: new Date(),
};

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);
}

describe('F2 registration flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
    Object.defineProperty(crypto, 'randomUUID', {
      configurable: true,
      value: jest.fn(() => '11111111-1111-4111-8111-111111111111'),
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('restores and updates only non-secret profile draft fields', async () => {
    sessionStorage.setItem(
      'waooaw:identity:registration-draft',
      JSON.stringify({
        displayName: 'Asha',
        businessName: 'Field Co',
        businessDomain: 'Agriculture',
      })
    );
    global.fetch = jest.fn(() => jsonResponse(baseRegistration));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    expect(await screen.findByLabelText('Your name')).toHaveValue('Asha');
    expect(screen.getByLabelText('Your name')).toHaveFocus();
    fireEvent.change(screen.getByLabelText('Business name'), {
      target: { value: 'Field Works' },
    });
    expect(sessionStorage.getItem('waooaw:identity:registration-draft')).toContain('Field Works');
    expect(sessionStorage.getItem('waooaw:identity:registration-draft')).not.toMatch(/email|mobile|code/i);

    const profileForm = screen.getByLabelText('Your name').closest('form');
    expect(profileForm).not.toBeNull();
    if (!profileForm) throw new Error('Profile form is required');
    fireEvent.submit(profileForm);
    await waitFor(() => expect(jest.mocked(fetch)).toHaveBeenCalledTimes(2));
    const profileCommand = JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body));
    expect(profileCommand).toMatchObject({
      action: 'profile',
      businessName: 'Field Works',
    });
  });

  it('never persists a one-time code and clears the challenge after confirmation', async () => {
    const verificationRequired = {
      ...baseRegistration,
      state: 'EMAIL_VERIFICATION_REQUIRED',
      nextAction: 'VERIFY_EMAIL',
      emailVerified: false,
    };
    const challenge = {
      challengeId: '22222222-2222-4222-8222-222222222222',
      purpose: 'EMAIL',
      state: 'PENDING',
      maskedDestination: 'a***@example.com',
      expiresAt: new Date(),
      resendAfter: new Date(),
    };
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() => jsonResponse(verificationRequired))
      .mockImplementationOnce(() => jsonResponse(challenge))
      .mockImplementationOnce(() => jsonResponse(baseRegistration));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    fireEvent.change(await screen.findByLabelText('Email address'), {
      target: { value: 'asha@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Send verification code/ }));
    fireEvent.change(await screen.findByLabelText('Six-digit code'), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Verify code/ }));
    await screen.findByLabelText('Your name');

    expect(JSON.stringify(sessionStorage)).not.toContain('123456');
    expect(screen.queryByText('a***@example.com')).not.toBeInTheDocument();
  });

  it('reuses the idempotency key when retrying an uncertain start outcome', async () => {
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() => Promise.reject(new Error('network unavailable')))
      .mockImplementationOnce(() => jsonResponse(baseRegistration));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Try again' }));
    await screen.findByLabelText('Your name');
    const first = JSON.parse(String(jest.mocked(fetch).mock.calls[0][1]?.body));
    const second = JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body));
    expect(second.idempotencyKey).toBe(first.idempotencyKey);
  });

  it.each([
    [400, 'IDENTITY_REQUEST_INVALID'],
    [409, 'IDENTITY_DUPLICATE_RESOLUTION_REQUIRED'],
    [409, 'IDENTITY_IDEMPOTENCY_CONFLICT'],
    [422, 'IDENTITY_VERIFICATION_REQUIRED'],
    [503, 'IDENTITY_DEPENDENCY_UNAVAILABLE'],
  ])('offers bounded retry recovery for HTTP %s code %s', async (status, code) => {
    global.fetch = jest.fn(() => jsonResponse({ code }, status));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    expect(await screen.findByText(getIdentityMessages('en').unavailable)).toBeVisible();
    expect(screen.getByRole('button', { name: getIdentityMessages('en').retry })).toBeVisible();
  });

  it.each([403, 429])(
    'requires a fresh sign-in after an HTTP %s policy denial without offering a retry loop',
    async (status) => {
      global.fetch = jest.fn(() => jsonResponse({ code: 'IDENTITY_ACTION_DENIED' }, status));
      render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} returnTo="/settings" />);

      expect(await screen.findByText(getIdentityMessages('en').signInRejected)).toBeVisible();
      expect(screen.getByRole('heading', { name: 'Create your WAOOAW account' })).toBeVisible();
      expect(screen.queryByRole('button', { name: getIdentityMessages('en').retry })).not.toBeInTheDocument();

      fireEvent.click(
        screen.getByRole('button', {
          name: getIdentityMessages('en').restartSignIn,
        })
      );
      expect(replace).toHaveBeenCalledWith('/login?returnTo=%2Fsettings');
      expect(fetch).toHaveBeenCalledTimes(1);
    }
  );

  it.each(['trial', 'hire'] as const)(
    'reauthenticates directly when %s registration requires a fresh session',
    async (intent) => {
      global.fetch = jest.fn(() => jsonResponse({ code: 'IDENTITY_STEP_UP_REQUIRED' }, 403));
      render(
        <RegistrationFlow
          locale="en"
          messages={getIdentityMessages('en')}
          returnTo={`/marketplace?professionalType=DIGITAL_MARKETING&version=3.1.0&intent=${intent}`}
        />
      );

      expect(await screen.findByText(getIdentityMessages('en').freshSignInRequired)).toBeVisible();
      fireEvent.click(
        screen.getByRole('button', {
          name: getIdentityMessages('en').continueSecurely,
        })
      );

      expect(signIn).toHaveBeenCalledWith(
        'keycloak-google',
        {
          callbackUrl: `/register?returnTo=%2Fmarketplace%3FprofessionalType%3DDIGITAL_MARKETING%26version%3D3.1.0%26intent%3D${intent}`,
        },
        { max_age: '0', prompt: 'select_account' }
      );
      expect(replace).not.toHaveBeenCalled();
    }
  );

  it('restarts sign-in when an in-progress registration is no longer accessible', async () => {
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() => jsonResponse(baseRegistration))
      .mockImplementationOnce(() =>
        jsonResponse(
          {
            code: 'IDENTITY_RESOURCE_NOT_ACCESSIBLE',
            correlationId: '11111111-1111-4111-8111-111111111111',
          },
          404
        )
      )
      .mockImplementationOnce(() =>
        jsonResponse({
          ...baseRegistration,
          registrationId: 'new-registration',
        })
      );
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} returnTo="/settings" />);
    const profileForm = (await screen.findByLabelText('Your name')).closest('form');
    if (!profileForm) throw new Error('Profile form is required');
    fireEvent.submit(profileForm);

    expect(await screen.findByText(getIdentityMessages('en').registrationLost)).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: getIdentityMessages('en').retry }));
    expect(await screen.findByLabelText('Your name')).toBeVisible();
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(replace).not.toHaveBeenCalled();
    expect(screen.queryByText(/11111111/)).not.toBeInTheDocument();
  });

  it.each([
    [401, {}],
    [403, { code: 'IDENTITY_SESSION_REQUIRED' }],
  ])('returns a missing session to provider choice for status %s', async (status, body) => {
    global.fetch = jest.fn(() => jsonResponse(body, status));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} returnTo="/settings" />);

    expect(await screen.findByText(getIdentityMessages('en').registrationLost)).toBeVisible();
    fireEvent.click(
      screen.getByRole('button', {
        name: getIdentityMessages('en').restartSignIn,
      })
    );
    expect(replace).toHaveBeenCalledWith('/login?returnTo=%2Fsettings');
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('returns an expired email challenge to the resend form', async () => {
    const verificationRequired = {
      ...baseRegistration,
      state: 'EMAIL_VERIFICATION_REQUIRED',
      nextAction: 'VERIFY_EMAIL',
      emailVerified: false,
    };
    const challenge = {
      challengeId: '22222222-2222-4222-8222-222222222222',
      purpose: 'EMAIL',
      state: 'PENDING',
      maskedDestination: 'a***@example.com',
      expiresAt: new Date(),
      resendAfter: new Date(),
    };
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() => jsonResponse(verificationRequired))
      .mockImplementationOnce(() => jsonResponse(challenge))
      .mockImplementationOnce(() => jsonResponse({ code: 'IDENTITY_CHALLENGE_EXPIRED' }, 410));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.change(await screen.findByLabelText('Email address'), {
      target: { value: 'asha@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Send verification code/ }));
    fireEvent.change(await screen.findByLabelText('Six-digit code'), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Verify code/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent(getIdentityMessages('en').verificationExpired);
    expect(screen.getByLabelText('Email address')).toBeVisible();
  });

  it('requires a WhatsApp number before registration can be completed', async () => {
    global.fetch = jest.fn(() =>
      jsonResponse({
        ...baseRegistration,
        state: 'REGISTRATION_COMPLETION_REQUIRED',
        nextAction: 'COMPLETE_REGISTRATION',
      })
    );
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    expect(await screen.findByLabelText('Verified email')).toHaveValue('a***@example.com');
    expect(screen.getByLabelText('Verified email')).toHaveAttribute('readonly');
    expect(screen.getByText('Verified by Google')).toBeVisible();
    expect(screen.getByLabelText('WhatsApp number')).toBeRequired();
    expect(screen.getByText(/only send a code after you request it/i)).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Register' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send WhatsApp verification code' })).toBeEnabled();
    expect(JSON.stringify(sessionStorage)).not.toContain('whatsapp-number');
  });

  it('verifies a WhatsApp number before allowing registration completion without persisting it', async () => {
    const challenge = {
      challengeId: '33333333-3333-4333-8333-333333333333',
      purpose: 'MOBILE',
      state: 'PENDING',
      maskedDestination: '+1******8900',
      expiresAt: new Date(),
      resendAfter: new Date(),
    };
    const verifiedRegistration = {
      ...baseRegistration,
      state: 'READY_TO_COMPLETE',
      nextAction: 'COMPLETE_REGISTRATION',
      mobileVerified: true,
    };
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() => jsonResponse({ ...baseRegistration, nextAction: 'VERIFY_MOBILE' }))
      .mockImplementationOnce(() => jsonResponse(challenge))
      .mockImplementationOnce(() => jsonResponse(verifiedRegistration))
      .mockImplementationOnce(() => jsonResponse({ handoffConfirmed: true }));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    fireEvent.change(await screen.findByLabelText('WhatsApp number'), {
      target: { value: '+12345678900' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send WhatsApp verification code' }));
    expect(await screen.findByText(/code sent on WhatsApp to/i)).toBeVisible();
    expect(screen.getByText('+1******8900')).toBeVisible();
    expect(JSON.stringify(sessionStorage)).not.toContain('+12345678900');

    fireEvent.change(screen.getByLabelText('Six-digit code'), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Verify code' }));
    expect(await screen.findByText('WhatsApp number verified')).toBeVisible();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Register' })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Register' }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/home'));

    const commands = jest.mocked(fetch).mock.calls.map(([, init]) => JSON.parse(String(init?.body)));
    expect(commands[1]).toMatchObject({
      action: 'mobile-start',
      mobile: '+12345678900',
    });
    expect(commands[2]).toMatchObject({
      action: 'mobile-confirm',
      code: '123456',
    });
    expect(commands[3]).toMatchObject({ action: 'complete' });
    expect(JSON.stringify(sessionStorage)).not.toContain('123456');
  });

  it('lets a rejected WhatsApp code be corrected with a fresh idempotency key', async () => {
    jest
      .mocked(crypto.randomUUID)
      .mockReturnValueOnce('11111111-1111-4111-8111-111111111111')
      .mockReturnValueOnce('22222222-2222-4222-8222-222222222222')
      .mockReturnValueOnce('33333333-3333-4333-8333-333333333333')
      .mockReturnValueOnce('44444444-4444-4444-8444-444444444444');
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() => jsonResponse({ ...baseRegistration, nextAction: 'VERIFY_MOBILE' }))
      .mockImplementationOnce(() =>
        jsonResponse({
          challengeId: '55555555-5555-4555-8555-555555555555',
          purpose: 'MOBILE',
          state: 'PENDING',
          maskedDestination: '+1******0100',
          expiresAt: new Date(),
          resendAfter: new Date(),
        })
      )
      .mockImplementationOnce(() => jsonResponse({ code: 'IDENTITY_ACTION_DENIED' }, 403))
      .mockImplementationOnce(() =>
        jsonResponse({
          ...baseRegistration,
          mobileVerified: true,
          nextAction: 'COMPLETE_REGISTRATION',
        })
      );
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.change(await screen.findByLabelText('WhatsApp number'), {
      target: { value: '+14155550100' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send WhatsApp verification code' }));
    fireEvent.change(await screen.findByLabelText('Six-digit code'), {
      target: { value: '000000' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Verify code' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(getIdentityMessages('en').verificationRejected);
    await waitFor(() => expect(screen.getByLabelText('Six-digit code')).toHaveValue(''));
    fireEvent.change(screen.getByLabelText('Six-digit code'), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Verify code' }));
    expect(await screen.findByText('WhatsApp number verified')).toBeVisible();
    const first = JSON.parse(String(jest.mocked(fetch).mock.calls[2][1]?.body));
    const corrected = JSON.parse(String(jest.mocked(fetch).mock.calls[3][1]?.body));
    expect(corrected.idempotencyKey).not.toBe(first.idempotencyKey);
    expect(corrected).toMatchObject({
      action: 'mobile-confirm',
      code: '123456',
    });
    expect(replace).not.toHaveBeenCalled();
    expect(JSON.stringify(sessionStorage)).not.toMatch(/123456|14155550100/);
  });

  it('replays unresolved OTP requests and sends a new request only on explicit choice', async () => {
    jest
      .mocked(crypto.randomUUID)
      .mockReturnValueOnce('11111111-1111-4111-8111-111111111111')
      .mockReturnValueOnce('22222222-2222-4222-8222-222222222222')
      .mockReturnValueOnce('33333333-3333-4333-8333-333333333333');
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() => jsonResponse({ ...baseRegistration, nextAction: 'VERIFY_MOBILE' }))
      .mockImplementationOnce(() => jsonResponse({ code: 'IDENTITY_DEPENDENCY_UNAVAILABLE' }, 503))
      .mockImplementationOnce(() => jsonResponse({ code: 'IDENTITY_DEPENDENCY_UNAVAILABLE' }, 503))
      .mockImplementationOnce(() => jsonResponse({ code: 'IDENTITY_RATE_LIMITED' }, 429));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.change(await screen.findByLabelText('WhatsApp number'), {
      target: { value: '+14155550100' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send WhatsApp verification code' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
    fireEvent.click(
      await screen.findByRole('button', {
        name: 'Request a new WhatsApp code',
      })
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(getIdentityMessages('en').verificationRateLimited);
    const commands = jest.mocked(fetch).mock.calls.map(([, init]) => JSON.parse(String(init?.body)));
    expect(commands[2].idempotencyKey).toBe(commands[1].idempotencyKey);
    expect(commands[3].idempotencyKey).not.toBe(commands[1].idempotencyKey);
    expect(JSON.stringify(sessionStorage)).not.toContain('+14155550100');
  });

  it('keeps the number form available after a resend cooldown denial', async () => {
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() => jsonResponse({ ...baseRegistration, nextAction: 'VERIFY_MOBILE' }))
      .mockImplementationOnce(() => jsonResponse({ code: 'IDENTITY_RATE_LIMITED' }, 429));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.change(await screen.findByLabelText('WhatsApp number'), {
      target: { value: '+14155550100' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send WhatsApp verification code' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(getIdentityMessages('en').verificationRateLimited);
    expect(screen.getByLabelText('WhatsApp number')).toHaveValue('+14155550100');
    expect(screen.queryByRole('button', { name: 'Sign in again' })).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it.each(['COMPLETE_REGISTRATION', 'CONTINUE_TO_DEFAULT_TARGET', 'NONE'])(
    'requires confirmation before leaving %s',
    async (nextAction) => {
      sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
      global.fetch = jest
        .fn()
        .mockImplementationOnce(() =>
          jsonResponse({
            ...baseRegistration,
            mobileVerified: true,
            nextAction,
          })
        )
        .mockImplementationOnce(() => jsonResponse({ handoffConfirmed: true }));
      render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
      fireEvent.click(
        await screen.findByRole('button', {
          name: getIdentityMessages('en').complete,
        })
      );
      await waitFor(() => expect(replace).toHaveBeenCalledWith('/home'));
      expect(refresh).toHaveBeenCalledTimes(1);
      expect(sessionStorage.getItem(draftKey)).toBeNull();
      expect(JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body)).action).toBe('complete');
    }
  );

  it('dispatches a server-confirmed returning session', async () => {
    sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
    global.fetch = jest.fn(() => jsonResponse({ handoffConfirmed: true }));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} returnTo="/settings" />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/settings'));
    expect(sessionStorage.getItem(draftKey)).toBeNull();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it.each([
    {},
    null,
    { handoffConfirmed: false },
    { accountReference: 'other-account', defaultTarget: 'APPLICATION_HOME' },
  ])('retains the draft and refuses unconfirmed completion: %p', async (body) => {
    sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() =>
        jsonResponse({
          ...baseRegistration,
          mobileVerified: true,
          nextAction: 'COMPLETE_REGISTRATION',
        })
      )
      .mockImplementationOnce(() => jsonResponse(body));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.click(
      await screen.findByRole('button', {
        name: getIdentityMessages('en').complete,
      })
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(getIdentityMessages('en').unavailable);
    expect(sessionStorage.getItem(draftKey)).toContain('Asha');
    expect(replace).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
  });

  it('shows a finite safe error and retries completion with the same key', async () => {
    sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() =>
        jsonResponse({
          ...baseRegistration,
          mobileVerified: true,
          nextAction: 'COMPLETE_REGISTRATION',
        })
      )
      .mockImplementationOnce(() => jsonResponse({ title: 'private-token other-account' }, 503))
      .mockImplementationOnce(() => jsonResponse({ handoffConfirmed: true }));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.click(
      await screen.findByRole('button', {
        name: getIdentityMessages('en').complete,
      })
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(getIdentityMessages('en').unavailable);
    expect(screen.queryByText(/private-token/)).not.toBeInTheDocument();
    expect(sessionStorage.getItem(draftKey)).toContain('Asha');
    expect(replace).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: getIdentityMessages('en').complete }));
    await waitFor(() => expect(replace).toHaveBeenCalledTimes(1));
    const commands = jest
      .mocked(fetch)
      .mock.calls.slice(1)
      .map(([, init]) => JSON.parse(String(init?.body)));
    expect(commands[0].idempotencyKey).toBe(commands[1].idempotencyKey);
  });

  it('aborts an unmounted completion and ignores even a late confirmed reply', async () => {
    sessionStorage.setItem(draftKey, '{"displayName":"Asha"}');
    let resolveCompletion!: (response: Response) => void;
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() =>
        jsonResponse({
          ...baseRegistration,
          mobileVerified: true,
          nextAction: 'COMPLETE_REGISTRATION',
        })
      )
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            resolveCompletion = resolve;
          })
      );
    const view = render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    fireEvent.click(
      await screen.findByRole('button', {
        name: getIdentityMessages('en').complete,
      })
    );
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
    global.fetch = jest.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolveStart = resolve;
        })
    );
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    const signal = jest.mocked(fetch).mock.calls[0][1]?.signal;

    act(() => {
      const event = new Event('storage');
      Object.defineProperties(event, {
        key: { value: 'waooaw:identity:session-change' },
        newValue: { value: '{"action":"SIGN_OUT","nonce":"other-tab"}' },
        storageArea: { value: localStorage },
      });
      window.dispatchEvent(event);
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
    global.fetch = jest
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            resolveStart = resolve;
          })
      )
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
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() =>
        jsonResponse({
          ...baseRegistration,
          mobileVerified: true,
          nextAction: 'COMPLETE_REGISTRATION',
        })
      )
      .mockImplementationOnce(
        (_url, init) =>
          new Promise((_resolve, reject) => {
            init.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
          })
      );
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);
    const completeButton = await screen.findByRole('button', {
      name: getIdentityMessages('en').complete,
    });
    jest.useFakeTimers();
    fireEvent.click(completeButton);
    expect(completeButton).toBeDisabled();
    await act(async () => {
      jest.advanceTimersByTime(20_000);
    });
    expect(completeButton).not.toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent(getIdentityMessages('en').unavailable);
    expect(replace).not.toHaveBeenCalled();
  });
});
