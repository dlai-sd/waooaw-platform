// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R005, WC149-R010
// Constitutional basis: C-023, C-059, C-063, C-083

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { fakeResponse } from '@/lib/pricing-admin-test-data';
import { fallbackProvidersFrom, type ProviderSummary } from '@/lib/provider-admin-client';
import { savePendingStepUp } from '@/lib/step-up-resume';
import { ProviderPanel } from './ProviderPanel';
import { ProviderTestAnswer } from './ProviderTestAnswer';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

function summary(providerName: string, displayName: string, active = true): ProviderSummary {
  return {
    id: `id-${providerName}`,
    providerName,
    displayName,
    category: 'PLATFORM_LLM',
    agentTypeId: null,
    authMethod: 'API_KEY',
    hasTestEndpoint: true,
    active: true,
    credential: {
      status: active ? 'ACTIVE' : 'NOT_SET',
      activeVersionNo: active ? 1 : null,
      activatedAt: null,
      lastTestOutcome: null,
    },
  };
}

const sarvam = summary('sarvam', 'Sarvam');
const openai = summary('openai', 'OpenAI');
const originalFetch = global.fetch;

function serve(response: Response) {
  const fetchMock = jest.fn(async () => response);
  global.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
  window.sessionStorage.clear();
});

test('offers only other LLM providers with an active credential as fallbacks', () => {
  const providers = [
    sarvam,
    openai,
    summary('anthropic', 'Anthropic'),
    summary('google', 'Google'),
    summary('meta', 'Meta'),
    summary('whatsapp', 'WhatsApp'),
    summary('mistral', 'Mistral', false),
  ];
  providers[3] = summary('google', 'Google', false);
  expect(fallbackProvidersFrom(providers, sarvam.id).map((entry) => entry.providerName)).toEqual([
    'openai',
    'anthropic',
  ]);
  providers[3] = summary('google', 'Google');
  expect(fallbackProvidersFrom(providers, sarvam.id).map((entry) => entry.providerName)).toEqual([
    'openai',
    'anthropic',
    'google',
  ]);
});

test('shows the answer, who answered, the reported model, tokens, latency and plain-language skip reasons', async () => {
  const fetchMock = serve(
    fakeResponse(200, {
      answered: {
        provider: 'openai',
        model: 'gpt-x',
        reportedModel: 'gpt-x-2027',
        text: 'Four.',
        inputTokens: 12,
        outputTokens: 3,
        latencyMs: 640,
      },
      attempts: [
        { provider: 'sarvam', outcome: 'SKIPPED', reason: 'KEY_REJECTED' },
        { provider: 'openai', outcome: 'ANSWERED', reason: null },
      ],
    })
  );
  render(<ProviderTestAnswer fallbackCandidates={[openai]} provider={sarvam} />);

  fireEvent.click(screen.getByLabelText('OpenAI'));
  fireEvent.change(screen.getByLabelText('Model (optional)'), { target: { value: ' gpt-x ' } });
  fireEvent.click(screen.getByRole('button', { name: 'Test answer' }));

  await screen.findByText('openai answered.');
  expect(screen.getByText('Four.')).toBeInTheDocument();
  expect(screen.getByText('gpt-x-2027')).toBeInTheDocument();
  expect(screen.getByText('12 tokens')).toBeInTheDocument();
  expect(screen.getByText('3 tokens')).toBeInTheDocument();
  expect(screen.getByText('640 ms')).toBeInTheDocument();
  expect(screen.getByText(/skipped because the provider rejected the saved key/)).toBeInTheDocument();
  const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe('/api/admin/providers/sarvam/test-answer');
  expect(JSON.parse(String(init.body))).toEqual({ model: 'gpt-x', fallbackProviders: ['openai'] });
});

test('says no provider answered and explains every skip reason', async () => {
  serve(
    fakeResponse(200, {
      answered: null,
      attempts: [
        { provider: 'sarvam', outcome: 'SKIPPED', reason: 'KEY_MISSING' },
        { provider: 'openai', outcome: 'SKIPPED', reason: 'TIMEOUT' },
        { provider: 'anthropic', outcome: 'SKIPPED', reason: 'PROVIDER_ERROR' },
        { provider: 'gemini', outcome: 'SKIPPED', reason: 'UNSUPPORTED' },
        { provider: 'meta', outcome: 'SKIPPED', reason: 'SOMETHING_NEW' },
      ],
    })
  );
  render(<ProviderTestAnswer fallbackCandidates={[]} provider={sarvam} />);

  fireEvent.click(screen.getByRole('button', { name: 'Test answer' }));

  await screen.findByText('No provider answered.');
  expect(screen.getByText(/no key is saved for this provider/)).toBeInTheDocument();
  expect(screen.getByText(/did not answer in time/)).toBeInTheDocument();
  expect(screen.getByText(/returned an error/)).toBeInTheDocument();
  expect(screen.getByText(/cannot answer text requests/)).toBeInTheDocument();
  expect(screen.getByText(/the provider could not answer/)).toBeInTheDocument();
  expect(screen.queryByText(/SOMETHING_NEW/)).not.toBeInTheDocument();
  expect(screen.queryByLabelText('OpenAI')).not.toBeInTheDocument();
});

test('a missing step-up offers the multi-factor sign-in and the probe outage is explained', async () => {
  serve(fakeResponse(403, { code: 'PROVIDER_STEP_UP_REQUIRED' }));
  render(<ProviderTestAnswer fallbackCandidates={[]} provider={sarvam} />);

  fireEvent.click(screen.getByRole('button', { name: 'Test answer' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Confirm with multi-factor sign-in' }));

  expect(signIn).toHaveBeenCalledWith(
    'keycloak',
    expect.objectContaining({ waooawIntent: 'LOGIN' }),
    expect.objectContaining({ max_age: '0' })
  );

  serve(fakeResponse(503, { code: 'PROVIDER_PROBE_UNAVAILABLE' }));
  fireEvent.click(screen.getByRole('button', { name: 'Test answer' }));
  await screen.findByText(/provider test is unavailable right now/);
  expect(screen.queryByRole('button', { name: 'Confirm with multi-factor sign-in' })).not.toBeInTheDocument();
});

test('after the step-up it restores the choices and asks again once on its own', async () => {
  savePendingStepUp('providers.answer.id-sarvam', {
    providerId: 'id-sarvam',
    model: 'gpt-x',
    fallbacks: ['openai', 'not-a-candidate'],
  });
  const fetchMock = serve(
    fakeResponse(200, {
      answered: { provider: 'openai', model: 'gpt-x', text: 'Four.' },
      attempts: [],
    })
  );
  const { unmount } = render(<ProviderTestAnswer fallbackCandidates={[openai]} provider={sarvam} />);

  expect(await screen.findByText('openai answered.')).toBeInTheDocument();
  expect(screen.getByLabelText('Model (optional)')).toHaveValue('gpt-x');
  expect(screen.getByLabelText('OpenAI')).toBeChecked();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  expect(JSON.parse(String(init.body))).toEqual({ model: 'gpt-x', fallbackProviders: ['openai'] });
  unmount();

  render(<ProviderTestAnswer fallbackCandidates={[openai]} provider={sarvam} />);
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test('the step-up remembers the model and fallbacks chosen', async () => {
  serve(fakeResponse(403, { code: 'PROVIDER_STEP_UP_REQUIRED' }));
  render(<ProviderTestAnswer fallbackCandidates={[openai]} provider={sarvam} />);
  fireEvent.click(screen.getByLabelText('OpenAI'));
  fireEvent.change(screen.getByLabelText('Model (optional)'), { target: { value: 'gpt-x' } });
  fireEvent.click(screen.getByRole('button', { name: 'Test answer' }));

  fireEvent.click(await screen.findByRole('button', { name: 'Confirm with multi-factor sign-in' }));

  const remembered = window.sessionStorage.getItem('waooaw.step-up.providers.answer.id-sarvam') ?? '';
  expect(JSON.parse(remembered).payload).toEqual({ providerId: 'id-sarvam', model: 'gpt-x', fallbacks: ['openai'] });
});

test('the panel offers Test answer only with a saved credential and lists other saved providers as fallbacks', async () => {
  global.fetch = jest.fn(async () => fakeResponse(200, [])) as unknown as typeof fetch;
  const { unmount } = render(
    <ProviderPanel fallbackCandidates={[openai]} focusOnMount={false} onChanged={jest.fn()} provider={sarvam} />
  );
  expect(screen.getByRole('button', { name: 'Test answer' })).toBeInTheDocument();
  expect(screen.getByLabelText('OpenAI')).toBeInTheDocument();
  expect(screen.getByTestId('provider-value-format')).toHaveTextContent(/validation response as proof/);
  await waitFor(() => expect(screen.getByText(/No value has been saved/)).toBeInTheDocument());
  unmount();

  render(<ProviderPanel focusOnMount={false} onChanged={jest.fn()} provider={summary('meta', 'Meta', false)} />);
  expect(screen.queryByRole('button', { name: 'Test answer' })).not.toBeInTheDocument();
  expect(screen.getByTestId('provider-value-format')).toHaveTextContent('{"appId":"...","appSecret":"..."}');
  await waitFor(() => expect(screen.getByText(/No value has been saved/)).toBeInTheDocument());
});
