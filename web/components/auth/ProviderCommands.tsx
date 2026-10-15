'use client';

// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md §5.1 Identity And Disclosure
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R001
// Implements: work-contracts/WC-119-auth-session-account-switch-recovery.md WC119-R001, WC119-R004, WC119-R005
// Implements: architecture/reference/ux/wc-105-authentication-flow-defect-remediation-plan.md AUTH-UI-02
// Constitutional basis: C-049 (Honest Limitation), C-063 (Data Minimisation)

import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';
import { recordAuthTransition } from '@/lib/auth-transition';
import { requestKeycloakLogout } from '@/lib/keycloak-logout';
import { signIn } from 'next-auth/react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  resumeProvider,
  navigate,
}: {
  callbackUrl: string;
  intent: ProviderIntent;
  providers: IdentityProvider[];
  readinessPending?: boolean;
  reload?: () => void;
  resetSessionBeforeLaunch?: boolean;
  resumeProvider?: IdentityProvider['id'];
  navigate?: (path: string) => void;
}) {
  const [pendingProvider, setPendingProvider] = useState<string>();
  const [launchFailure, setLaunchFailure] = useState<string>();
  const resumedProvider = useRef(false);
  const orderedProviders = useMemo(
    () => [...providers].sort((left, right) => providerOrder.indexOf(left.id) - providerOrder.indexOf(right.id)),
    [providers]
  );

  useEffect(() => {
    recordAuthTransition('PROVIDER_PROJECTION_READY');
  }, []);

  function actionLabel(provider: IdentityProvider) {
    const action = intent === 'login' ? 'Log in' : 'Sign up';
    return `${action} with ${provider.displayName}`;
  }

  const begin = useCallback(
    async (provider: IdentityProvider, registrationSessionReset = false) => {
      if (!isActionable(provider) || !supportsNextAuth(provider.id)) return;
      setLaunchFailure(undefined);
      setPendingProvider(provider.id);
      try {
        if (resetSessionBeforeLaunch || (intent === 'register' && !registrationSessionReset)) {
          recordAuthTransition('ACCOUNT_SWITCH_REQUESTED', 'SESSION_RECOVERY', provider.id);
          const logoutPath = await requestKeycloakLogout(
            intent === 'register' ? 'REGISTRATION' : 'ACCOUNT_SWITCH',
            intent === 'register' && (provider.id === 'GOOGLE' || provider.id === 'FACEBOOK') ? provider.id : undefined
          );
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
    },
    [callbackUrl, intent, navigate, resetSessionBeforeLaunch]
  );

  useEffect(() => {
    if (resumedProvider.current) return;
    const currentParameters = new URLSearchParams(window.location.search);
    const currentProvider =
      currentParameters.get('sessionReset') === '1' &&
      (currentParameters.get('provider') === 'GOOGLE' || currentParameters.get('provider') === 'FACEBOOK')
        ? (currentParameters.get('provider') as 'GOOGLE' | 'FACEBOOK')
        : undefined;
    const provider = orderedProviders.find((candidate) => candidate.id === (resumeProvider ?? currentProvider));
    if (!provider) return;
    resumedProvider.current = true;
    void begin(provider, true);
  }, [begin, orderedProviders, resumeProvider]);

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
              onClick={() => void begin(provider)}
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
    </div>
  );
}
