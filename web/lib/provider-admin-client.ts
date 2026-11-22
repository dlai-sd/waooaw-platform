// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

export type ProviderCategory = 'PLATFORM_LLM' | 'AGENT_API';
export type TestAuthScheme = 'BEARER' | 'X_API_KEY' | 'X_GOOG_API_KEY' | 'HEADER';
export type TestOutcome = 'PASSED' | 'FAILED' | 'NOT_TESTABLE';

export type ProviderSummary = {
  id: string;
  providerName: string;
  displayName: string;
  category: ProviderCategory;
  agentTypeId: string | null;
  authMethod: string;
  hasTestEndpoint: boolean;
  active: boolean;
  credential: {
    status: 'NOT_SET' | 'ACTIVE';
    activeVersionNo: number | null;
    activatedAt: string | null;
    lastTestOutcome: TestOutcome | null;
  };
};

export type CredentialVersion = {
  versionId: string;
  versionNo: number;
  status: 'ACTIVE' | 'SUPERSEDED';
  createdAt: string;
  activatedAt: string | null;
  testOutcome: TestOutcome | null;
};

export type CredentialTestResult = {
  outcome: TestOutcome;
  detail: string;
  httpStatus?: number;
};
export type SavedVersion = {
  versionId: string;
  versionNo: number;
  status: string;
};

export type CreateProviderInput = {
  providerName: string;
  displayName: string;
  category: ProviderCategory;
  agentTypeId?: string;
  testUrl?: string;
  testAuthScheme?: TestAuthScheme;
  testAuthHeader?: string;
};

export type ProviderProblem = {
  code?: string;
  title?: string;
  status?: number;
  correlationId?: string;
};

export type ProviderResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; problem: ProviderProblem };

export const providerNamePattern = /^[a-z0-9-]{2,48}$/;

const problemMessages: Record<string, string> = {
  PROVIDER_FORBIDDEN: 'Only the Founder may manage provider credentials.',
  PROVIDER_STEP_UP_REQUIRED: 'Confirm your identity again with multi-factor sign-in, then enter the value again.',
  PROVIDER_INVALID: 'The request was not valid. Check the fields and try again. Nothing was saved.',
  PROVIDER_NOT_FOUND: 'That provider or version no longer exists.',
  PROVIDER_CONFLICT: 'That provider already exists or changed. Reload and try again.',
  PROVIDER_RATE_LIMITED: 'Too many changes in a minute. Wait and try again.',
  PROVIDER_VAULT_UNAVAILABLE: 'The secret store is unavailable. Nothing was saved. Try again shortly.',
};

export function problemText(problem: ProviderProblem): string {
  return problemMessages[problem.code ?? ''] ?? problemMessages.PROVIDER_VAULT_UNAVAILABLE;
}

export const categoryHeadings: Record<ProviderCategory, string> = {
  PLATFORM_LLM: 'Platform APIs (LLM etc.)',
  AGENT_API: 'Agent APIs',
};

export function credentialLabel(provider: ProviderSummary): string {
  const { status, activeVersionNo } = provider.credential;
  return status === 'ACTIVE' ? `Active v${activeVersionNo ?? '?'}` : 'Not set';
}

export const outcomeLabel: Record<TestOutcome, string> = {
  PASSED: 'Test passed',
  FAILED: 'Test failed',
  NOT_TESTABLE: 'Cannot be tested',
};
