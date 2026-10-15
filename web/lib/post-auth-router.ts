export type AuthenticationIntent = 'LOGIN' | 'REGISTER' | 'TRIAL' | 'HIRE';
export type AuthenticationRoute =
  | 'READY'
  | 'AUTHENTICATED_VISITOR'
  | 'ONBOARDING_REQUIRED'
  | 'TENANT_SELECTION_REQUIRED'
  | 'RECOVERY_REQUIRED'
  | 'TERMINAL_FAILURE';
export type SafeReturnRoute = 'HOME' | 'MARKETPLACE' | 'MY_PROFESSIONALS' | 'SETTINGS';

export interface PostAuthenticationInput {
  intent: AuthenticationIntent;
  returnRoute: SafeReturnRoute;
  membershipCount: number;
  selectedMembershipValid: boolean;
  onboardingComplete: boolean;
  recoveryRequired: boolean;
  terminalFailure?: 'IDENTITY_ACTION_DENIED' | 'IDENTITY_DEPENDENCY_UNAVAILABLE';
}

export interface PostAuthenticationDecision {
  route: AuthenticationRoute;
  returnRoute: SafeReturnRoute;
  resumeIntent?: Exclude<AuthenticationIntent, 'LOGIN'>;
  failureCode?: PostAuthenticationInput['terminalFailure'];
}

export function routeAfterAuthentication(input: PostAuthenticationInput): PostAuthenticationDecision {
  if (!Number.isInteger(input.membershipCount) || input.membershipCount < 0 || input.membershipCount > 100)
    return {
      route: 'TERMINAL_FAILURE',
      returnRoute: input.returnRoute,
      failureCode: 'IDENTITY_ACTION_DENIED',
    };
  if (input.terminalFailure)
    return {
      route: 'TERMINAL_FAILURE',
      returnRoute: input.returnRoute,
      failureCode: input.terminalFailure,
    };
  if (input.recoveryRequired) return { route: 'RECOVERY_REQUIRED', returnRoute: input.returnRoute };
  if (!input.onboardingComplete || input.membershipCount === 0) {
    if (input.intent === 'LOGIN') return { route: 'AUTHENTICATED_VISITOR', returnRoute: input.returnRoute };
    return {
      route: 'ONBOARDING_REQUIRED',
      returnRoute: input.returnRoute,
      resumeIntent: input.intent,
    };
  }
  if (input.membershipCount > 1 && !input.selectedMembershipValid)
    return { route: 'TENANT_SELECTION_REQUIRED', returnRoute: input.returnRoute };
  if (!input.selectedMembershipValid)
    return {
      route: 'TERMINAL_FAILURE',
      returnRoute: input.returnRoute,
      failureCode: 'IDENTITY_ACTION_DENIED',
    };
  return { route: 'READY', returnRoute: input.returnRoute };
}
