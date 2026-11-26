// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { fakeResponse } from '@/lib/pricing-admin-test-data';
import type { ProviderSummary } from '@/lib/provider-admin-client';
import { ProvidersWorkspace } from './ProvidersWorkspace';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const originalFetch = global.fetch;

function provider(overrides: Partial<ProviderSummary> & { id: string; providerName: string }): ProviderSummary {
  return {
    displayName: overrides.providerName,
    category: 'PLATFORM_LLM',
    agentTypeId: null,
    authMethod: 'API_KEY',
    hasTestEndpoint: true,
    active: true,
    credential: {
      status: 'NOT_SET',
      activeVersionNo: null,
      activatedAt: null,
      lastTestOutcome: null,
    },
    ...overrides,
  };
}

const openai = provider({
  id: 'p1',
  providerName: 'openai',
  displayName: 'OpenAI',
});
const sarvam = provider({
  id: 'p2',
  providerName: 'sarvam',
  displayName: 'Sarvam',
  credential: {
    status: 'ACTIVE',
    activeVersionNo: 4,
    activatedAt: '2027-01-01T00:00:00Z',
    lastTestOutcome: 'PASSED',
  },
});
const search = provider({
  id: 'p3',
  providerName: 'acme-search',
  displayName: 'Acme Search',
  category: 'AGENT_API',
  agentTypeId: 'dma',
  active: false,
  credential: {
    status: 'ACTIVE',
    activeVersionNo: 1,
    activatedAt: null,
    lastTestOutcome: 'FAILED',
  },
});

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
});

test('providers are grouped as platform APIs and agent APIs with status chips', () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, []));
  render(<ProvidersWorkspace initialProviders={[openai, sarvam, search]} />);

  const platform = screen.getByRole('region', {
    name: 'Platform APIs (LLM etc.)',
  });
  const agents = screen.getByRole('region', { name: 'Agent APIs' });

  expect(within(platform).getByRole('button', { name: /OpenAI/ })).toHaveTextContent('Not set');
  expect(within(platform).getByRole('button', { name: /Sarvam/ })).toHaveTextContent('Active v4');
  expect(within(platform).getByRole('button', { name: /Sarvam/ })).toHaveTextContent('Test passed');
  const agent = within(agents).getByRole('button', { name: /Acme Search/ });
  expect(agent).toHaveTextContent('Active v1');
  expect(agent).toHaveTextContent('Test failed');
  expect(agent).toHaveTextContent('Inactive');
  expect(agent).toHaveTextContent('dma');
  expect(
    screen.getByText('Select a provider to test and save its value, or to roll back to an earlier version.')
  ).toBeVisible();
});

test('an empty registry says so and an empty group points to Add provider', () => {
  render(<ProvidersWorkspace initialProviders={[]} />);

  expect(screen.getByText('No providers are registered yet. Add one to get started.')).toBeVisible();
  expect(screen.getAllByText('No providers here yet. Use Add provider below.')).toHaveLength(2);
});

test('selecting a provider opens its own page with a way back, and moves focus to it', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, []));
  render(<ProvidersWorkspace initialProviders={[openai, sarvam]} />);

  fireEvent.click(screen.getByRole('button', { name: /Sarvam/ }));

  const heading = await screen.findByRole('heading', {
    level: 2,
    name: 'Sarvam',
  });
  expect(heading).toHaveFocus();
  expect(screen.queryByRole('button', { name: /OpenAI/ })).not.toBeInTheDocument();
  await screen.findByText('No value has been saved for this provider yet.');

  fireEvent.click(screen.getByRole('button', { name: 'Providers' }));
  expect(screen.getByRole('button', { name: /OpenAI/ })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Sarvam/ })).toBeInTheDocument();
});

test('a saved value refreshes the list so the chip shows the new version', async () => {
  const saved = fakeResponse(201, {
    versionId: 'v',
    versionNo: 1,
    status: 'ACTIVE',
  });
  const refreshed = [
    {
      ...openai,
      credential: {
        ...openai.credential,
        status: 'ACTIVE',
        activeVersionNo: 1,
      },
    },
    sarvam,
  ];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (method === 'POST' && url.endsWith('/test')) return fakeResponse(200, { outcome: 'PASSED', detail: 'ok' });
    if (method === 'POST') return saved;
    if (url.endsWith('/credentials')) return fakeResponse(200, []);
    return fakeResponse(200, refreshed);
  }) as typeof fetch;
  render(<ProvidersWorkspace initialProviders={[openai, sarvam]} />);
  fireEvent.click(screen.getByRole('button', { name: /OpenAI/ }));
  fireEvent.change(await screen.findByLabelText('API key or secret value'), {
    target: { value: 'k-123' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Test' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirm and save' })).toBeEnabled());

  fireEvent.click(screen.getByRole('button', { name: 'Confirm and save' }));

  await waitFor(() => expect(screen.getAllByText('Active v1').length).toBeGreaterThan(0));
  fireEvent.click(screen.getByRole('button', { name: 'Providers' }));
  await waitFor(() => expect(screen.getByRole('button', { name: /OpenAI/ })).toHaveTextContent('Active v1'));
});

test('a refresh that fails is reported without losing the list', async () => {
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (method === 'POST' && url.endsWith('/test')) return fakeResponse(200, { outcome: 'PASSED', detail: 'ok' });
    if (method === 'POST')
      return fakeResponse(201, {
        versionId: 'v',
        versionNo: 1,
        status: 'ACTIVE',
      });
    if (url.endsWith('/credentials')) return fakeResponse(200, []);
    return fakeResponse(503, { code: 'PROVIDER_VAULT_UNAVAILABLE' });
  }) as typeof fetch;
  render(<ProvidersWorkspace initialProviders={[openai]} />);
  fireEvent.click(screen.getByRole('button', { name: /OpenAI/ }));
  fireEvent.change(await screen.findByLabelText('API key or secret value'), {
    target: { value: 'k-123' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Test' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirm and save' })).toBeEnabled());

  fireEvent.click(screen.getByRole('button', { name: 'Confirm and save' }));

  expect(await screen.findByText(/The provider list could not be refreshed\./)).toHaveAttribute('role', 'alert');
  fireEvent.click(screen.getByRole('button', { name: 'Providers' }));
  expect(screen.getByRole('button', { name: /OpenAI/ })).toBeInTheDocument();
});

test('a created provider joins its group and is opened for a value', async () => {
  const created = provider({
    id: 'p9',
    providerName: 'acme-maps',
    displayName: 'Acme Maps',
    category: 'AGENT_API',
  });
  global.fetch = jest.fn(async (_input: RequestInfo | URL, init?: RequestInit) =>
    init?.method === 'POST' ? fakeResponse(201, created) : fakeResponse(200, [])
  ) as typeof fetch;
  render(<ProvidersWorkspace initialProviders={[openai]} />);
  fireEvent.click(screen.getByRole('button', { name: 'Add provider' }));
  fireEvent.change(screen.getByLabelText('Provider name'), {
    target: { value: 'acme-maps' },
  });
  fireEvent.change(screen.getByLabelText('Display name'), {
    target: { value: 'Acme Maps' },
  });
  fireEvent.change(screen.getByLabelText('Category'), {
    target: { value: 'AGENT_API' },
  });

  fireEvent.click(screen.getByRole('button', { name: 'Create provider' }));

  const heading = await screen.findByRole('heading', {
    level: 2,
    name: 'Acme Maps',
  });
  expect(heading).toHaveFocus();
  fireEvent.click(screen.getByRole('button', { name: 'Providers' }));
  const agents = screen.getByRole('region', { name: 'Agent APIs' });
  expect(within(agents).getByRole('button', { name: /Acme Maps/ })).toBeInTheDocument();
});
