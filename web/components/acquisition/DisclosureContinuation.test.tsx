import { fireEvent, render, screen } from '@testing-library/react';
import { DisclosureContinuation } from './DisclosureContinuation';

const push = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));

describe('DisclosureContinuation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Object.defineProperty(crypto, 'randomUUID', {
      configurable: true,
      value: jest.fn(() => '11111111-1111-4111-8111-111111111111'),
    });
  });

  it('requires explicit acceptance and preserves the exact offer binding', () => {
    render(<DisclosureContinuation
      disclosureRevision="1.0.0"
      initialIntent="trial"
      professionalType="DIGITAL_MARKETING_LOCAL_SERVICE"
      professionalVersion="1.0.0"
      termsVersion="2026-07-18"
      trialAvailable
    />);

    const continueButton = screen.getByRole('button', { name: 'Continue to trial' });
    expect(continueButton).toBeDisabled();
    expect(screen.getByRole('link', { name: 'Terms' })).toHaveAttribute('href', '/terms');
    expect(screen.getByRole('link', { name: 'Privacy Policy' })).toHaveAttribute('href', '/privacy');
    expect(screen.queryByRole('button', { name: 'Continue to hire' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(continueButton);

    const registrationUrl = new URL(push.mock.calls[0][0], 'https://waooaw.test');
    const returnTo = new URL(registrationUrl.searchParams.get('returnTo')!, 'https://waooaw.test');
    expect(registrationUrl.pathname).toBe('/register');
    expect(Object.fromEntries(returnTo.searchParams)).toEqual({
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      version: '1.0.0',
      intent: 'trial',
      disclosureRevision: '1.0.0',
      termsVersion: '2026-07-18',
      idempotencyKey: '11111111-1111-4111-8111-111111111111',
    });
  });

  it('offers a no-state-change path back to Marketplace', () => {
    render(<DisclosureContinuation
      disclosureRevision="1.0.0"
      professionalType="DIGITAL_MARKETING_LOCAL_SERVICE"
      professionalVersion="1.0.0"
      termsVersion="2026-07-18"
      trialAvailable
    />);

    expect(screen.getByRole('link', { name: 'Not now' })).toHaveAttribute('href', '/marketplace');
    expect(push).not.toHaveBeenCalled();
  });
});