import { routeAfterAuthentication, type AuthenticationIntent } from './post-auth-router';

describe('post-authentication router', () => {
  it('never turns Login into registration', () => {
    expect(
      routeAfterAuthentication({
        intent: 'LOGIN',
        returnRoute: 'HOME',
        membershipCount: 0,
        selectedMembershipValid: false,
        onboardingComplete: false,
        recoveryRequired: false,
      })
    ).toEqual({ route: 'AUTHENTICATED_VISITOR', returnRoute: 'HOME' });
  });

  it.each<AuthenticationIntent>(['REGISTER', 'TRIAL', 'HIRE'])(
    'resumes only an explicit %s intent through onboarding',
    (intent) => {
      expect(
        routeAfterAuthentication({
          intent,
          returnRoute: 'MARKETPLACE',
          membershipCount: 0,
          selectedMembershipValid: false,
          onboardingComplete: false,
          recoveryRequired: false,
        })
      ).toEqual({
        route: 'ONBOARDING_REQUIRED',
        returnRoute: 'MARKETPLACE',
        resumeIntent: intent,
      });
    }
  );

  it('requires selection for many current memberships', () => {
    expect(
      routeAfterAuthentication({
        intent: 'LOGIN',
        returnRoute: 'HOME',
        membershipCount: 2,
        selectedMembershipValid: false,
        onboardingComplete: true,
        recoveryRequired: false,
      }).route
    ).toBe('TENANT_SELECTION_REQUIRED');
  });

  it('routes one validated membership to the safe target', () => {
    expect(
      routeAfterAuthentication({
        intent: 'LOGIN',
        returnRoute: 'MY_PROFESSIONALS',
        membershipCount: 1,
        selectedMembershipValid: true,
        onboardingComplete: true,
        recoveryRequired: false,
      })
    ).toEqual({ route: 'READY', returnRoute: 'MY_PROFESSIONALS' });
  });

  it('makes recovery and terminal failures deterministic', () => {
    expect(
      routeAfterAuthentication({
        intent: 'LOGIN',
        returnRoute: 'SETTINGS',
        membershipCount: 1,
        selectedMembershipValid: true,
        onboardingComplete: true,
        recoveryRequired: true,
      }).route
    ).toBe('RECOVERY_REQUIRED');
    expect(
      routeAfterAuthentication({
        intent: 'LOGIN',
        returnRoute: 'SETTINGS',
        membershipCount: 101,
        selectedMembershipValid: true,
        onboardingComplete: true,
        recoveryRequired: false,
      })
    ).toMatchObject({ route: 'TERMINAL_FAILURE', failureCode: 'IDENTITY_ACTION_DENIED' });
  });
});
