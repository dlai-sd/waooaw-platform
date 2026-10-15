'use client';

// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md §5.1 Identity And Disclosure
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R001
// Implements: work-contracts/WC-119-auth-session-account-switch-recovery.md WC119-R001, WC119-R004, WC119-R005
// Implements: architecture/reference/ux/wc-105-authentication-flow-defect-remediation-plan.md AUTH-UI-02
// Constitutional basis: C-049 (Honest Limitation), C-063 (Data Minimisation)

import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';
import { recordAuthTransition } from '@/lib/auth-transition';
import { requestKeycloakLogout } from '@/lib/keycloak-logout';
import Link from 'next/link';
import { signIn } from 'next-auth/react';
import { useEffect, useRef, useState } from 'react';
import { FaApple, FaEnvelope, FaFacebookF, FaGoogle } from 'react-icons/fa6';
import { clearProtectedClientState } from './SignOutCommand';

const nextAuthProvider = {
  GOOGLE: 'keycloak-google',
  FACEBOOK: 'keycloak-facebook',
  APPLE: 'keycloak-apple',
  EMAIL: 'keycloak',
} as const;

const icons = {
  GOOGLE: FaGoogle,
  FACEBOOK: FaFacebookF,
  APPLE: FaApple,
  EMAIL: FaEnvelope,
} as const;

const providerOrder: IdentityProvider['id'][] = ['GOOGLE', 'FACEBOOK', 'APPLE', 'EMAIL'];

export const pendingIdentityProviders: IdentityProvider[] = [
  { id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'UNAVAILABLE' },
  { id: 'FACEBOOK', displayName: 'Facebook', authenticationPath: 'META', availability: 'UNAVAILABLE' },
  { id: 'APPLE', displayName: 'Apple', authenticationPath: 'APPLE', availability: 'UNAVAILABLE' },
  { id: 'EMAIL', displayName: 'Email', authenticationPath: 'CREDENTIAL', availability: 'UNAVAILABLE' },
];

type ProviderIntent = 'login' | 'register';

function supportsNextAuth(providerId: IdentityProvider['id']): providerId is keyof typeof nextAuthProvider {
  return providerId in nextAuthProvider;
}

function isActionable(provider: IdentityProvider) {
  return provider.availability === 'AVAILABLE' && (provider.id === 'GOOGLE' || provider.id === 'FACEBOOK');
}

export function ProviderCommands({
  callbackUrl,
  intent,
  providers,
  readinessPending = false,
  reload = () => window.location.reload(),
  resetSessionBeforeLaunch = false,
  navigate,
}: {
  callbackUrl: string;
  intent: ProviderIntent;
  providers: IdentityProvider[];
  readinessPending?: boolean;
  reload?: () => void;
  resetSessionBeforeLaunch?: boolean;
  navigate?: (path: string) => void;
}) {
  const [pendingProvider, setPendingProvider] = useState<string>();
  const [disclosureProvider, setDisclosureProvider] = useState<IdentityProvider>();
  const [launchFailure, setLaunchFailure] = useState<string>();
  const providerCommand = useRef<HTMLButtonElement | null>(null);
  const disclosure = useRef<HTMLDialogElement>(null);
  const continueCommand = useRef<HTMLButtonElement>(null);
  const orderedProviders = [...providers].sort(
    (left, right) => providerOrder.indexOf(left.id) - providerOrder.indexOf(right.id)
  );

  useEffect(() => {
    if (!disclosureProvider) return;
    continueCommand.current?.focus();
    function handleDisclosureKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setDisclosureProvider(undefined);
        providerCommand.current?.focus();
        return;
      }
      if (event.key !== 'Tab') return;
      const commands = disclosure.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
      if (!commands?.length) return;
      const first = commands[0];
      const last = commands[commands.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        last.focus();
        event.preventDefault();
      } else if (!event.shiftKey && document.activeElement === last) {
        first.focus();
        event.preventDefault();
      }
    }
    window.addEventListener('keydown', handleDisclosureKey);
    return () => window.removeEventListener('keydown', handleDisclosureKey);
  }, [disclosureProvider]);

  useEffect(() => {
    recordAuthTransition('PROVIDER_PROJECTION_READY');
  }, []);

  function actionLabel(provider: IdentityProvider) {
    const action = intent === 'login' ? 'Log in' : 'Sign up';
    return `${action} with ${provider.displayName}`;
  }

  async function begin(provider: IdentityProvider) {
    if (!isActionable(provider) || !supportsNextAuth(provider.id)) return;
    setLaunchFailure(undefined);
    setPendingProvider(provider.id);
    try {
      if (resetSessionBeforeLaunch) {
        recordAuthTransition('ACCOUNT_SWITCH_REQUESTED', 'SESSION_RECOVERY', provider.id);
        const logoutPath = await requestKeycloakLogout('ACCOUNT_SWITCH');
        clearProtectedClientState();
        if (navigate) navigate(logoutPath);
        else window.location.assign(logoutPath);
        return;
      }
      recordAuthTransition('BROKER_REDIRECT_REQUESTED', 'OK', provider.id);
      await signIn(
        nextAuthProvider[provider.id],
        {
          callbackUrl,
          waooawIntent: intent === 'login' ? 'LOGIN' : 'REGISTER',
        },
        provider.id === 'GOOGLE' ? { max_age: '0', prompt: 'select_account' } : undefined
      );
    } catch {
      setPendingProvider(undefined);
      setLaunchFailure(provider.displayName);
      recordAuthTransition('BROKER_LAUNCH_FAILED', 'BROKER_LAUNCH_FAILED', provider.id);
    }
  }

  function cancelDisclosure() {
    setDisclosureProvider(undefined);
    providerCommand.current?.focus();
    recordAuthTransition('PROVIDER_CANCELLED', 'CUSTOMER_CANCELLED', disclosureProvider?.id);
  }

  const readinessUnavailable = providers.some((provider) => provider.unavailableReason === 'TEMPORARILY_UNAVAILABLE');

  return (
    <div className="provider-commands">
      <div className="provider-grid">
        {orderedProviders.map((provider) => {
          const Icon = icons[provider.id];
          const unavailable = readinessPending || !isActionable(provider);
          const label = actionLabel(provider);
          return (
            <button
              aria-label={unavailable ? `${label} (Unavailable)` : label}
              className={`provider-icon-command provider-command-${provider.id.toLowerCase()}`}
              disabled={unavailable || pendingProvider !== undefined}
              key={provider.id}
              onClick={(event) => {
                providerCommand.current = event.currentTarget;
                setDisclosureProvider(provider);
              }}
              title={unavailable ? `${provider.displayName} is unavailable` : label}
              type="button"
            >
              <Icon aria-hidden="true" size={20} />
              <span className="visually-hidden">{label}</span>
            </button>
          );
        })}
      </div>
      {readinessUnavailable && !readinessPending ? (
        <output className="provider-readiness">
          <span>Sign-in services are still starting.</span>
          <button className="text-command" type="button" onClick={reload}>
            Try again
          </button>
        </output>
      ) : null}
      {launchFailure ? (
        <div className="provider-readiness" data-reason-code="BROKER_LAUNCH_FAILED" role="alert">
          <p>{launchFailure} sign-in could not start.</p>
          <button className="text-command" onClick={() => setLaunchFailure(undefined)} type="button">
            Try again
          </button>
        </div>
      ) : null}
      {disclosureProvider ? (
        <dialog aria-labelledby="provider-disclosure-title" className="provider-disclosure" open ref={disclosure}>
          <div className="provider-disclosure-content">
            <h2 id="provider-disclosure-title">Continue to {disclosureProvider.displayName}</h2>
            <p>
              WAOOAW will receive your name, email address, profile information and {disclosureProvider.displayName}{' '}
              account identifier to sign you in, identify your WAOOAW account, and support registration only when you
              explicitly choose it. WAOOAW does not receive your {disclosureProvider.displayName} password.
            </p>
            <p>
              {disclosureProvider.displayName} manages its own consent screen. Read the WAOOAW{' '}
              <Link href="/privacy">Privacy Notice</Link> before continuing.
            </p>
            <div className="provider-disclosure-actions">
              <button className="text-command" onClick={cancelDisclosure} type="button">
                Cancel
              </button>
              <button
                className="primary-command"
                onClick={() => {
                  const provider = disclosureProvider;
                  setDisclosureProvider(undefined);
                  void begin(provider);
                }}
                ref={continueCommand}
                type="button"
              >
                Continue to {disclosureProvider.displayName}
              </button>
            </div>
          </div>
        </dialog>
      ) : null}
    </div>
  );
}
